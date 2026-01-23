"""
Integration Tests for Render Plan Layer

Tests verify:
- Complete workflow (build → validate → serialize → deserialize)
- Snapshot testing (JSON output consistency)
- Integration with upstream layers
"""

import json
import pytest

from bot.render_plan.builder import RenderPlanBuilder
from bot.render_plan.validator import validate_render_plan
from bot.render_plan.serializer import serialize_render_plan, deserialize_render_plan


def _create_realistic_script():
    """Create a realistic script matching actual use case."""
    return {
        "beats": [
            {
                "role": "hook",
                "text": "¿Alguna vez te preguntaste por qué las cosas son así?",
                "duration": 5.2,
                "keywords": ["preguntaste"],
            },
            {
                "role": "argument",
                "text": "La respuesta está en la historia.",
                "duration": 4.8,
                "keywords": ["historia"],
            },
            {
                "role": "argument",
                "text": "Cada decisión tiene consecuencias.",
                "duration": 4.5,
                "keywords": ["consecuencias"],
            },
            {
                "role": "conclusion",
                "text": "Y ahora tú puedes elegir.",
                "duration": 3.5,
                "keywords": ["elegir"],
            },
        ],
    }


def _create_realistic_template():
    """Create a realistic template matching actual use case."""
    return {
        "id": "opinion_monologue_reel",
        "allowed_formats": ["REEL_VERTICAL"],
        "audio_rules": {
            "music_allowed": True,
        },
        "visual_rules": {
            "text_overlay_required": True,
        },
    }


def _create_realistic_visual_strategy():
    """Create a realistic visual strategy."""
    return {
        "soundtrack_id": "upbeat_energy_01.mp3",
        "visual_prompts": {
            "hook_0": "dramatic_question_visual",
            "argument_1": "historical_imagery",
        },
    }


def test_complete_workflow_build_validate_serialize():
    """Complete workflow from inputs to JSON output."""
    # Build
    builder = RenderPlanBuilder()
    plan = builder.build(
        script=_create_realistic_script(),
        template=_create_realistic_template(),
        visual_strategy=_create_realistic_visual_strategy(),
        audio_source="s3://bucket/audio/voice_original.wav",
    )

    # Validate
    validation = validate_render_plan(plan)
    assert validation.passed is True
    assert validation.fatal_count == 0

    # Serialize
    serialized = serialize_render_plan(plan)
    json_str = json.dumps(serialized, indent=2)
    assert len(json_str) > 0

    # Verify JSON is parseable
    parsed = json.loads(json_str)
    assert parsed["format"] == "REEL_VERTICAL"


def test_deserialized_plan_passes_validation():
    """Plan survives round-trip and remains valid."""
    builder = RenderPlanBuilder()

    original_plan = builder.build(
        script=_create_realistic_script(),
        template=_create_realistic_template(),
        visual_strategy=_create_realistic_visual_strategy(),
        audio_source="audio.wav",
    )

    # Serialize and deserialize
    serialized = serialize_render_plan(original_plan)
    restored_plan = deserialize_render_plan(serialized)

    # Validate restored plan
    validation = validate_render_plan(restored_plan)
    assert validation.passed is True


def test_realistic_plan_has_expected_structure():
    """Generated plan contains all expected components."""
    builder = RenderPlanBuilder()

    plan = builder.build(
        script=_create_realistic_script(),
        template=_create_realistic_template(),
        visual_strategy=_create_realistic_visual_strategy(),
        audio_source="audio.wav",
    )

    # Verify structure
    assert plan.format == "REEL_VERTICAL"
    assert plan.fps == 30
    assert plan.resolution.width == 1080
    assert plan.resolution.height == 1920

    # Should have 4 scenes (4 beats)
    assert len(plan.scenes) == 4

    # Should have voice + music (2 audio tracks)
    assert len(plan.audio_tracks) == 2
    voice_track = [t for t in plan.audio_tracks if t.type == "voice"][0]
    music_track = [t for t in plan.audio_tracks if t.type == "music"][0]
    assert voice_track.volume == 1.0
    assert music_track.volume < 1.0  # Ducked

    # Subtitles should be enabled with 4 segments
    assert plan.subtitles.enabled is True
    assert len(plan.subtitles.segments) == 4

    # Output should be configured for Instagram
    assert plan.output.platform_profile == "instagram_reel"
    assert plan.output.container == "mp4"


