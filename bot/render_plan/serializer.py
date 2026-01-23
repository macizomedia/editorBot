"""
Render Plan Serializer

Converts RenderPlan domain objects to/from JSON.

Design Principles:
- No business logic (pure transformation)
- No mutation (immutable inputs/outputs)
- Stable output ordering (consistent JSON structure)
- Type-safe conversions

Why serialization is isolated:
- Separates domain models from wire format
- Enables format changes without touching domain logic
- Makes testing easier (can compare JSON snapshots)
- Enables replay/debugging (can save/load plans from disk)
- Supports multiple output formats (could add YAML, protobuf, etc.)

Serialization Strategy:
- Convert dataclasses to dicts recursively
- Preserve field names exactly (no camelCase conversion)
- Include all fields (no filtering)
- Order fields logically (metadata first, data second)
"""

from __future__ import annotations

from typing import Dict, Any, List

from .models import (
    RenderPlan,
    Resolution,
    AudioTrack,
    Scene,
    Visual,
    Overlay,
    Transition,
    Subtitles,
    SubtitleSegment,
    Output,
)


def serialize_render_plan(plan: RenderPlan) -> Dict[str, Any]:
    """
    Convert RenderPlan to JSON-compatible dict.

    This is the primary serialization entry point.

    Parameters:
    - plan: RenderPlan domain object

    Returns:
    Dict suitable for JSON.dumps() with stable key ordering

    Example output:
    {
        "render_plan_id": "rp-uuid",
        "format": "REEL_VERTICAL",
        "total_duration_seconds": 52.0,
        ...
    }
    """
    return {
        # Metadata (top-level identification)
        "render_plan_id": plan.render_plan_id,
        "format": plan.format,
        "total_duration_seconds": plan.total_duration_seconds,
        "fps": plan.fps,
        "resolution": _serialize_resolution(plan.resolution),
        # Content layers
        "audio_tracks": [_serialize_audio_track(t) for t in plan.audio_tracks],
        "scenes": [_serialize_scene(s) for s in plan.scenes],
        "subtitles": _serialize_subtitles(plan.subtitles),
        # Output configuration
        "output": _serialize_output(plan.output),
    }


def deserialize_render_plan(data: Dict[str, Any]) -> RenderPlan:
    """
    Convert JSON-compatible dict to RenderPlan.

    This enables loading saved plans from disk or API responses.

    Parameters:
    - data: Dict from JSON.loads()

    Returns:
    RenderPlan domain object

    Raises:
    KeyError if required fields are missing
    TypeError if field types are incorrect
    """
    return RenderPlan(
        render_plan_id=data["render_plan_id"],
        format=data["format"],
        total_duration_seconds=float(data["total_duration_seconds"]),
        fps=int(data["fps"]),
        resolution=_deserialize_resolution(data["resolution"]),
        audio_tracks=[_deserialize_audio_track(t) for t in data["audio_tracks"]],
        scenes=[_deserialize_scene(s) for s in data["scenes"]],
        subtitles=_deserialize_subtitles(data["subtitles"]),
        output=_deserialize_output(data["output"]),
    )


# ============================================================================
# Resolution Serialization
# ============================================================================


def _serialize_resolution(res: Resolution) -> Dict[str, int]:
    """Convert Resolution to dict."""
    return {
        "width": res.width,
        "height": res.height,
    }


def _deserialize_resolution(data: Dict[str, int]) -> Resolution:
    """Convert dict to Resolution."""
    return Resolution(
        width=int(data["width"]),
        height=int(data["height"]),
    )


# ============================================================================
# AudioTrack Serialization
# ============================================================================


def _serialize_audio_track(track: AudioTrack) -> Dict[str, Any]:
    """Convert AudioTrack to dict."""
    return {
        "type": track.type,
        "source": track.source,
        "start_time": track.start_time,
        "volume": track.volume,
        "fade_in": track.fade_in,
        "fade_out": track.fade_out,
    }


def _deserialize_audio_track(data: Dict[str, Any]) -> AudioTrack:
    """Convert dict to AudioTrack."""
    return AudioTrack(
        type=data["type"],
        source=data["source"],
        start_time=float(data["start_time"]),
        volume=float(data["volume"]),
        fade_in=float(data["fade_in"]) if data.get("fade_in") is not None else None,
        fade_out=float(data["fade_out"]) if data.get("fade_out") is not None else None,
    )


# ============================================================================
# Visual Serialization
# ============================================================================


