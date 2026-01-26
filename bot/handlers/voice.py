import logging
import tempfile
import asyncio
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, UTC

from telegram import Update
from telegram.ext import ContextTypes

from bot.graph.state import ConversationMessage, create_initial_state
from bot.handlers.commands import get_graph
from bot.services.transcription import transcribe_audio
from bot.services.mediation import mediate_text

logger = logging.getLogger(__name__)

# S3 configuration
S3_BUCKET = "content-pipeline"
S3_AUDIO_PREFIX = "audio"


def save_audio_to_s3(local_path: str, chat_id: int) -> str:
    """Save audio file to S3 and return the S3 path."""
    try:
        s3_client = boto3.client("s3")
        s3_key = f"{S3_AUDIO_PREFIX}/{chat_id}/narration.wav"

        s3_client.upload_file(
            local_path,
            S3_BUCKET,
            s3_key,
            ExtraArgs={"ContentType": "audio/wav"}
        )

        s3_path = f"s3://{S3_BUCKET}/{s3_key}"
        logger.info(
            "audio_saved_to_s3",
            extra={
                "chat_id": chat_id,
                "s3_path": s3_path,
            }
        )
        return s3_path
    except ClientError as e:
        logger.exception(f"Failed to save audio to S3 for chat {chat_id}: {e}")
        raise


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.voice:
        logger.warning("Received voice update without voice payload")
        return

    chat_id = update.effective_chat.id
    voice = update.message.voice

    logger.info(
        "voice_message_received",
        extra={
            "chat_id": chat_id,
            "duration_seconds": voice.duration,
            "file_size_bytes": voice.file_size,
            "mime_type": voice.mime_type,
        }
    )

    try:
        graph = await get_graph()
        thread_id = f"{chat_id}:{update.effective_user.id}"
        state = await graph.get_state(thread_id) or create_initial_state(chat_id, update.effective_user.id)

        # 1. Send user feedback
        await update.message.reply_text("🎤 Audio recibido. Transcribiendo...")

        # 3. Download voice file
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)

        with tempfile.NamedTemporaryFile(suffix=".ogg") as tmp:
            await file.download_to_drive(tmp.name)

            # Convert to WAV for consistency (rename since we already have .ogg)
            wav_path = tmp.name.replace(".ogg", ".wav")
            import shutil
            shutil.copy(tmp.name, wav_path)

            # 4. Transcribe (run in thread)
            transcript = await asyncio.to_thread(transcribe_audio, tmp.name)

            logger.info(
                "transcription_complete",
                extra={
                    "chat_id": chat_id,
                    "transcript_length": len(transcript),
                    "transcript_preview": transcript[:100] if transcript else None,
                    "success": not (transcript.startswith("[Error") or transcript.startswith("[No speech")),
                }
            )

            if transcript.startswith("[Error") or transcript.startswith("[No speech"):
                logger.warning(
                    "transcription_failed",
                    extra={"chat_id": chat_id, "error": transcript}
                )
                await update.message.reply_text(
                    "⚠️ No pude transcribir el audio. Intenta nuevamente."
                )
                return

            # 4b. Save audio to S3 for later use in render plan
            try:
                audio_s3_path = await asyncio.to_thread(save_audio_to_s3, wav_path, chat_id)
            except Exception as e:
                audio_s3_path = None
                logger.warning(f"Failed to save audio to S3, but continuing: {e}")

        # 5. Mediate (run in thread)
        mediated = await asyncio.to_thread(mediate_text, transcript)

        logger.info(
            "mediation_complete",
            extra={
                "chat_id": chat_id,
                "original_length": len(transcript),
                "mediated_length": len(mediated),
                "mediated_preview": mediated[:100] if mediated else None,
            }
        )

        state["transcript"] = transcript
        state["mediated_text"] = mediated
        state["audio_s3_path"] = audio_s3_path
        state["messages"].append(
            ConversationMessage(
                role="user",
                content=mediated,
                timestamp=datetime.now(UTC).isoformat(),
                metadata={"raw_transcript": transcript},
            )
        )

        prev_len = len(state["messages"])
        result = await graph.invoke(state, thread_id)
        new_messages = result["messages"][prev_len:]
        for msg in new_messages:
            if msg["role"] == "assistant":
                await update.message.reply_text(msg["content"])

    except Exception:
        logger.exception("Error handling voice message")
        await update.message.reply_text("⚠️ Ocurrió un error. Intenta de nuevo.")
