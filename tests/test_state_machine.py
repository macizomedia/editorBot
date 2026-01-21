import pytest

from bot.state.machine import handle_event, EventType, InvalidTransition
from bot.state.models import Conversation, BotState


def test_audio_received_to_transcribed():
    """Test new AUDIO_RECEIVED state"""
    convo = Conversation()

    convo = handle_event(convo, EventType.VOICE_RECEIVED)
    assert convo.state == BotState.AUDIO_RECEIVED

    convo = handle_event(convo, EventType.TRANSCRIPTION_COMPLETE, "transcript text")
    assert convo.state == BotState.TRANSCRIBED
    assert convo.transcript == "transcript text"


def test_happy_path_to_ready_for_render():
    """Test complete flow through new states"""
    convo = Conversation()

    # Audio flow
    convo = handle_event(convo, EventType.VOICE_RECEIVED)
    assert convo.state == BotState.AUDIO_RECEIVED

    convo = handle_event(convo, EventType.TRANSCRIPTION_COMPLETE, "raw transcript")
    assert convo.state == BotState.TRANSCRIBED

    # Mediation
    convo = handle_event(convo, EventType.TEXT_RECEIVED, "mediated text")
    assert convo.state == BotState.MEDIATED

    # Script draft
    convo = handle_event(convo, EventType.COMMAND_OK)
    assert convo.state == BotState.SCRIPT_DRAFTED

    # Final script
    convo = handle_event(convo, EventType.COMMAND_OK)
    assert convo.state == BotState.FINAL_SCRIPT

    # Template selection
    convo = handle_event(convo, EventType.COMMAND_NEXT)
    assert convo.state == BotState.TEMPLATE_PROPOSED

    # Soundtrack selection
    convo = handle_event(convo, EventType.TEMPLATE_SELECTED, "template_1")
    assert convo.state == BotState.SELECT_SOUNDTRACK
    assert convo.template_id == "template_1"

    # Asset options
    convo = handle_event(convo, EventType.SOUNDTRACK_SELECTED, "soundtrack_1")
    assert convo.state == BotState.ASSET_OPTIONS
    assert convo.soundtrack_id == "soundtrack_1"

    # Ready for render
    convo = handle_event(convo, EventType.ASSETS_CONFIGURED)
    assert convo.state == BotState.READY_FOR_RENDER

    # Complete cycle back to IDLE
    convo = handle_event(convo, EventType.RENDER_APPROVED)
    assert convo.state == BotState.IDLE


def test_invalid_transition_from_idle():
    convo = Conversation()

    with pytest.raises(InvalidTransition):
        handle_event(convo, EventType.TEXT_RECEIVED, "unexpected")


def test_cancel_from_mediated():
    convo = Conversation()
    convo = handle_event(convo, EventType.VOICE_RECEIVED)
    convo = handle_event(convo, EventType.TRANSCRIPTION_COMPLETE, "transcript")
    convo = handle_event(convo, EventType.TEXT_RECEIVED, "mediated")

    assert convo.state == BotState.MEDIATED

    convo = handle_event(convo, EventType.COMMAND_CANCELAR)
    assert convo.state == BotState.IDLE
