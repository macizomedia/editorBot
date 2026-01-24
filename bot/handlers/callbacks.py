from __future__ import annotations

import logging

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes

from bot.state.machine import handle_event, EventType
from bot.state.models import BotState
from bot.state.runtime import get_conversation, save_conversation
from bot.templates.client import TemplateClient
from bot.templates.validator import validate_script
from bot.templates.models import TemplateSpec
from bot.handlers.render_plan import build_render_plan, format_render_plan_summary

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

    convo = get_conversation(chat_id)
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

            # Fetch full template specification
            try:
                client = TemplateClient()
                template_spec = client.get_template(template_id)
            except Exception as e:
                logger.exception(f"Failed to fetch template {template_id}")
                await query.message.reply_text(f"❌ Error al cargar template: {str(e)}")
                return

            if not template_spec:
                logger.error(f"Template {template_id} not found")
                await query.message.reply_text("❌ Template no encontrado. Intenta de nuevo.")
                return

            # Validate script against template
            if convo.final_script:
                # Parse final_script if it's a string
                script_data = convo.final_script
                if isinstance(script_data, str):
                    try:
                        import json
                        script_data = json.loads(script_data)
                    except:
                        # If parsing fails, create minimal structure for validation
                        script_data = {'total_duration': 0, 'structure_type': 'unknown', 'beats': []}

                result = validate_script(script_data, template_spec)

                # Store validation result
                convo.validation_result = result.to_dict()

                # Handle validation result based on enforcement policy
                if not result.passed and template_spec.enforcement.strict:
                    # Strict template: reject if validation fails
                    error_msg = f"❌ Este guión NO es compatible con {template_spec.name}\n\nProblemas detectados:\n"
                    for error in result.errors[:5]:  # Limit to first 5 errors
                        error_msg += f"• {error}\n"
                    error_msg += "\nOpciones:\n"
                    error_msg += "Escribe EDITAR para modificar el guión\n"
                    error_msg += "O selecciona otro template"

                    await query.message.reply_text(error_msg)
                    return

                elif result.warnings and not result.passed:
                    # Flexible template with warnings
                    warning_msg = f"⚠️ Template: {template_spec.name} (modo flexible)\n\nSugerencias de mejora:\n"
                    for warning in result.warnings[:3]:
                        warning_msg += f"• {warning}\n"
                    if result.errors:
                        warning_msg += "\nProblemas detectados:\n"
                        for error in result.errors[:3]:
                            warning_msg += f"• {error}\n"
                    warning_msg += "\n¿Continuar de todas formas? (OK/EDITAR)"

                    await query.message.reply_text(warning_msg)
                    # Allow continuation even with warnings

                # Success case
                success_msg = f"✅ Template seleccionado: {template_spec.name}\n\n"
                if result.passed:
                    success_msg += "Tu guión cumple con todos los requisitos.\n"
                success_msg += "\nAhora elige una banda sonora..."

            # Update conversation - transition to SELECT_SOUNDTRACK state
            convo = handle_event(convo, EventType.TEMPLATE_SELECTED, template_id)
            convo.template_spec = template_spec.to_dict()

            # Add explicit state transition to SELECT_SOUNDTRACK before sending keyboard
            convo.state = BotState.SELECT_SOUNDTRACK
            save_conversation(chat_id, convo)

            await query.message.reply_text(
                success_msg if convo.final_script else f"✅ Template seleccionado: {template_spec.name}\n\n🎵 Selecciona un soundtrack:",
                reply_markup=_soundtrack_keyboard()
            )
            return

        if data.startswith("music:"):
            soundtrack_id = data.split(":", 1)[1]

            logger.info(
                "soundtrack_selected",
                extra={
                    "chat_id": chat_id,
                    "soundtrack_id": soundtrack_id,
                }
            )

            convo = handle_event(convo, EventType.SOUNDTRACK_SELECTED, soundtrack_id)
            save_conversation(chat_id, convo)

            # Trigger asset configuration (for now, use default config)
            default_asset_config = {
                "visual_prompts": {},
                "style_preset": "cinematic"
            }
            convo = handle_event(convo, EventType.ASSETS_CONFIGURED, default_asset_config)
            save_conversation(chat_id, convo)

            # Build render plan
            await query.message.reply_text("⚙️ Generando plan de render...")

            try:
                # Use audio path from conversation (saved when voice was processed)
                if not convo.audio_s3_path:
                    logger.error("Audio S3 path not available in conversation")
                    await query.message.reply_text(
                        "❌ Error: Archivo de audio no disponible. Intenta de nuevo."
                    )
                    return

                render_plan_json = await build_render_plan(
                    final_script=convo.final_script,
                    template_id=convo.template_id,
                    soundtrack_id=soundtrack_id if soundtrack_id != "none" else None,
                    asset_config=default_asset_config,
                    audio_source=convo.audio_s3_path,
                )

                # Save to conversation state
                convo = handle_event(convo, EventType.RENDER_PLAN_BUILT, render_plan_json)
                convo.visual_strategy = {
                    "soundtrack_id": soundtrack_id,
                    "visual_prompts": default_asset_config.get("visual_prompts", {}),
                    "style_preset": default_asset_config.get("style_preset"),
                }
                save_conversation(chat_id, convo)

                # Send summary
                summary = format_render_plan_summary(render_plan_json)
                await query.message.reply_text(summary, parse_mode="Markdown")

            except ValueError as e:
                logger.error(f"Render plan generation failed: {e}")
                await query.message.reply_text(
                    f"❌ Error generando render plan: {e}\n\n"
                    "Por favor revisa el guión y template e intenta de nuevo."
                )
            except Exception:
                logger.exception("Unexpected error building render plan")
                await query.message.reply_text("⚠️ Error inesperado. Intenta de nuevo.")

            return

    except Exception:
        logger.exception("Error handling callback")
        await query.message.reply_text("⚠️ Ocurrió un error. Intenta de nuevo.")


async def send_template_selection(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send template selection keyboard to user."""
    try:
        logger.info(f"Fetching templates for chat {chat_id}")
        client = TemplateClient()
        templates = client.list_templates()
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
