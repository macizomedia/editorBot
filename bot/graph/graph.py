"""
LangGraph definition for EditorBot state machine.

Defines the graph structure, conditional routing, and checkpointing.
"""

import os
import logging
from typing import Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

try:
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    HAS_ASYNC_SQLITE = True
except (ImportError, ModuleNotFoundError):
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        HAS_ASYNC_SQLITE = False
    except (ImportError, ModuleNotFoundError):
        SqliteSaver = None
        HAS_ASYNC_SQLITE = False

from .state import GraphState, create_initial_state
from .nodes import (
    intake_node,
    template_suggest_node,
    requirement_collector_node,
    validator_node,
    finalize_json_node,
)

logger = logging.getLogger(__name__)


# ============================================================================
# CONDITIONAL ROUTING FUNCTIONS
# ============================================================================

def route_after_intake(state: GraphState) -> Literal["template_suggest", "collection", "error"]:
    """
    Route after intake node based on current phase.

    - If no template: prompt for template selection
    - If template selected: start collection
    - If error: halt
    """
    if state["current_phase"] == "error":
        return "error"

    if not state.get("template_id"):
        logger.info("[ROUTE] No template selected, routing to template_suggest")
        return "template_suggest"

    logger.info("[ROUTE] Template selected, routing to collection")
    return "collection"


def route_after_template_suggest(
    state: GraphState
) -> Literal["template_suggest", "error"]:
    """
    After suggesting templates, pause execution.
    """
    if state["current_phase"] == "error":
        return "error"
    return "template_suggest"


def route_after_collection(
    state: GraphState
) -> Literal["validation", "collection", "error"]:
    """
    Route after collection node.

    - If all fields collected: move to validation
    - If still collecting: loop back to collection (wait for user input)
    - If error: halt
    """
    if state["current_phase"] == "error":
        return "error"

    if state["current_phase"] == "validation":
        logger.info("[ROUTE] Collection complete, routing to validation")
        return "validation"

    logger.info("[ROUTE] Still collecting fields, staying in collection")
    return "collection"


def route_after_validation(
    state: GraphState
) -> Literal["finalize", "collection", "interrupt", "error"]:
    """
    Route after validation node (self-correction loop).

    - If valid: finalize
    - If invalid and under retry limit: back to collection
    - If max retries exceeded: interrupt for human
    - If error: halt
    """
    if state["current_phase"] == "error":
        return "error"

    if state.get("interrupt_for_human"):
        logger.info("[ROUTE] Human intervention required, interrupting")
        return "interrupt"

    if state["current_phase"] == "finalized":
        logger.info("[ROUTE] Validation passed, routing to finalize")
        return "finalize"

    # Validation failed, route back to collection for retry
    logger.info(
        f"[ROUTE] Validation failed (attempt {state['validation_attempts']}), "
        "routing back to collection"
    )
    return "collection"


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def create_editor_graph() -> StateGraph:
    """
    Create the LangGraph state machine for EditorBot.

    Graph structure:

                      ┌──────────┐
                      │  START   │
                      └────┬─────┘
                           │
                      ┌────▼─────┐
                      │  INTAKE  │ (voice/text processing)
                      └────┬─────┘
                           │
                    ┌──────▼───────┐
                    │ Route: Template?│
                    └──┬───────┬───┘
                       │       │
           ┌───────────▼──┐    │
           │ TEMPLATE_SELECT│   │ (template already selected)
           └───────────┬───┘    │
                       │        │
                  ┌────▼────────▼────┐
                  │  REQUIREMENT      │ ◄──┐ (self-correction loop)
                  │  COLLECTOR        │    │
                  └────┬──────────────┘    │
                       │                   │
                  ┌────▼─────┐             │
                  │ Route:    │             │
                  │ Complete? │             │
                  └──┬────┬───┘             │
                     │    │                 │
         ┌───────────▼──┐ │                 │
         │  VALIDATOR   │ │ (still collecting)
         └───────┬──────┘ │                 │
                 │        │                 │
            ┌────▼────┐   │                 │
            │ Route:  │   │                 │
            │ Valid?  │   │                 │
            └─┬───┬───┘   │                 │
              │   │       │                 │
    ┌─────────▼┐  └───────┴─────────────────┘ (invalid → retry)
    │ FINALIZE │
    └────┬─────┘
         │
    ┌────▼────┐
    │   END   │
    └─────────┘

    Checkpointing:
    - SqliteSaver persists state after each node
    - Thread resumption via thread_id
    - Human-in-loop interrupts at validation
    """
    logger.info("[GRAPH] Creating EditorBot state graph")

    # Initialize graph with state schema
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("intake", intake_node)
    workflow.add_node("template_suggest", template_suggest_node)
    workflow.add_node("collection", requirement_collector_node)
    workflow.add_node("validation", validator_node)
    workflow.add_node("finalize", finalize_json_node)

    # Set entry point
    workflow.set_entry_point("intake")

    # Add conditional edges
    workflow.add_conditional_edges(
        "intake",
        route_after_intake,
        {
            "template_suggest": "template_suggest",
            "collection": "collection",
            "error": END,
        }
    )

    workflow.add_conditional_edges(
        "template_suggest",
        route_after_template_suggest,
        {
            "template_suggest": END,
            "error": END,
        }
    )

    workflow.add_conditional_edges(
        "collection",
        route_after_collection,
        {
            "validation": "validation",
            "collection": "collection",  # Wait for more user input
            "error": END,
        }
    )

    workflow.add_conditional_edges(
        "validation",
        route_after_validation,
        {
            "finalize": "finalize",
            "collection": "collection",  # Retry collection with feedback
            "interrupt": END,  # Human-in-loop
            "error": END,
        }
    )

    # Finalize node terminates
    workflow.add_edge("finalize", END)

    logger.info("[GRAPH] Graph construction complete")

    return workflow


