# Bot Workflow Simulation Guide

Complete guide for testing EditorBot interactions using the CLI simulator.

## Quick Start

### Run a Single Scenario

```bash
cd editorBot

# Text-only conversation (recommended for first test)
python -m bot.cli.simulate_full_workflow --scenario text_only

# Voice workflow (requires audio file)
python -m bot.cli.simulate_full_workflow --scenario voice_full

# Multiple edits
python -m bot.cli.simulate_full_workflow --scenario text_edit

# Template selection flow
python -m bot.cli.simulate_full_workflow --scenario template_flow

# Cancellation testing
python -m bot.cli.simulate_full_workflow --scenario cancel

# State inspection
python -m bot.cli.simulate_full_workflow --scenario inspection
```

### Run All Scenarios

```bash
# Run complete test suite
python -m bot.cli.simulate_full_workflow --scenario all

# With verbose output and interactive pauses
python -m bot.cli.simulate_full_workflow --scenario all --verbose
```

### Interactive Mode

For manual testing with REPL interface:

```bash
# Standard mode
python -m bot.cli

# Verbose mode
python -m bot.cli --verbose
```

## Available Scenarios

### 1. Text-Only Conversation (`text_only`)

**Purpose:** Test basic text input flow without voice messages

**Flow:**
1. Send text message → Bot enters TRANSCRIBED state
2. Bot mediates text automatically
3. User approves with "OK" → Transitions to TEMPLATE_PROPOSED
4. User clicks template button → Template selected

**Use Case:**
- Testing text-only interactions
- CLI debugging without audio files
- Rapid iteration on mediation logic

**Example:**
```bash
python -m bot.cli.simulate_full_workflow --scenario text_only --verbose
```

### 2. Voice Message Workflow (`voice_full`)

**Purpose:** Test complete voice-to-text pipeline

**Flow:**
1. Send voice message → AUDIO_RECEIVED
2. Whisper transcribes → TRANSCRIBED
3. Gemini mediates → MEDIATED
4. User requests edit → EDITING_MEDIATED
5. User submits new text → SCRIPT_DRAFTED

**Requirements:**
- Audio file at `data/samples/sample_voice.ogg`
- Whisper API/local model configured
- Falls back to inject_transcript if audio missing

**Use Case:**
- Testing Whisper integration
- Voice quality validation
- Full transcription pipeline

### 3. Multiple Text Edits (`text_edit`)

**Purpose:** Test iterative editing workflow

**Flow:**
1. Send initial text → TRANSCRIBED
2. Request edit → EDITING_MEDIATED
3. Submit edit → SCRIPT_DRAFTED
4. Request another edit → EDITING_SCRIPT
5. Submit final version → FINAL_SCRIPT
6. Approve → TEMPLATE_PROPOSED

**Use Case:**
- Testing state transitions during editing
- Validating edit history tracking
- User correction flows

### 4. Complete Template Workflow (`template_flow`)

**Purpose:** Test end-to-end template selection and configuration

**Flow:**
1. Quick setup with inject_transcript
2. Approve to reach TEMPLATE_PROPOSED
3. Select template → SELECT_SOUNDTRACK
4. Select soundtrack → ASSET_OPTIONS
5. Configure assets → RENDER_PLAN_GENERATED
6. Review and approve → READY_FOR_RENDER

**Use Case:**
- Template system integration
- Soundtrack selection
- Asset configuration
- Render plan generation

### 5. Cancellation Flow (`cancel`)

**Purpose:** Test CANCELAR command at various states

**Flow:**
1. Start conversation → TRANSCRIBED
2. Send CANCELAR → IDLE
3. Repeat from EDITING_MEDIATED → IDLE
4. Verify state resets correctly

**Use Case:**
- Testing cancel functionality
- State cleanup validation
- Error recovery

### 6. State Inspection (`inspection`)

**Purpose:** Demonstrate debugging and state inspection commands

**Flow:**
1. Show initial IDLE state
2. Send message and inspect TRANSCRIBED
3. Export state as JSON
4. Reset and verify cleanup

**Use Case:**
- Learning CLI debugging commands
- Understanding state structure
- Troubleshooting state issues

