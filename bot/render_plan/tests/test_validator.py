"""
Tests for Render Plan Validator

Tests verify:
- Fatal errors prevent rendering
- Warnings allow rendering but flag issues
- Validation returns structured results
- No exceptions for expected errors
"""

import pytest

from bot.render_plan.models import (
    RenderPlan,
    Resolution,
    AudioTrack,
    Scene,
    Visual,
    Transition,
    Subtitles,
    SubtitleSegment,
    Output,
)
from bot.render_plan.validator import (
    validate_render_plan,
    ValidationResult,
    ValidationError,
)


def _create_minimal_valid_plan() -> RenderPlan:
    """Helper to create a minimal valid RenderPlan for testing."""
    return RenderPlan(
        render_plan_id="rp-test",
        format="REEL_VERTICAL",
        total_duration_seconds=10.0,
        fps=30,
        resolution=Resolution(width=1080, height=1920),
        audio_tracks=[
            AudioTrack(
                type="voice",
                source="audio.wav",
                start_time=0.0,
                volume=1.0,
            ),
        ],
        scenes=[
            Scene(
                scene_id="scene_1",
                start_time=0.0,
                end_time=10.0,
                visual=Visual(type="solid_color", source="#000000"),
                overlays=[],
                transition_in=Transition(type="cut", duration=0.0),
                transition_out=Transition(type="cut", duration=0.0),
            ),
        ],
        subtitles=Subtitles(enabled=False, style="", segments=[]),
        output=Output(
            container="mp4",
            codec="h264",
            bitrate="6M",
            platform_profile="instagram_reel",
            filename="test.mp4",
        ),
    )


def test_minimal_valid_plan_passes_validation():
    """A properly constructed plan with all required fields passes validation."""
    plan = _create_minimal_valid_plan()
    result = validate_render_plan(plan)

    assert result.passed is True
    assert result.fatal_count == 0
    assert len(result.errors) == 0


def test_negative_resolution_is_fatal_error():
    """Resolution with negative dimensions fails validation."""
    plan = _create_minimal_valid_plan()
    # Replace with invalid resolution (immutable, so create new plan)
    invalid_plan = RenderPlan(
        render_plan_id=plan.render_plan_id,
        format=plan.format,
        total_duration_seconds=plan.total_duration_seconds,
        fps=plan.fps,
        resolution=Resolution(width=-1080, height=1920),
        audio_tracks=plan.audio_tracks,
        scenes=plan.scenes,
        subtitles=plan.subtitles,
        output=plan.output,
    )

    result = validate_render_plan(invalid_plan)

    assert result.passed is False
    assert result.fatal_count > 0
    assert any(e.code == "INVALID_RESOLUTION" for e in result.errors)


def test_odd_resolution_is_warning_not_fatal():
    """Resolution with odd dimensions produces warning but allows rendering."""
    plan = _create_minimal_valid_plan()
    odd_plan = RenderPlan(
        render_plan_id=plan.render_plan_id,
        format=plan.format,
        total_duration_seconds=plan.total_duration_seconds,
        fps=plan.fps,
        resolution=Resolution(width=1081, height=1921),  # Odd numbers
        audio_tracks=plan.audio_tracks,
        scenes=plan.scenes,
        subtitles=plan.subtitles,
        output=plan.output,
    )

    result = validate_render_plan(odd_plan)

    assert result.passed is True  # Warnings don't block
    assert result.warning_count > 0
    assert any(e.code == "ODD_RESOLUTION" and e.severity == "warning" for e in result.errors)


def test_zero_duration_is_fatal_error():
    """Video with zero duration fails validation."""
    plan = _create_minimal_valid_plan()
    zero_duration_plan = RenderPlan(
        render_plan_id=plan.render_plan_id,
        format=plan.format,
        total_duration_seconds=0.0,  # Invalid
        fps=plan.fps,
        resolution=plan.resolution,
        audio_tracks=plan.audio_tracks,
        scenes=plan.scenes,
        subtitles=plan.subtitles,
        output=plan.output,
    )

    result = validate_render_plan(zero_duration_plan)

    assert result.passed is False
    assert any(e.code == "INVALID_DURATION" for e in result.errors)


def test_scene_overlap_is_fatal_error():
    """Overlapping scenes fail validation."""
    plan = _create_minimal_valid_plan()
    overlapping_scenes = [
        Scene(
            scene_id="scene_1",
            start_time=0.0,
            end_time=6.0,  # Ends at 6s
            visual=Visual(type="solid_color", source="#000000"),
            overlays=[],
            transition_in=Transition(type="cut", duration=0.0),
            transition_out=Transition(type="cut", duration=0.0),
        ),
        Scene(
            scene_id="scene_2",
            start_time=5.0,  # Starts at 5s (overlaps!)
            end_time=10.0,
            visual=Visual(type="solid_color", source="#000000"),
            overlays=[],
            transition_in=Transition(type="cut", duration=0.0),
            transition_out=Transition(type="cut", duration=0.0),
        ),
    ]

    overlapping_plan = RenderPlan(
        render_plan_id=plan.render_plan_id,
        format=plan.format,
        total_duration_seconds=10.0,
        fps=plan.fps,
        resolution=plan.resolution,
        audio_tracks=plan.audio_tracks,
        scenes=overlapping_scenes,
        subtitles=plan.subtitles,
        output=plan.output,
    )

    result = validate_render_plan(overlapping_plan)

    assert result.passed is False
    assert any(e.code == "SCENE_OVERLAP" for e in result.errors)


