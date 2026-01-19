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
    convo = get_conversation(chat_id)

    try:
        # 1. FSM: voice received
        convo = handle_event(convo, EventType.VOICE_RECEIVED)
        save_conversation(chat_id, convo)

        # 2. Download voice file
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)

        with tempfile.NamedTemporaryFile(suffix=".ogg") as tmp:
            await file.download_to_drive(tmp.name)

            # 3. Transcribe
            transcript = transcribe_audio(tmp.name)

            if transcript.startswith("[Error") or transcript.startswith("[No speech"):
                save_conversation(chat_id, Conversation())
                await update.message.reply_text(
                    "⚠️ No pude transcribir el audio. Intenta nuevamente."
                )
                return

        # 4. FSM: transcription ready
        convo = handle_event(convo, EventType.TEXT_RECEIVED, transcript)
        save_conversation(chat_id, convo)

        # 5. Mediate
        mediated = mediate_text(transcript)

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
