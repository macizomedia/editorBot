"""
Tests for Render Plan Models

Tests verify:
- Immutability (frozen dataclasses)
- Field types and constraints
- No hidden defaults
"""

import pytest

from bot.render_plan.models import (
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


def test_resolution_is_immutable():
    """Resolution cannot be modified after creation."""
    res = Resolution(width=1080, height=1920)

    with pytest.raises(AttributeError):
        res.width = 1920  # Should fail: frozen dataclass


def test_resolution_requires_all_fields():
    """Resolution requires explicit width and height."""
    with pytest.raises(TypeError):
        Resolution()  # Should fail: missing required fields


def test_audio_track_is_immutable():
    """AudioTrack cannot be modified after creation."""
    track = AudioTrack(
        type="voice",
        source="audio.wav",
        start_time=0.0,
        volume=1.0,
    )

    with pytest.raises(AttributeError):
        track.volume = 0.5  # Should fail: frozen


def test_audio_track_optional_fades_default_to_none():
    """AudioTrack fades are explicitly optional."""
    track = AudioTrack(
        type="music",
        source="track.mp3",
        start_time=0.0,
        volume=0.5,
    )

    assert track.fade_in is None
    assert track.fade_out is None


def test_scene_contains_all_required_components():
    """Scene must have id, timing, visual, overlays, and transitions."""
    scene = Scene(
        scene_id="scene_1",
        start_time=0.0,
        end_time=10.0,
        visual=Visual(
            type="solid_color",
            source="#000000",
        ),
        overlays=[],
        transition_in=Transition(type="cut", duration=0.0),
        transition_out=Transition(type="cut", duration=0.0),
    )

    assert scene.scene_id == "scene_1"
    assert scene.start_time == 0.0
    assert scene.end_time == 10.0
    assert scene.visual.type == "solid_color"
    assert len(scene.overlays) == 0


def test_scene_is_immutable():
    """Scene cannot be modified after creation."""
    scene = Scene(
        scene_id="scene_1",
        start_time=0.0,
        end_time=10.0,
        visual=Visual(type="solid_color", source="#000000"),
        overlays=[],
        transition_in=Transition(type="cut", duration=0.0),
        transition_out=Transition(type="cut", duration=0.0),
    )

    with pytest.raises(AttributeError):
        scene.start_time = 5.0  # Should fail: frozen


def test_subtitle_segment_supports_optional_highlights():
    """SubtitleSegment can highlight specific words."""
    segment_without_highlight = SubtitleSegment(
        start=0.0,
        end=3.0,
        text="Hello world",
    )

    assert segment_without_highlight.highlight is None

    segment_with_highlight = SubtitleSegment(
        start=0.0,
        end=3.0,
        text="Hello world",
        highlight=["world"],
    )

    assert segment_with_highlight.highlight == ["world"]


def test_render_plan_is_immutable():
    """RenderPlan cannot be modified after creation."""
    plan = RenderPlan(
        render_plan_id="rp-test",
        format="REEL_VERTICAL",
        total_duration_seconds=30.0,
        fps=30,
        resolution=Resolution(width=1080, height=1920),
        audio_tracks=[],
        scenes=[],
        subtitles=Subtitles(enabled=False, style="", segments=[]),
        output=Output(
            container="mp4",
            codec="h264",
            bitrate="6M",
            platform_profile="instagram_reel",
            filename="test.mp4",
        ),
    )

    with pytest.raises(AttributeError):
        plan.fps = 60  # Should fail: frozen


def test_overlay_requires_explicit_timing():
    """Overlay must have explicit start and end times."""
    overlay = Overlay(
        type="text",
        content_ref="keyword",
        position="center",
        start_time=1.0,
        end_time=5.0,
        style="bold",
    )

    assert overlay.start_time == 1.0
    assert overlay.end_time == 5.0
    assert overlay.animation is None  # Optional field