def test_scene_gap_is_fatal_error():
    """Gap between scenes fails validation."""
    plan = _create_minimal_valid_plan()
    gapped_scenes = [
        Scene(
            scene_id="scene_1",
            start_time=0.0,
            end_time=4.0,  # Ends at 4s
            visual=Visual(type="solid_color", source="#000000"),
            overlays=[],
            transition_in=Transition(type="cut", duration=0.0),
            transition_out=Transition(type="cut", duration=0.0),
        ),
        Scene(
            scene_id="scene_2",
            start_time=5.0,  # Starts at 5s (1s gap!)
            end_time=10.0,
            visual=Visual(type="solid_color", source="#000000"),
            overlays=[],
            transition_in=Transition(type="cut", duration=0.0),
            transition_out=Transition(type="cut", duration=0.0),
        ),
    ]

    gapped_plan = RenderPlan(
        render_plan_id=plan.render_plan_id,
        format=plan.format,
        total_duration_seconds=10.0,
        fps=plan.fps,
        resolution=plan.resolution,
        audio_tracks=plan.audio_tracks,
        scenes=gapped_scenes,
        subtitles=plan.subtitles,
        output=plan.output,
    )

    result = validate_render_plan(gapped_plan)

    assert result.passed is False
    assert any(e.code == "SCENE_GAP" for e in result.errors)


def test_negative_audio_volume_is_fatal_error():
    """Negative audio volume fails validation."""
    plan = _create_minimal_valid_plan()
    invalid_audio = [
        AudioTrack(
            type="voice",
            source="audio.wav",
            start_time=0.0,
            volume=-0.5,  # Invalid
        ),
    ]

    invalid_plan = RenderPlan(
        render_plan_id=plan.render_plan_id,
        format=plan.format,
        total_duration_seconds=plan.total_duration_seconds,
        fps=plan.fps,
        resolution=plan.resolution,
        audio_tracks=invalid_audio,
        scenes=plan.scenes,
        subtitles=plan.subtitles,
        output=plan.output,
    )

    result = validate_render_plan(invalid_plan)

    assert result.passed is False
    assert any(e.code == "NEGATIVE_VOLUME" for e in result.errors)


def test_high_audio_volume_is_warning():
    """Very high audio volume produces warning."""
    plan = _create_minimal_valid_plan()
    loud_audio = [
        AudioTrack(
            type="voice",
            source="audio.wav",
            start_time=0.0,
            volume=5.0,  # Very high
        ),
    ]

    loud_plan = RenderPlan(
        render_plan_id=plan.render_plan_id,
        format=plan.format,
        total_duration_seconds=plan.total_duration_seconds,
        fps=plan.fps,
        resolution=plan.resolution,
        audio_tracks=loud_audio,
        scenes=plan.scenes,
        subtitles=plan.subtitles,
        output=plan.output,
    )

    result = validate_render_plan(loud_plan)

    assert result.passed is True  # Warning, not fatal
    assert result.warning_count > 0
    assert any(e.code == "HIGH_VOLUME" for e in result.errors)


def test_subtitle_overlap_is_warning():
    """Overlapping subtitles produce warning."""
    plan = _create_minimal_valid_plan()
    overlapping_subtitles = Subtitles(
        enabled=True,
        style="default",
        segments=[
            SubtitleSegment(start=0.0, end=3.0, text="First"),
            SubtitleSegment(start=2.5, end=5.0, text="Second"),  # Overlaps
        ],
    )

    overlap_plan = RenderPlan(
        render_plan_id=plan.render_plan_id,
        format=plan.format,
        total_duration_seconds=plan.total_duration_seconds,
        fps=plan.fps,
        resolution=plan.resolution,
        audio_tracks=plan.audio_tracks,
        scenes=plan.scenes,
        subtitles=overlapping_subtitles,
        output=plan.output,
    )

    result = validate_render_plan(overlap_plan)

    assert result.passed is True  # Warning, not fatal
    assert any(e.code == "SUBTITLE_OVERLAP" for e in result.errors)


def test_empty_filename_is_fatal_error():
    """Empty output filename fails validation."""
    plan = _create_minimal_valid_plan()
    invalid_output = Output(
        container="mp4",
        codec="h264",
        bitrate="6M",
        platform_profile="instagram_reel",
        filename="",  # Invalid
    )

    invalid_plan = RenderPlan(
        render_plan_id=plan.render_plan_id,
        format=plan.format,
        total_duration_seconds=plan.total_duration_seconds,
        fps=plan.fps,
        resolution=plan.resolution,
        audio_tracks=plan.audio_tracks,
        scenes=plan.scenes,
        subtitles=plan.subtitles,
        output=invalid_output,
    )

    result = validate_render_plan(invalid_plan)

    assert result.passed is False
    assert any(e.code == "EMPTY_FILENAME" for e in result.errors)


def test_validation_result_counts_errors_correctly():
    """ValidationResult accurately counts fatal vs warning errors."""
    plan = _create_minimal_valid_plan()

    # Create plan with both fatal and warning issues
    problematic_plan = RenderPlan(
        render_plan_id=plan.render_plan_id,
        format=plan.format,
        total_duration_seconds=-1.0,  # Fatal: negative duration
        fps=25,  # Warning: unusual FPS
        resolution=Resolution(width=1081, height=1921),  # Warning: odd dimensions
        audio_tracks=plan.audio_tracks,
        scenes=plan.scenes,
        subtitles=plan.subtitles,
        output=plan.output,
    )

    result = validate_render_plan(problematic_plan)

    assert result.passed is False  # Fatal error present
    assert result.fatal_count >= 1
    assert result.warning_count >= 2
    assert len(result.errors) == result.fatal_count + result.warning_count
