#!/usr/bin/env python3
"""Quick test of the updated state machine"""

import sys
sys.path.insert(0, '.')

from bot.state.machine import handle_event, EventType, InvalidTransition
from bot.state.models import Conversation, BotState

print("Testing state machine transitions...")
print("-" * 50)

# Test 1: IDLE → AUDIO_RECEIVED → TRANSCRIBED
print("\n✓ Test 1: Audio reception and transcription")
convo = Conversation()
assert convo.state == BotState.IDLE, "Should start in IDLE"

convo = handle_event(convo, EventType.VOICE_RECEIVED)
assert convo.state == BotState.AUDIO_RECEIVED, "Should transition to AUDIO_RECEIVED"
print("  IDLE → AUDIO_RECEIVED ✓")

convo = handle_event(convo, EventType.TRANSCRIPTION_COMPLETE, "test transcript")
assert convo.state == BotState.TRANSCRIBED, "Should transition to TRANSCRIBED"
assert convo.transcript == "test transcript", "Should store transcript"
print("  AUDIO_RECEIVED → TRANSCRIBED ✓")

# Test 2: Complete flow to READY_FOR_RENDER
print("\n✓ Test 2: Complete pipeline flow")
convo = Conversation()
convo = handle_event(convo, EventType.VOICE_RECEIVED)
convo = handle_event(convo, EventType.TRANSCRIPTION_COMPLETE, "transcript")
print("  Audio flow ✓")

convo = handle_event(convo, EventType.TEXT_RECEIVED, "mediated")
assert convo.state == BotState.MEDIATED
print("  Mediation ✓")

convo = handle_event(convo, EventType.COMMAND_OK)
assert convo.state == BotState.SCRIPT_DRAFTED
print("  Script draft ✓")

convo = handle_event(convo, EventType.COMMAND_OK)
assert convo.state == BotState.FINAL_SCRIPT
print("  Final script ✓")

convo = handle_event(convo, EventType.COMMAND_NEXT)
assert convo.state == BotState.TEMPLATE_PROPOSED
print("  Template proposed ✓")

convo = handle_event(convo, EventType.TEMPLATE_SELECTED, "template_1")
assert convo.state == BotState.SELECT_SOUNDTRACK
assert convo.template_id == "template_1"
print("  Soundtrack selection ✓")

convo = handle_event(convo, EventType.SOUNDTRACK_SELECTED, "soundtrack_1")
assert convo.state == BotState.ASSET_OPTIONS
assert convo.soundtrack_id == "soundtrack_1"
print("  Asset options ✓")

convo = handle_event(convo, EventType.ASSETS_CONFIGURED)
assert convo.state == BotState.READY_FOR_RENDER
print("  Ready for render ✓")

convo = handle_event(convo, EventType.RENDER_APPROVED)
assert convo.state == BotState.IDLE
print("  Back to IDLE (cycle complete) ✓")

# Test 3: Invalid transition
print("\n✓ Test 3: Invalid transition handling")
convo = Conversation()
try:
    handle_event(convo, EventType.TEXT_RECEIVED, "should fail")
    print("  ERROR: Should have raised InvalidTransition")
    sys.exit(1)
except InvalidTransition:
    print("  Invalid transition correctly rejected ✓")

# Test 4: Cancel from any state
print("\n✓ Test 4: Cancel functionality")
convo = Conversation()
convo = handle_event(convo, EventType.VOICE_RECEIVED)
convo = handle_event(convo, EventType.TRANSCRIPTION_COMPLETE, "transcript")
convo = handle_event(convo, EventType.TEXT_RECEIVED, "mediated")
assert convo.state == BotState.MEDIATED

convo = handle_event(convo, EventType.COMMAND_CANCELAR)
assert convo.state == BotState.IDLE
print("  Cancel from MEDIATED → IDLE ✓")

print("\n" + "=" * 50)
print("✅ All tests passed!")
print("=" * 50)
