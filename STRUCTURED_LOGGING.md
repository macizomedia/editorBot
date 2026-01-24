# Structured Logging Reference

Complete reference for all structured log events in EditorBot.

## Overview

Structured logging uses the `extra` parameter to attach JSON-serializable metadata to log messages. This enables:
- Easy filtering by event type
- Structured data analysis
- Better debugging with context
- Performance monitoring

## Log Events by Module

### 🎤 Voice Handler (`bot/handlers/voice.py`)

#### `voice_message_received`
**Level:** INFO
**When:** User sends voice message
**Fields:**
- `chat_id`: int — User's chat ID
- `duration_seconds`: int — Audio duration
- `file_size_bytes`: int — Audio file size
- `mime_type`: str — Audio format (e.g., "audio/ogg")

**Example:**
```python
logger.info(
    "voice_message_received",
    extra={
        "chat_id": 12345,
        "duration_seconds": 15,
        "file_size_bytes": 245760,
        "mime_type": "audio/ogg",
    }
)
```

#### `transcription_complete`
**Level:** INFO
**When:** Whisper transcription finishes
**Fields:**
- `chat_id`: int
- `transcript_length`: int — Character count
- `transcript_preview`: str — First 100 chars
- `success`: bool — Whether transcription succeeded

**Example:**
```python
logger.info(
    "transcription_complete",
    extra={
        "chat_id": 12345,
        "transcript_length": 150,
        "transcript_preview": "Hello, this is a test message...",
        "success": true,
    }
)
```

#### `transcription_failed`
**Level:** WARNING
**When:** Transcription returns error
**Fields:**
- `chat_id`: int
- `error`: str — Error message from Whisper

#### `mediation_complete`
**Level:** INFO
**When:** Gemini mediation finishes
**Fields:**
- `chat_id`: int
- `original_length`: int — Transcript length
- `mediated_length`: int — Mediated text length
- `mediated_preview`: str — First 100 chars

---

### 🔄 State Machine (`bot/state/machine.py`)

#### `state_transition_attempt`
**Level:** INFO
**When:** Before any state transition
**Fields:**
- `current_state`: str — Current state name
- `event`: str — Event triggering transition
- `has_payload`: bool — Whether payload is present
- `payload_preview`: str — First 50 chars of payload or type name

**Example:**
```python
logger.info(
    "state_transition_attempt",
    extra={
        "current_state": "transcribed",
        "event": "text_received",
        "has_payload": true,
        "payload_preview": "Enhanced: Hello, this is...",
    }
)
```

#### `state_transition_complete`
**Level:** INFO
**When:** After successful state transition
**Fields:**
- `from_state`: str — Previous state
- `to_state`: str — New state
- `event`: str — Event that triggered transition
- `reason`: str (optional) — Special reason (e.g., "voice_restart")

**Example:**
```python
logger.info(
    "state_transition_complete",
    extra={
        "from_state": "transcribed",
        "to_state": "mediated",
        "event": "text_received",
    }
)
```

#### `invalid_state_transition`
**Level:** ERROR
**When:** Invalid transition attempted
**Fields:**
- `state`: str — Current state
- `event`: str — Invalid event

---

### 📝 Text Handler (`bot/handlers/text.py`)

#### `script_generated`
**Level:** INFO
**When:** Script generation completes
**Fields:**
- `chat_id`: int
- `script_length`: int — Script length
- `script_preview`: str — First 100 chars

---

### 🎬 Callbacks Handler (`bot/handlers/callbacks.py`)

#### `template_selected`
**Level:** INFO
**When:** User selects template
**Fields:**
- `chat_id`: int
- `template_id`: str — Selected template ID

#### `soundtrack_selected`
**Level:** INFO
**When:** User selects soundtrack
**Fields:**
- `chat_id`: int
- `soundtrack_id`: str — Selected soundtrack ID

---

### 🎥 Render Plan Builder (`bot/render_plan/builder.py`)

#### `render_plan_build_started`
**Level:** INFO
**When:** Render plan build begins
**Fields:**
- `num_beats`: int — Number of script beats
- `template_id`: str — Template being used
- `has_soundtrack`: bool — Whether soundtrack is included

**Example:**
```python
logger.info(
    "render_plan_build_started",
    extra={
        "num_beats": 5,
        "template_id": "explainer_slides",
        "has_soundtrack": true,
    }
)
```

