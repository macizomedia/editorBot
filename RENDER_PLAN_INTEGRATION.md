# Render Plan Integration — Complete

## ✅ What Was Implemented

### 1. State Machine Integration
**New State:** `RENDER_PLAN_GENERATED`
- Inserted between `ASSET_OPTIONS` and `READY_FOR_RENDER`
- Bot now builds render plan after assets are configured

**New Events:**
- `RENDER_PLAN_BUILT` — Triggered when render plan is successfully created
- `RENDER_PLAN_VALIDATED` — Reserved for explicit validation step (optional)

**Updated Conversation Model:**
- Added `visual_strategy: Dict[str, Any]` — Visual generation config
- Added `render_plan: Dict[str, Any]` — Serialized RenderPlan (JSON ready for render engine)

### 2. Handler Logic
**New File:** `bot/handlers/render_plan.py`
- `build_render_plan()` — Orchestrates building + validation + serialization
- `format_render_plan_summary()` — Generates Telegram-friendly summary

**Updated:** `bot/handlers/callbacks.py`
- When user selects soundtrack, automatically triggers render plan generation
- Displays validation errors to user if plan is invalid
- Shows summary when plan is ready

### 3. Complete Workflow

```
IDLE
  ↓ (user sends voice)
AUDIO_RECEIVED
  ↓ (transcription complete)
TRANSCRIBED
  ↓ (mediator enhances)
MEDIATED
  ↓ (user approves)
SCRIPT_DRAFTED
  ↓ (user approves)
FINAL_SCRIPT
  ↓ (user selects template)
TEMPLATE_PROPOSED
  ↓ (user selects soundtrack)
SELECT_SOUNDTRACK
  ↓ (assets configured automatically)
ASSET_OPTIONS
  ↓ (render plan built + validated)  ← NEW
RENDER_PLAN_GENERATED               ← NEW
  ↓ (plan serialized to JSON)       ← NEW
READY_FOR_RENDER
  ↓ (user triggers render)
IDLE (after render completes)
```

---

## 📦 Output: JSON Render Plan

When state reaches `READY_FOR_RENDER`, the `convo.render_plan` field contains:

```json
{
  "render_plan_id": "rp-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "total_duration": 45.5,
  "resolution": {
    "width": 1080,
    "height": 1920,
    "fps": 30
  },
  "audio_tracks": [
    {
      "track_id": "audio-voice",
      "source": "s3://content-pipeline/audio/123456/narration.wav",
      "volume": 1.0,
      "start_time": 0.0,
      "fade_in": null,
      "fade_out": null
    },
    {
      "track_id": "audio-music",
      "source": "s3://content-pipeline/music/lofi1.mp3",
      "volume": 0.3,
      "start_time": 0.0,
      "fade_in": 2.0,
      "fade_out": 3.0
    }
  ],
  "scenes": [
    {
      "scene_id": "scene-0",
      "start_time": 0.0,
      "duration": 5.5,
      "visual": {
        "type": "generated_image",
        "prompt": "Cinematic wide shot of a modern city skyline at sunset",
        "seed": 42,
        "guidance_scale": 7.5
      },
      "overlays": [
        {
          "overlay_id": "overlay-text-0",
          "type": "text",
          "content": "MODERN",
          "position": {"x": 0.5, "y": 0.8},
          "font_size": 48,
          "color": "#FFFFFF",
          "start_time": 1.0,
          "duration": 2.0
        }
      ],
      "transition": {
        "type": "crossfade",
        "duration": 0.5
      }
    }
  ],
  "subtitles": {
    "font": "Arial",
    "font_size": 36,
    "color": "#FFFFFF",
    "background_color": "#000000",
    "position": "bottom",
    "segments": [
      {
        "text": "Welcome to our story",
        "start_time": 0.5,
        "end_time": 3.0,
        "highlight_words": ["Welcome"]
      }
    ]
  },
  "output": {
    "filename": "video_20260123_123045.mp4",
    "container": "mp4",
    "codec": "libx264",
    "bitrate": 5000,
    "platform_profile": "instagram_reel"
  }
}
```

---

