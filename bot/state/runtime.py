from __future__ import annotations

from threading import Lock
from typing import Dict

from .models import Conversation


_conversations: Dict[int, Conversation] = {}
_lock = Lock()


def get_conversation(chat_id: int) -> Conversation:
    """Return the current conversation state for a chat."""
    with _lock:
        return _conversations.get(chat_id, Conversation())


def save_conversation(chat_id: int, convo: Conversation) -> None:
    """Persist a conversation state for a chat (in-memory)."""
    with _lock:
        _conversations[chat_id] = convo


def reset_conversation(chat_id: int) -> None:
    """Reset the conversation state for a chat."""
    with _lock:
        _conversations.pop(chat_id, None)
