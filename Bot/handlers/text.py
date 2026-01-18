from telegram import Update
from telegram.ext import ContextTypes

from bot.state.machine import handle_event, EventType
from bot.state.runtime import get_conversation, save_conversation


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

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
            await update.message.reply_text(
                 "✏️ Pega el texto editado a continuación."
            )


        else:
            convo = handle_event(convo, EventType.TEXT_RECEIVED, text)

            await update.message.reply_text(
                "✍️ Texto recibido.\nPuedes editarlo o responder OK."
            )

        save_conversation(chat_id, convo)

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

