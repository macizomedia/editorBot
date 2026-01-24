"""
Feature flag system for gradual LangGraph rollout.

Controls which users get the new LangGraph system vs. legacy FSM.
"""

import os
import logging
from typing import Literal

logger = logging.getLogger(__name__)


def get_rollout_percentage() -> int:
    """
    Get current LangGraph rollout percentage from environment.

    Returns:
        Percentage (0-100) of users that should use LangGraph
    """
    return int(os.getenv("LANGGRAPH_ROLLOUT_PCT", "0"))


def use_langgraph_for_user(chat_id: int, user_id: int) -> bool:
    """
    Determine if a specific user should use LangGraph vs. legacy FSM.

    Uses deterministic hash to ensure consistent routing for same user.

    Args:
        chat_id: Telegram chat ID
        user_id: Telegram user ID

    Returns:
        True if user should use LangGraph, False for legacy FSM
    """
    rollout_pct = get_rollout_percentage()

    if rollout_pct == 0:
        return False  # LangGraph disabled

    if rollout_pct >= 100:
        return True  # Full rollout

    # Hash user ID to get deterministic bucket (0-99)
    user_hash = hash(f"{chat_id}:{user_id}") % 100

    enabled = user_hash < rollout_pct

    logger.info(
        f"[FEATURE_FLAG] User {user_id} in chat {chat_id}: "
        f"hash={user_hash}, rollout={rollout_pct}%, "
        f"langgraph={'ENABLED' if enabled else 'DISABLED'}"
    )

    return enabled


def get_system_version(chat_id: int, user_id: int) -> Literal["langgraph", "fsm"]:
    """
    Get which system version a user should use.

    Returns:
        "langgraph" or "fsm"
    """
    return "langgraph" if use_langgraph_for_user(chat_id, user_id) else "fsm"
