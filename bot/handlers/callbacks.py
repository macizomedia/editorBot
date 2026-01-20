from __future__ import annotations

import logging

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes

from bot.state.machine import handle_event, EventType
from bot.state.runtime import get_conversation, save_conversation

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


def _soundtrack_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Sin música", callback_data="music:none"),
                InlineKeyboardButton("Lofi 1", callback_data="music:lofi1"),
            ],
            [
                InlineKeyboardButton("Lofi 2", callback_data="music:lofi2"),
                InlineKeyboardButton("Corporate 1", callback_data="music:corp1"),
            ],
        ]
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.callback_query:
        return

    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id if query.message else None
    if chat_id is None:
        return

    convo = get_conversation(chat_id)
    data = query.data or ""

    try:
        if data.startswith("template:"):
            template_id = data.split(":", 1)[1]
            convo = handle_event(convo, EventType.TEMPLATE_SELECTED, template_id)
            save_conversation(chat_id, convo)
            await query.message.reply_text(
                "🎵 Selecciona un soundtrack:", reply_markup=_soundtrack_keyboard()
            )
            return

        if data.startswith("music:"):
            soundtrack_id = data.split(":", 1)[1]
            convo = handle_event(convo, EventType.SOUNDTRACK_SELECTED, soundtrack_id)
            save_conversation(chat_id, convo)
            await query.message.reply_text(
                "✅ Selección guardada. Listo para pasar a la etapa de video."
            )
            return

    except Exception:
        logger.exception("Error handling callback")
        await query.message.reply_text("⚠️ Ocurrió un error. Intenta de nuevo.")
