from enum import Enum
from .models import BotState, Conversation


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
    state = convo.state

    # IDLE
    if state == BotState.IDLE:
        if event == EventType.VOICE_RECEIVED:
            return Conversation(state=BotState.TRANSCRIBED)

        raise InvalidTransition(state, event)

    # TRANSCRIBED
    if state == BotState.TRANSCRIBED:
        if event == EventType.TEXT_RECEIVED:
            return Conversation(
                state=BotState.MEDIATED,
                transcript=payload,
            )

        raise InvalidTransition(state, event)

    # MEDIATED
    if state == BotState.MEDIATED:
        if event == EventType.TEXT_RECEIVED:
            return Conversation(
                state=BotState.AWAITING_EDIT,
                transcript=convo.transcript,
                mediated_text=payload,
            )
        if event == EventType.COMMAND_OK:
            return Conversation(
                state=BotState.CONFIRMED,
                transcript=convo.transcript,
                mediated_text=convo.mediated_text,
                )
        if event == EventType.COMMAND_EDITAR:
            return Conversation(
                state=BotState.AWAITING_EDIT,
                transcript=convo.transcript,
                mediated_text=convo.mediated_text,
                )
        if event == EventType.COMMAND_CANCELAR:
            return Conversation(state=BotState.IDLE)


        raise InvalidTransition(state, event)

    # AWAITING_EDIT
    if state == BotState.AWAITING_EDIT:
        if event == EventType.TEXT_RECEIVED:
            return Conversation(
                state=BotState.AWAITING_EDIT,
                transcript=convo.transcript,
                mediated_text=payload,
            )

        if event == EventType.COMMAND_OK:
            return Conversation(
                state=BotState.CONFIRMED,
                transcript=convo.transcript,
                mediated_text=convo.mediated_text,
            )

        if event == EventType.COMMAND_CANCELAR:
            return Conversation(state=BotState.IDLE)

        raise InvalidTransition(state, event)

    # CONFIRMED
    if state == BotState.CONFIRMED:
        return Conversation(state=BotState.IDLE)

    raise InvalidTransition(state, event)
