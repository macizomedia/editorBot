# EditorBot Testing Sandbox

Testing environment for debugging bot workflow and state machine.

## Directory Structure

```
sandbox/
  audio_samples/          # Test audio files (WAV, OGG)
  test_outputs/           # Generated outputs (scripts, render plans)
  audit_logs/             # Manual audit notes
  README.md               # This file
  test_session.log        # CLI session logs
```

## Testing Workflow

### 1. Prepare Audio Sample

Record or place a test audio file:
```bash
# Example: Record with ffmpeg
ffmpeg -f avfoundation -i ":0" -t 10 -ar 16000 audio_samples/test_voice.wav

# Or use existing file
cp ~/path/to/voice.ogg audio_samples/
```

### 2. Start CLI in Verbose Mode

```bash
cd /Users/user/Documents/BLAS/PRODUCTION/DIALECT_BOT_TERRAFORM_AWS_V1/editorbot-stack/editorBot
editorbot-cli --verbose

# Or with logging to file
editorbot-cli --verbose 2>&1 | tee sandbox/test_session.log
```

### 3. State Machine Testing Sequence

#### Step 1: IDLE → VOICE_RECEIVED
```
[idle] > voice sandbox/audio_samples/test_voice.wav
```

**Expected:**
- State: `idle` → `voice_received`
- Log: `voice_message_received` with duration, file_size
- Conversation: `audio_file_path` populated

**Audit:**
- [ ] Voice file loaded successfully
- [ ] File metadata logged correctly
- [ ] State transition clean

---

#### Step 2: VOICE_RECEIVED → TRANSCRIBED
```
# Automatic: Transcription service runs
# Wait for processing...
```

**Expected:**
- State: `voice_received` → `transcribed`
- Log: `transcription_complete` with transcript preview
- Conversation: `transcript` populated

**Audit:**
- [ ] Whisper transcription completed
- [ ] Transcript readable
- [ ] No transcription errors
- [ ] Language detected correctly

---

#### Step 3: TRANSCRIBED → MEDIATED
```
# Automatic: Mediation service runs
# Wait for Gemini processing...
```

**Expected:**
- State: `transcribed` → `mediated`
- Log: `mediation_complete` with mediated preview
- Conversation: `mediated_text` populated

**Audit:**
- [ ] Gemini API responded
- [ ] Text enhanced/cleaned
- [ ] Original meaning preserved
- [ ] Grammar improved

---

#### Step 4: MEDIATED → SCRIPT_GENERATED (User confirms)
```
[mediated] > text "OK"
```

**Expected:**
- State: `mediated` → `script_generated`
- Log: `script_generated` with script preview
- Conversation: `final_script` populated with beats

**Audit:**
- [ ] Script has beats array
- [ ] Each beat has text and duration
- [ ] Total duration calculated
- [ ] Script format valid

---

#### Step 5: SCRIPT_GENERATED → TEMPLATE_SELECTED
```
[script_generated] > click "template:explainer_slides"
```

**Expected:**
- State: `script_generated` → `template_selected`
- Log: `template_selected` with template_id
- Conversation: `selected_template` = "explainer_slides"

**Audit:**
- [ ] Template loaded from templates/
- [ ] Template has valid structure
- [ ] allowed_formats present
- [ ] visual_strategy_schema present

---

#### Step 6: TEMPLATE_SELECTED → ASSET_OPTIONS
```
# Automatic: Asset options generated
# Bot should show soundtrack options
```

**Expected:**
- State: `template_selected` → `asset_options`
- Soundtrack keyboard displayed

**Audit:**
- [ ] Soundtrack options presented
- [ ] At least 2-3 options shown
- [ ] "No music" option available

---

#### Step 7: ASSET_OPTIONS → RENDER_PLAN_GENERATED
```
[asset_options] > click "soundtrack:upbeat"
```

**Expected:**
- State: `asset_options` → `render_plan_generated`
- Log: `soundtrack_selected` with soundtrack_id
- Log: `render_plan_build_started`
- Log: `render_plan_parsing_complete`
- Log: `render_plan_build_complete` with metrics
- Conversation: `render_plan` populated

**Audit:**
- [ ] Render plan has render_plan_id
- [ ] total_duration_seconds calculated
- [ ] scenes array populated
- [ ] audio_tracks has voice + soundtrack
- [ ] subtitles generated
- [ ] Validation passed (no fatal errors)

