"""Main entry point when running bot.cli as a module."""

from bot.cli.main import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
