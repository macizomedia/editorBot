import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.state.machine import handle_event, EventType
from bot.state.models import BotState
from bot.state.runtime import get_conversation, save_conversation
from bot.services.script_generation import generate_script
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)


def _template_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Long", callback_data="template:long"),
                InlineKeyboardButton("Short", callback_data="template:short"),
            ],
            [
                InlineKeyboardButton("Reel", callback_data="template:reel"),
                InlineKeyboardButton("Slides", callback_data="template:slides"),
            ],
        ]
    )


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

            if convo.state == BotState.SCRIPT_DRAFTED:
                script_draft = generate_script(convo.mediated_text or "")
                convo.script_draft = script_draft
                save_conversation(chat_id, convo)
                await update.message.reply_text(
                    "📝 Guion (borrador):\n\n"
                    f"{script_draft}\n\n"
                    "Responde con:\n"
                    "- OK\n"
                    "- EDITAR (pegando texto)\n"
                    "- CANCELAR"
                )
            elif convo.state == BotState.FINAL_SCRIPT:
                convo = handle_event(convo, EventType.COMMAND_NEXT)
                save_conversation(chat_id, convo)
                await update.message.reply_text(
                    "✅ Guion final confirmado. Ahora elige un template:",
                    reply_markup=_template_keyboard(),
                )
            elif convo.state == BotState.SELECT_TEMPLATE:
                save_conversation(chat_id, convo)
                await update.message.reply_text("Selecciona un template con los botones.")
            else:
                await update.message.reply_text("✅ Texto confirmado. Continuamos.")

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

        elif text.upper() == "NEXT":
            convo = handle_event(convo, EventType.COMMAND_NEXT)
            await update.message.reply_text("Continuamos al siguiente paso.")


        else:
            convo = handle_event(convo, EventType.TEXT_RECEIVED, text)

            if convo.state == BotState.SCRIPT_DRAFTED:
                script_draft = generate_script(convo.mediated_text or "")
                convo.script_draft = script_draft
                save_conversation(chat_id, convo)
                await update.message.reply_text(
                    "📝 Guion (borrador):\n\n"
                    f"{script_draft}\n\n"
                    "Responde con:\n"
                    "- OK\n"
                    "- EDITAR (pegando texto)\n"
                    "- CANCELAR"
                )
            elif convo.state == BotState.FINAL_SCRIPT:
                convo = handle_event(convo, EventType.COMMAND_NEXT)
                save_conversation(chat_id, convo)
                await update.message.reply_text(
                    "✅ Guion final confirmado. Ahora elige un template:",
                    reply_markup=_template_keyboard(),
                )
            else:
                await update.message.reply_text(
                    "✍️ Texto recibido.\nPuedes editarlo o responder OK."
                )

        save_conversation(chat_id, convo)

    except Exception:
        logger.exception("Error handling text message")
        await update.message.reply_text("⚠️ Ocurrió un error. Intenta de nuevo.")

