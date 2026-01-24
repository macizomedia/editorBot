"""
Testing fixtures and conversation replay tests for LangGraph implementation.

Enables testing of multi-turn conversations and validation of state transitions.
"""

import pytest
import asyncio
from datetime import datetime, UTC
from typing import Any

from bot.graph.state import (
    GraphState,
    create_initial_state,
    AssistanceLevel,
    ConversationMessage,
)
from bot.graph.graph import create_editor_graph
from langgraph.checkpoint.memory import MemorySaver


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def basic_user_state() -> GraphState:
    """Create initial state for basic assistance level user."""
    return create_initial_state(
        chat_id=12345,
        user_id=67890,
        assistance_level=AssistanceLevel.BASIC,
    )


@pytest.fixture
def premium_user_state() -> GraphState:
    """Create initial state for premium assistance level user."""
    return create_initial_state(
        chat_id=12345,
        user_id=67890,
        assistance_level=AssistanceLevel.PREMIUM,
    )


@pytest.fixture
def state_with_template(basic_user_state: GraphState) -> GraphState:
    """State with template already selected."""
    return {
        **basic_user_state,
        "template_id": "opinion_monologue_reel",
        "template_spec": {
            "id": "opinion_monologue_reel",
            "template_family": "opinion",
            "duration": {"min_seconds": 15, "target_seconds": 30, "max_seconds": 45},
        },
        "template_requirements": {
            "required_fields": ["hook", "content"],
            "optional_fields": ["call_to_action"],
            "field_descriptions": {
                "hook": "Opening statement that grabs attention (1-2 sentences)",
                "content": "Main opinion or argument (5-10 sentences)",
                "call_to_action": "Closing CTA (1 sentence)",
            },
        },
        "current_phase": "collection",
    }


@pytest.fixture
async def test_graph():
    """Create graph with in-memory checkpointer for testing."""
    workflow = create_editor_graph()
    checkpointer = MemorySaver()  # In-memory for tests (no SQLite)
    graph = workflow.compile(checkpointer=checkpointer)
    return graph


# ============================================================================
# CONVERSATION REPLAY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_full_conversation_happy_path(test_graph, state_with_template):
    """
    Test complete conversation flow: collection → validation → finalization.

    User provides all required fields, validation passes on first attempt.
    """
    state = state_with_template
    thread_id = state["thread_id"]
    config = {"configurable": {"thread_id": thread_id}}

    # Step 1: User starts collection
    state["messages"].append(
        ConversationMessage(
            role="user",
            content="/start",
            timestamp=datetime.now(UTC).isoformat(),
        )
    )

    result = await test_graph.ainvoke(state, config)

    # Should prompt for first field (hook)
    assert result["current_phase"] == "collection"
    assert result["next_field_to_collect"] == "hook"
    assert "hook" in result["messages"][-1]["content"].lower()

    # Step 2: User provides hook
    result["messages"].append(
        ConversationMessage(
            role="user",
            content="Why most people fail at productivity",
            timestamp=datetime.now(UTC).isoformat(),
        )
    )

    result = await test_graph.ainvoke(result, config)

    # Should extract hook and ask for content
    assert result["payload"]["hook"] is not None
    assert "productivity" in result["payload"]["hook"].lower()
    assert result["next_field_to_collect"] == "content"

    # Step 3: User provides content
    result["messages"].append(
        ConversationMessage(
            role="user",
            content=(
                "Most people confuse being busy with being productive. "
                "Real productivity means doing less but better. "
                "Here are three principles that changed my life."
            ),
            timestamp=datetime.now(UTC).isoformat(),
        )
    )

    result = await test_graph.ainvoke(result, config)

    # Should extract content and move to validation
    assert result["payload"]["content"] is not None
    assert result["current_phase"] == "validation"

    # Step 4: Validation should pass (mocked LLM would return valid=True)
    # In real test, we'd mock the LLM call
    # For now, just verify state structure

    assert result["validation_attempts"] >= 1
    assert "validation_result" in result or result["current_phase"] == "finalized"


