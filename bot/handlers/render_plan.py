"""
Handler for building and validating render plans.

This module bridges the state machine and the render_plan domain layer.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Any

from bot.render_plan.builder import RenderPlanBuilder
from bot.render_plan.validator import validate_render_plan
from bot.render_plan.serializer import serialize_render_plan
from bot.templates.client import TemplateClient

logger = logging.getLogger(__name__)


async def build_render_plan(
    final_script: str,
    template_id: str,
    soundtrack_id: str | None,
    asset_config: Dict[str, Any] | None,
    audio_source: str,
) -> Dict[str, Any]:
    """
    Build and validate a render plan from conversation state.

    Args:
        final_script: JSON string or dict containing script with beats
        template_id: Selected template identifier
        soundtrack_id: Selected soundtrack (or None)
        asset_config: Visual generation configuration
        audio_source: S3 path or local path to narration audio

    Returns:
        Serialized RenderPlan as JSON-compatible dict

    Raises:
        ValueError: If render plan validation fails with fatal errors
    """
    # Step 1: Parse script if it's a string
    try:
        script_dict = json.loads(final_script) if isinstance(final_script, str) else final_script
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse final_script: {e}")
        raise ValueError(f"Invalid script JSON: {e}")
    logger.info(
        "render_plan_parsing_complete",
        extra={
            "script_beats": len(script_dict.get("beats", [])),
            "template_id": template_id,
            "has_soundtrack": soundtrack_id is not None,
        }
    )
    # Step 2: Fetch template specification
    template_client = TemplateClient()
    try:
        template_spec = template_client.get_template(template_id)
    except Exception as e:
        logger.error(f"Failed to fetch template {template_id}: {e}")
        raise ValueError(f"Template not found: {template_id}")

    # Step 3: Build visual strategy
    visual_strategy = {
        "soundtrack_id": soundtrack_id,
        "visual_prompts": asset_config.get("visual_prompts", {}) if asset_config else {},
        "style_preset": asset_config.get("style_preset") if asset_config else None,
    }

    # Step 4: Build render plan using domain logic
    builder = RenderPlanBuilder()
    try:
        render_plan = builder.build(
            script=script_dict,
            template=template_spec,
            visual_strategy=visual_strategy,
            audio_source=audio_source,
        )
    except Exception as e:
        logger.error(f"RenderPlanBuilder failed: {e}")
        raise ValueError(f"Failed to build render plan: {e}")

    # Step 5: Validate render plan
    validation_result = validate_render_plan(render_plan)

    if not validation_result.is_valid:
        # Log all errors
        for error in validation_result.fatal_errors:
            logger.error(f"FATAL: {error.message} (field: {error.field})")
        for warning in validation_result.warnings:
            logger.warning(f"WARNING: {warning.message} (field: {warning.field})")

        # Fail fast on fatal errors
        error_summary = "; ".join([e.message for e in validation_result.fatal_errors])
        logger.error(
            "render_plan_validation_failed",
            extra={
                "num_fatal_errors": len(validation_result.fatal_errors),
                "num_warnings": len(validation_result.warnings),
                "error_summary": error_summary,
            }
        )
        raise ValueError(f"Render plan validation failed: {error_summary}")

    # Log warnings (non-blocking)
    for warning in validation_result.warnings:
        logger.warning(f"Render plan warning: {warning.message} (field: {warning.field})")

    # Step 6: Serialize to JSON
    serialized = serialize_render_plan(render_plan)

    logger.info(
        f"Render plan generated successfully: {render_plan.render_plan_id} "
        f"({len(render_plan.scenes)} scenes, {render_plan.total_duration}s)"
    )

    return serialized


def format_render_plan_summary(render_plan_json: Dict[str, Any]) -> str:
    """
    Format a human-readable summary of a render plan for Telegram display.

    Args:
        render_plan_json: Serialized render plan

    Returns:
        Markdown-formatted summary string
    """
    plan_id = render_plan_json.get("render_plan_id", "unknown")
    duration = render_plan_json.get("total_duration", 0)
    num_scenes = len(render_plan_json.get("scenes", []))
    num_audio_tracks = len(render_plan_json.get("audio_tracks", []))
    resolution = render_plan_json.get("resolution", {})
    output = render_plan_json.get("output", {})

    summary = f"""
📋 *Render Plan Generated*

🆔 ID: `{plan_id[:12]}...`
⏱ Duration: {duration:.1f}s
🎬 Scenes: {num_scenes}
🎵 Audio Tracks: {num_audio_tracks}
📐 Resolution: {resolution.get('width')}x{resolution.get('height')} @ {resolution.get('fps')}fps
📦 Output: {output.get('filename', 'unknown')}

Ready to render. Use /render to start.
"""

    return summary.strip()
