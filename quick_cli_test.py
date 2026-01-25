#!/usr/bin/env python3
"""
Quick CLI Test - Minimal example of bot interaction

Demonstrates the simplest possible conversation flow:
1. Send text
2. Send mediated version
3. Approve with OK

Usage:
    python quick_cli_test.py
"""

import asyncio
from bot.cli.commands import CLICommands
from bot.state.runtime import reset_conversation, get_conversation


async def quick_test():
    """Run a minimal test conversation."""

    # Create CLI interface
    cli = CLICommands(chat_id=12345, verbose=False)

    print("=" * 60)
    print("Quick CLI Test - Minimal Conversation Flow")
    print("=" * 60)
    print()

    # Reset to clean state
    print("Step 1: Reset to IDLE")
    reset_conversation(12345)
    convo = get_conversation(12345)
    print(f"✓ State: {convo.state.value}\n")

    # Send initial text
    print("Step 2: Send text message")
    await cli.send_text("Quiero hablar sobre inteligencia artificial")
    convo = get_conversation(12345)
    print(f"✓ State: {convo.state.value}\n")

    # Send mediated text
    print("Step 3: Send mediated text")
    await cli.send_text("La IA está revolucionando nuestra sociedad")
    convo = get_conversation(12345)
    print(f"✓ State: {convo.state.value}\n")

    # Approve
    print("Step 4: Approve with OK")
    await cli.send_text("OK")
    convo = get_conversation(12345)
    print(f"✓ State: {convo.state.value}\n")

    print("=" * 60)
    print("✅ Test Complete!")
    print(f"   Final State: {convo.state.value}")
    print(f"   Transcript: {convo.transcript[:50] if convo.transcript else 'None'}...")
    print(f"   Mediated: {convo.mediated_text[:50] if convo.mediated_text else 'None'}...")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(quick_test())
