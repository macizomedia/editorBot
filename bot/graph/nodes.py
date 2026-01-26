"""
Core LangGraph nodes for EditorBot workflow.

Each node is a pure function: GraphState → GraphState
Nodes perform one responsibility and update state immutably.
"""

import logging
import re
from datetime import datetime, UTC
from typing import Any

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .state import (
    GraphState,
    ConversationMessage,
    ValidationResult,
    AssistanceLevel,
)
from ..templates.client import TemplateClient
from ..handlers.render_plan import build_render_plan, format_render_plan_summary

logger = logging.getLogger(__name__)


# ============================================================================
# INTAKE NODE: Process user input (voice or text)
# ============================================================================

async def intake_node(state: GraphState) -> GraphState:
    """
    Process incoming voice or text message.

    - If voice: transcribe → mediate → add to messages
    - If text: add directly to messages
    - Updates transcript and mediated_text fields
    """
    logger.info(f"[INTAKE] Processing input for thread {state['thread_id']}")

    # Get latest message from conversation history
    if not state["messages"]:
        logger.warning("[INTAKE] No messages found, returning state unchanged")
        return state

    latest_msg = state["messages"][-1]

    # Voice is pre-processed in the handler; avoid trying to transcribe S3 paths here.
    if state.get("audio_s3_path") and not state.get("transcript"):
        logger.warning(
            "[INTAKE] audio_s3_path set without transcript; "
            "voice should be processed in the handler."
        )
        return state

    # Text input already added to messages, just return
    logger.info("[INTAKE] Text message processed, moving to next node")
    return state


# ============================================================================
# TEMPLATE SUGGEST NODE: Propose templates based on user idea
# ============================================================================

async def template_suggest_node(state: GraphState) -> GraphState:
    """
    Suggest templates based on user's mediated text.

    - Fetch templates from API
    - Rank by simple keyword overlap
    - Store top candidates in state
    - Add assistant message with options
    """
    if state.get("template_id"):
        return state

    idea_text = (state.get("mediated_text") or "").strip()
    client = TemplateClient()
    templates = await client.get_template_summaries()

    ranked = _rank_templates(templates, idea_text)
    top = ranked[:5]

    if not top:
        return {
            **state,
            "current_phase": "template_select",
            "messages": state["messages"] + [
                ConversationMessage(
                    role="assistant",
                    content=(
                        "⚠️ No pude cargar templates ahora mismo.\n"
                        "Intenta más tarde o usa /template para reintentar."
                    ),
                    timestamp=datetime.now(UTC).isoformat(),
                )
            ],
        }

    lines = ["🎯 Templates sugeridos:"]
    for tmpl in top:
        name = tmpl.get("name", "Unnamed")
        tid = tmpl.get("id", "unknown")
        desc = tmpl.get("description", "Sin descripción")
        lines.append(f"- {name} (`{tid}`): {desc}")

    lines.append("\nElige uno con: /template <id>")

    return {
        **state,
        "template_candidates": top,
        "current_phase": "template_select",
        "messages": state["messages"] + [
            ConversationMessage(
                role="assistant",
                content="\n".join(lines),
                timestamp=datetime.now(UTC).isoformat(),
                metadata={"template_candidates": [t.get("id") for t in top]},
            )
        ],
    }


# ============================================================================
# REQUIREMENT COLLECTOR NODE: Ask for missing fields
# ============================================================================

