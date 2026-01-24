"""
CLI command implementations.

Handles user commands and orchestrates bot interactions.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from bot.cli.simulator import TelegramSimulator
from bot.cli.inspector import StateInspector, print_separator, print_json
from bot.state.runtime import get_conversation, save_conversation
from bot.state.machine import handle_event, EventType

logger = logging.getLogger(__name__)


class CLICommands:
    """
    Executes CLI commands and manages bot interaction.
    """

    def __init__(self, chat_id: int = 12345, verbose: bool = False):
        self.chat_id = chat_id
        self.verbose = verbose
        self.simulator = TelegramSimulator(chat_id=chat_id)
        self.inspector = StateInspector()

    async def send_voice(self, audio_path: str) -> None:
        """
        Simulate sending a voice message.

        Args:
            audio_path: Path to audio file
        """
        # Lazy import to avoid loading dependencies until needed
        from bot.handlers.voice import handle_voice

        print(f"📤 Sending voice message: {audio_path}")

        # Check if file exists
        if not Path(audio_path).exists():
            print(f"❌ Error: File not found: {audio_path}")
            return

        # Create mock update and context
        update = self.simulator.create_voice_update(audio_path)
        context = self.simulator.create_context()

        # Log initial state
        if self.verbose:
            convo = get_conversation(self.chat_id)
            print_separator("BEFORE HANDLER")
            print(self.inspector.format_conversation(convo))

        # Call voice handler
        print_separator("PROCESSING")
        try:
            await handle_voice(update, context)
        except Exception as e:
            print(f"❌ Error in voice handler: {e}")
            if self.verbose:
                logger.exception("Voice handler error")
            return

        # Log final state
        print_separator("AFTER HANDLER")
        convo = get_conversation(self.chat_id)
        print(self.inspector.format_conversation(convo, verbose=self.verbose))

        if self.verbose and convo.transcript:
            print_json({"transcript": convo.transcript}, "Transcript JSON")

    async def inject_transcript(self, transcript: str) -> None:
        """
        Inject mock transcript directly (bypasses transcription).

        Useful for testing when Whisper is unavailable.

        Args:
            transcript: Text to use as transcript
        """
        from bot.state.machine import handle_event, EventType
        from bot.services.mediation import mediate_text

        print(f"💉 Injecting mock transcript: {transcript[:50]}...")

        convo = get_conversation(self.chat_id)

        # Log initial state
        if self.verbose:
            print_separator("BEFORE INJECTION")
            print(self.inspector.format_conversation(convo))

        print_separator("PROCESSING")

        # Step 1: Transition to AUDIO_RECEIVED
        convo = handle_event(convo, EventType.VOICE_RECEIVED)
        save_conversation(self.chat_id, convo)
        print("✅ State: AUDIO_RECEIVED")

        # Step 2: Add transcript and transition
        convo = handle_event(convo, EventType.TRANSCRIPTION_COMPLETE, transcript)
        save_conversation(self.chat_id, convo)
        print(f"✅ Transcript injected: {transcript[:100]}")

        # Step 3: Mediate
        print("🔄 Mediating text...")
        try:
            mediated = mediate_text(transcript)
        except RuntimeError as e:
            # If Gemini API key missing, use mock mediation
            if "GEMINI_API_KEY" in str(e):
                print(f"⚠️  {e}")
                print("📝 Using mock mediation (no LLM)")
                mediated = f"[MOCK MEDIATION] {transcript}"
            else:
                raise
        print(f"✅ Mediated: {mediated[:100]}")

        # Step 4: Transition to TEXT_RECEIVED
        convo = handle_event(convo, EventType.TEXT_RECEIVED, mediated)
        save_conversation(self.chat_id, convo)
        print("✅ State: TEXT_RECEIVED")

        # Show user message
        print("\n🤖 Bot Message:")
        print("✍️ Texto mediado (borrador):\n")
        print(f"{mediated}\n")
        print("Responde con:")
        print("- OK")
        print("- EDITAR (pegando texto)")
        print("- CANCELAR")

        # Log final state
        print_separator("AFTER INJECTION")
        convo = get_conversation(self.chat_id)
        print(self.inspector.format_conversation(convo, verbose=self.verbose))

    async def send_text(self, message: str) -> None:
        """
        Simulate sending a text message.

        Args:
            message: Text message content
        """
        # Lazy import
        from bot.handlers.text import handle_text

        print(f"📤 Sending text: {message}")

        # Create mock update and context
        update = self.simulator.create_text_update(message)
        context = self.simulator.create_context()

        # Log initial state
        if self.verbose:
            convo = get_conversation(self.chat_id)
            print_separator("BEFORE HANDLER")
            print(self.inspector.format_conversation(convo))

        # Call text handler
        print_separator("PROCESSING")
        try:
            await handle_text(update, context)
        except Exception as e:
            print(f"❌ Error in text handler: {e}")
            if self.verbose:
                logger.exception("Text handler error")
            return

        # Log final state
        print_separator("AFTER HANDLER")
        convo = get_conversation(self.chat_id)
        print(self.inspector.format_conversation(convo, verbose=self.verbose))

    async def click_button(self, callback_data: str) -> None:
        """
        Simulate clicking an inline keyboard button.

        Args:
            callback_data: Button callback data (e.g., "template:explainer")
        """
        # Lazy import
        from bot.handlers.callbacks import handle_callback

        print(f"🖱️  Clicking button: {callback_data}")

        # Create mock update and context
        update = self.simulator.create_callback_update(callback_data)
        context = self.simulator.create_context()

        # Log initial state
        if self.verbose:
            convo = get_conversation(self.chat_id)
            print_separator("BEFORE HANDLER")
            print(self.inspector.format_conversation(convo))

        # Call callback handler
        print_separator("PROCESSING")
        try:
            await handle_callback(update, context)
        except Exception as e:
            print(f"❌ Error in callback handler: {e}")
            if self.verbose:
                logger.exception("Callback handler error")
            return

        # Log final state
        print_separator("AFTER HANDLER")
        convo = get_conversation(self.chat_id)
        print(self.inspector.format_conversation(convo, verbose=self.verbose))

        # Show render plan if generated
        if self.verbose and convo.render_plan:
            print_separator("RENDER PLAN")
            print(self.inspector.format_render_plan(convo.render_plan))
            print_json(convo.render_plan, "Full Render Plan JSON")

    def show_state(self, format_json: bool = False) -> None:
        """
        Display current conversation state.

        Args:
            format_json: If True, output as JSON instead of formatted text
        """
        convo = get_conversation(self.chat_id)

        if format_json:
            # Convert to dict for JSON output
            state_dict = {
                "state": convo.state.value,
                "transcript": convo.transcript,
                "mediated_text": convo.mediated_text,
                "script_draft": convo.script_draft,
                "final_script": convo.final_script,
                "template_id": convo.template_id,
                "soundtrack_id": convo.soundtrack_id,
                "render_plan": convo.render_plan,
            }
            print_json(state_dict, "Conversation State")
        else:
            print(self.inspector.format_conversation(convo, verbose=self.verbose))

    def reset(self) -> None:
        """Reset conversation to IDLE state."""
        from bot.state.models import Conversation, BotState

        print("🔄 Resetting conversation to IDLE...")
        convo = Conversation(state=BotState.IDLE)
        save_conversation(self.chat_id, convo)
        print("✅ Reset complete")

    async def run_interactive(self) -> None:
        """
        Run interactive CLI mode with REPL.
        """
        print("╔══════════════════════════════════════════╗")
        print("║      EditorBot CLI Debugger v0.1         ║")
        print("╚══════════════════════════════════════════╝")
        print(f"\nChat ID: {self.chat_id}")
        print(f"Verbose: {'ON' if self.verbose else 'OFF'}")
        print("\nCommands:")
        print("  voice <path>     - Send voice message")
        print("  inject <text>    - Inject mock transcript (bypass Whisper)")
        print("  text <message>   - Send text message")
        print("  click <data>     - Click inline button")
        print("  state            - Show conversation state")
        print("  state --json     - Show state as JSON")
        print("  log on/off       - Toggle verbose logging")
        print("  reset            - Reset to IDLE")
        print("  help             - Show this help")
        print("  exit             - Quit")
        print()

        while True:
            try:
                # Prompt
                convo = get_conversation(self.chat_id)
                prompt = f"[{convo.state.value}] > "
                user_input = input(prompt).strip()

                if not user_input:
                    continue

                # Parse command
                parts = user_input.split(maxsplit=1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""

                # Execute command
                if command == "exit":
                    print("👋 Goodbye!")
                    break
                elif command == "help":
                    continue  # Help already shown above
                elif command == "voice":
                    if not args:
                        print("❌ Usage: voice <path>")
                        continue
                    await self.send_voice(args)
                elif command == "inject":
                    if not args:
                        print("❌ Usage: inject <text>")
                        continue
                    await self.inject_transcript(args)
                elif command == "text":
                    if not args:
                        print("❌ Usage: text <message>")
                        continue
                    await self.send_text(args)
                elif command == "click":
                    if not args:
                        print("❌ Usage: click <callback_data>")
                        continue
                    await self.click_button(args)
                elif command == "state":
                    format_json = args == "--json"
                    self.show_state(format_json=format_json)
                elif command == "log":
                    if args == "on":
                        self.verbose = True
                        print("✅ Verbose logging enabled")
                    elif args == "off":
                        self.verbose = False
                        print("✅ Verbose logging disabled")
                    else:
                        print("❌ Usage: log on/off")
                elif command == "reset":
                    self.reset()
                else:
                    print(f"❌ Unknown command: {command}")
                    print("Type 'help' for available commands")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                if self.verbose:
                    logger.exception("CLI error")
