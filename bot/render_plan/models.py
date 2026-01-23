"""
Render Plan Domain Models

These are immutable data structures that represent the final rendering specification.

Design Principles:
- Frozen dataclasses (immutable)
- No business logic (pure data)
- No I/O operations
- No hidden defaults
- Explicit over implicit

Each model represents a precise contract with the rendering engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass(frozen=True)
class Resolution:
    """
    Video resolution specification.

    Why this exists:
    Different platforms require different resolutions (1080x1920 for Reels, 1920x1080 for YouTube).
    Renderer needs exact pixel dimensions before execution.

    Fields:
    - width: Horizontal pixels (must be positive, even number for codec compatibility)
    - height: Vertical pixels (must be positive, even number for codec compatibility)
    """

    width: int
    height: int


@dataclass(frozen=True)
class AudioTrack:
    """
    Single audio layer in the timeline.

    Why this exists:
    Video can have multiple audio layers (voice + music).
    Each layer needs independent control (volume, timing, fades).
    Renderer applies these values directly without decision-making.

    Fields:
    - type: "voice" or "music" (determines mixing priority)
    - source: Reference to audio file (S3 path or identifier)
    - start_time: When this audio begins (seconds, can be non-zero for delayed entry)
    - volume: Amplitude multiplier (0.0 = silent, 1.0 = original, >1.0 = amplified)
    - fade_in: Optional fade-in duration (seconds)
    - fade_out: Optional fade-out duration (seconds)
    """

    type: str
    source: str
    start_time: float
    volume: float
    fade_in: Optional[float] = None
    fade_out: Optional[float] = None


@dataclass(frozen=True)
class Visual:
    """
    Visual content for a scene.

    Why this exists:
    Each scene needs a background visual (image, video, solid color, gradient).
    Visual properties (motion, color) are pre-decided, not computed at render time.

    Fields:
    - type: "image" | "video" | "solid_color" | "gradient"
    - source: Reference to visual asset (can be "ai_generated", S3 path, or color hex)
    - prompt_ref: Optional reference to generation prompt (for debugging/auditing)
    - motion: Optional motion effect ("slow_zoom_in", "pan_right", "static")
    - background_color: Fallback or fill color (hex format, e.g., "#000000")
    """

    type: str
    source: str
    prompt_ref: Optional[str] = None
    motion: Optional[str] = None
    background_color: Optional[str] = None


@dataclass(frozen=True)
class Overlay:
    """
    Text or graphic layer on top of scene visual.

    Why this exists:
    Overlays (text highlights, keywords, graphics) are independent of background visuals.
    Multiple overlays can exist per scene with different timing and positioning.

    Fields:
    - type: "text" | "graphic" (determines how renderer interprets content_ref)
    - content_ref: Reference to content (e.g., "beat_1.keywords" or asset path)
    - position: Placement on screen ("center", "top", "bottom", "left", "right")
    - start_time: When overlay appears (relative to scene start, seconds)
    - end_time: When overlay disappears (relative to scene start, seconds)
    - style: Rendering style reference ("bold_caps", "subtitle_emphasis", etc.)
    - animation: Optional entrance/exit animation ("fade_in_up", "slide_left", etc.)
    """

    type: str
    content_ref: str
    position: str
    start_time: float
    end_time: float
    style: str
    animation: Optional[str] = None


@dataclass(frozen=True)
class Transition:
    """
    Scene entrance or exit transition.

    Why this exists:
    Scenes need smooth entry/exit (cut, fade, dissolve).
    Transition timing affects perceived pacing.

    Fields:
    - type: "cut" | "fade" | "dissolve" | "wipe"
    - duration: Transition duration (seconds, 0.0 for instant cut)
    """

    type: str
    duration: float = 0.0


@dataclass(frozen=True)
class Scene:
    """
    Time-bounded visual container.

    Why this exists:
    Video is segmented into scenes (typically aligned with script beats).
    Each scene has:
    - Exact timing (start/end)
    - One primary visual
    - Zero or more overlays
    - Entry/exit transitions

    Fields:
    - scene_id: Unique identifier (for debugging, logging, asset reference)
    - start_time: Scene begins (seconds from video start)
    - end_time: Scene ends (seconds from video start)
    - visual: Primary background visual
    - overlays: List of text/graphic overlays (can be empty)
    - transition_in: How scene enters (default: cut)
    - transition_out: How scene exits (default: cut)
    """

    scene_id: str
    start_time: float
    end_time: float
    visual: Visual
    overlays: List[Overlay]
    transition_in: Transition
    transition_out: Transition


@dataclass(frozen=True)
class SubtitleSegment:
    """
    Single subtitle entry with timing.

    Why this exists:
    Subtitles must be time-aligned with audio.
    Each segment is a discrete unit (one sentence or phrase).

    Fields:
    - start: Segment appears (seconds from video start)
    - end: Segment disappears (seconds from video start)
    - text: Subtitle content (plain text, renderer handles styling)
    - highlight: Optional list of words to emphasize (for dynamic styling)
    """

    start: float
    end: float
    text: str
    highlight: Optional[List[str]] = None


@dataclass(frozen=True)
class Subtitles:
    """
    Global subtitle configuration.

    Why this exists:
    Subtitles are global (not per-scene).
    Configuration (enabled/disabled, style) applies to all segments.

    Fields:
    - enabled: Whether to render subtitles (boolean flag)
    - style: Rendering style reference ("subtitle_emphasis", "minimal", "bold", etc.)
    - segments: List of timed subtitle entries
    """

    enabled: bool
    style: str
    segments: List[SubtitleSegment]


@dataclass(frozen=True)
class Output:
    """
    Final video encoding specification.

    Why this exists:
    Different platforms require different encoding (Instagram requires specific codec settings).
    These values are passed directly to FFmpeg/encoder.

    Fields:
    - container: File format ("mp4", "mov", "webm")
    - codec: Video codec ("h264", "h265", "vp9")
    - bitrate: Target bitrate (e.g., "6M" for 6 megabits/second)
    - platform_profile: Pre-defined platform preset ("instagram_reel", "youtube_landscape")
    - filename: Output filename (without path, just basename)
    """

    container: str
    codec: str
    bitrate: str
    platform_profile: str
    filename: str


@dataclass(frozen=True)
class RenderPlan:
    """
    Complete, deterministic rendering specification.

    This is the top-level object that answers:
    "Exactly what happens on the timeline, second by second?"

    Why this exists:
    - Separates decision-making from execution
    - Makes rendering reproducible (same plan = same output)
    - Enables validation without rendering
    - Allows cost estimation before execution
    - Provides audit trail (can inspect plan before committing resources)

    Fields:
    - render_plan_id: Unique identifier (UUID, for logging/debugging)
    - format: Video format type ("REEL_VERTICAL", "LANDSCAPE_16_9", etc.)
    - total_duration_seconds: Total video length (must match sum of scenes)
    - fps: Frames per second (typically 30 or 60)
    - resolution: Pixel dimensions (width x height)
    - audio_tracks: List of audio layers (voice, music, effects)
    - scenes: List of time-bounded visual containers (sequential, no gaps)
    - subtitles: Global subtitle configuration
    - output: Encoding and export settings

    Invariants (enforced by validator, not this class):
    - Scenes must not overlap
    - Scenes must cover entire duration (no gaps)
    - Audio tracks must fit within total duration
    - Subtitle segments must fit within total duration
    """

    render_plan_id: str
    format: str
    total_duration_seconds: float
    fps: int
    resolution: Resolution
    audio_tracks: List[AudioTrack]
    scenes: List[Scene]
    subtitles: Subtitles
    output: Output