def _serialize_visual(visual: Visual) -> Dict[str, Any]:
    """Convert Visual to dict."""
    return {
        "type": visual.type,
        "source": visual.source,
        "prompt_ref": visual.prompt_ref,
        "motion": visual.motion,
        "background_color": visual.background_color,
    }


def _deserialize_visual(data: Dict[str, Any]) -> Visual:
    """Convert dict to Visual."""
    return Visual(
        type=data["type"],
        source=data["source"],
        prompt_ref=data.get("prompt_ref"),
        motion=data.get("motion"),
        background_color=data.get("background_color"),
    )


# ============================================================================
# Overlay Serialization
# ============================================================================


def _serialize_overlay(overlay: Overlay) -> Dict[str, Any]:
    """Convert Overlay to dict."""
    return {
        "type": overlay.type,
        "content_ref": overlay.content_ref,
        "position": overlay.position,
        "start_time": overlay.start_time,
        "end_time": overlay.end_time,
        "style": overlay.style,
        "animation": overlay.animation,
    }


def _deserialize_overlay(data: Dict[str, Any]) -> Overlay:
    """Convert dict to Overlay."""
    return Overlay(
        type=data["type"],
        content_ref=data["content_ref"],
        position=data["position"],
        start_time=float(data["start_time"]),
        end_time=float(data["end_time"]),
        style=data["style"],
        animation=data.get("animation"),
    )


# ============================================================================
# Transition Serialization
# ============================================================================


def _serialize_transition(transition: Transition) -> Dict[str, Any]:
    """Convert Transition to dict."""
    return {
        "type": transition.type,
        "duration": transition.duration,
    }


def _deserialize_transition(data: Dict[str, Any]) -> Transition:
    """Convert dict to Transition."""
    return Transition(
        type=data["type"],
        duration=float(data["duration"]),
    )


# ============================================================================
# Scene Serialization
# ============================================================================


def _serialize_scene(scene: Scene) -> Dict[str, Any]:
    """Convert Scene to dict."""
    return {
        "scene_id": scene.scene_id,
        "start_time": scene.start_time,
        "end_time": scene.end_time,
        "visual": _serialize_visual(scene.visual),
        "overlays": [_serialize_overlay(o) for o in scene.overlays],
        "transition_in": _serialize_transition(scene.transition_in),
        "transition_out": _serialize_transition(scene.transition_out),
    }


def _deserialize_scene(data: Dict[str, Any]) -> Scene:
    """Convert dict to Scene."""
    return Scene(
        scene_id=data["scene_id"],
        start_time=float(data["start_time"]),
        end_time=float(data["end_time"]),
        visual=_deserialize_visual(data["visual"]),
        overlays=[_deserialize_overlay(o) for o in data["overlays"]],
        transition_in=_deserialize_transition(data["transition_in"]),
        transition_out=_deserialize_transition(data["transition_out"]),
    )


# ============================================================================
# Subtitle Serialization
# ============================================================================


def _serialize_subtitle_segment(segment: SubtitleSegment) -> Dict[str, Any]:
    """Convert SubtitleSegment to dict."""
    return {
        "start": segment.start,
        "end": segment.end,
        "text": segment.text,
        "highlight": segment.highlight,
    }


def _deserialize_subtitle_segment(data: Dict[str, Any]) -> SubtitleSegment:
    """Convert dict to SubtitleSegment."""
    return SubtitleSegment(
        start=float(data["start"]),
        end=float(data["end"]),
        text=data["text"],
        highlight=data.get("highlight"),
    )


def _serialize_subtitles(subtitles: Subtitles) -> Dict[str, Any]:
    """Convert Subtitles to dict."""
    return {
        "enabled": subtitles.enabled,
        "style": subtitles.style,
        "segments": [_serialize_subtitle_segment(s) for s in subtitles.segments],
    }


def _deserialize_subtitles(data: Dict[str, Any]) -> Subtitles:
    """Convert dict to Subtitles."""
    return Subtitles(
        enabled=bool(data["enabled"]),
        style=data["style"],
        segments=[_deserialize_subtitle_segment(s) for s in data["segments"]],
    )


# ============================================================================
# Output Serialization
# ============================================================================


def _serialize_output(output: Output) -> Dict[str, Any]:
    """Convert Output to dict."""
    return {
        "container": output.container,
        "codec": output.codec,
        "bitrate": output.bitrate,
        "platform_profile": output.platform_profile,
        "filename": output.filename,
    }


def _deserialize_output(data: Dict[str, Any]) -> Output:
    """Convert dict to Output."""
    return Output(
        container=data["container"],
        codec=data["codec"],
        bitrate=data["bitrate"],
        platform_profile=data["platform_profile"],
        filename=data["filename"],
    )