async def requirement_collector_node(state: GraphState) -> GraphState:
    """
    Collect required fields from user based on template requirements.

    - Checks which fields are missing from payload
    - Uses LLM to parse user's response and extract field values
    - Updates payload and determines next_field_to_collect
    - Routes back to collection or forward to validation
    """
    logger.info(f"[COLLECTOR] Starting collection for thread {state['thread_id']}")

    # Check if template is selected
    if not state.get("template_id") or not state.get("template_requirements"):
        logger.error("[COLLECTOR] No template selected, cannot collect requirements")
        return {
            **state,
            "current_phase": "error",
            "error_message": "Template must be selected before collection",
            "error_count": state["error_count"] + 1,
        }

    requirements = state["template_requirements"]
    payload = state["payload"]
    assistance_level = state["config"]["assistance_level"]

    # Determine which fields are still missing
    missing_required = [
        field for field in requirements["required_fields"]
        if not payload.get(field)
    ]

    missing_optional = [
        field for field in requirements.get("optional_fields", [])
        if not payload.get(field)
    ]

    logger.info(
        f"[COLLECTOR] Missing fields - Required: {missing_required}, "
        f"Optional: {missing_optional}"
    )

    # If user provided input, try to extract field values
    if state["messages"] and state["messages"][-1]["role"] == "user":
        latest_input = state["messages"][-1]["content"]

        # Use LLM to parse user input and extract field values
        extracted_fields = await extract_fields_from_input(
            user_input=latest_input,
            missing_fields=missing_required + missing_optional,
            field_descriptions=requirements["field_descriptions"],
            assistance_level=assistance_level,
        )

        logger.info(f"[COLLECTOR] Extracted fields: {list(extracted_fields.keys())}")

        # Update payload with extracted fields
        updated_payload = {**payload, **extracted_fields}

        # Recompute missing fields
        missing_required = [
            field for field in requirements["required_fields"]
            if not updated_payload.get(field)
        ]
    else:
        updated_payload = payload

    # Determine next action
    if missing_required:
        # Still have required fields missing, ask for next one
        next_field = missing_required[0]
        field_desc = requirements["field_descriptions"].get(
            next_field, next_field.replace("_", " ").title()
        )

        prompt_message = ConversationMessage(
            role="assistant",
            content=f"📋 Please provide: **{field_desc}**",
            timestamp=datetime.now(UTC).isoformat(),
            metadata={"field_requested": next_field},
        )

        logger.info(f"[COLLECTOR] Requesting field: {next_field}")

        return {
            **state,
            "payload": updated_payload,
            "next_field_to_collect": next_field,
            "current_phase": "collection",
            "messages": state["messages"] + [prompt_message],
        }

    elif missing_optional and assistance_level.auto_fill_enabled:
        # Auto-fill optional fields using LLM if permitted
        logger.info("[COLLECTOR] Auto-filling optional fields for premium user")

        auto_filled = await auto_fill_optional_fields(
            payload=updated_payload,
            missing_optional=missing_optional,
            field_descriptions=requirements["field_descriptions"],
            template_spec=state["template_spec"],
        )

        updated_payload = {**updated_payload, **auto_filled}

    # All required fields collected, move to validation
    logger.info("[COLLECTOR] All required fields collected, moving to validation")

    return {
        **state,
        "payload": updated_payload,
        "next_field_to_collect": None,
        "current_phase": "validation",
        "messages": state["messages"] + [
            ConversationMessage(
                role="assistant",
                content="✅ All fields collected! Validating...",
                timestamp=datetime.now(UTC).isoformat(),
            )
        ],
    }


# ============================================================================
# VALIDATOR NODE: Self-correction loop with LLM reflection
# ============================================================================

async def validator_node(state: GraphState) -> GraphState:
    """
    Validate collected payload against template requirements using LLM.

    - Uses Gemini to review completeness and quality
    - Returns structured validation result
    - Increments validation_attempts counter
    - Routes back to collector if invalid (up to max retries)
    """
    logger.info(f"[VALIDATOR] Validating payload for thread {state['thread_id']}")

    assistance_level = state["config"]["assistance_level"]
    max_retries = assistance_level.max_validation_retries
    current_attempt = state["validation_attempts"] + 1

    logger.info(
        f"[VALIDATOR] Attempt {current_attempt}/{max_retries} "
        f"(assistance_level: {assistance_level.value})"
    )

    # Check if max retries exceeded
    if current_attempt > max_retries:
        logger.warning(
            f"[VALIDATOR] Max retries ({max_retries}) exceeded, "
            "triggering human-in-loop"
        )

        return {
            **state,
            "validation_attempts": current_attempt,
            "interrupt_for_human": True,
            "current_phase": "validation",
            "messages": state["messages"] + [
                ConversationMessage(
                    role="assistant",
                    content=(
                        f"⚠️ Validation failed after {max_retries} attempts. "
                        "Please review manually.\n\n"
                        "Commands: /reset (start over) | /skip (bypass validation)"
                    ),
                    timestamp=datetime.now(UTC).isoformat(),
                )
            ],
        }

    # Perform LLM validation
    validation_result = await validate_payload_with_llm(
        payload=state["payload"],
        template_spec=state["template_spec"],
        template_requirements=state["template_requirements"],
    )

    logger.info(
        f"[VALIDATOR] Validation result: valid={validation_result['valid']}, "
        f"confidence={validation_result['confidence']}"
    )

    if validation_result["valid"]:
        # Payload is valid, move to finalization
        logger.info("[VALIDATOR] Payload valid, moving to finalization")

        return {
            **state,
            "validation_result": validation_result,
            "validation_attempts": current_attempt,
            "current_phase": "finalized",
            "messages": state["messages"] + [
                ConversationMessage(
                    role="assistant",
                    content="✅ Validation successful! Generating render plan...",
                    timestamp=datetime.now(UTC).isoformat(),
                )
            ],
        }

    else:
        # Validation failed, route back to collector with feedback
        logger.info(
            f"[VALIDATOR] Validation failed: {validation_result['missing_fields']}"
        )

        feedback_message = "⚠️ Validation issues detected:\n\n"
        for suggestion in validation_result["suggestions"]:
            feedback_message += f"• {suggestion}\n"

        return {
            **state,
            "validation_result": validation_result,
            "validation_attempts": current_attempt,
            "current_phase": "collection",  # Route back to collector
            "messages": state["messages"] + [
                ConversationMessage(
                    role="assistant",
                    content=feedback_message,
                    timestamp=datetime.now(UTC).isoformat(),
                )
            ],
        }