async def get_checkpointer():
    """
    Create checkpointer for persistent state.

    Tries (in order):
    1. Async SQLite saver (langgraph 0.3+)
    2. Sync SQLite saver (langgraph 0.2.x)
    3. Memory saver (fallback, data lost on restart)
    """
    db_path = os.getenv("CHECKPOINT_DB_PATH", "/app/data/checkpoints.db")
    logger.info(f"[CHECKPOINT] Initializing checkpointer at {db_path}")

    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    if HAS_ASYNC_SQLITE:
        try:
            logger.info("[CHECKPOINT] Using AsyncSqliteSaver (langgraph 0.3+)")
            checkpointer = AsyncSqliteSaver.from_conn_string(db_path)
            await checkpointer.setup()
            return checkpointer
        except Exception as e:
            logger.warning(f"[CHECKPOINT] AsyncSqliteSaver failed: {e}, falling back")

    if SqliteSaver:
        try:
            logger.info("[CHECKPOINT] Using SqliteSaver (langgraph 0.2.x)")
            checkpointer = SqliteSaver(db_path)
            return checkpointer
        except Exception as e:
            logger.warning(f"[CHECKPOINT] SqliteSaver failed: {e}, falling back")

    # Fallback to memory
    logger.warning("[CHECKPOINT] Using MemorySaver (data lost on restart!)")
    return MemorySaver()


# ============================================================================
# MAIN GRAPH INSTANCE (for import)
# ============================================================================

class EditorGraph:
    """
    Singleton wrapper for compiled LangGraph with checkpointing.

    Usage:
        graph = EditorGraph()
        result = await graph.invoke(state, thread_id="chat:user")
    """

    _instance = None
    _graph = None
    _checkpointer = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self):
        """Initialize graph and checkpointer (call once at startup)."""
        if self._graph is None:
            logger.info("[GRAPH] Initializing EditorGraph singleton")

            workflow = create_editor_graph()
            self._checkpointer = await get_checkpointer()
            self._graph = workflow.compile(checkpointer=self._checkpointer)

            logger.info("[GRAPH] Graph compiled with checkpointing enabled")

    async def invoke(
        self,
        state: GraphState,
        thread_id: str,
    ) -> GraphState:
        """
        Execute graph with checkpointing.

        Args:
            state: Current graph state
            thread_id: Unique thread ID (f"{chat_id}:{user_id}")

        Returns:
            Updated state after graph execution
        """
        if self._graph is None:
            await self.initialize()

        config = {"configurable": {"thread_id": thread_id}}

        logger.info(f"[GRAPH] Invoking graph for thread {thread_id}")
        result = await self._graph.ainvoke(state, config)

        return result

    async def stream(
        self,
        state: GraphState,
        thread_id: str,
    ):
        """
        Stream graph execution for real-time updates.

        Yields state updates as each node completes.
        """
        if self._graph is None:
            await self.initialize()

        config = {"configurable": {"thread_id": thread_id}}

        logger.info(f"[GRAPH] Streaming graph execution for thread {thread_id}")

        async for chunk in self._graph.astream(state, config):
            yield chunk

    async def get_state(self, thread_id: str) -> GraphState | None:
        """
        Retrieve persisted state for a thread.

        Returns None if thread has no saved state.
        """
        if self._checkpointer is None:
            await self.initialize()

        config = {"configurable": {"thread_id": thread_id}}
        state_snapshot = await self._graph.aget_state(config)

        return state_snapshot.values if state_snapshot else None

    async def reset_thread(self, thread_id: str):
        """
        Clear persisted state for a thread (implements /reset command).
        """
        if self._checkpointer is None:
            await self.initialize()

        config = {"configurable": {"thread_id": thread_id}}

        # LangGraph doesn't have native reset, so we'll save an empty state
        # This effectively resets the conversation
        logger.info(f"[GRAPH] Resetting thread {thread_id}")

        # Extract chat_id and user_id from thread_id
        chat_id, user_id = thread_id.split(":")
        initial_state = create_initial_state(int(chat_id), int(user_id))

        await self._graph.aupdate_state(config, initial_state)
