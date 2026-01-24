import logging
import tempfile

from telegram import Update
from telegram.ext import ContextTypes

from bot.state.machine import handle_event, EventType
from bot.state.models import Conversation
from bot.state.runtime import get_conversation, save_conversation
from bot.services.transcription import transcribe_audio
from bot.services.mediation import mediate_text

logger = logging.getLogger(__name__)


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
