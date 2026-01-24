import logging
from enum import Enum
from .models import BotState, Conversation

logger = logging.getLogger(__name__)


class EventType(Enum):
    VOICE_RECEIVED = "voice_received"
    TRANSCRIPTION_COMPLETE = "transcription_complete"
    TEXT_RECEIVED = "text_received"
    COMMAND_OK = "command_ok"
    COMMAND_EDITAR = "command_editar"
    COMMAND_CANCELAR = "command_cancelar"
    COMMAND_NEXT = "command_next"
    TEMPLATE_SELECTED = "template_selected"
    SOUNDTRACK_SELECTED = "soundtrack_selected"
    ASSETS_CONFIGURED = "assets_configured"
    RENDER_PLAN_BUILT = "render_plan_built"
    RENDER_PLAN_VALIDATED = "render_plan_validated"
    RENDER_APPROVED = "render_approved"


class InvalidTransition(Exception):
    pass


def handle_event(
    convo: Conversation,
    event: EventType,
    payload: str | None = None,
) -> Conversation:
    state = convo.state

    logger.info(
        "state_transition_attempt",
        extra={
            "current_state": state.value,
            "event": event.value,
            "has_payload": payload is not None,
            "payload_preview": payload[:50] if payload and isinstance(payload, str) else type(payload).__name__,
        }
    )

    # Allow new voice input to restart flow from any state
    if event == EventType.VOICE_RECEIVED and state != BotState.IDLE:
        new_convo = Conversation(state=BotState.AUDIO_RECEIVED)
        logger.info(
            "state_transition_complete",
            extra={
                "from_state": state.value,
                "to_state": new_convo.state.value,
                "event": event.value,
                "reason": "voice_restart",
            }
        )
        return new_convo

    # IDLE
    if state == BotState.IDLE:
        if event == EventType.VOICE_RECEIVED:
            new_convo = Conversation(state=BotState.AUDIO_RECEIVED)
            logger.info(
                "state_transition_complete",
                extra={
                    "from_state": state.value,
                    "to_state": new_convo.state.value,
                    "event": event.value,
                }
            )
            return new_convo

        logger.error(
            "invalid_state_transition",
            extra={
                "state": state.value,
                "event": event.value,
            }
        )
        raise InvalidTransition(state, event)
    # AUDIO_RECEIVED
    if state == BotState.AUDIO_RECEIVED:
        if event == EventType.TRANSCRIPTION_COMPLETE:
            return Conversation(
                state=BotState.TRANSCRIBED,
                transcript=payload,
            )

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
                mediated_text=convo.transcript,  # Copy mediated text from transcript
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
                state=BotState.TEMPLATE_PROPOSED,
                transcript=convo.transcript,
                mediated_text=convo.mediated_text,
                script_draft=convo.script_draft,
                final_script=convo.final_script,
            )
        if event == EventType.COMMAND_CANCELAR:
            return Conversation(state=BotState.IDLE)

        raise InvalidTransition(state, event)

    # TEMPLATE_PROPOSED
    if state == BotState.TEMPLATE_PROPOSED:
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
                state=BotState.ASSET_OPTIONS,
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

    # ASSET_OPTIONS
    if state == BotState.ASSET_OPTIONS:
        if event == EventType.ASSETS_CONFIGURED:
            return Conversation(
                state=BotState.RENDER_PLAN_GENERATED,
                transcript=convo.transcript,
                mediated_text=convo.mediated_text,
                script_draft=convo.script_draft,
                final_script=convo.final_script,
                template_id=convo.template_id,
                soundtrack_id=convo.soundtrack_id,
                asset_config=payload,
            )
        if event == EventType.COMMAND_CANCELAR:
            return Conversation(state=BotState.IDLE)

        raise InvalidTransition(state, event)

    # RENDER_PLAN_GENERATED
    if state == BotState.RENDER_PLAN_GENERATED:
        if event == EventType.RENDER_PLAN_BUILT:
            # Render plan has been built and validated
            return Conversation(
                state=BotState.READY_FOR_RENDER,
                transcript=convo.transcript,
                mediated_text=convo.mediated_text,
                script_draft=convo.script_draft,
                final_script=convo.final_script,
                template_id=convo.template_id,
                soundtrack_id=convo.soundtrack_id,
                asset_config=convo.asset_config,
                visual_strategy=convo.visual_strategy,
                render_plan=payload,  # Serialized RenderPlan JSON
            )
        if event == EventType.COMMAND_CANCELAR:
            return Conversation(state=BotState.IDLE)

        raise InvalidTransition(state, event)

    # READY_FOR_RENDER
    if state == BotState.READY_FOR_RENDER:
        if event == EventType.RENDER_APPROVED:
            # Video render triggered, return to IDLE after completion
            return Conversation(state=BotState.IDLE)
        if event == EventType.COMMAND_CANCELAR:
            return Conversation(state=BotState.IDLE)

        raise InvalidTransition(state, event)

    raise InvalidTransition(state, event)