# Snapshot testing disabled (requires pytest-snapshot)
# def test_json_snapshot_structure(snapshot):
#     """JSON output structure matches expected snapshot."""
#     builder = RenderPlanBuilder()

#     # Use fixed inputs for deterministic output (except UUID)
#     plan = builder.build(
#         script={
#             "beats": [
#                 {"role": "hook", "text": "Test", "duration": 5.0, "keywords": ["test"]},
#             ],
#         },
#         template={
#             "id": "test_template",
#             "allowed_formats": ["REEL_VERTICAL"],
#             "audio_rules": {"music_allowed": False},
#             "visual_rules": {"text_overlay_required": True},
#         },
#         visual_strategy={
#             "soundtrack_id": None,
#             "visual_prompts": {},
#         },
#         audio_source="audio.wav",
#     )

#     serialized = serialize_render_plan(plan)

#     # Remove non-deterministic fields for snapshot comparison
#     serialized_copy = serialized.copy()
#     serialized_copy["render_plan_id"] = "rp-snapshot"  # Replace UUID
#     serialized_copy["output"]["filename"] = "snapshot.mp4"  # Replace timestamp

#     # Convert to formatted JSON
#     json_output = json.dumps(serialized_copy, indent=2, sort_keys=True)

#     # Verify structure (snapshot comparison would go here in actual test)
#     assert "render_plan_id" in serialized_copy
#     assert "scenes" in serialized_copy
#     assert len(serialized_copy["scenes"]) == 1


def test_scene_timing_is_continuous():
    """All scenes connect without gaps."""
    builder = RenderPlanBuilder()

    plan = builder.build(
        script=_create_realistic_script(),
        template=_create_realistic_template(),
        visual_strategy=_create_realistic_visual_strategy(),
        audio_source="audio.wav",
    )

    # First scene starts at 0
    assert plan.scenes[0].start_time == 0.0

    # Each scene connects to next
    for i in range(len(plan.scenes) - 1):
        current_end = plan.scenes[i].end_time
        next_start = plan.scenes[i + 1].start_time
        assert abs(current_end - next_start) < 0.001  # Allow floating point tolerance

    # Last scene ends at total duration
    assert abs(plan.scenes[-1].end_time - plan.total_duration_seconds) < 0.001


def test_subtitle_timing_matches_scenes():
    """Subtitles align with scene timing."""
    builder = RenderPlanBuilder()

    plan = builder.build(
        script=_create_realistic_script(),
        template=_create_realistic_template(),
        visual_strategy=_create_realistic_visual_strategy(),
        audio_source="audio.wav",
    )

    # Should have same number of subtitles as scenes
    assert len(plan.subtitles.segments) == len(plan.scenes)

    # Each subtitle should align with corresponding scene
    for i, (scene, subtitle) in enumerate(zip(plan.scenes, plan.subtitles.segments)):
        assert abs(subtitle.start - scene.start_time) < 0.001
        assert abs(subtitle.end - scene.end_time) < 0.001


def test_builder_with_minimal_inputs_produces_valid_plan():
    """Builder gracefully handles minimal inputs."""
    builder = RenderPlanBuilder()

    minimal_script = {
        "beats": [
            {"role": "hook", "text": "Minimal", "duration": 3.0, "keywords": []},
        ],
    }

    minimal_template = {
        "id": "minimal",
        "allowed_formats": ["REEL_VERTICAL"],
        "audio_rules": {"music_allowed": False},
        "visual_rules": {"text_overlay_required": False},
    }

    minimal_strategy = {
        "soundtrack_id": None,
        "visual_prompts": {},
    }

    plan = builder.build(
        script=minimal_script,
        template=minimal_template,
        visual_strategy=minimal_strategy,
        audio_source="audio.wav",
    )

    validation = validate_render_plan(plan)
    assert validation.passed is True
