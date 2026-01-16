from enum import Enum
from .store import Conversation
from .machine import BotState, EventType

class BotState(Enum):
    IDLE = "idle"
    TRANSCRIBED = "transcribed"
    MEDIATED = "mediated"
    AWAITING_EDIT = "awaiting_edit"
    CONFIRMED = "confirmed"

class EventType(Enum):
    VOICE_RECEIVED = "voice_received"
    TEXT_RECEIVED = "text_received"
    COMMAND_OK = "command_ok"
    COMMAND_EDITAR = "command_editar"
    COMMAND_CANCELAR = "command_cancelar"


class InvalidTransition(Exception):
    pass


def handle_event(
    convo: Conversation,
    event: EventType,
    payload: str | None = None,
) -> Conversation:
    """
    Returns a NEW Conversation with updated state.
    Does not mutate the original.
    """

    # IDLE → VOICE
    if convo.state == BotState.IDLE:
        if event == EventType.VOICE_RECEIVED:
            return Conversation(
                state=BotState.TRANSCRIBED,
                transcript=payload,
            )

        raise InvalidTransition(convo.state, event)

    # TRANSCRIBED → MEDIATED
    if convo.state == BotState.TRANSCRIBED:
        if event == EventType.TEXT_RECEIVED:
            return Conversation(
                state=BotState.MEDIATED,
                transcript=convo.transcript,
                mediated_text=payload,
            )

        raise InvalidTransition(convo.state, event)

    # MEDIATED → AWAITING_EDIT
    if convo.state == BotState.MEDIATED:
        return Conversation(
            state=BotState.AWAITING_EDIT,
            transcript=convo.transcript,
            mediated_text=convo.mediated_text,
        )

    # AWAITING_EDIT
    if convo.state == BotState.AWAITING_EDIT:
        if event == EventType.COMMAND_OK:
            return Conversation(
                state=BotState.CONFIRMED,
                transcript=convo.transcript,
                mediated_text=convo.mediated_text,
            )

        if event == EventType.TEXT_RECEIVED:
            # User pasted edited text
            return Conversation(
                state=BotState.AWAITING_EDIT,
                transcript=convo.transcript,
                mediated_text=payload,
            )

        if event == EventType.COMMAND_CANCELAR:
            return Conversation(state=BotState.IDLE)

        raise InvalidTransition(convo.state, event)

    # CONFIRMED → reset
    if convo.state == BotState.CONFIRMED:
        return Conversation(state=BotState.IDLE)

    raise InvalidTransition(convo.state, event)




