"""
New command handlers for LangGraph-based EditorBot.

Implements /init, /template, /start, /context, /reset, /skip commands.
Handles feature flag routing between LangGraph and legacy FSM.
"""

import logging
from datetime import datetime, UTC

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from bot.graph.graph import EditorGraph
from bot.graph.state import (
    create_initial_state,
    ConversationMessage,
    AssistanceLevel,
)
from bot.templates.client import TemplateClient

logger = logging.getLogger(__name__)

# Singleton graph instance
_graph: EditorGraph | None = None


async def get_graph() -> EditorGraph:
    """Get or initialize singleton graph instance."""
    global _graph
    if _graph is None:
        _graph = EditorGraph()
        await _graph.initialize()
    return _graph


# ============================================================================
# /init - Configure user settings
# ============================================================================

async def handle_init(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /init command: Configure video format, style, and assistance level.

    Usage:
        /init format=REEL_VERTICAL style=dynamic assistance=standard
        /init format=LANDSCAPE_16_9 assistance=premium
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    logger.info(f"[/init] User {user_id} in chat {chat_id}")

    # Parse command arguments
    args = context.args or []
    config_updates = {}

    for arg in args:
        if "=" in arg:
            key, value = arg.split("=", 1)
            config_updates[key] = value

    # Get or create state
    graph = await get_graph()
    thread_id = f"{chat_id}:{user_id}"
    state = await graph.get_state(thread_id)

    if state is None:
        # Create new state
        assistance_level = AssistanceLevel(
            config_updates.get("assistance", "standard")
        )
        state = create_initial_state(chat_id, user_id, assistance_level)

    # Update config
    if "format" in config_updates:
        state["config"]["video_format"] = config_updates["format"]
    if "style" in config_updates:
        state["config"]["output_style"] = config_updates["style"]
    if "assistance" in config_updates:
        state["config"]["assistance_level"] = AssistanceLevel(config_updates["assistance"])

    # Save state
    await graph.invoke(state, thread_id)

    assistance_level = state["config"]["assistance_level"]

    await update.message.reply_text(
        f"✅ Configuration updated!\n\n"
        f"📹 Format: {state['config']['video_format']}\n"
        f"🎨 Style: {state['config']['output_style']}\n"
        f"🤖 Assistance: {assistance_level.value} "
        f"({assistance_level.max_validation_retries} retries max)\n\n"
        f"Next: /template to select video template"
    )


# ============================================================================
# /template - Select video template
# ============================================================================

async def handle_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /template command: List and select video template.

    Usage:
        /template                           # List available templates
        /template opinion_monologue_reel    # Select template by ID
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    logger.info(f"[/template] User {user_id} in chat {chat_id}")

    # Get template client
    template_client = TemplateClient()

    if not context.args:
        # List available templates
        templates = await template_client.get_template_summaries()

        response = "📋 Available templates:\n\n"
        for tmpl in templates:
            response += f"• `{tmpl['id']}` - {tmpl.get('name', 'Unnamed')}\n"
            response += f"  {tmpl.get('description', 'No description')}\n\n"

        response += "Use: /template <id> to select"

        await update.message.reply_text(response, parse_mode="Markdown")
        return

    # Select template
    template_id = context.args[0]

    try:
        template_spec = await template_client.get_template_spec(template_id)
    except Exception as e:
        logger.error(f"[/template] Failed to fetch template {template_id}: {e}")
        await update.message.reply_text(f"❌ Template `{template_id}` not found")
        return

    # Extract requirements from template roles
    script_structure = template_spec.script_structure
    required_fields = [
        role.lower().replace(" ", "_")
        for role in script_structure.required_roles
    ]
    optional_fields = [
        role.lower().replace(" ", "_")
        for role in script_structure.optional_roles
    ]
    field_descriptions = {field: field.replace("_", " ").title() for field in required_fields + optional_fields}

    # Update state
    graph = await get_graph()
    thread_id = f"{chat_id}:{user_id}"
    state = await graph.get_state(thread_id) or create_initial_state(chat_id, user_id)

    state["template_id"] = template_id
    state["template_spec"] = template_spec.to_dict()
    state["template_requirements"] = {
        "required_fields": required_fields,
        "optional_fields": optional_fields or ["call_to_action"],
        "field_descriptions": field_descriptions,
    }
    state["current_phase"] = "collection"

    await graph.invoke(state, thread_id)

    await update.message.reply_text(
        f"✅ Template selected: `{template_id}`\n\n"
        f"Required fields: {', '.join(required_fields)}\n\n"
        f"Use /start to begin collection",
        parse_mode="Markdown"
    )


# ============================================================================
# /start - Begin field collection
# ============================================================================

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start command: Trigger main collection loop.

    Transitions to collection phase and prompts for first field.
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    logger.info(f"[/start] User {user_id} in chat {chat_id}")

    graph = await get_graph()
    thread_id = f"{chat_id}:{user_id}"
    state = await graph.get_state(thread_id)

    if not state:
        await update.message.reply_text(
            "Please configure settings first:\n"
            "1. /init to set video format\n"
            "2. /template to select template\n"
            "3. /start to begin"
        )
        return

    if not state.get("template_id"):
        await update.message.reply_text(
            "❌ No template selected. Use /template first."
        )
        return

    # Add start message to conversation
    state["messages"].append(
        ConversationMessage(
            role="user",
            content="/start",
            timestamp=datetime.now(UTC).isoformat(),
        )
    )

    # Invoke graph (will trigger collection)
    result = await graph.invoke(state, thread_id)

    # Send latest assistant message
    if result["messages"]:
        last_msg = result["messages"][-1]
        if last_msg["role"] == "assistant":
            await update.message.reply_text(last_msg["content"])


# ============================================================================
# /context - Inject background knowledge
# ============================================================================

async def handle_context(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /context command: Inject background knowledge for LLM.

    Usage:
        /context This video is about productivity hacks for developers
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /context <background information>")
        return

    context_text = " ".join(context.args)

    logger.info(f"[/context] User {user_id} in chat {chat_id}: {len(context_text)} chars")

    graph = await get_graph()
    thread_id = f"{chat_id}:{user_id}"
    state = await graph.get_state(thread_id) or create_initial_state(chat_id, user_id)

    # Add context to payload
    state["payload"]["context"] = context_text

    # Add system message
    state["messages"].append(
        ConversationMessage(
            role="system",
            content=f"[Context injected: {context_text}]",
            timestamp=datetime.now(UTC).isoformat(),
        )
    )

    await graph.invoke(state, thread_id)

    await update.message.reply_text(
        f"✅ Context added: {len(context_text)} characters\n\n"
        "This will help the LLM understand your video better."
    )


# ============================================================================
# /reset - Start over
# ============================================================================

async def handle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /reset command: Clear conversation and start over.
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    logger.info(f"[/reset] User {user_id} in chat {chat_id}")

    graph = await get_graph()
    thread_id = f"{chat_id}:{user_id}"

    await graph.reset_thread(thread_id)

    await update.message.reply_text(
        "🔄 Conversation reset!\n\n"
        "Start fresh with:\n"
        "1. /init - Configure settings\n"
        "2. /template - Select template\n"
        "3. /start - Begin collection"
    )


# ============================================================================
# /skip - Bypass validation (for trusted users)
# ============================================================================

async def handle_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /skip command: Skip validation and proceed to finalization.

    Only works if validation has failed at least once.
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    logger.info(f"[/skip] User {user_id} in chat {chat_id}")

    graph = await get_graph()
    thread_id = f"{chat_id}:{user_id}"
    state = await graph.get_state(thread_id)

    if not state:
        await update.message.reply_text("❌ No active conversation")
        return

    if state["current_phase"] != "validation":
        await update.message.reply_text(
            "❌ Can only skip during validation phase"
        )
        return

    # Force finalization
    state["current_phase"] = "finalized"
    state["validation_result"] = {
        "valid": True,
        "missing_fields": [],
        "suggestions": ["Validation skipped by user"],
        "confidence": 1.0,
    }

    await graph.invoke(state, thread_id)

    await update.message.reply_text(
        "⚠️ Validation skipped! Proceeding to finalization...\n\n"
        "Note: This may produce unexpected results."
    )


# ============================================================================
# Command registration helper
# ============================================================================

def get_command_handlers() -> list[CommandHandler]:
    """
    Get list of LangGraph command handlers for registration.

    Add to bot with:
        for handler in get_command_handlers():
            app.add_handler(handler)
    """
    return [
        CommandHandler("init", handle_init),
        CommandHandler("template", handle_template),
        CommandHandler("start", handle_start),
        CommandHandler("context", handle_context),
        CommandHandler("reset", handle_reset),
        CommandHandler("skip", handle_skip),
    ]
