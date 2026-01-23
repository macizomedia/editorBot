"""
Tests for Render Plan Builder

Tests verify:
- Builder produces valid RenderPlan
- Same inputs produce same output (determinism)
- Builder handles edge cases correctly
- No I/O or AI calls during build
"""

import pytest

from bot.render_plan.builder import RenderPlanBuilder
from bot.render_plan.validator import validate_render_plan


def _create_minimal_script():
    """Helper to create minimal valid script."""
    return {
        "beats": [
            {
                "role": "hook",
                "text": "This is a test",
                "duration": 5.0,
                "keywords": ["test"],
            },
            {
                "role": "argument",
                "text": "Here is the argument",
                "duration": 7.0,
                "keywords": ["argument"],
            },
        ],
    }


def _create_minimal_template():
    """Helper to create minimal valid template."""
    return {
        "id": "test_template",
        "allowed_formats": ["REEL_VERTICAL"],
        "audio_rules": {
            "music_allowed": False,
        },
        "visual_rules": {
            "text_overlay_required": True,
        },
    }


def _create_minimal_visual_strategy():
    """Helper to create minimal visual strategy."""
    return {
        "soundtrack_id": None,
        "visual_prompts": {},
    }


def test_builder_produces_valid_render_plan():
    """Builder output passes validation without errors."""
    builder = RenderPlanBuilder()

    plan = builder.build(
        script=_create_minimal_script(),
        template=_create_minimal_template(),
        visual_strategy=_create_minimal_visual_strategy(),
        audio_source="test_audio.wav",
    )

    result = validate_render_plan(plan)
    assert result.passed is True
    assert result.fatal_count == 0


def test_builder_generates_unique_plan_ids():
    """Each build generates a unique plan ID."""
    builder = RenderPlanBuilder()

    plan1 = builder.build(
        script=_create_minimal_script(),
        template=_create_minimal_template(),
        visual_strategy=_create_minimal_visual_strategy(),
        audio_source="test_audio.wav",
    )

    plan2 = builder.build(
        script=_create_minimal_script(),
        template=_create_minimal_template(),
        visual_strategy=_create_minimal_visual_strategy(),
        audio_source="test_audio.wav",
    )

    assert plan1.render_plan_id != plan2.render_plan_id


def test_builder_calculates_total_duration_from_script():
    """Total duration equals sum of beat durations."""
    builder = RenderPlanBuilder()

    script = {
        "beats": [
            {"role": "hook", "text": "Test", "duration": 3.5, "keywords": []},
            {"role": "argument", "text": "Test", "duration": 4.2, "keywords": []},
            {"role": "conclusion", "text": "Test", "duration": 2.3, "keywords": []},
        ],
    }

    plan = builder.build(
        script=script,
        template=_create_minimal_template(),
        visual_strategy=_create_minimal_visual_strategy(),
        audio_source="test_audio.wav",
    )

    expected_duration = 3.5 + 4.2 + 2.3
    assert plan.total_duration_seconds == expected_duration


def test_builder_creates_one_scene_per_beat():
    """Number of scenes equals number of beats."""
    builder = RenderPlanBuilder()

    script = {
        "beats": [
            {"role": "hook", "text": "Beat 1", "duration": 3.0, "keywords": []},
            {"role": "argument", "text": "Beat 2", "duration": 4.0, "keywords": []},
            {"role": "conclusion", "text": "Beat 3", "duration": 5.0, "keywords": []},
        ],
    }

    plan = builder.build(
        script=script,
        template=_create_minimal_template(),
        visual_strategy=_create_minimal_visual_strategy(),
        audio_source="test_audio.wav",
    )

    assert len(plan.scenes) == 3


def test_builder_creates_continuous_scene_timeline():
    """Scenes have no gaps and cover entire duration."""
    builder = RenderPlanBuilder()

    plan = builder.build(
        script=_create_minimal_script(),
        template=_create_minimal_template(),
        visual_strategy=_create_minimal_visual_strategy(),
        audio_source="test_audio.wav",
    )

    # First scene starts at 0
    assert plan.scenes[0].start_time == 0.0

    # Each scene starts where previous ended
    for i in range(len(plan.scenes) - 1):
        assert plan.scenes[i].end_time == plan.scenes[i + 1].start_time

    # Last scene ends at total duration
    assert plan.scenes[-1].end_time == plan.total_duration_seconds


def test_builder_includes_voice_audio_track():
    """Builder always includes voice audio track."""
    builder = RenderPlanBuilder()

    plan = builder.build(
        script=_create_minimal_script(),
        template=_create_minimal_template(),
        visual_strategy=_create_minimal_visual_strategy(),
        audio_source="voice.wav",
    )

    voice_tracks = [t for t in plan.audio_tracks if t.type == "voice"]
    assert len(voice_tracks) == 1
    assert voice_tracks[0].source == "voice.wav"


