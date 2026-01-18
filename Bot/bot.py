import os
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
)

from bot.handlers.voice import handle_voice
from bot.handlers.text import handle_text


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Bot running…")
    app.run_polling()


if __name__ == "__main__":
    main()