# ============================================================================
# FINALIZE NODE: Generate render plan and exit
# ============================================================================

async def finalize_json_node(state: GraphState) -> GraphState:
    """
    Final node: payload validated and ready for render.

    - Returns finalized state with render plan
    - Marks conversation as complete
    """
    logger.info(f"[FINALIZE] Finalizing payload for thread {state['thread_id']}")

    template_spec = state.get("template_spec") or {}
    audio_source = state.get("audio_s3_path")

    if not state.get("script"):
        script = _build_script_from_payload(
            payload=state["payload"],
            template_spec=template_spec,
        )
    else:
        script = state["script"]

    if not audio_source:
        return {
            **state,
            "script": script,
            "current_phase": "finalized",
            "messages": state["messages"] + [
                ConversationMessage(
                    role="assistant",
                    content=(
                        "✅ Contenido validado, pero falta el audio original.\n"
                        "Envía un mensaje de voz para generar el render plan."
                    ),
                    timestamp=datetime.now(UTC).isoformat(),
                )
            ],
        }

    visual_strategy = {
        "soundtrack_id": None,
        "visual_prompts": {},
        "style_preset": "cinematic",
    }

    render_plan_json = await build_render_plan(
        final_script=script,
        template_id=state.get("template_id"),
        soundtrack_id=None,
        asset_config=visual_strategy,
        audio_source=audio_source,
    )

    summary = format_render_plan_summary(render_plan_json)

    return {
        **state,
        "script": script,
        "render_plan": render_plan_json,
        "current_phase": "finalized",
        "messages": state["messages"] + [
            ConversationMessage(
                role="assistant",
                content=(
                    "🎬 Render plan generado.\n\n"
                    f"{summary}\n\n"
                    "Listo para render. Usa /render para iniciar producción."
                ),
                timestamp=datetime.now(UTC).isoformat(),
            )
        ],
    }


# ============================================================================
# HELPER FUNCTIONS: LLM-powered extraction and validation
# ============================================================================

async def extract_fields_from_input(
    user_input: str,
    missing_fields: list[str],
    field_descriptions: dict[str, str],
    assistance_level: AssistanceLevel,
) -> dict[str, str]:
    """
    Use LLM to extract field values from user's natural language input.

    Few-shot examples guide the LLM to parse responses correctly.
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",  # Cheaper model for intent extraction
        temperature=0.1,
    )

    # Few-shot prompt with examples
    system_prompt = f"""You are a field extraction assistant.
Extract values for these fields from the user's input: {missing_fields}

Field descriptions:
{chr(10).join(f"- {field}: {field_descriptions.get(field, field)}" for field in missing_fields)}

Examples:
User: "My hook is: Why you're failing at content creation"
→ {{"hook": "Why you're failing at content creation"}}

User: "The main content should explain the 3 biggest mistakes"
→ {{"content": "The 3 biggest mistakes in content creation are..."}}

User: "Hook: Stop wasting time. Content: Here's why most creators fail..."
→ {{"hook": "Stop wasting time", "content": "Here's why most creators fail..."}}

Return ONLY a JSON object with extracted fields. If a field cannot be extracted, omit it.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input),
    ]

    response = await llm.ainvoke(messages)

    # Parse JSON response
    import json
    try:
        extracted = json.loads(response.content)
        logger.info(f"[EXTRACT] Successfully extracted: {list(extracted.keys())}")
        return extracted
    except json.JSONDecodeError:
        logger.warning(f"[EXTRACT] Failed to parse LLM response: {response.content}")
        return {}


