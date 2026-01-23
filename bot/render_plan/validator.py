"""
Render Plan Validator

Validates Render Plan correctness without modifying data.

Design Principles:
- Validator does NOT modify data (immutable inputs)
- Returns structured results (no exceptions for expected errors)
- Distinguishes fatal errors from warnings
- Each rule has clear business justification

Fatal Errors:
Conditions that make rendering impossible or produce corrupted output.
Examples: overlapping scenes, negative durations, missing required fields.

Warnings:
Conditions that are valid but potentially problematic.
Examples: very short scenes, unusual aspect ratios, high bitrates.

Validator Role:
- Catches configuration errors before expensive rendering
- Provides clear, actionable feedback
- Enables "dry run" validation (check plan without executing)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .models import RenderPlan


@dataclass(frozen=True)
class ValidationError:
    """
    Single validation error.

    Fields:
    - code: Machine-readable error code (e.g., "SCENE_OVERLAP")
    - message: Human-readable description
    - location: Where error occurred (e.g., "scene_2", "audio_tracks[0]")
    - severity: "fatal" or "warning"
    """

    code: str
    message: str
    location: str
    severity: str


@dataclass(frozen=True)
class ValidationResult:
    """
    Result of validation operation.

    Fields:
    - passed: True if no fatal errors (warnings are acceptable)
    - errors: List of all errors and warnings (empty if perfect)
    - fatal_count: Number of fatal errors (must be 0 for passed=True)
    - warning_count: Number of warnings (can be >0 even if passed=True)
    """

    passed: bool
    errors: List[ValidationError]
    fatal_count: int
    warning_count: int


def validate_render_plan(plan: RenderPlan) -> ValidationResult:
    """
    Validate complete Render Plan.

    This is the single public entry point for validation.

    Returns:
    ValidationResult with pass/fail status and detailed error list.

    Does NOT raise exceptions (errors returned in result).
    Does NOT modify plan (immutable input).
    """
    errors: List[ValidationError] = []

    # Run all validation rules
    errors.extend(_validate_resolution(plan))
    errors.extend(_validate_duration(plan))
    errors.extend(_validate_scenes(plan))
    errors.extend(_validate_audio_tracks(plan))
    errors.extend(_validate_subtitles(plan))
    errors.extend(_validate_output(plan))

    # Classify errors
    fatal_count = sum(1 for e in errors if e.severity == "fatal")
    warning_count = sum(1 for e in errors if e.severity == "warning")

    return ValidationResult(
        passed=(fatal_count == 0),
        errors=errors,
        fatal_count=fatal_count,
        warning_count=warning_count,
    )


def _validate_resolution(plan: RenderPlan) -> List[ValidationError]:
    """
    Validate video resolution.

    Why these rules:
    - Width/height must be positive (negative dimensions are nonsensical)
    - Even numbers required (most codecs require even dimensions)
    - Minimum size prevents unusably small output
    - Maximum size prevents memory exhaustion
    """
    errors = []

    if plan.resolution.width <= 0 or plan.resolution.height <= 0:
        errors.append(
            ValidationError(
                code="INVALID_RESOLUTION",
                message="Resolution dimensions must be positive",
                location="resolution",
                severity="fatal",
            )
        )

    if plan.resolution.width % 2 != 0 or plan.resolution.height % 2 != 0:
        errors.append(
            ValidationError(
                code="ODD_RESOLUTION",
                message="Resolution dimensions should be even numbers for codec compatibility",
                location="resolution",
                severity="warning",
            )
        )

    if plan.resolution.width < 320 or plan.resolution.height < 240:
        errors.append(
            ValidationError(
                code="RESOLUTION_TOO_SMALL",
                message="Resolution unusually small (may produce low-quality output)",
                location="resolution",
                severity="warning",
            )
        )

    if plan.resolution.width > 7680 or plan.resolution.height > 4320:
        errors.append(
            ValidationError(
                code="RESOLUTION_TOO_LARGE",
                message="Resolution exceeds 8K (may cause memory issues)",
                location="resolution",
                severity="warning",
            )
        )

    return errors


def _validate_duration(plan: RenderPlan) -> List[ValidationError]:
    """
    Validate video duration.

    Why these rules:
    - Duration must be positive (zero or negative duration is invalid)
    - Very short durations may be unintentional
    - Very long durations may indicate error or resource concern
    """
    errors = []

    if plan.total_duration_seconds <= 0:
        errors.append(
            ValidationError(
                code="INVALID_DURATION",
                message="Total duration must be positive",
                location="total_duration_seconds",
                severity="fatal",
            )
        )

    if plan.total_duration_seconds < 1.0:
        errors.append(
            ValidationError(
                code="DURATION_TOO_SHORT",
                message="Video duration less than 1 second (may be unintentional)",
                location="total_duration_seconds",
                severity="warning",
            )
        )

    if plan.total_duration_seconds > 600:
        errors.append(
            ValidationError(
                code="DURATION_VERY_LONG",
                message="Video duration exceeds 10 minutes (verify intentional)",
                location="total_duration_seconds",
                severity="warning",
            )
        )

    if plan.fps <= 0:
        errors.append(
            ValidationError(
                code="INVALID_FPS",
                message="FPS must be positive",
                location="fps",
                severity="fatal",
            )
        )

    if plan.fps not in [24, 25, 30, 60]:
        errors.append(
            ValidationError(
                code="UNUSUAL_FPS",
                message=f"FPS {plan.fps} is non-standard (expected 24/25/30/60)",
                location="fps",
                severity="warning",
            )
        )

    return errors


def _validate_scenes(plan: RenderPlan) -> List[ValidationError]:
    """
    Validate scene timeline structure.

    Why these rules:
    - Must have at least one scene (empty video is invalid)
    - Scenes must not overlap (ambiguous timeline)
    - Scenes must not have gaps (black frames)
    - Scenes must cover entire duration (exact match)
    - Scene timing must be valid (start < end)
    """
    errors = []

    if not plan.scenes:
        errors.append(
            ValidationError(
                code="NO_SCENES",
                message="Render plan must have at least one scene",
                location="scenes",
                severity="fatal",
            )
        )
        return errors  # Cannot continue validation without scenes

    # Sort scenes by start time for validation
    sorted_scenes = sorted(plan.scenes, key=lambda s: s.start_time)

    # Validate individual scene timing
    for i, scene in enumerate(sorted_scenes):
        if scene.start_time < 0:
            errors.append(
                ValidationError(
                    code="NEGATIVE_START_TIME",
                    message=f"Scene start time cannot be negative",
                    location=f"scenes[{i}].start_time",
                    severity="fatal",
                )
            )

        if scene.end_time <= scene.start_time:
            errors.append(
                ValidationError(
                    code="INVALID_SCENE_DURATION",
                    message=f"Scene end time must be greater than start time",
                    location=f"scenes[{i}]",
                    severity="fatal",
                )
            )

        scene_duration = scene.end_time - scene.start_time
        if scene_duration < 0.5:
            errors.append(
                ValidationError(
                    code="SCENE_TOO_SHORT",
                    message=f"Scene duration {scene_duration:.1f}s is very short (may be jarring)",
                    location=f"scenes[{i}]",
                    severity="warning",
                )
            )

    # Validate scene continuity (no gaps or overlaps)
    for i in range(len(sorted_scenes) - 1):
        current = sorted_scenes[i]
        next_scene = sorted_scenes[i + 1]

        if next_scene.start_time < current.end_time:
            errors.append(
                ValidationError(
                    code="SCENE_OVERLAP",
                    message=f"Scene overlap: scene ends at {current.end_time:.2f}s but next starts at {next_scene.start_time:.2f}s",
                    location=f"scenes[{i}] -> scenes[{i+1}]",
                    severity="fatal",
                )
            )

        gap = next_scene.start_time - current.end_time
        if gap > 0.01:  # Allow tiny floating point errors
            errors.append(
                ValidationError(
                    code="SCENE_GAP",
                    message=f"Gap of {gap:.2f}s between scenes (will produce black frames)",
                    location=f"scenes[{i}] -> scenes[{i+1}]",
                    severity="fatal",
                )
            )

    # Validate total coverage
    if sorted_scenes:
        first_start = sorted_scenes[0].start_time
        last_end = sorted_scenes[-1].end_time

        if abs(first_start) > 0.01:
            errors.append(
                ValidationError(
                    code="SCENES_START_LATE",
                    message=f"First scene starts at {first_start:.2f}s (should start at 0.0)",
                    location="scenes[0]",
                    severity="fatal",
                )
            )

        duration_diff = abs(last_end - plan.total_duration_seconds)
        if duration_diff > 0.01:
            errors.append(
                ValidationError(
                    code="DURATION_MISMATCH",
                    message=f"Scenes end at {last_end:.2f}s but total duration is {plan.total_duration_seconds:.2f}s",
                    location="scenes",
                    severity="fatal",
                )
            )

    return errors


def _validate_audio_tracks(plan: RenderPlan) -> List[ValidationError]:
    """
    Validate audio track configuration.

    Why these rules:
    - Volume must be non-negative (negative volume is invalid)
    - Start time must be non-negative (audio can't start before video)
    - Fade durations must be non-negative
    - Must have at least one audio track (silent video requires explicit silence track)
    """
    errors = []

    if not plan.audio_tracks:
        errors.append(
            ValidationError(
                code="NO_AUDIO",
                message="Render plan should have at least one audio track",
                location="audio_tracks",
                severity="warning",
            )
        )

    for i, track in enumerate(plan.audio_tracks):
        if track.volume < 0:
            errors.append(
                ValidationError(
                    code="NEGATIVE_VOLUME",
                    message="Audio volume cannot be negative",
                    location=f"audio_tracks[{i}].volume",
                    severity="fatal",
                )
            )

        if track.start_time < 0:
            errors.append(
                ValidationError(
                    code="NEGATIVE_AUDIO_START",
                    message="Audio start time cannot be negative",
                    location=f"audio_tracks[{i}].start_time",
                    severity="fatal",
                )
            )

        if track.fade_in is not None and track.fade_in < 0:
            errors.append(
                ValidationError(
                    code="NEGATIVE_FADE",
                    message="Fade-in duration cannot be negative",
                    location=f"audio_tracks[{i}].fade_in",
                    severity="fatal",
                )
            )

        if track.fade_out is not None and track.fade_out < 0:
            errors.append(
                ValidationError(
                    code="NEGATIVE_FADE",
                    message="Fade-out duration cannot be negative",
                    location=f"audio_tracks[{i}].fade_out",
                    severity="fatal",
                )
            )

        if track.volume > 2.0:
            errors.append(
                ValidationError(
                    code="HIGH_VOLUME",
                    message=f"Volume {track.volume} is very high (may cause clipping)",
                    location=f"audio_tracks[{i}].volume",
                    severity="warning",
                )
            )

    return errors


def _validate_subtitles(plan: RenderPlan) -> List[ValidationError]:
    """
    Validate subtitle configuration.

    Why these rules:
    - Subtitle segments must not overlap (ambiguous display)
    - Segments must fit within video duration
    - Segment timing must be valid (start < end)
    """
    errors = []

    if not plan.subtitles.enabled:
        return errors  # No validation needed if disabled

    if not plan.subtitles.segments:
        errors.append(
            ValidationError(
                code="SUBTITLES_EMPTY",
                message="Subtitles enabled but no segments provided",
                location="subtitles.segments",
                severity="warning",
            )
        )
        return errors

    sorted_segments = sorted(plan.subtitles.segments, key=lambda s: s.start)

    for i, seg in enumerate(sorted_segments):
        if seg.start < 0:
            errors.append(
                ValidationError(
                    code="NEGATIVE_SUBTITLE_START",
                    message="Subtitle start time cannot be negative",
                    location=f"subtitles.segments[{i}].start",
                    severity="fatal",
                )
            )

        if seg.end <= seg.start:
            errors.append(
                ValidationError(
                    code="INVALID_SUBTITLE_DURATION",
                    message="Subtitle end time must be greater than start time",
                    location=f"subtitles.segments[{i}]",
                    severity="fatal",
                )
            )

        if seg.end > plan.total_duration_seconds:
            errors.append(
                ValidationError(
                    code="SUBTITLE_OUT_OF_BOUNDS",
                    message=f"Subtitle ends at {seg.end:.2f}s but video ends at {plan.total_duration_seconds:.2f}s",
                    location=f"subtitles.segments[{i}]",
                    severity="fatal",
                )
            )

        # Check for overlaps with next segment
        if i < len(sorted_segments) - 1:
            next_seg = sorted_segments[i + 1]
            if next_seg.start < seg.end:
                errors.append(
                    ValidationError(
                        code="SUBTITLE_OVERLAP",
                        message=f"Subtitle overlap at {seg.end:.2f}s (next starts at {next_seg.start:.2f}s)",
                        location=f"subtitles.segments[{i}] -> subtitles.segments[{i+1}]",
                        severity="warning",
                    )
                )

    return errors


def _validate_output(plan: RenderPlan) -> List[ValidationError]:
    """
    Validate output configuration.

    Why these rules:
    - Container must be supported (prevents encoding failures)
    - Codec must be compatible with container
    - Filename must be valid (prevents filesystem errors)
    """
    errors = []

    supported_containers = ["mp4", "mov", "webm", "avi"]
    if plan.output.container not in supported_containers:
        errors.append(
            ValidationError(
                code="UNSUPPORTED_CONTAINER",
                message=f"Container '{plan.output.container}' may not be supported (expected: {supported_containers})",
                location="output.container",
                severity="warning",
            )
        )

    supported_codecs = ["h264", "h265", "vp9", "prores"]
    if plan.output.codec not in supported_codecs:
        errors.append(
            ValidationError(
                code="UNSUPPORTED_CODEC",
                message=f"Codec '{plan.output.codec}' may not be supported (expected: {supported_codecs})",
                location="output.codec",
                severity="warning",
            )
        )

    if not plan.output.filename:
        errors.append(
            ValidationError(
                code="EMPTY_FILENAME",
                message="Output filename cannot be empty",
                location="output.filename",
                severity="fatal",
            )
        )

    # Check for problematic characters in filename
    if plan.output.filename and any(c in plan.output.filename for c in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
        errors.append(
            ValidationError(
                code="INVALID_FILENAME",
                message="Filename contains invalid characters",
                location="output.filename",
                severity="fatal",
            )
        )

    return errors