---

#### Step 8: RENDER_PLAN_GENERATED → READY_FOR_RENDER (User confirms)
```
[render_plan_generated] > click "confirm_render_plan"
```

**Expected:**
- State: `render_plan_generated` → `ready_for_render`
- Render plan summary shown

**Audit:**
- [ ] Ready for rendering
- [ ] All data present for video generation

---

### 4. Inspect State at Any Point

```bash
# Show current state
[any_state] > state

# Show as JSON for detailed inspection
[any_state] > state --json

# Copy JSON to file
[any_state] > state --json > sandbox/test_outputs/state_snapshot.json
```

### 5. Reset and Retry

```bash
# Reset to IDLE to test again
[any_state] > reset
```

---

## Common Issues to Watch For

### Transcription Issues
- [ ] Whisper fails with non-speech audio
- [ ] Very short audio (<1 sec) rejected
- [ ] Large files (>20MB) cause timeout
- [ ] Non-16kHz audio quality issues

### Mediation Issues
- [ ] Gemini API key expired
- [ ] Rate limiting errors
- [ ] Response parsing failures
- [ ] Text truncation

### Script Generation Issues
- [ ] Beats missing duration
- [ ] Empty text in beats
- [ ] Total duration mismatch
- [ ] Invalid JSON structure

### Template Issues
- [ ] Template file not found
- [ ] Invalid template schema
- [ ] Missing required fields

### Render Plan Issues
- [ ] Validation errors (check error_summary)
- [ ] Scene timing misalignment
- [ ] Audio track duration mismatch
- [ ] Subtitle timing issues

---

## Data Flow Visualization

```
┌─────────────────────────────────────────────────────┐
│  VOICE FILE                                         │
│  sandbox/audio_samples/test_voice.wav               │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  TRANSCRIPTION (Whisper)                            │
│  "Hello, today I want to talk about..."            │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  MEDIATION (Gemini)                                 │
│  Enhanced: "Hello! Today I want to talk about..."  │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  SCRIPT GENERATION                                  │
│  {                                                  │
│    "beats": [                                       │
│      {"text": "Hello!", "duration": 2.5},          │
│      {"text": "Today...", "duration": 5.0}         │
│    ]                                                │
│  }                                                  │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  TEMPLATE SELECTION                                 │
│  templates/explainer_slides.json                    │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  SOUNDTRACK SELECTION                               │
│  "upbeat" or "none"                                 │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  RENDER PLAN BUILD                                  │
│  {                                                  │
│    "render_plan_id": "rp-abc123...",               │
│    "scenes": [...],                                 │
│    "audio_tracks": [...],                          │
│    "subtitles": {...}                              │
│  }                                                  │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│  READY FOR RENDER                                   │
│  → Send to video generation pipeline                │
└─────────────────────────────────────────────────────┘
```

---

## Audit Checklist Template

Copy this for each test session:

```
### Test Session: [DATE] [TIME]

**Audio File:** sandbox/audio_samples/[filename]
**Duration:** [X] seconds
**File Size:** [X] KB

#### State Transitions
- [ ] IDLE → VOICE_RECEIVED
- [ ] VOICE_RECEIVED → TRANSCRIBED
- [ ] TRANSCRIBED → MEDIATED
- [ ] MEDIATED → SCRIPT_GENERATED
- [ ] SCRIPT_GENERATED → TEMPLATE_SELECTED
- [ ] TEMPLATE_SELECTED → ASSET_OPTIONS
- [ ] ASSET_OPTIONS → RENDER_PLAN_GENERATED
- [ ] RENDER_PLAN_GENERATED → READY_FOR_RENDER

#### Data Quality
- [ ] Transcript accurate
- [ ] Mediation improved text
- [ ] Script beats timed correctly
- [ ] Render plan validated

#### Errors Encountered
[None / List errors here]

#### Notes
[Any observations about data flow, timing, quality]
```

---

## Quick Commands Reference

```bash
# Start testing
editorbot-cli --verbose

# Send voice
voice sandbox/audio_samples/test.wav

# Send text
text "OK"

# Click button
click "template:explainer_slides"
click "soundtrack:upbeat"
click "confirm_render_plan"

# Inspect state
state
state --json

# Toggle logging
log on
log off

# Reset
reset

# Exit
exit
```