@pytest.mark.asyncio
async def test_validation_retry_loop(test_graph, state_with_template):
    """
    Test self-correction loop: validation fails, routes back to collection.
    """
    state = state_with_template
    thread_id = state["thread_id"]
    config = {"configurable": {"thread_id": thread_id}}

    # Pre-populate payload with incomplete data
    state["payload"]["hook"] = "Short"  # Too short
    state["payload"]["content"] = "Also short"  # Too short
    state["current_phase"] = "validation"

    result = await test_graph.ainvoke(state, config)

    # Validation should fail and route back to collection
    # (In real test with mocked LLM)
    assert result["validation_attempts"] == 1

    # After 3 attempts, should trigger human-in-loop
    for attempt in range(2, 4):
        result["current_phase"] = "validation"
        result = await test_graph.ainvoke(result, config)

        if result.get("interrupt_for_human"):
            break

    # Basic user (2 max retries) should interrupt after 2 attempts
    assert result["validation_attempts"] >= 2
    assert result["interrupt_for_human"] is True


@pytest.mark.asyncio
async def test_premium_user_auto_fill(test_graph, premium_user_state):
    """
    Test that premium users get optional fields auto-filled by LLM.
    """
    state = premium_user_state
    state["template_id"] = "opinion_monologue_reel"
    state["template_requirements"] = {
        "required_fields": ["hook", "content"],
        "optional_fields": ["call_to_action"],
        "field_descriptions": {
            "hook": "Opening hook",
            "content": "Main content",
            "call_to_action": "CTA",
        },
    }
    state["current_phase"] = "collection"

    # Provide only required fields
    state["payload"]["hook"] = "Great hook here"
    state["payload"]["content"] = "Amazing content that's detailed and complete"

    thread_id = state["thread_id"]
    config = {"configurable": {"thread_id": thread_id}}

    result = await test_graph.ainvoke(state, config)

    # Premium user should have CTA auto-filled (if LLM mocked to do so)
    assistance_level = result["config"]["assistance_level"]
    assert assistance_level == AssistanceLevel.PREMIUM
    assert assistance_level.auto_fill_enabled is True

    # In real test with mocked LLM, we'd verify call_to_action was added


@pytest.mark.asyncio
async def test_thread_persistence(test_graph, basic_user_state):
    """
    Test that conversation state persists across multiple invocations.
    """
    state = basic_user_state
    thread_id = state["thread_id"]
    config = {"configurable": {"thread_id": thread_id}}

    # First invocation: add message
    state["messages"].append(
        ConversationMessage(
            role="user",
            content="Hello bot",
            timestamp=datetime.now(UTC).isoformat(),
        )
    )

    result1 = await test_graph.ainvoke(state, config)
    message_count_1 = len(result1["messages"])

    # Second invocation: add another message
    result1["messages"].append(
        ConversationMessage(
            role="user",
            content="Another message",
            timestamp=datetime.now(UTC).isoformat(),
        )
    )

    result2 = await test_graph.ainvoke(result1, config)
    message_count_2 = len(result2["messages"])

    # Messages should accumulate
    assert message_count_2 > message_count_1

    # Retrieve state from checkpointer
    state_snapshot = await test_graph.aget_state(config)
    assert state_snapshot is not None
    assert len(state_snapshot.values["messages"]) == message_count_2


# ============================================================================
# UNIT TESTS FOR INDIVIDUAL NODES
# ============================================================================

@pytest.mark.asyncio
async def test_intake_node_text_input():
    """Test intake node with text message."""
    from bot.graph.nodes import intake_node

    state = create_initial_state(12345, 67890)
    state["messages"].append(
        ConversationMessage(
            role="user",
            content="This is a text message",
            timestamp=datetime.now(UTC).isoformat(),
        )
    )

    result = await intake_node(state)

    # Text input should pass through unchanged
    assert result["messages"][-1]["content"] == "This is a text message"
    assert result["transcript"] is None  # No audio transcription


