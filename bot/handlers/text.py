import logging
from datetime import datetime, UTC

from telegram import Update
from telegram.ext import ContextTypes

from bot.graph.state import ConversationMessage, create_initial_state
from bot.handlers.commands import get_graph

logger = logging.getLogger(__name__)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        logger.warning("Received text update without message payload")
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("⚠️ El mensaje está vacío.")
        return

    try:
        graph = await get_graph()
        thread_id = f"{chat_id}:{user_id}"
        state = await graph.get_state(thread_id) or create_initial_state(chat_id, user_id)

        state["messages"].append(
            ConversationMessage(
                role="user",
                content=text,
                timestamp=datetime.now(UTC).isoformat(),
            )
        )

        prev_len = len(state["messages"])
        result = await graph.invoke(state, thread_id)

        new_messages = result["messages"][prev_len:]
        for msg in new_messages:
            if msg["role"] == "assistant":
                await update.message.reply_text(msg["content"])

    except Exception:
        logger.exception("Error handling text message")
        await update.message.reply_text("⚠️ Ocurrió un error. Intenta de nuevo.")
