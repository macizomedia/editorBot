# Quick Start Test Session

Run this to start:
```bash
cd /Users/user/Documents/BLAS/PRODUCTION/DIALECT_BOT_TERRAFORM_AWS_V1/editorbot-stack/editorBot
editorbot-cli --verbose
```

## Test Sequence

### 1. Check Initial State
```
state
```
Expected: `idle`

### 2. Send Voice Message
```
voice sandbox/audio_samples/test_voice_short.wav
```
Expected logs:
- `voice_message_received` with duration ~8s, file size ~262KB
- State changes to `voice_received`

### 3. Wait for Transcription
(Automatic - Whisper runs)

Expected logs:
- `transcription_complete` with transcript preview
- State changes to `transcribed`

Check state:
```
state
```

### 4. Wait for Mediation
(Automatic - Gemini runs)

Expected logs:
- `mediation_complete` with enhanced text preview
- State changes to `mediated`

Check state:
```
state
```

### 5. Confirm Script
```
text OK
```
Expected logs:
- `script_generated` with script preview
- State changes to `script_generated`

Check state:
```
state --json
```
Look for `final_script` with `beats` array.

### 6. Select Template
```
click template:explainer_slides
```
Expected logs:
- `template_selected` with template_id
- State changes to `template_selected` → `asset_options`

### 7. Select Soundtrack
```
click soundtrack:upbeat
```
Expected logs:
- `soundtrack_selected` with soundtrack_id
- `render_plan_build_started`
- `render_plan_parsing_complete`
- `render_plan_build_complete` with metrics
- State changes to `render_plan_generated`

Check render plan:
```
state --json
```
Look for `render_plan` object with:
- `render_plan_id`
- `scenes` array
- `audio_tracks` array
- `subtitles`

### 8. Confirm Render Plan
```
click confirm_render_plan
```
Expected:
- State changes to `ready_for_render`

## If Something Goes Wrong

Reset and try again:
```
reset
```

Exit:
```
exit
```

## Save Your Session

To capture all logs:
```bash
editorbot-cli --verbose 2>&1 | tee sandbox/test_session.log
```

Then follow the test sequence above.