## 🎯 What This JSON Enables

### For the Render Engine
This JSON is a **complete, deterministic specification** that tells the render engine:

1. **Timeline structure** — Exact scene timing (no gaps, no overlaps)
2. **Audio mixing** — Voice + music tracks with volumes and fades
3. **Visual generation** — AI prompts for each scene (ready for Stable Diffusion)
4. **Text overlays** — Keywords to display at specific times
5. **Subtitles** — Timed text segments (from Whisper transcription)
6. **Output format** — Resolution, codec, platform optimization

### No Human Intervention Required
The render engine can:
- Generate images via Stable Diffusion API
- Fetch audio from S3
- Assemble video using FFmpeg
- Burn subtitles
- Export final MP4

**This JSON is the contract between Bot ↔ Render Engine.**

---

## 🚧 What's Left to Implement

### 1. Render Engine (Separate Service)
**Location:** New container or Lambda function

**Responsibilities:**
- Accept JSON render plan via API or S3
- Generate images (call GPU instance with Stable Diffusion)
- Download audio from S3
- Assemble video using FFmpeg/MoviePy
- Upload final video to S3
- Notify bot when complete

**Tools needed:**
- Python FFmpeg wrapper (e.g., `ffmpeg-python`)
- Stable Diffusion API client
- S3 upload logic

**Estimated work:** 3-5 days

---

### 2. Actual Audio Upload to S3
**Current:** Placeholder path `s3://content-pipeline/audio/{chat_id}/narration.wav`

**Needed:**
- When user sends voice message, upload to S3
- Store S3 path in conversation state
- Pass real path to render plan builder

**Estimated work:** 1-2 hours

---

### 3. Visual Strategy UI (Asset Configuration)
**Current:** Hardcoded default config in `callbacks.py`

**Needed:**
- Let user configure visual style:
  - Style preset (cinematic, cartoon, photorealistic)
  - Custom prompts per scene/beat
  - Seed control for determinism
- UI flow after soundtrack selection

**Estimated work:** 1-2 days

---

### 4. Render Approval Flow
**Current:** State machine reaches `READY_FOR_RENDER` but no trigger exists

**Needed:**
- Show render plan summary to user
- `/render` command to trigger render engine
- Poll or webhook for render completion
- Send final video back to Telegram

**Estimated work:** 1-2 days

---

### 5. Error Handling & Retries
**Needed:**
- Render engine failures (GPU timeout, S3 errors)
- Retry logic with exponential backoff
- User notifications for failures

**Estimated work:** 1 day

---

### 6. Template System (Partially Done)
**Current:** Templates exist but are basic

**Needed:**
- More sophisticated template rules:
  - Scene transition styles
  - Text overlay positioning per template
  - Audio mix constraints
- Template validation against script

**Estimated work:** 2-3 days

---

## 📊 Summary

| Component | Status | Output |
|-----------|--------|--------|
| **Render Plan Domain Models** | ✅ Complete | Immutable dataclasses |
| **Validator** | ✅ Complete | Fatal/warning distinction |
| **Builder** | ✅ Complete | Deterministic construction |
| **Serializer** | ✅ Complete | JSON serialization |
| **State Machine Integration** | ✅ Complete | New state + events |
| **Handler Logic** | ✅ Complete | Build → validate → serialize |
| **JSON Output** | ✅ Complete | Ready for render engine |
| | | |
| **Render Engine** | ❌ Not Started | Video assembly service |
| **Audio Upload to S3** | ❌ Not Started | Real audio paths |
| **Visual Strategy UI** | ❌ Not Started | User asset config |
| **Render Trigger** | ❌ Not Started | `/render` command |
| **Template System** | 🟡 Partial | Needs refinement |

---

## 🎉 Current Achievement

**The bot now produces a complete, validated, render-ready JSON specification.**

This JSON is:
- ✅ Deterministic (same inputs → same output)
- ✅ Validated (no timing overlaps, all required fields present)
- ✅ Self-contained (all info needed to render video)
- ✅ Platform-aware (Instagram/TikTok format rules)

**Next milestone:** Build the render engine to consume this JSON and produce MP4 files.
