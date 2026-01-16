from dataclasses import dataclass
from typing import Optional
from .machine import BotState


@dataclass
class Conversation:
    state: BotState = BotState.IDLE
    transcript: Optional[str] = None
    mediated_text: Optional[str] = None