async def auto_fill_optional_fields(
    payload: dict[str, str],
    missing_optional: list[str],
    field_descriptions: dict[str, str],
    template_spec: dict[str, Any],
) -> dict[str, str]:
    """
    Auto-fill missing optional fields using LLM inference (Premium users only).
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",  # Stronger model for generation
        temperature=0.3,
    )

    prompt = f"""Based on the provided content, generate values for these optional fields:

{chr(10).join(f"- {field}: {field_descriptions.get(field, field)}" for field in missing_optional)}

Existing content:
{chr(10).join(f"{k}: {v}" for k, v in payload.items())}

Template context: {template_spec.get('template_family', 'generic')} video

Generate ONLY a JSON object with the optional field values.
"""

    response = await llm.ainvoke([HumanMessage(content=prompt)])

    import json
    try:
        generated = json.loads(response.content)
        logger.info(f"[AUTO_FILL] Generated optional fields: {list(generated.keys())}")
        return generated
    except json.JSONDecodeError:
        logger.warning("[AUTO_FILL] Failed to parse generated fields")
        return {}


async def validate_payload_with_llm(
    payload: dict[str, str],
    template_spec: dict[str, Any],
    template_requirements: dict[str, Any],
) -> ValidationResult:
    """
    Use Gemini Pro to validate payload completeness and quality.

    Returns structured validation result with missing fields and suggestions.
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        temperature=0.0,  # Deterministic validation
    )

    prompt = f"""Validate this video content payload against the template requirements.

Template: {template_spec.get('template_family', 'unknown')}
Required fields: {template_requirements['required_fields']}
Optional fields: {template_requirements.get('optional_fields', [])}

Payload:
{chr(10).join(f"{k}: {v}" for k, v in payload.items())}

Check:
1. All required fields are present and non-empty
2. Content is appropriate for template type
3. Text length is reasonable (not too short/long)

Return JSON:
{{
  "valid": boolean,
  "missing_fields": ["field1", "field2"],
  "suggestions": ["specific feedback 1", "specific feedback 2"],
  "confidence": 0.0-1.0
}}
"""

    response = await llm.ainvoke([HumanMessage(content=prompt)])

    import json
    try:
        result = json.loads(response.content)
        return ValidationResult(
            valid=result["valid"],
            missing_fields=result.get("missing_fields", []),
            suggestions=result.get("suggestions", []),
            confidence=result.get("confidence", 0.8),
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"[VALIDATE] Failed to parse validation result: {e}")
        return ValidationResult(
            valid=False,
            missing_fields=[],
            suggestions=["Validation error: could not parse LLM response"],
            confidence=0.0,
        )


def _rank_templates(templates: list[dict[str, Any]], idea_text: str) -> list[dict[str, Any]]:
    if not idea_text:
        return templates

    tokens = set(re.findall(r"[a-zA-Záéíóúñü]+", idea_text.lower()))

    def score(tmpl: dict[str, Any]) -> int:
        hay = f"{tmpl.get('name', '')} {tmpl.get('description', '')}".lower()
        hits = sum(1 for tok in tokens if tok in hay)
        return hits

    return sorted(templates, key=score, reverse=True)


def _build_script_from_payload(
    payload: dict[str, Any],
    template_spec: dict[str, Any],
) -> dict[str, Any]:
    duration = template_spec.get("duration", {})
    target_seconds = duration.get("target_seconds", 45)

    script_structure = template_spec.get("script_structure", {})
    required_roles = script_structure.get("required_roles", [])
    optional_roles = script_structure.get("optional_roles", [])

    beats = []
    roles = required_roles + optional_roles
    usable_roles = []

    for role in roles:
        role_key = role.lower().replace(" ", "_")
        text = payload.get(role_key)
        if text:
            usable_roles.append((role_key, text))

    if not usable_roles:
        # Fallback: use any payload fields in order
        usable_roles = [(k, v) for k, v in payload.items() if v]

    if not usable_roles:
        raise ValueError("Cannot build script: payload is empty")

    beat_duration = max(3, int(target_seconds / len(usable_roles)))

    for role_key, text in usable_roles:
        beats.append(
            {
                "role": role_key,
                "text": text,
                "duration": beat_duration,
                "keywords": [],
            }
        )

    total_duration = sum(beat["duration"] for beat in beats)

    return {
        "total_duration": total_duration,
        "structure_type": "auto_generated",
        "beats": beats,
    }
