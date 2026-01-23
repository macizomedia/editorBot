import logging
import os
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from bot.handlers.voice import handle_voice
from bot.handlers.text import handle_text
from bot.handlers.callbacks import handle_callback
from bot.logging import setup_logging


def _configure_logging() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.INFO)


def main() -> None:
    setup_logging()
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.getLogger().setLevel(level)
    _configure_logging()
    logger = logging.getLogger(__name__)
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot running")
    app.run_polling()


if __name__ == "__main__":
    main()

