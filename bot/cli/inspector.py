"""
State inspection and JSON formatting utilities.

Pretty-prints conversation state and structured data for debugging.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from dataclasses import asdict

from bot.state.models import Conversation, BotState


class StateInspector:
    """
    Formats and displays conversation state for debugging.
    """

    @staticmethod
    def format_conversation(convo: Conversation, verbose: bool = False) -> str:
        """
        Format conversation state as readable text.

        Args:
            convo: Conversation object
            verbose: If True, show all fields including None values

        Returns:
            Formatted string representation
        """
        lines = []
        lines.append("╔══════════════════════════════════════════╗")
        lines.append("║        CONVERSATION STATE                ║")
        lines.append("╚══════════════════════════════════════════╝")
        lines.append("")
        lines.append(f"🔄 State: {convo.state.value}")
        lines.append("")

        # Core fields
        if convo.transcript:
            lines.append("📝 Transcript:")
            lines.append(f"   {StateInspector._truncate(convo.transcript, 100)}")
            lines.append("")

        if convo.mediated_text:
            lines.append("🤖 Mediated Text:")
            lines.append(f"   {StateInspector._truncate(convo.mediated_text, 100)}")
            lines.append("")

        if convo.script_draft:
            lines.append("📄 Script Draft:")
            lines.append(f"   {StateInspector._truncate(str(convo.script_draft), 100)}")
            lines.append("")

        if convo.final_script:
            lines.append("✅ Final Script:")
            lines.append(f"   {StateInspector._truncate(str(convo.final_script), 100)}")
            lines.append("")

        # Template system
        if convo.template_id:
            lines.append(f"📋 Template: {convo.template_id}")
            lines.append("")

        if convo.soundtrack_id:
            lines.append(f"🎵 Soundtrack: {convo.soundtrack_id}")
            lines.append("")

        # Render plan
        if convo.render_plan:
            lines.append("🎬 Render Plan:")
            plan_id = convo.render_plan.get("render_plan_id", "unknown")
            duration = convo.render_plan.get("total_duration", 0)
            num_scenes = len(convo.render_plan.get("scenes", []))
            lines.append(f"   ID: {plan_id[:16]}...")
            lines.append(f"   Duration: {duration}s")
            lines.append(f"   Scenes: {num_scenes}")
            lines.append("")

        if verbose:
            lines.append("─" * 44)
            lines.append("VERBOSE MODE - All Fields:")
            lines.append("─" * 44)
            # Show all fields including None (handle slots=True dataclass)
            convo_dict = asdict(convo) if hasattr(convo, '__dataclass_fields__') else convo.__dict__
            for key, value in convo_dict.items():
                if value is not None:
                    lines.append(f"{key}: {StateInspector._truncate(str(value), 80)}")
                else:
                    lines.append(f"{key}: None")

        return "\n".join(lines)

    @staticmethod
    def format_json(data: Any, indent: int = 2) -> str:
        """
        Format data as pretty-printed JSON.

        Args:
            data: Data to format (dict, list, or JSON-serializable object)
            indent: JSON indentation level

        Returns:
            Formatted JSON string
        """
        # Convert dataclass to dict (handles slots=True)
        if hasattr(data, '__dataclass_fields__'):
            data = asdict(data)
        elif hasattr(data, '__dict__'):
            data = data.__dict__

        try:
            return json.dumps(data, indent=indent, ensure_ascii=False, default=str)
        except Exception as e:
            return f"<Error formatting JSON: {e}>"

    @staticmethod
    def format_state_transition(
        from_state: BotState,
        to_state: BotState,
        event: str,
        payload_preview: Optional[str] = None
    ) -> str:
        """
        Format a state transition for logging.

        Args:
            from_state: Previous state
            to_state: New state
            event: Event that triggered transition
            payload_preview: Optional preview of payload

        Returns:
            Formatted transition string
        """
        lines = []
        lines.append("┌─────────────────────────────────────────┐")
        lines.append("│         STATE TRANSITION                │")
        lines.append("└─────────────────────────────────────────┘")
        lines.append(f"  {from_state.value}")
        lines.append(f"    ↓ [{event}]")
        lines.append(f"  {to_state.value}")

        if payload_preview:
            lines.append("")
            lines.append(f"  Payload: {StateInspector._truncate(payload_preview, 60)}")

        return "\n".join(lines)

    @staticmethod
    def format_render_plan(render_plan: Dict[str, Any]) -> str:
        """
        Format render plan with highlighted sections.

        Args:
            render_plan: Render plan dictionary

        Returns:
            Formatted string
        """
        lines = []
        lines.append("╔══════════════════════════════════════════╗")
        lines.append("║           RENDER PLAN                    ║")
        lines.append("╚══════════════════════════════════════════╝")
        lines.append("")

        # Overview
        lines.append(f"ID:       {render_plan.get('render_plan_id', 'unknown')}")
        lines.append(f"Duration: {render_plan.get('total_duration', 0)}s")

        # Resolution
        resolution = render_plan.get("resolution", {})
        lines.append(f"Size:     {resolution.get('width')}x{resolution.get('height')} @ {resolution.get('fps')}fps")
        lines.append("")

        # Audio tracks
        audio_tracks = render_plan.get("audio_tracks", [])
        lines.append(f"🎵 Audio Tracks: {len(audio_tracks)}")
        for track in audio_tracks:
            lines.append(f"   - {track.get('track_id')}: vol={track.get('volume')}")
        lines.append("")

        # Scenes
        scenes = render_plan.get("scenes", [])
        lines.append(f"🎬 Scenes: {len(scenes)}")
        for i, scene in enumerate(scenes[:3]):  # Show first 3
            visual = scene.get("visual", {})
            lines.append(f"   {i}: {scene.get('start_time')}s → {scene.get('start_time') + scene.get('duration')}s")
            lines.append(f"      {StateInspector._truncate(visual.get('prompt', 'No prompt'), 60)}")
        if len(scenes) > 3:
            lines.append(f"   ... and {len(scenes) - 3} more scenes")
        lines.append("")

        # Output
        output = render_plan.get("output", {})
        lines.append(f"📦 Output: {output.get('filename', 'unknown')}")
        lines.append(f"   Format: {output.get('container')} / {output.get('codec')}")

        return "\n".join(lines)

    @staticmethod
    def _truncate(text: str, max_length: int) -> str:
        """Truncate text to max length with ellipsis."""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."


def print_separator(title: Optional[str] = None):
    """Print a visual separator with optional title."""
    if title:
        print(f"\n{'═' * 20} {title} {'═' * 20}\n")
    else:
        print("\n" + "─" * 50 + "\n")


def print_json(data: Any, title: Optional[str] = None):
    """Print JSON with title and formatting."""
    if title:
        print(f"\n📋 {title}")
        print("─" * 50)
    print(StateInspector.format_json(data))
    print()