#### `render_plan_build_complete`
**Level:** INFO
**When:** Render plan successfully built
**Fields:**
- `render_plan_id`: str — Generated plan UUID
- `total_duration`: float — Video duration in seconds
- `num_scenes`: int — Number of scenes
- `num_audio_tracks`: int — Number of audio tracks
- `resolution`: str — Video resolution (e.g., "1080x1920")
- `fps`: int — Frames per second

**Example:**
```python
logger.info(
    "render_plan_build_complete",
    extra={
        "render_plan_id": "rp-abc123...",
        "total_duration": 45.5,
        "num_scenes": 5,
        "num_audio_tracks": 2,
        "resolution": "1080x1920",
        "fps": 30,
    }
)
```

---

### 🔧 Render Plan Handler (`bot/handlers/render_plan.py`)

#### `render_plan_parsing_complete`
**Level:** INFO
**When:** Script parsed successfully
**Fields:**
- `script_beats`: int — Number of beats
- `template_id`: str — Template ID
- `has_soundtrack`: bool — Whether soundtrack is included

#### `render_plan_validation_failed`
**Level:** ERROR
**When:** Render plan fails validation
**Fields:**
- `num_fatal_errors`: int — Count of fatal errors
- `num_warnings`: int — Count of warnings
- `error_summary`: str — Concatenated error messages

---

## Using Logs in CLI

### Verbose Mode

Enable verbose logging to see all structured logs:

```bash
python -m bot.cli --verbose
```

### Filtering Logs

Extract specific events:

```bash
# Show only state transitions
python -m bot.cli --verbose 2>&1 | grep "state_transition"

# Show only render plan events
python -m bot.cli --verbose 2>&1 | grep "render_plan"

# Show all INFO events
python -m bot.cli --verbose 2>&1 | grep "INFO"
```

### Log Format

Logs are output in Python's standard format:
```
LEVEL:module_name:event_name
```

With verbose logging, you'll also see the `extra` fields in the log output.

---

## Analyzing Logs

### Extract JSON Data

To extract and analyze structured log data programmatically:

```python
import json
import logging

# Custom formatter to output JSON
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include extra fields
        if hasattr(record, "chat_id"):
            log_data["chat_id"] = record.chat_id
        if hasattr(record, "state"):
            log_data["state"] = record.state
        # ... add more fields as needed

        return json.dumps(log_data)
```

### Common Analysis Queries

**Average transcription time:**
```bash
grep "transcription_complete" logs.txt | wc -l
```

**Failed transcriptions:**
```bash
grep "transcription_failed" logs.txt
```

**State transition flow for a session:**
```bash
grep "state_transition_complete" logs.txt | grep "chat_id: 12345"
```

---

## Best Practices

### Adding New Log Events

When adding new structured logs:

1. **Choose appropriate level:**
   - INFO: Normal operation milestones
   - WARNING: Non-fatal issues (e.g., validation warnings)
   - ERROR: Failures requiring attention

2. **Use descriptive event names:**
   - Use snake_case
   - Include action and result (e.g., `transcription_complete`, not just `transcribed`)

3. **Include relevant context:**
   - Always include identifiers (chat_id, render_plan_id)
   - Include data that helps debugging
   - Avoid sensitive information (no API keys, tokens)

4. **Keep payload previews short:**
   - Limit to 50-100 chars
   - Use `[:100]` slicing for safety

### Example Template

```python
logger.info(
    "event_name_complete",
    extra={
        "chat_id": chat_id,
        "operation_specific_field": value,
        "preview": str(data)[:100] if data else None,
        "success": True,
    }
)
```

---

## Performance Monitoring

### Useful Metrics to Track

From structured logs, you can extract:

1. **Conversion funnel:**
   - `voice_message_received` → `transcription_complete` → `mediation_complete` → `render_plan_build_complete`

2. **Failure rates:**
   - `transcription_failed` / `transcription_complete`
   - `render_plan_validation_failed` / `render_plan_build_complete`

3. **State machine usage:**
   - Most common paths
   - Where users drop off

4. **Average durations:**
   - Audio file sizes vs transcription success
   - Script lengths vs render plan complexity

---

## Future Enhancements

Potential additions:

1. **Timing information:**
   ```python
   extra={"duration_ms": elapsed_time}
   ```

2. **Error codes:**
   ```python
   extra={"error_code": "TRANSCRIPTION_TIMEOUT"}
   ```

3. **User metadata:**
   ```python
   extra={"user_language": "es", "user_timezone": "UTC-5"}
   ```

4. **Distributed tracing:**
   ```python
   extra={"trace_id": correlation_id}
   ```