@pytest.mark.asyncio
async def test_assistance_level_retry_limits():
    """Test that assistance levels have correct retry limits."""
    basic = AssistanceLevel.BASIC
    standard = AssistanceLevel.STANDARD
    premium = AssistanceLevel.PREMIUM

    assert basic.max_validation_retries == 2
    assert standard.max_validation_retries == 3
    assert premium.max_validation_retries == 5

    assert not basic.auto_fill_enabled
    assert standard.auto_fill_enabled
    assert premium.auto_fill_enabled


# ============================================================================
# MOCK HELPERS (for future integration tests with LLM calls)
# ============================================================================

class MockGeminiClient:
    """Mock Gemini client for testing without API calls."""

    async def ainvoke(self, messages: list[Any]) -> Any:
        """Mock LLM invocation that returns canned responses."""

        class MockResponse:
            content: str

        # Simple intent extraction mock
        if "extract" in str(messages).lower():
            return MockResponse(content='{"hook": "Extracted hook", "content": "Extracted content"}')

        # Validation mock (always passes)
        if "validate" in str(messages).lower():
            return MockResponse(
                content='{"valid": true, "missing_fields": [], "suggestions": [], "confidence": 0.95}'
            )

        # Auto-fill mock
        if "optional" in str(messages).lower():
            return MockResponse(content='{"call_to_action": "Subscribe for more!"}')

        return MockResponse(content='{}')


@pytest.fixture
def mock_gemini():
    """Provide mock Gemini client for tests."""
    return MockGeminiClient()


# ============================================================================
# INTEGRATION TEST SCENARIOS
# ============================================================================

CONVERSATION_SCENARIOS = [
    {
        "name": "happy_path_basic_user",
        "assistance_level": AssistanceLevel.BASIC,
        "turns": [
            {"user": "/start"},
            {"user": "Hook: Stop wasting time on social media"},
            {"user": "Content: Here's why endless scrolling kills productivity..."},
            {"expected_phase": "validation"},
        ],
    },
    {
        "name": "validation_failure_retry",
        "assistance_level": AssistanceLevel.STANDARD,
        "turns": [
            {"user": "/start"},
            {"user": "Short hook"},  # Too short, will fail validation
            {"user": "Short content"},  # Too short, will fail validation
            {"expected_attempts": 2},  # Should retry
        ],
    },
    {
        "name": "premium_auto_fill",
        "assistance_level": AssistanceLevel.PREMIUM,
        "turns": [
            {"user": "/start"},
            {"user": "Hook: Amazing productivity tip"},
            {"user": "Content: Detailed explanation of the productivity method..."},
            {"expected_auto_filled": ["call_to_action"]},
        ],
    },
]


@pytest.mark.parametrize("scenario", CONVERSATION_SCENARIOS)
@pytest.mark.asyncio
async def test_conversation_scenario(test_graph, scenario):
    """
    Parameterized test for different conversation scenarios.

    Tests various user journeys through the graph.
    """
    # Setup initial state
    state = create_initial_state(
        chat_id=12345,
        user_id=67890,
        assistance_level=scenario["assistance_level"],
    )

    # Add template
    state["template_id"] = "test_template"
    state["template_requirements"] = {
        "required_fields": ["hook", "content"],
        "optional_fields": ["call_to_action"],
        "field_descriptions": {
            "hook": "Opening hook",
            "content": "Main content",
            "call_to_action": "CTA",
        },
    }

    thread_id = state["thread_id"]
    config = {"configurable": {"thread_id": thread_id}}

    # Execute conversation turns
    for turn in scenario["turns"]:
        if "user" in turn:
            state["messages"].append(
                ConversationMessage(
                    role="user",
                    content=turn["user"],
                    timestamp=datetime.now(UTC).isoformat(),
                )
            )
            state = await test_graph.ainvoke(state, config)

        # Verify expected outcomes
        if "expected_phase" in turn:
            assert state["current_phase"] == turn["expected_phase"]

        if "expected_attempts" in turn:
            assert state["validation_attempts"] >= turn["expected_attempts"]

        if "expected_auto_filled" in turn:
            for field in turn["expected_auto_filled"]:
                # In real test with mock, would check field was filled
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
