from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


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
    READY_FOR_RENDER = "ready_for_render"


@dataclass(slots=True)
class Conversation:
    state: BotState = BotState.IDLE
    transcript: Optional[str] = None
    mediated_text: Optional[str] = None
    script_draft: Optional[str] = None
    final_script: Optional[str] = None
    template_id: Optional[str] = None
    soundtrack_id: Optional[str] = None
