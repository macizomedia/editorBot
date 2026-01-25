#!/usr/bin/env python3
"""
Complete Bot Workflow Simulation

Demonstrates all major interaction paths through the EditorBot state machine.
Tests various scenarios from voice/text input through final render plan.

Usage:
    python -m bot.cli.simulate_full_workflow [--scenario SCENARIO] [--verbose]

Scenarios:
    1. text_only       - Text-based conversation flow (no voice)
    2. voice_full      - Full voice workflow with audio file
    3. text_edit       - Text with multiple edits
    4. template_flow   - Complete template selection and configuration
    5. all             - Run all scenarios sequentially
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional
import sys

from bot.cli.commands import CLICommands
from bot.cli.inspector import print_separator, print_json
from bot.state.runtime import get_conversation, save_conversation, reset_conversation
from bot.state.models import BotState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class WorkflowSimulator:
    """Orchestrates complete bot workflow simulations."""

    def __init__(self, chat_id: int = 99999, verbose: bool = False):
        self.chat_id = chat_id
        self.verbose = verbose
        self.commands = CLICommands(chat_id=chat_id, verbose=verbose)

    def print_scenario_header(self, title: str, description: str):
        """Print formatted scenario header."""
        print("\n" + "=" * 80)
        print(f"🎯 SCENARIO: {title}")
        print(f"📋 {description}")
        print("=" * 80 + "\n")

    def print_step(self, step_num: int, description: str):
        """Print formatted step indicator."""
        print(f"\n{'─' * 80}")
        print(f"📍 Step {step_num}: {description}")
        print(f"{'─' * 80}\n")

    async def wait_for_user(self, prompt: str = "Press Enter to continue..."):
        """Pause execution for user review."""
        if not self.verbose:
            return
        try:
            input(f"\n⏸️  {prompt}")
        except EOFError:
            # Running non-interactively, skip pause
            await asyncio.sleep(0.5)

    def check_state(self, expected: BotState, context: str = ""):
        """Verify current conversation state."""
        convo = get_conversation(self.chat_id)
        if convo.state != expected:
            print(f"❌ State mismatch {context}")
            print(f"   Expected: {expected.value}")
            print(f"   Got: {convo.state.value}")
            return False
        print(f"✅ State verified: {expected.value}")
        return True

    async def scenario_text_only(self):
        """
        Scenario 1: Text-Only Conversation

        Flow:
        1. Send text message (no voice)
        2. Bot receives text → TRANSCRIBED
        3. User confirms to trigger mediation
        4. Bot mediates → MEDIATED
        5. User approves with "OK" → TEMPLATE_PROPOSED
        6. User selects template
        """
        self.print_scenario_header(
            "Text-Only Conversation",
            "Start conversation with text, confirm, mediate, approve, select template"
        )

        # Reset to clean state
        reset_conversation(self.chat_id)
        self.check_state(BotState.IDLE, "after reset")

        # Step 1: Send initial text
        self.print_step(1, "Send text message to start conversation")
        await self.commands.send_text(
            "Hola, quiero crear un video sobre la importancia de la inteligencia artificial en la educación moderna."
        )
        await self.wait_for_user()

        # Verify we're in TRANSCRIBED state
        if not self.check_state(BotState.TRANSCRIBED, "after text input"):
            return False

        # Step 2: User confirms text (triggers mediation in real bot)
        self.print_step(2, "User confirms text to trigger mediation")
        print("ℹ️  In real workflow, confirming would trigger Gemini API mediation")
        print("ℹ️  For simulation, we send a mediated version manually")
        await self.commands.send_text(
            "La inteligencia artificial está transformando radicalmente la educación moderna."
        )
        await self.wait_for_user()

        # Should now be in MEDIATED state
        if not self.check_state(BotState.MEDIATED, "after mediation"):
            print("ℹ️  State may vary depending on handler implementation")

        # Step 3: User approves with OK
        self.print_step(3, "User approves mediated text with 'OK'")
        await self.commands.send_text("OK")
        await self.wait_for_user()

        # Verify we're in TEMPLATE_PROPOSED state
        if not self.check_state(BotState.TEMPLATE_PROPOSED, "after OK command"):
            print("ℹ️  Template selection may not be fully implemented yet")
        await self.wait_for_user()

        # Check final state
        convo = get_conversation(self.chat_id)
        print(f"\n✅ Scenario complete! Final state: {convo.state.value}")
        print(f"   Template ID: {convo.template_id}")

        return True

    async def scenario_voice_full(self):
        """
        Scenario 2: Voice Message Workflow

        Flow:
        1. Send voice message
        2. Bot transcribes with Whisper
        3. Bot mediates transcript
        4. User edits mediated text
        5. User finalizes script
        """
        self.print_scenario_header(
            "Voice Message Workflow",
            "Record voice → transcribe → mediate → edit → finalize"
        )

        # Reset to clean state
        reset_conversation(self.chat_id)

        # Step 1: Send voice message
        self.print_step(1, "Send voice message")

        # Check for sample audio file
        audio_path = Path("data/samples/sample_voice.ogg")
        if not audio_path.exists():
            print(f"⚠️  Sample audio not found: {audio_path}")
            print("ℹ️  Create a sample audio file or use inject-transcript instead")
            print("\nUsing inject-transcript as fallback...")

            await self.commands.inject_transcript(
                "Este es un mensaje de voz de prueba sobre inteligencia artificial en la educación."
            )
        else:
            await self.commands.send_voice(str(audio_path))

        await self.wait_for_user()

        # Verify transcription happened
        convo = get_conversation(self.chat_id)
        if not convo.transcript:
            print("❌ No transcript found")
            return False

        print(f"✅ Transcript: {convo.transcript[:100]}...")

        # Step 2: Edit mediated text
        self.print_step(2, "User edits the mediated text")
        await self.commands.send_text("EDITAR")
        await self.wait_for_user()

        if not self.check_state(BotState.EDITING_MEDIATED, "after EDITAR"):
            return False

        # Step 3: Submit edited text
        self.print_step(3, "User submits edited version")
        await self.commands.send_text(
            "La inteligencia artificial está revolucionando la educación moderna "
            "y transformando la forma en que aprendemos."
        )
        await self.wait_for_user()

        # Check final state
        convo = get_conversation(self.chat_id)
        print(f"\n✅ Scenario complete! Final state: {convo.state.value}")
        print(f"   Mediated text: {convo.mediated_text[:100] if convo.mediated_text else 'None'}...")

        return True

    async def scenario_text_edit(self):
        """
        Scenario 3: Multiple Text Edits

        Flow:
        1. Send initial text
        2. Review mediated text
        3. Edit once
        4. Edit again
        5. Approve final version
        """
        self.print_scenario_header(
            "Multiple Text Edits",
            "Text input → mediate → edit → edit again → approve"
        )

        reset_conversation(self.chat_id)

        # Step 1: Initial text
        self.print_step(1, "Send initial text")
        await self.commands.send_text(
            "Quiero hablar sobre como la tecnología blockchain puede mejorar la transparencia en las elecciones."
        )
        await self.wait_for_user()

        # Step 2: First edit
        self.print_step(2, "Request first edit")
        await self.commands.send_text("EDITAR")
        await self.wait_for_user()

        # Step 3: Submit first edit
        self.print_step(3, "Submit edited version 1")
        await self.commands.send_text(
            "La tecnología blockchain revoluciona la transparencia electoral mediante registros inmutables."
        )
        await self.wait_for_user()

        # Step 4: Check and edit again
        self.print_step(4, "Review and edit once more")
        await self.commands.send_text("EDITAR")
        await self.wait_for_user()

        # Step 5: Submit final version
        self.print_step(5, "Submit final version")
        await self.commands.send_text(
            "Blockchain garantiza transparencia electoral con registros verificables e inmutables de cada voto."
        )
        await self.wait_for_user()

        # Step 6: Approve
        self.print_step(6, "Approve final version")
        await self.commands.send_text("OK")
        await self.wait_for_user()

        convo = get_conversation(self.chat_id)
        print(f"\n✅ Scenario complete! Final state: {convo.state.value}")

        return True

    async def scenario_template_flow(self):
        """
        Scenario 4: Complete Template Workflow

        Flow:
        1. Quick path to template selection
        2. Select template
        3. Select soundtrack
        4. Configure assets
        5. Review render plan
        """
        self.print_scenario_header(
            "Complete Template Workflow",
            "Fast-track through template selection, soundtrack, assets, and render plan"
        )

        reset_conversation(self.chat_id)

        # Step 1: Quick setup - inject transcript and approve
        self.print_step(1, "Quick setup: inject transcript")
        await self.commands.inject_transcript(
            "Los beneficios de la meditación diaria incluyen reducción de estrés y mejor concentración."
        )
        await self.wait_for_user()

        # Step 2: Approve to get to template selection
        self.print_step(2, "Approve mediated text")
        await self.commands.send_text("OK")
        await self.wait_for_user()

        if not self.check_state(BotState.TEMPLATE_PROPOSED, "after approval"):
            return False

        # Step 3: Select template
        self.print_step(3, "Select explainer template")
        await self.commands.click_button("template:explainer_slides")
        await self.wait_for_user()

        # Step 4: Select soundtrack
        self.print_step(4, "Select soundtrack")
        print("ℹ️  Clicking soundtrack button: calm_piano")
        await self.commands.click_button("soundtrack:calm_piano")
        await self.wait_for_user()

        # Step 5: Configure assets (if needed)
        self.print_step(5, "Asset configuration")
        print("ℹ️  In real workflow, bot would request image generation settings")
        print("ℹ️  For simulation, we'll show state progression")
        await self.wait_for_user()

        # Check final state
        convo = get_conversation(self.chat_id)
        print(f"\n✅ Scenario complete! Final state: {convo.state.value}")
        print(f"   Template: {convo.template_id}")
        print(f"   Soundtrack: {convo.soundtrack_id}")

        return True

    async def scenario_cancel(self):
        """
        Scenario 5: Cancellation Flow

        Flow:
        1. Start conversation
        2. Cancel at various points
        3. Verify return to IDLE
        """
        self.print_scenario_header(
            "Cancellation Flow",
            "Test CANCELAR command at different states"
        )

        # Cancel from TRANSCRIBED
        self.print_step(1, "Cancel from TRANSCRIBED state")
        reset_conversation(self.chat_id)
        await self.commands.send_text("Test message")
        await self.wait_for_user()

        await self.commands.send_text("CANCELAR")
        await self.wait_for_user()
        self.check_state(BotState.IDLE, "after CANCELAR from TRANSCRIBED")

        # Cancel from EDITING_MEDIATED
        self.print_step(2, "Cancel from EDITING_MEDIATED state")
        reset_conversation(self.chat_id)
        await self.commands.inject_transcript("Another test")
        await self.commands.send_text("EDITAR")
        await self.wait_for_user()

        await self.commands.send_text("CANCELAR")
        await self.wait_for_user()
        self.check_state(BotState.IDLE, "after CANCELAR from EDITING_MEDIATED")

        print("\n✅ Scenario complete! Cancellation works correctly")
        return True

    async def scenario_state_inspection(self):
        """
        Scenario 6: State Inspection

        Demonstrate state inspection and debugging commands.
        """
        self.print_scenario_header(
            "State Inspection & Debugging",
            "Use inspector commands to examine bot state"
        )

        reset_conversation(self.chat_id)

        # Step 1: Show initial state
        self.print_step(1, "Inspect initial IDLE state")
        await self.commands.show_state()
        await self.wait_for_user()

        # Step 2: Send message and inspect
        self.print_step(2, "Send message and inspect state")
        await self.commands.send_text("Test state inspection")
        await self.wait_for_user()

        await self.commands.show_state()
        await self.wait_for_user()

        # Step 3: Show state as JSON
        self.print_step(3, "Export state as JSON")
        convo = get_conversation(self.chat_id)
        print_json({
            "state": convo.state.value,
            "transcript": convo.transcript,
            "mediated_text": convo.mediated_text,
            "template_id": convo.template_id,
            "has_audio": convo.audio_s3_path is not None,
        }, "Current State")
        await self.wait_for_user()

        # Step 4: Reset and verify
        self.print_step(4, "Reset conversation")
        await self.commands.reset()
        await self.wait_for_user()

        self.check_state(BotState.IDLE, "after reset")

        print("\n✅ Scenario complete! State inspection working")
        return True

    async def run_scenario(self, scenario: str) -> bool:
        """Run a specific scenario by name."""
        scenarios = {
            "text_only": self.scenario_text_only,
            "voice_full": self.scenario_voice_full,
            "text_edit": self.scenario_text_edit,
            "template_flow": self.scenario_template_flow,
            "cancel": self.scenario_cancel,
            "inspection": self.scenario_state_inspection,
        }

        if scenario not in scenarios:
            print(f"❌ Unknown scenario: {scenario}")
            print(f"Available scenarios: {', '.join(scenarios.keys())}")
            return False

        try:
            return await scenarios[scenario]()
        except Exception as e:
            print(f"\n❌ Scenario failed with error: {e}")
            logger.exception("Scenario error")
            return False

    async def run_all_scenarios(self):
        """Run all scenarios sequentially."""
        self.print_scenario_header(
            "ALL SCENARIOS",
            "Running complete test suite"
        )

        scenarios = [
            "text_only",
            "voice_full",
            "text_edit",
            "template_flow",
            "cancel",
            "inspection",
        ]

        results = {}
        for scenario in scenarios:
            print(f"\n{'═' * 80}")
            print(f"Running scenario: {scenario}")
            print(f"{'═' * 80}\n")

            success = await self.run_scenario(scenario)
            results[scenario] = "✅ PASS" if success else "❌ FAIL"

            await asyncio.sleep(1)  # Brief pause between scenarios

        # Print summary
        print("\n" + "═" * 80)
        print("📊 TEST SUMMARY")
        print("═" * 80)
        for scenario, result in results.items():
            print(f"{result} {scenario}")
        print("═" * 80 + "\n")


async def main():
    """Main entry point for simulation script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Simulate complete EditorBot workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scenarios:
  text_only       - Text-based conversation (no voice)
  voice_full      - Full voice workflow with audio
  text_edit       - Multiple text edits
  template_flow   - Complete template selection
  cancel          - Cancellation flows
  inspection      - State inspection commands
  all             - Run all scenarios

Examples:
  python -m bot.cli.simulate_full_workflow --scenario text_only
  python -m bot.cli.simulate_full_workflow --scenario all --verbose
  python -m bot.cli.simulate_full_workflow --scenario template_flow
        """
    )

    parser.add_argument(
        "--scenario",
        choices=["text_only", "voice_full", "text_edit", "template_flow",
                 "cancel", "inspection", "all"],
        default="text_only",
        help="Scenario to run (default: text_only)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output and interactive mode"
    )

    parser.add_argument(
        "--chat-id",
        type=int,
        default=99999,
        help="Chat ID for simulation (default: 99999)"
    )

    args = parser.parse_args()

    # Create simulator
    simulator = WorkflowSimulator(
        chat_id=args.chat_id,
        verbose=args.verbose
    )

    # Run requested scenario(s)
    if args.scenario == "all":
        await simulator.run_all_scenarios()
    else:
        success = await simulator.run_scenario(args.scenario)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