## Command Reference

### Direct CLI Commands

```bash
# Send text message
python -m bot.cli send-text "Your message here"

# Send voice message
python -m bot.cli send-voice path/to/audio.ogg

# Inject mock transcript (bypass Whisper)
python -m bot.cli inject-transcript "Mock transcript text"

# Click inline button
python -m bot.cli click "template:explainer_slides"

# Show current state
python -m bot.cli show-state

# Show state as JSON
python -m bot.cli show-state --json

# Reset to IDLE
python -m bot.cli reset

# Enable verbose logging
python -m bot.cli --verbose <command>
```

### Interactive REPL Commands

When running `python -m bot.cli`:

```
[idle] > text Hello, I want to create a video
[transcribed] > state
[transcribed] > text OK
[template_proposed] > click template:explainer_slides
[select_soundtrack] > state --json
[select_soundtrack] > reset
[idle] > exit
```

## State Machine Reference

### State Flow Diagram

```
IDLE
  ├─ [TEXT_RECEIVED] → TRANSCRIBED
  └─ [VOICE_RECEIVED] → AUDIO_RECEIVED
                          └─ [TRANSCRIPTION_COMPLETE] → TRANSCRIBED

TRANSCRIBED
  ├─ [TEXT_RECEIVED] → MEDIATED (auto-mediation)
  └─ [COMMAND_CANCELAR] → IDLE

MEDIATED
  ├─ [COMMAND_OK] → TEMPLATE_PROPOSED
  ├─ [COMMAND_EDITAR] → EDITING_MEDIATED
  └─ [COMMAND_CANCELAR] → IDLE

EDITING_MEDIATED
  ├─ [TEXT_RECEIVED] → SCRIPT_DRAFTED
  └─ [COMMAND_CANCELAR] → IDLE

SCRIPT_DRAFTED
  ├─ [COMMAND_OK] → FINAL_SCRIPT
  ├─ [COMMAND_EDITAR] → EDITING_SCRIPT
  └─ [COMMAND_CANCELAR] → IDLE

EDITING_SCRIPT
  ├─ [TEXT_RECEIVED] → FINAL_SCRIPT
  └─ [COMMAND_CANCELAR] → IDLE

FINAL_SCRIPT
  └─ [COMMAND_OK] → TEMPLATE_PROPOSED

TEMPLATE_PROPOSED
  └─ [TEMPLATE_SELECTED] → SELECT_SOUNDTRACK

SELECT_SOUNDTRACK
  └─ [SOUNDTRACK_SELECTED] → ASSET_OPTIONS

ASSET_OPTIONS
  └─ [ASSETS_CONFIGURED] → RENDER_PLAN_GENERATED

RENDER_PLAN_GENERATED
  └─ [RENDER_APPROVED] → READY_FOR_RENDER
```

### Key Commands

- `OK` - Approve current state, move forward
- `EDITAR` - Request editing mode
- `CANCELAR` - Cancel and return to IDLE
- `NEXT` - Skip optional step

## Testing Patterns

### Unit Test Pattern

Test individual state transitions:

```bash
# Test TEXT_RECEIVED in IDLE
python -m bot.cli reset
python -m bot.cli send-text "Test message"
python -m bot.cli show-state  # Verify TRANSCRIBED

# Test COMMAND_OK
python -m bot.cli send-text "OK"
python -m bot.cli show-state  # Verify next state
```

### Integration Test Pattern

Test complete workflows:

```bash
# Full text-to-template flow
python -m bot.cli.simulate_full_workflow --scenario text_only --verbose
```

### Regression Test Pattern

Run all scenarios to catch regressions:

```bash
# Complete suite with summary
python -m bot.cli.simulate_full_workflow --scenario all
```

## Debugging Tips

### Enable Verbose Logging

```bash
# See detailed state transitions
python -m bot.cli --verbose send-text "Debug message"

# See JSON payloads
python -m bot.cli --verbose show-state
```

### Inspect State Between Steps

```bash
# Send command
python -m bot.cli send-text "Test"

# Check state
python -m bot.cli show-state --json

# Continue
python -m bot.cli send-text "OK"
```

### Reset to Clean State

