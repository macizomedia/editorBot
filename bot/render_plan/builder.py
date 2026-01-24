"""
Render Plan Builder

Deterministically constructs a RenderPlan from creative inputs.

Design Principles:
- Single public method: build()
- No randomness (deterministic output)
- No retries (fails fast)
- No LLM calls (no AI decisions)
- No I/O (pure computation)
- No hidden state (all state in parameters)

Build Flow:
1. Extract metadata from inputs
2. Calculate video dimensions and format
3. Build audio tracks
4. Allocate timeline (map beats to scenes)
5. Construct scenes with visuals
6. Generate subtitle segments
7. Configure output encoding
8. Assemble final RenderPlan

The builder translates creative intent into precise rendering instructions.
"""

from __future__ import annotations

import logging
import uuid
from typing import Dict, Any, List, Tuple

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

logger = logging.getLogger(__name__)


class RenderPlanBuilder:
    """
    Constructs RenderPlan from creative inputs.

    Responsibility:
    Transform Script + TemplateSpec + VisualStrategy into deterministic RenderPlan.

    This is a stateless builder (no instance variables).
    All logic is deterministic (same inputs → same output).
    """

    def build(
        self,
        script: Dict[str, Any],
        template: Dict[str, Any],
        visual_strategy: Dict[str, Any],
        audio_source: str,
    ) -> RenderPlan:
        """
        Build complete RenderPlan.

        This is the single public entry point.

        Parameters:
        - script: Final script with beats (from FINAL_SCRIPT state)
        - template: TemplateSpec (from TEMPLATE_SELECTED state)
        - visual_strategy: Visual strategy config (from VISUAL_STRATEGY_READY state)
        - audio_source: Reference to original voice audio (S3 path or identifier)

        Returns:
        Complete, validated RenderPlan ready for rendering.

        Note:
        Inputs are dicts (not domain objects) to avoid coupling to upstream layers.
        Builder extracts only what it needs.
        """

        logger.info(
            "render_plan_build_started",
            extra={
                "num_beats": len(script.get("beats", [])),
                "template_id": template.get("id", "unknown") if isinstance(template, dict) else getattr(template, "id", "unknown"),
                "has_soundtrack": visual_strategy.get("soundtrack_id") is not None,
            }
        )

        # Step 1: Generate unique identifier
        render_plan_id = self._generate_plan_id()

        # Step 2: Determine video format and resolution
        video_format = self._extract_format(template)
        resolution = self._calculate_resolution(video_format)
        fps = self._determine_fps(video_format)

        # Step 3: Calculate total duration from script
        total_duration = self._calculate_total_duration(script)

        # Step 4: Build audio tracks (voice + optional music)
        audio_tracks = self._build_audio_tracks(
            audio_source=audio_source,
            total_duration=total_duration,
            template=template,
            visual_strategy=visual_strategy,
        )

        # Step 5: Allocate timeline (map script beats to scenes)
        scenes = self._build_scenes(
            script=script,
            visual_strategy=visual_strategy,
            total_duration=total_duration,
        )

        # Step 6: Generate subtitle segments from script
        subtitles = self._build_subtitles(
            script=script,
            template=template,
        )

        # Step 7: Configure output encoding
        output = self._build_output(
            video_format=video_format,
            template=template,
        )

        # Step 8: Assemble final RenderPlan
        render_plan = RenderPlan(
            render_plan_id=render_plan_id,
            format=video_format,
            total_duration_seconds=total_duration,
            fps=fps,
            resolution=resolution,
            audio_tracks=audio_tracks,
            scenes=scenes,
            subtitles=subtitles,
            output=output,
        )

        logger.info(
            "render_plan_build_complete",
            extra={
                "render_plan_id": render_plan_id,
                "total_duration": total_duration,
                "num_scenes": len(scenes),
                "num_audio_tracks": len(audio_tracks),
                "resolution": f"{resolution.width}x{resolution.height}",
                "fps": fps,
            }
        )

        return render_plan

    def _generate_plan_id(self) -> str:
        """
        Generate unique render plan identifier.

        Why UUID:
        - Globally unique (no collision risk)
        - Useful for logging, debugging, audit trails
        - Deterministic alternative would require complex seeding

        Returns:
        UUID string (e.g., "rp-550e8400-e29b-41d4-a716-446655440000")
        """
        return f"rp-{uuid.uuid4()}"

    def _extract_format(self, template: Dict[str, Any]) -> str:
        """
        Extract video format from template.

        Template specifies allowed_formats (e.g., ["REEL_VERTICAL"]).
        We take the first format (template should have been validated upstream).

        Parameters:
        - template: TemplateSpec dict

        Returns:
        Format string (e.g., "REEL_VERTICAL", "LANDSCAPE_16_9")
        """
        allowed_formats = template.get("allowed_formats", [])
        if not allowed_formats:
            # Fallback to default (should not happen if template is validated)
            return "REEL_VERTICAL"

        return allowed_formats[0]

    def _calculate_resolution(self, video_format: str) -> Resolution:
        """
        Calculate pixel resolution based on video format.

        Format determines aspect ratio and platform requirements.

        Why hardcoded mappings:
        - Platform requirements are stable (Instagram Reels = 1080x1920)
        - Avoids configuration complexity
        - Makes output predictable

        Parameters:
        - video_format: Format string (e.g., "REEL_VERTICAL")

        Returns:
        Resolution with width and height
        """
        format_resolutions = {
            "REEL_VERTICAL": Resolution(width=1080, height=1920),  # 9:16
            "LANDSCAPE_16_9": Resolution(width=1920, height=1080),  # 16:9
            "SQUARE_1_1": Resolution(width=1080, height=1080),  # 1:1
            "PORTRAIT_4_5": Resolution(width=1080, height=1350),  # 4:5
        }

        return format_resolutions.get(
            video_format,
            Resolution(width=1080, height=1920),  # Default: vertical
        )

    def _determine_fps(self, video_format: str) -> int:
        """
        Determine frames per second based on format.

        Why 30 FPS:
        - Standard for social media (Instagram, TikTok, YouTube)
        - Good balance of smoothness and file size
        - Compatible with most devices

        Why not 60 FPS:
        - Larger file sizes
        - Minimal quality improvement for static/slow content
        - Can be added as format-specific override if needed

        Parameters:
        - video_format: Format string

        Returns:
        FPS (currently always 30)
        """
        return 30  # Standard for social media

    def _calculate_total_duration(self, script: Dict[str, Any]) -> float:
        """
        Calculate total video duration from script.

        Script contains beats with individual durations.
        Total duration = sum of all beat durations.

        Parameters:
        - script: Script dict with 'beats' array

        Returns:
        Total duration in seconds
        """
        beats = script.get("beats", [])
        total = sum(beat.get("duration", 0) for beat in beats)

        # Sanity check (should be caught by upstream validation)
        if total <= 0:
            raise ValueError("Script has zero or negative total duration")

        return float(total)

    def _build_audio_tracks(
        self,
        audio_source: str,
        total_duration: float,
        template: Dict[str, Any],
        visual_strategy: Dict[str, Any],
    ) -> List[AudioTrack]:
        """
        Build audio track list.

        Always includes voice track.
        Optionally includes music track (if template allows).

        Parameters:
        - audio_source: Voice audio reference (S3 path or identifier)
        - total_duration: Video length (for music fade calculation)
        - template: TemplateSpec (to check music_allowed)
        - visual_strategy: Visual config (to check soundtrack selection)

        Returns:
        List of AudioTrack objects (1-2 tracks)
        """
        tracks = []

        # Voice track (always present)
        voice_track = AudioTrack(
            type="voice",
            source=audio_source,
            start_time=0.0,
            volume=1.0,
            fade_in=None,
            fade_out=None,
        )
        tracks.append(voice_track)

        # Music track (optional, based on template and user selection)
        audio_rules = template.get("audio_rules", {})
        music_allowed = audio_rules.get("music_allowed", False)
        soundtrack_id = visual_strategy.get("soundtrack_id")

        if music_allowed and soundtrack_id:
            # Music track with ducking and fades
            music_track = AudioTrack(
                type="music",
                source=soundtrack_id,
                start_time=0.0,
                volume=0.25,  # Ducked under voice
                fade_in=1.5,  # Gentle entrance
                fade_out=min(2.0, total_duration * 0.1),  # Fade out last 10% or 2s
            )
            tracks.append(music_track)

        return tracks

    def _build_scenes(
        self,
        script: Dict[str, Any],
        visual_strategy: Dict[str, Any],
        total_duration: float,
    ) -> List[Scene]:
        """
        Build scene list from script beats.

        Scene allocation strategy:
        - One scene per script beat (typically)
        - Scene timing matches beat timing
        - Visual content determined by visual_strategy

        Parameters:
        - script: Script with beats
        - visual_strategy: Visual config (image prompts, strategy type)
        - total_duration: Total video length (for validation)

        Returns:
        List of Scene objects (sequential, no gaps)
        """
        scenes = []
        beats = script.get("beats", [])
        visual_prompts = visual_strategy.get("visual_prompts", {})

        current_time = 0.0

        for i, beat in enumerate(beats):
            beat_duration = beat.get("duration", 0)
            scene_id = f"scene_{i + 1}"

            # Calculate scene timing
            start_time = current_time
            end_time = start_time + beat_duration

            # Build visual for this scene
            visual = self._build_visual(
                beat=beat,
                visual_prompts=visual_prompts,
                scene_index=i,
            )

            # Build overlays (text highlights, keywords)
            overlays = self._build_overlays(
                beat=beat,
                scene_duration=beat_duration,
            )

            # Default transitions (can be enhanced later)
            transition_in = Transition(type="cut", duration=0.0)
            transition_out = Transition(type="cut", duration=0.0)

            # Assemble scene
            scene = Scene(
                scene_id=scene_id,
                start_time=start_time,
                end_time=end_time,
                visual=visual,
                overlays=overlays,
                transition_in=transition_in,
                transition_out=transition_out,
            )

            scenes.append(scene)
            current_time = end_time

        return scenes

    def _build_visual(
        self,
        beat: Dict[str, Any],
        visual_prompts: Dict[str, Any],
        scene_index: int,
    ) -> Visual:
        """
        Build visual content for a scene.

        Visual strategy determines approach:
        - "mixed": AI-generated images
        - "slides": Text-based slides
        - "minimal": Solid colors

        Parameters:
        - beat: Script beat (contains role, text, keywords)
        - visual_prompts: Pre-generated prompts for image generation
        - scene_index: Scene position (for prompt lookup)

        Returns:
        Visual object
        """
        beat_role = beat.get("role", "default")
        prompt_key = f"{beat_role}_{scene_index}"

        # Check if we have a specific prompt for this beat
        if prompt_key in visual_prompts:
            return Visual(
                type="image",
                source="ai_generated",
                prompt_ref=prompt_key,
                motion="slow_zoom_in",
                background_color="#000000",
            )

        # Fallback: solid color based on beat role
        role_colors = {
            "hook": "#1a1a1a",
            "argument": "#2a2a2a",
            "conclusion": "#3a3a3a",
        }

        background = role_colors.get(beat_role, "#000000")

        return Visual(
            type="solid_color",
            source=background,
            prompt_ref=None,
            motion=None,
            background_color=background,
        )

    def _build_overlays(
        self,
        beat: Dict[str, Any],
        scene_duration: float,
    ) -> List[Overlay]:
        """
        Build text overlays for a scene.

        Overlays highlight keywords or key phrases from the beat.

        Parameters:
        - beat: Script beat (contains keywords)
        - scene_duration: Scene length (for overlay timing)

        Returns:
        List of Overlay objects (can be empty)
        """
        overlays = []
        keywords = beat.get("keywords", [])

        if not keywords:
            return overlays

        # Display keywords in center for most of scene duration
        # Start slightly delayed, end slightly early (breathing room)
        overlay = Overlay(
            type="text",
            content_ref=f"beat_keywords",
            position="center",
            start_time=0.3,  # 300ms delay
            end_time=max(0.5, scene_duration - 0.5),  # Leave 500ms at end
            style="bold_caps",
            animation="fade_in_up",
        )
        overlays.append(overlay)

        return overlays

    def _build_subtitles(
        self,
        script: Dict[str, Any],
        template: Dict[str, Any],
    ) -> Subtitles:
        """
        Build subtitle configuration from script.

        Subtitle timing is derived from beat timing.
        Each beat becomes one or more subtitle segments.

        Parameters:
        - script: Script with beats and text
        - template: TemplateSpec (to check subtitle requirements)

        Returns:
        Subtitles object with segments
        """
        visual_rules = template.get("visual_rules", {})
        subtitles_required = visual_rules.get("text_overlay_required", True)

        if not subtitles_required:
            return Subtitles(enabled=False, style="", segments=[])

        segments = []
        beats = script.get("beats", [])
        current_time = 0.0

        for beat in beats:
            beat_text = beat.get("text", "")
            beat_duration = beat.get("duration", 0)
            keywords = beat.get("keywords", [])

            if not beat_text:
                current_time += beat_duration
                continue

            # Split long text into multiple subtitle segments
            # Simple split: one subtitle per beat (can be enhanced)
            segment = SubtitleSegment(
                start=current_time,
                end=current_time + beat_duration,
                text=beat_text,
                highlight=keywords if keywords else None,
            )
            segments.append(segment)

            current_time += beat_duration

        return Subtitles(
            enabled=True,
            style="subtitle_emphasis",
            segments=segments,
        )

    def _build_output(
        self,
        video_format: str,
        template: Dict[str, Any],
    ) -> Output:
        """
        Build output encoding configuration.

        Output settings depend on format and platform requirements.

        Parameters:
        - video_format: Video format (e.g., "REEL_VERTICAL")
        - template: TemplateSpec (for template ID/name)

        Returns:
        Output object with encoding settings
        """
        template_id = template.get("id", "default")

        # Generate filename from template and timestamp
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"editorbot_{template_id}_{timestamp}.mp4"

        # Platform-specific encoding profiles
        format_profiles = {
            "REEL_VERTICAL": ("mp4", "h264", "6M", "instagram_reel"),
            "LANDSCAPE_16_9": ("mp4", "h264", "8M", "youtube_landscape"),
            "SQUARE_1_1": ("mp4", "h264", "6M", "instagram_square"),
            "PORTRAIT_4_5": ("mp4", "h264", "6M", "instagram_portrait"),
        }

        profile = format_profiles.get(
            video_format,
            ("mp4", "h264", "6M", "generic"),
        )

        return Output(
            container=profile[0],
            codec=profile[1],
            bitrate=profile[2],
            platform_profile=profile[3],
            filename=filename,
        )
