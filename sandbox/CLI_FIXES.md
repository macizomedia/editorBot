# CLI Debugging Tool - Bug Fixes (2026-01-24)

## Issues Fixed

### 1. Conversation State Display Bug
**Problem:** `'Conversation' object has no attribute '__dict__'`

**Root Cause:** The `Conversation` dataclass uses `@dataclass(slots=True)`, which prevents access to `__dict__`.

**Solution:** Modified `bot/cli/inspector.py` to use `asdict()` from dataclasses module instead of accessing `__dict__` directly.

**Files Changed:**
- `bot/cli/inspector.py` (lines 83-112)

### 2. Voice File Handling Bug
**Problem:** Mock file download wasn't copying actual audio files, causing test failures.

**Root Cause:** Multiple issues in the mock Telegram object chain:
- `MockFile.download_to_drive()` didn't actually copy files
- `MockBot` didn't track actual file paths
- `TelegramSimulator` didn't pass itself to `MockContext`
- `create_context()` didn't pass simulator reference

**Solution:**
1. Added file path tracking to `TelegramSimulator` via `file_paths` dict
2. Modified `MockFile.download_to_drive()` to use `shutil.copy2()` for actual copying
3. Converted `MockBot` from dataclass to regular class to accept simulator reference
4. Updated `MockBot.get_file()` to lookup actual file paths from simulator
5. Modified `MockContext.__init__` to accept and pass simulator to `MockBot`
6. Updated `TelegramSimulator.create_context()` to pass itself to `MockContext`

**Files Changed:**
- `bot/cli/simulator.py` (MockFile, MockBot, MockContext, TelegramSimulator)

### 3. Structured Logging Bug
**Problem:** `AttributeError: 'str' object has no attribute '__name__'`

**Root Cause:** In state machine logging, used `str(type(payload)).__name__` instead of `type(payload).__name__`.

**Solution:** Removed extra `str()` call - `type()` already returns the type object.

**Files Changed:**
- `bot/state/machine.py` (line 41)

## Current Status

✅ **Working:**
- State display (`editorbot-cli show-state`)
- Voice message handling (`editorbot-cli send-voice <path>`)
- File copying from audio samples to temp directory
- State machine transitions
- Structured logging output
- All CLI commands (send-voice, send-text, click, show-state, reset)

⚠️ **Known Limitations:**
- **Whisper transcription fails on Python 3.14** due to build incompatibilities
  - Error: `KeyError: '__version__'` during openai-whisper installation
  - Bot shows: "No pude transcribir el audio"
  - This is expected and does not block CLI testing of state machine flow

## Testing the CLI

### Test State Display:
```bash
editorbot-cli show-state --verbose
```

### Test Voice Message (will fail at transcription but tests file handling):
```bash
editorbot-cli send-voice sandbox/audio_samples/audio_2026-01-24_09-21-30.ogg --verbose
```

### Expected Output:
- ✅ "Audio recibido. Transcribiendo..."
- ✅ State transitions logged
- ⚠️ "No pude transcribir el audio" (Whisper not available)

### Test Text Message:
```bash
editorbot-cli send-text "Test message" --verbose
```

### Test Button Click:
```bash
editorbot-cli click "template:explainer" --verbose
```

## Next Steps for Norman Audit

Since transcription is blocked by Python 3.14 compatibility:

**Option A: Test with Mock Data**
- Modify CLI to inject transcript directly
- Focus on state machine and UX flow testing
- Document issues found in NORMAN_AUDIT_REPORT.md

**Option B: Use Cloud Bot**
- Test full workflow on Telegram with EC2-hosted bot
- EC2 instance may have different Python version with Whisper working
- Use CLI only for state inspection

**Option C: Python Version Workaround**
- Create separate Python 3.11 environment for Whisper
- Or wait for openai-whisper fix for Python 3.14

**Recommendation:** Start with **Option A** (mock data) since CLI is working perfectly for state machine testing. The UX audit focuses on conversation flow, not transcription accuracy.

## Files Modified in This Session

1. `bot/cli/inspector.py` - Fixed dataclass handling
2. `bot/cli/simulator.py` - Fixed file handling chain
3. `bot/cli/commands.py` - Added debug, then cleaned up
4. `bot/handlers/voice.py` - Added debug, then cleaned up
5. `bot/state/machine.py` - Fixed logging type bug

All changes committed to git and ready for Norman UX audit.