```bash
# Always reset before new test
python -m bot.cli reset
python -m bot.cli show-state  # Verify IDLE
```

### Check Logs

Structured logs are output to console:

```json
{
  "ts": "2026-01-25T10:30:00Z",
  "level": "INFO",
  "message": "state_transition_complete",
  "from_state": "idle",
  "to_state": "transcribed",
  "event": "text_received"
}
```

## Common Issues

### Issue: "InvalidTransition" Error

**Cause:** Sending wrong event for current state

**Solution:**
1. Check current state: `python -m bot.cli show-state`
2. Verify allowed transitions in State Machine Reference
3. Send correct command/event

### Issue: "No transcript found"

**Cause:** Voice message not transcribed

**Solutions:**
- Use `inject-transcript` to bypass Whisper
- Check audio file exists and is valid format
- Verify Whisper API key configured

### Issue: "Gemini API key missing"

**Cause:** GEMINI_API_KEY not set

**Solutions:**
- Set environment variable: `export GEMINI_API_KEY=your_key`
- Or use mock mediation (automatically falls back)
- Test without mediation using inject-transcript

### Issue: Template button not working

**Cause:** Incorrect callback data format

**Solution:**
```bash
# Correct format
python -m bot.cli click "template:explainer_slides"

# NOT: template_explainer or template/explainer
```

## Advanced Usage

### Custom Chat ID

Test multiple conversations in parallel:

```bash
# Conversation 1
python -m bot.cli.simulate_full_workflow --chat-id 11111 --scenario text_only

# Conversation 2
python -m bot.cli.simulate_full_workflow --chat-id 22222 --scenario voice_full
```

### Automated Testing

Run simulations in CI/CD:

```bash
#!/bin/bash
# test_bot.sh

scenarios=("text_only" "text_edit" "cancel" "inspection")

for scenario in "${scenarios[@]}"; do
  echo "Testing: $scenario"
  python -m bot.cli.simulate_full_workflow --scenario "$scenario"
  if [ $? -ne 0 ]; then
    echo "FAIL: $scenario"
    exit 1
  fi
done

echo "All tests passed!"
```

### Capture Output

Save simulation output for review:

```bash
# Save to file
python -m bot.cli.simulate_full_workflow --scenario all --verbose > test_output.log 2>&1

# Save only errors
python -m bot.cli.simulate_full_workflow --scenario all 2> errors.log
```

## Integration with Development

### Pre-Commit Testing

```bash
# Add to .git/hooks/pre-commit
python -m bot.cli.simulate_full_workflow --scenario text_only
```

### Feature Development

1. Write test scenario in `simulate_full_workflow.py`
2. Run scenario: `python -m bot.cli.simulate_full_workflow --scenario my_feature`
3. Iterate until passing
4. Commit with test included

### Bug Reproduction

1. Use CLI to reproduce user-reported issue
2. Create minimal scenario
3. Fix bug
4. Verify fix with scenario
5. Add scenario to test suite

## Next Steps

1. **Run First Simulation:**
   ```bash
   python -m bot.cli.simulate_full_workflow --scenario text_only --verbose
   ```

2. **Try Interactive Mode:**
   ```bash
   python -m bot.cli
   ```

3. **Read Code:**
   - `bot/cli/simulate_full_workflow.py` - Simulation scenarios
   - `bot/cli/commands.py` - CLI command implementations
   - `bot/state/machine.py` - State machine logic

4. **Create Custom Scenario:**
   Add new method to `WorkflowSimulator` class in `simulate_full_workflow.py`

5. **Run Full Suite:**
   ```bash
   python -m bot.cli.simulate_full_workflow --scenario all
   ```

## Resources

- **CLI README:** `bot/cli/README.md`
- **State Machine:** `bot/state/machine.py`
- **Models:** `bot/state/models.py`
- **Handlers:** `bot/handlers/`
- **LangGraph Testing:** `LANGGRAPH_SANDBOX_TESTING.md`

## Support

For issues or questions:

1. Check logs with `--verbose` flag
2. Inspect state with `show-state --json`
3. Review state machine diagram above
4. Check handler implementations in `bot/handlers/`
5. Test with minimal scenario to isolate issue
