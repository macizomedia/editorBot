from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class BotState(Enum):
    IDLE = "idle"
    TRANSCRIBED = "transcribed"
    MEDIATED = "mediated"
    AWAITING_EDIT = "awaiting_edit"
    CONFIRMED = "confirmed"


@dataclass(slots=True)
class Conversation:
    state: BotState = BotState.IDLE
    transcript: Optional[str] = None
    mediated_text: Optional[str] = None
