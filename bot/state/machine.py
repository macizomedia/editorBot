from enum import Enum
from .models import BotState, Conversation


class EventType(Enum):
    VOICE_RECEIVED = "voice_received"
    TEXT_RECEIVED = "text_received"
    COMMAND_OK = "command_ok"
    COMMAND_EDITAR = "command_editar"
    COMMAND_CANCELAR = "command_cancelar"
    COMMAND_NEXT = "command_next"
    TEMPLATE_SELECTED = "template_selected"
    SOUNDTRACK_SELECTED = "soundtrack_selected"


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
                state=BotState.EDITING_MEDIATED,
                transcript=convo.transcript,
                mediated_text=payload,
            )
        if event == EventType.COMMAND_OK:
            return Conversation(
                state=BotState.SCRIPT_DRAFTED,
                transcript=convo.transcript,
                mediated_text=convo.mediated_text,
                script_draft=None,
            )
        if event == EventType.COMMAND_EDITAR:
            return Conversation(
                state=BotState.EDITING_MEDIATED,
                transcript=convo.transcript,
                mediated_text=convo.mediated_text,
            )
        if event == EventType.COMMAND_CANCELAR:
            return Conversation(state=BotState.IDLE)


        raise InvalidTransition(state, event)

    # EDITING_MEDIATED
    if state == BotState.EDITING_MEDIATED:
        if event == EventType.TEXT_RECEIVED:
            return Conversation(
                state=BotState.SCRIPT_DRAFTED,
                transcript=convo.transcript,
                mediated_text=payload,
                script_draft=None,
            )

        if event == EventType.COMMAND_OK:
            return Conversation(
                state=BotState.SCRIPT_DRAFTED,
                transcript=convo.transcript,
                mediated_text=convo.mediated_text,
                script_draft=None,
            )

        if event == EventType.COMMAND_CANCELAR:
            return Conversation(state=BotState.IDLE)

        raise InvalidTransition(state, event)

    # SCRIPT_DRAFTED
    if state == BotState.SCRIPT_DRAFTED:
        if event == EventType.COMMAND_OK:
            return Conversation(
                state=BotState.FINAL_SCRIPT,
                transcript=convo.transcript,
                mediated_text=convo.mediated_text,
                script_draft=convo.script_draft,
                final_script=convo.script_draft,
            )
        if event == EventType.COMMAND_EDITAR:
            return Conversation(
                state=BotState.EDITING_SCRIPT,
                transcript=convo.transcript,
                mediated_text=convo.mediated_text,
                script_draft=convo.script_draft,
            )
        if event == EventType.COMMAND_CANCELAR:
            return Conversation(state=BotState.IDLE)

        raise InvalidTransition(state, event)

    # EDITING_SCRIPT
    if state == BotState.EDITING_SCRIPT:
        if event == EventType.TEXT_RECEIVED:
            return Conversation(
                state=BotState.FINAL_SCRIPT,
                transcript=convo.transcript,
                mediated_text=convo.mediated_text,
                script_draft=convo.script_draft,
                final_script=payload,
            )
        if event == EventType.COMMAND_CANCELAR:
            return Conversation(state=BotState.IDLE)

        raise InvalidTransition(state, event)

    # FINAL_SCRIPT
    if state == BotState.FINAL_SCRIPT:
        if event in (EventType.COMMAND_OK, EventType.COMMAND_NEXT):
            return Conversation(
                state=BotState.SELECT_TEMPLATE,
                transcript=convo.transcript,
                mediated_text=convo.mediated_text,
                script_draft=convo.script_draft,
                final_script=convo.final_script,
            )
        if event == EventType.COMMAND_CANCELAR:
            return Conversation(state=BotState.IDLE)

        raise InvalidTransition(state, event)

    # SELECT_TEMPLATE
    if state == BotState.SELECT_TEMPLATE:
        if event == EventType.TEMPLATE_SELECTED:
            return Conversation(
                state=BotState.SELECT_SOUNDTRACK,
                transcript=convo.transcript,
                mediated_text=convo.mediated_text,
                script_draft=convo.script_draft,
                final_script=convo.final_script,
                template_id=payload,
            )
        if event == EventType.COMMAND_CANCELAR:
            return Conversation(state=BotState.IDLE)

        raise InvalidTransition(state, event)

    # SELECT_SOUNDTRACK
    if state == BotState.SELECT_SOUNDTRACK:
        if event == EventType.SOUNDTRACK_SELECTED:
            return Conversation(
                state=BotState.FINAL_SCRIPT,
                transcript=convo.transcript,
                mediated_text=convo.mediated_text,
                script_draft=convo.script_draft,
                final_script=convo.final_script,
                template_id=convo.template_id,
                soundtrack_id=payload,
            )
        if event == EventType.COMMAND_CANCELAR:
            return Conversation(state=BotState.IDLE)

        raise InvalidTransition(state, event)

    raise InvalidTransition(state, event)
