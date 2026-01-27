from __future__ import annotations

import logging

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes
from bot.graph.state import create_initial_state
from bot.handlers.commands import get_graph
from bot.templates.client import TemplateClient

logger = logging.getLogger(__name__)


def _build_template_keyboard(templates: list) -> InlineKeyboardMarkup:
    """Build inline keyboard from template list."""
    buttons = []
    for template in templates:
        duration_range = f"{template.get('min_seconds', '?')}-{template.get('max_seconds', '?')}s"
        button_text = f"{template['name']} ({duration_range})"
        callback_data = f"template:{template['id']}"
        buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    return InlineKeyboardMarkup(buttons)


def _soundtrack_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Sin música", callback_data="music:none"),
                InlineKeyboardButton("Lofi 1", callback_data="music:lofi1"),
            ],
            [
                InlineKeyboardButton("Lofi 2", callback_data="music:lofi2"),
                InlineKeyboardButton("Corporate 1", callback_data="music:corp1"),
            ],
        ]
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.callback_query:
        return

    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id if query.message else None
    if chat_id is None:
        return

    data = query.data or ""

    try:
        if data.startswith("template:"):
            template_id = data.split(":", 1)[1]

            logger.info(
                "template_selected",
                extra={
                    "chat_id": chat_id,
                    "template_id": template_id,
                }
            )

            try:
                client = TemplateClient()
                template_spec = await client.get_template_spec(template_id)
            except Exception as e:
                logger.exception(f"Failed to fetch template {template_id}")
                await query.message.reply_text(f"❌ Error al cargar template: {str(e)}")
                return

            if not template_spec:
                logger.error(f"Template {template_id} not found")
                await query.message.reply_text("❌ Template no encontrado. Intenta de nuevo.")
                return

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

            graph = await get_graph()
            thread_id = f"{chat_id}:{update.effective_user.id}"
            state = await graph.get_state(thread_id) or create_initial_state(chat_id, update.effective_user.id)

            state["template_id"] = template_id
            state["template_spec"] = template_spec.to_dict()
            state["template_requirements"] = {
                "required_fields": required_fields,
                "optional_fields": optional_fields or ["call_to_action"],
                "field_descriptions": field_descriptions,
            }
            state["current_phase"] = "collection"

            await query.message.reply_text(f"✅ Template seleccionado: {template_spec.name}")

            prev_len = len(state["messages"])
            result = await graph.invoke(state, thread_id)
            new_messages = result["messages"][prev_len:]
            for msg in new_messages:
                if msg["role"] == "assistant":
                    await query.message.reply_text(msg["content"])
            return

        if data.startswith("music:"):
            await query.message.reply_text(
                "🎵 La selección de soundtrack está temporalmente deshabilitada "
                "mientras migramos el flujo a LangGraph."
            )

            return

    except Exception:
        logger.exception("Error handling callback")
        await query.message.reply_text("⚠️ Ocurrió un error. Intenta de nuevo.")


async def send_template_selection(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send template selection keyboard to user."""
    try:
        logger.info(f"Fetching templates for chat {chat_id}")
        client = TemplateClient()
        templates = await client.get_template_summaries()
        logger.info(f"Retrieved {len(templates)} templates for chat {chat_id}")

        if not templates:
            logger.warning(f"No templates available for chat {chat_id}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ No se pudieron cargar los templates. Intenta más tarde."
            )
            return

        keyboard = _build_template_keyboard(templates)
        logger.info(f"Sending template keyboard with {len(templates)} options to chat {chat_id}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Guion final confirmado. Ahora elige un template:",
            reply_markup=keyboard
        )
        logger.info(f"Template selection sent successfully to chat {chat_id}")
    except Exception:
        logger.exception(f"Error sending template selection to chat {chat_id}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Error al cargar templates. Intenta de nuevo."
        )
