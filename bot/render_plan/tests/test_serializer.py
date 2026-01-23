"""
Tests for Render Plan Serializer

Tests verify:
- Round-trip serialization (plan → JSON → plan)
- JSON structure is stable
- Deserialization handles valid input
- Type safety is maintained
"""

import json

from bot.render_plan.models import (
    RenderPlan,
    Resolution,
    AudioTrack,
    Scene,
    Visual,
    Transition,
    Subtitles,
    Output,
)
from bot.render_plan.serializer import (
    serialize_render_plan,
    deserialize_render_plan,
)


def _create_test_plan() -> RenderPlan:
    """Create a complete RenderPlan for testing."""
    return RenderPlan(
        render_plan_id="rp-test-123",
        format="REEL_VERTICAL",
        total_duration_seconds=15.5,
        fps=30,
        resolution=Resolution(width=1080, height=1920),
        audio_tracks=[
            AudioTrack(
                type="voice",
                source="voice.wav",
                start_time=0.0,
                volume=1.0,
                fade_in=None,
                fade_out=None,
            ),
        ],
        scenes=[
            Scene(
                scene_id="scene_1",
                start_time=0.0,
                end_time=15.5,
                visual=Visual(
                    type="solid_color",
                    source="#000000",
                    prompt_ref=None,
                    motion=None,
                    background_color="#000000",
                ),
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


def test_serialization_produces_json_compatible_dict():
    """Serialized plan can be converted to JSON string."""
    plan = _create_test_plan()
    serialized = serialize_render_plan(plan)

    # Should not raise exception
    json_string = json.dumps(serialized)
    assert isinstance(json_string, str)
    assert len(json_string) > 0


def test_serialization_preserves_all_top_level_fields():
    """Serialized dict contains all required RenderPlan fields."""
    plan = _create_test_plan()
    serialized = serialize_render_plan(plan)

    assert "render_plan_id" in serialized
    assert "format" in serialized
    assert "total_duration_seconds" in serialized
    assert "fps" in serialized
    assert "resolution" in serialized
    assert "audio_tracks" in serialized
    assert "scenes" in serialized
    assert "subtitles" in serialized
    assert "output" in serialized


def test_serialization_preserves_field_values():
    """Serialized values match original plan values."""
    plan = _create_test_plan()
    serialized = serialize_render_plan(plan)

    assert serialized["render_plan_id"] == "rp-test-123"
    assert serialized["format"] == "REEL_VERTICAL"
    assert serialized["total_duration_seconds"] == 15.5
    assert serialized["fps"] == 30


def test_serialization_handles_nested_objects():
    """Nested objects (resolution, scenes) are serialized correctly."""
    plan = _create_test_plan()
    serialized = serialize_render_plan(plan)

    # Resolution is nested dict
    assert serialized["resolution"]["width"] == 1080
    assert serialized["resolution"]["height"] == 1920

    # Scenes are array of dicts
    assert len(serialized["scenes"]) == 1
    assert serialized["scenes"][0]["scene_id"] == "scene_1"


def test_serialization_handles_optional_fields():
    """Optional fields (None values) are preserved in serialization."""
    plan = _create_test_plan()
    serialized = serialize_render_plan(plan)

    audio_track = serialized["audio_tracks"][0]
    assert audio_track["fade_in"] is None
    assert audio_track["fade_out"] is None


def test_deserialization_reconstructs_render_plan():
    """Deserialized dict creates valid RenderPlan object."""
    plan = _create_test_plan()
    serialized = serialize_render_plan(plan)
    deserialized = deserialize_render_plan(serialized)

    assert isinstance(deserialized, RenderPlan)
    assert deserialized.render_plan_id == plan.render_plan_id
    assert deserialized.format == plan.format


def test_round_trip_serialization_preserves_data():
    """Plan → serialize → deserialize → produces equivalent plan."""
    original_plan = _create_test_plan()

    # Serialize
    serialized = serialize_render_plan(original_plan)

    # Deserialize
    restored_plan = deserialize_render_plan(serialized)

    # Verify equivalence
    assert restored_plan.render_plan_id == original_plan.render_plan_id
    assert restored_plan.format == original_plan.format
    assert restored_plan.total_duration_seconds == original_plan.total_duration_seconds
    assert restored_plan.fps == original_plan.fps
    assert restored_plan.resolution.width == original_plan.resolution.width
    assert restored_plan.resolution.height == original_plan.resolution.height
    assert len(restored_plan.audio_tracks) == len(original_plan.audio_tracks)
    assert len(restored_plan.scenes) == len(original_plan.scenes)


def test_deserialization_converts_numeric_types_correctly():
    """Deserialization handles type conversions (int, float)."""
    data = {
        "render_plan_id": "rp-test",
        "format": "REEL_VERTICAL",
        "total_duration_seconds": "10.5",  # String (from JSON parsing)
        "fps": "30",  # String
        "resolution": {"width": "1080", "height": "1920"},
        "audio_tracks": [],
        "scenes": [],
        "subtitles": {"enabled": False, "style": "", "segments": []},
        "output": {
            "container": "mp4",
            "codec": "h264",
            "bitrate": "6M",
            "platform_profile": "instagram_reel",
            "filename": "test.mp4",
        },
    }

    plan = deserialize_render_plan(data)

    assert isinstance(plan.total_duration_seconds, float)
    assert isinstance(plan.fps, int)
    assert isinstance(plan.resolution.width, int)


def test_serialization_json_structure_is_stable():
    """JSON structure remains consistent across multiple serializations."""
    plan = _create_test_plan()

    serialized1 = serialize_render_plan(plan)
    json_str1 = json.dumps(serialized1, sort_keys=True)

    serialized2 = serialize_render_plan(plan)
    json_str2 = json.dumps(serialized2, sort_keys=True)

    # Same input produces same JSON (stable ordering)
    assert json_str1 == json_str2


def test_serialization_handles_complex_scene_with_overlays():
    """Scenes with overlays serialize correctly."""
    from bot.render_plan.models import Overlay, SubtitleSegment

    complex_plan = RenderPlan(
        render_plan_id="rp-complex",
        format="REEL_VERTICAL",
        total_duration_seconds=10.0,
        fps=30,
        resolution=Resolution(width=1080, height=1920),
        audio_tracks=[],
        scenes=[
            Scene(
                scene_id="scene_1",
                start_time=0.0,
                end_time=10.0,
                visual=Visual(type="solid_color", source="#000000"),
                overlays=[
                    Overlay(
                        type="text",
                        content_ref="keyword",
                        position="center",
                        start_time=1.0,
                        end_time=5.0,
                        style="bold",
                        animation="fade_in",
                    ),
                ],
                transition_in=Transition(type="cut", duration=0.0),
                transition_out=Transition(type="fade", duration=0.5),
            ),
        ],
        subtitles=Subtitles(
            enabled=True,
            style="default",
            segments=[
                SubtitleSegment(start=0.0, end=3.0, text="Test subtitle", highlight=["Test"]),
            ],
        ),
        output=Output(
            container="mp4",
            codec="h264",
            bitrate="6M",
            platform_profile="instagram_reel",
            filename="complex.mp4",
        ),
    )

    serialized = serialize_render_plan(complex_plan)

    # Verify overlay serialization
    assert len(serialized["scenes"][0]["overlays"]) == 1
    overlay = serialized["scenes"][0]["overlays"][0]
    assert overlay["type"] == "text"
    assert overlay["animation"] == "fade_in"

    # Verify subtitle serialization
    assert serialized["subtitles"]["enabled"] is True
    assert len(serialized["subtitles"]["segments"]) == 1
    segment = serialized["subtitles"]["segments"][0]
    assert segment["text"] == "Test subtitle"
    assert segment["highlight"] == ["Test"]

    # Verify round-trip
    restored = deserialize_render_plan(serialized)
    assert len(restored.scenes[0].overlays) == 1
    assert len(restored.subtitles.segments) == 1
