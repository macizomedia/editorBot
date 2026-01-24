"""
LangGraph State Schema for EditorBot.

Defines the TypedDict state that flows through all graph nodes,
including conversation history, user config, template selection,
and the accumulating JSON payload for video generation.
"""

from typing import TypedDict, Literal, Optional, Any
from dataclasses import dataclass
from enum import Enum


class AssistanceLevel(str, Enum):
    """
    User assistance level determining LLM autonomy and retry limits.

    BASIC: Limited loops (2 retries), explicit field input required
    STANDARD: Moderate loops (3 retries), LLM infers some fields from context
    PREMIUM: Extended loops (5 retries), LLM fills missing optional fields automatically
    """
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"

    @property
    def max_validation_retries(self) -> int:
        """Maximum validation retry attempts before human-in-loop."""
        return {
            AssistanceLevel.BASIC: 2,
            AssistanceLevel.STANDARD: 3,
            AssistanceLevel.PREMIUM: 5,
        }[self]

    @property
    def auto_fill_enabled(self) -> bool:
        """Whether LLM can automatically fill missing fields."""
        return self in (AssistanceLevel.STANDARD, AssistanceLevel.PREMIUM)


@dataclass(frozen=True)
class ConversationMessage:
    """Single message in conversation history."""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: str  # ISO format
    metadata: Optional[dict[str, Any]] = None


class UserConfig(TypedDict, total=False):
    """User-configurable global settings (set via /init command)."""
    video_format: Literal["REEL_VERTICAL", "LANDSCAPE_16_9", "SQUARE_1_1"]
    output_style: Literal["minimal", "dynamic", "cinematic"]
    assistance_level: AssistanceLevel
    language: str  # ISO 639-1 code, e.g., "es", "en"


class TemplateRequirements(TypedDict, total=False):
    """
    Required and optional fields extracted from selected template spec.
    Used by requirement collector to determine what to ask user.
    """
    required_fields: list[str]  # Must be collected (e.g., ["hook", "content"])
    optional_fields: list[str]  # Nice to have (e.g., ["call_to_action"])
    field_descriptions: dict[str, str]  # Human-readable descriptions for prompts


class VideoPayload(TypedDict, total=False):
    """
    Accumulating JSON payload for video generation.
    Fields are dynamically collected based on selected template.
    """
    hook: Optional[str]  # Opening line (1-2 sentences)
    content: Optional[str]  # Main body (5-10 sentences)
    call_to_action: Optional[str]  # Closing CTA (1 sentence)
    context: Optional[str]  # Background knowledge injected via /context
    # Additional fields added dynamically based on template


class ValidationResult(TypedDict):
    """Result from LLM validation of collected payload."""
    valid: bool
    missing_fields: list[str]  # Fields that still need collection
    suggestions: list[str]  # Specific feedback for user
    confidence: float  # 0.0-1.0, LLM's confidence in validation


class GraphState(TypedDict):
    """
    Main state object flowing through all LangGraph nodes.
    Persisted via SqliteSaver checkpointing.
    """
    # Telegram context
    chat_id: int
    user_id: int
    thread_id: str  # f"{chat_id}:{user_id}"

    # User configuration
    config: UserConfig

    # Conversation history (full context for LLM)
    messages: list[ConversationMessage]

    # Template selection
    template_id: Optional[str]
    template_spec: Optional[dict[str, Any]]  # Full template JSON
    template_requirements: Optional[TemplateRequirements]

    # Accumulating video payload
    payload: VideoPayload

    # Validation tracking
    validation_result: Optional[ValidationResult]
    validation_attempts: int  # Increments on each validator retry

    # Audio/transcription (from voice messages)
    audio_s3_path: Optional[str]
    transcript: Optional[str]
    mediated_text: Optional[str]  # Dialect-neutralized version

    # Workflow control
    current_phase: Literal[
        "init",           # User configuring settings
        "template_select",  # Choosing video template
        "collection",     # Collecting required fields
        "validation",     # LLM checking completeness
        "finalized",      # Ready for render
        "error"           # Unrecoverable error state
    ]
    next_field_to_collect: Optional[str]  # Which field to ask for next
    interrupt_for_human: bool  # Trigger human-in-loop

    # Migration flag (for backward compatibility during rollout)
    system_version: Literal["fsm", "langgraph"]  # Which system created this state
    migrated_at: Optional[str]  # ISO timestamp of migration

    # Error tracking
    error_message: Optional[str]
    error_count: int  # Total errors encountered in this conversation


# Example initial state
def create_initial_state(
    chat_id: int,
    user_id: int,
    assistance_level: AssistanceLevel = AssistanceLevel.STANDARD,
) -> GraphState:
    """Create a fresh state for a new conversation."""
    return GraphState(
        chat_id=chat_id,
        user_id=user_id,
        thread_id=f"{chat_id}:{user_id}",
        config=UserConfig(
            video_format="REEL_VERTICAL",
            output_style="dynamic",
            assistance_level=assistance_level,
            language="es",
        ),
        messages=[],
        template_id=None,
        template_spec=None,
        template_requirements=None,
        payload=VideoPayload(),
        validation_result=None,
        validation_attempts=0,
        audio_s3_path=None,
        transcript=None,
        mediated_text=None,
        current_phase="init",
        next_field_to_collect=None,
        interrupt_for_human=False,
        system_version="langgraph",
        migrated_at=None,
        error_message=None,
        error_count=0,
    )
