import logging
import tempfile
import boto3
from botocore.exceptions import ClientError

from telegram import Update
from telegram.ext import ContextTypes

from bot.state.machine import handle_event, EventType
from bot.state.models import Conversation
from bot.state.runtime import get_conversation, save_conversation
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

    convo = get_conversation(chat_id)

    try:
        # 1. FSM: voice received
        convo = handle_event(convo, EventType.VOICE_RECEIVED)
        save_conversation(chat_id, convo)

        # 2. Send user feedback
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

            # 4. Transcribe
            transcript = transcribe_audio(tmp.name)

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
                save_conversation(chat_id, Conversation())
                await update.message.reply_text(
                    "⚠️ No pude transcribir el audio. Intenta nuevamente."
                )
                return

            # 4b. Save audio to S3 for later use in render plan
            try:
                audio_s3_path = save_audio_to_s3(wav_path, chat_id)
                convo.audio_s3_path = audio_s3_path
            except Exception as e:
                logger.warning(f"Failed to save audio to S3, but continuing: {e}")

        # 5. FSM: transcription complete
        convo = handle_event(convo, EventType.TRANSCRIPTION_COMPLETE, transcript)
        save_conversation(chat_id, convo)

        # 5. Mediate
        mediated = mediate_text(transcript)

        logger.info(
            "mediation_complete",
            extra={
                "chat_id": chat_id,
                "original_length": len(transcript),
                "mediated_length": len(mediated),
                "mediated_preview": mediated[:100] if mediated else None,
            }
        )

        # 6. FSM: mediated text ready
        convo = handle_event(convo, EventType.TEXT_RECEIVED, mediated)
        save_conversation(chat_id, convo)

        # 7. Send to user
        await update.message.reply_text(
            "✍️ Texto mediado (borrador):\n\n"
            f"{mediated}\n\n"
            "Responde con:\n"
            "- OK\n"
            "- EDITAR (pegando texto)\n"
            "- CANCELAR"
        )

    except Exception:
        logger.exception("Error handling voice message")
        await update.message.reply_text("⚠️ Ocurrió un error. Intenta de nuevo.")
