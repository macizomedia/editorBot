import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.state.machine import handle_event, EventType
from bot.state.runtime import get_conversation, save_conversation

logger = logging.getLogger(__name__)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        logger.warning("Received text update without message payload")
        return

    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("⚠️ El mensaje está vacío.")
        return

    convo = get_conversation(chat_id)

    try:
        if text.upper() == "OK":
            convo = handle_event(convo, EventType.COMMAND_OK)

            await update.message.reply_text(
                "✅ Texto confirmado. Continuamos."
            )

        elif text.upper() == "CANCELAR":
            convo = handle_event(convo, EventType.COMMAND_CANCELAR)

            await update.message.reply_text(
                "❌ Proceso cancelado."
            )
        elif text.upper() == "EDITAR":
            convo = handle_event(convo, EventType.COMMAND_EDITAR)
            await update.message.reply_text(
                "✏️ Pega el texto editado a continuación."
            )


        else:
            convo = handle_event(convo, EventType.TEXT_RECEIVED, text)

            await update.message.reply_text(
                "✍️ Texto recibido.\nPuedes editarlo o responder OK."
            )

        save_conversation(chat_id, convo)

    except Exception:
        logger.exception("Error handling text message")
        await update.message.reply_text("⚠️ Ocurrió un error. Intenta de nuevo.")