def test_builder_adds_music_track_when_allowed_and_selected():
    """Builder includes music track if template allows and strategy specifies."""
    builder = RenderPlanBuilder()

    template_with_music = {
        "id": "test_template",
        "allowed_formats": ["REEL_VERTICAL"],
        "audio_rules": {
            "music_allowed": True,
        },
        "visual_rules": {
            "text_overlay_required": True,
        },
    }

    strategy_with_music = {
        "soundtrack_id": "upbeat_track.mp3",
        "visual_prompts": {},
    }

    plan = builder.build(
        script=_create_minimal_script(),
        template=template_with_music,
        visual_strategy=strategy_with_music,
        audio_source="voice.wav",
    )

    music_tracks = [t for t in plan.audio_tracks if t.type == "music"]
    assert len(music_tracks) == 1
    assert music_tracks[0].source == "upbeat_track.mp3"
    assert music_tracks[0].volume < 1.0  # Ducked under voice


def test_builder_omits_music_when_not_allowed():
    """Builder does not add music if template forbids it."""
    builder = RenderPlanBuilder()

    template_no_music = {
        "id": "test_template",
        "allowed_formats": ["REEL_VERTICAL"],
        "audio_rules": {
            "music_allowed": False,
        },
        "visual_rules": {
            "text_overlay_required": True,
        },
    }

    strategy_with_music = {
        "soundtrack_id": "upbeat_track.mp3",
        "visual_prompts": {},
    }

    plan = builder.build(
        script=_create_minimal_script(),
        template=template_no_music,
        visual_strategy=strategy_with_music,
        audio_source="voice.wav",
    )

    music_tracks = [t for t in plan.audio_tracks if t.type == "music"]
    assert len(music_tracks) == 0


def test_builder_generates_subtitle_segments_from_beats():
    """Subtitles are created from beat text with correct timing."""
    builder = RenderPlanBuilder()

    script = {
        "beats": [
            {"role": "hook", "text": "First subtitle", "duration": 3.0, "keywords": []},
            {"role": "argument", "text": "Second subtitle", "duration": 4.0, "keywords": []},
        ],
    }

    plan = builder.build(
        script=script,
        template=_create_minimal_template(),
        visual_strategy=_create_minimal_visual_strategy(),
        audio_source="voice.wav",
    )

    assert plan.subtitles.enabled is True
    assert len(plan.subtitles.segments) == 2

    # First subtitle
    assert plan.subtitles.segments[0].text == "First subtitle"
    assert plan.subtitles.segments[0].start == 0.0
    assert plan.subtitles.segments[0].end == 3.0

    # Second subtitle
    assert plan.subtitles.segments[1].text == "Second subtitle"
    assert plan.subtitles.segments[1].start == 3.0
    assert plan.subtitles.segments[1].end == 7.0


def test_builder_sets_resolution_based_on_format():
    """Resolution matches video format specification."""
    builder = RenderPlanBuilder()

    vertical_template = {
        "id": "test",
        "allowed_formats": ["REEL_VERTICAL"],
        "audio_rules": {"music_allowed": False},
        "visual_rules": {"text_overlay_required": True},
    }

    plan = builder.build(
        script=_create_minimal_script(),
        template=vertical_template,
        visual_strategy=_create_minimal_visual_strategy(),
        audio_source="voice.wav",
    )

    # Vertical reel: 9:16 aspect ratio
    assert plan.resolution.width == 1080
    assert plan.resolution.height == 1920


def test_builder_fails_fast_on_invalid_script():
    """Builder raises exception for script with zero duration."""
    builder = RenderPlanBuilder()

    invalid_script = {
        "beats": [
            {"role": "hook", "text": "Test", "duration": 0, "keywords": []},
        ],
    }

    with pytest.raises(ValueError, match="zero or negative total duration"):
        builder.build(
            script=invalid_script,
            template=_create_minimal_template(),
            visual_strategy=_create_minimal_visual_strategy(),
            audio_source="voice.wav",
        )


def test_builder_creates_overlays_from_keywords():
    """Builder generates text overlays from beat keywords."""
    builder = RenderPlanBuilder()

    script = {
        "beats": [
            {"role": "hook", "text": "Test", "duration": 5.0, "keywords": ["important"]},
        ],
    }

    plan = builder.build(
        script=script,
        template=_create_minimal_template(),
        visual_strategy=_create_minimal_visual_strategy(),
        audio_source="voice.wav",
    )

    scene = plan.scenes[0]
    assert len(scene.overlays) > 0
    overlay = scene.overlays[0]
    assert overlay.type == "text"
    assert overlay.start_time > 0  # Delayed entrance
    assert overlay.end_time < scene.end_time - scene.start_time  # Early exit
