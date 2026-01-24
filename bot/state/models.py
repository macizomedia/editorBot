from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class BotState(Enum):
    IDLE = "idle"
    AUDIO_RECEIVED = "audio_received"
    TRANSCRIBED = "transcribed"
    MEDIATED = "mediated"
    EDITING_MEDIATED = "editing_mediated"
    SCRIPT_DRAFTED = "script_drafted"
    EDITING_SCRIPT = "editing_script"
    FINAL_SCRIPT = "final_script"
    TEMPLATE_PROPOSED = "template_proposed"
    SELECT_SOUNDTRACK = "select_soundtrack"
    ASSET_OPTIONS = "asset_options"
    RENDER_PLAN_GENERATED = "render_plan_generated"
    READY_FOR_RENDER = "ready_for_render"


@dataclass(slots=True)
class Conversation:
    state: BotState = BotState.IDLE
    transcript: Optional[str] = None
    mediated_text: Optional[str] = None
    script_draft: Optional[str] = None
    final_script: Optional[str] = None

    # Template system
    template_id: Optional[str] = None
    template_spec: Optional[Dict[str, Any]] = None  # Cached template JSON
    validation_result: Optional[Dict[str, Any]] = None  # Validation status

    # Asset selection
    soundtrack_id: Optional[str] = None
    asset_config: Optional[Dict[str, Any]] = None  # Image generation config

    # Render Plan (final video specification)
    visual_strategy: Optional[Dict[str, Any]] = None  # Visual generation strategy
    render_plan: Optional[Dict[str, Any]] = None  # Serialized RenderPlan ready for render engine
