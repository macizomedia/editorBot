"""
CLI entry point for EditorBot debugger.

Usage:
    python -m bot.cli                          # Interactive mode
    python -m bot.cli --verbose                # Interactive with verbose logs
    python -m bot.cli send-voice audio.wav     # Send voice message
    python -m bot.cli send-text "Hello"        # Send text message
    python -m bot.cli click "template:explainer" # Click button
    python -m bot.cli show-state               # Show current state
    python -m bot.cli reset                    # Reset to IDLE
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Ensure bot module is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot.cli.commands import CLICommands
from bot.logging import setup_logging


def setup_cli_logging(verbose: bool = False):
    """Setup logging for CLI mode."""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(level=level)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="EditorBot CLI Debugger - Test bot interactions from command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python -m bot.cli
  python -m bot.cli --verbose

  # Single commands
  python -m bot.cli send-voice sample.wav
  python -m bot.cli send-text "Hello world"
  python -m bot.cli click "template:explainer"
  python -m bot.cli show-state
  python -m bot.cli show-state --json
  python -m bot.cli reset
  python -m bot.cli inject-transcript "Hello world"

Interactive Commands:
  voice <path>        - Send voice message
  inject <text>       - Inject mock transcript (bypass Whisper)
  text <message>      - Send text message
  click <data>        - Click inline button
  state               - Show conversation state
  state --json        - Show state as JSON
  log on/off          - Toggle verbose logging
  reset               - Reset to IDLE
  exit                - Quit
        """
    )

    parser.add_argument(
        "command",
        nargs="?",
        choices=["send-voice", "inject-transcript", "send-text", "click", "show-state", "reset"],
        help="Command to execute (omit for interactive mode)"
    )
    parser.add_argument(
        "args",
        nargs="*",
        help="Command arguments"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging (show all JSON data)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (for show-state command)"
    )
    parser.add_argument(
        "--chat-id",
        type=int,
        default=12345,
        help="Chat ID to use (default: 12345)"
    )

    args = parser.parse_args()

    # Setup logging
    setup_cli_logging(verbose=args.verbose)

    # Create command handler
    cli = CLICommands(chat_id=args.chat_id, verbose=args.verbose)

    # Execute command or run interactive mode
    if args.command is None:
        # Interactive mode
        await cli.run_interactive()

    elif args.command == "send-voice":
        if not args.args:
            print("❌ Error: Missing audio file path")
            print("Usage: python -m bot.cli send-voice <path>")
            sys.exit(1)
        await cli.send_voice(args.args[0])

    elif args.command == "inject-transcript":
        if not args.args:
            print("❌ Error: Missing transcript text")
            print("Usage: python -m bot.cli inject-transcript <text>")
            sys.exit(1)
        transcript = " ".join(args.args)
        await cli.inject_transcript(transcript)

    elif args.command == "send-text":
        if not args.args:
            print("❌ Error: Missing message text")
            print("Usage: python -m bot.cli send-text <message>")
            sys.exit(1)
        message = " ".join(args.args)
        await cli.send_text(message)

    elif args.command == "click":
        if not args.args:
            print("❌ Error: Missing callback data")
            print("Usage: python -m bot.cli click <callback_data>")
            sys.exit(1)
        await cli.click_button(args.args[0])

    elif args.command == "show-state":
        cli.show_state(format_json=args.json)

    elif args.command == "reset":
        cli.reset()


if __name__ == "__main__":
    asyncio.run(main())
