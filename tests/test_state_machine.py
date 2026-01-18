import pytest

from bot.state.machine import handle_event, EventType, InvalidTransition
from bot.state.models import Conversation, BotState

def test_happy_path():
    convo = Conversation()

    convo = handle_event(convo, EventType.VOICE_RECEIVED)
    assert convo.state == BotState.TRANSCRIBED

    convo = handle_event(convo, EventType.TEXT_RECEIVED, "raw transcript")
    assert convo.state == BotState.MEDIATED

    convo = handle_event(convo, EventType.TEXT_RECEIVED, "mediated text")
    assert convo.state == BotState.AWAITING_EDIT

    convo = handle_event(convo, EventType.COMMAND_OK)
    assert convo.state == BotState.CONFIRMED


def test_invalid_transition_from_idle():
    convo = Conversation()

    with pytest.raises(InvalidTransition):
        handle_event(convo, EventType.TEXT_RECEIVED, "unexpected")


def test_edit_loop_and_cancel():
    convo = Conversation()
    convo = handle_event(convo, EventType.VOICE_RECEIVED)
    convo = handle_event(convo, EventType.TEXT_RECEIVED, "transcript")
    convo = handle_event(convo, EventType.TEXT_RECEIVED, "first draft")

    assert convo.state == BotState.AWAITING_EDIT

    convo = handle_event(convo, EventType.TEXT_RECEIVED, "edited text")
    assert convo.mediated_text == "edited text"

    convo = handle_event(convo, EventType.COMMAND_CANCELAR)
    assert convo.state == BotState.IDLE
