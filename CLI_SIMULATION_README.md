# CLI Bot Simulation - Quick Start

Complete system for simulating bot interactions without Telegram.

## Files Created

### Core Simulation
- **`bot/cli/simulate_full_workflow.py`** - Main simulation engine with 6 scenarios
- **`bot/cli/SIMULATION_GUIDE.md`** - Complete documentation and reference
- **`bot/cli/simulate`** - Bash wrapper script for easy execution
- **`quick_cli_test.py`** - Minimal example for learning

## Instant Start

### Run the Quick Test (30 seconds)

```bash
cd editorBot
python quick_cli_test.py
```

This demonstrates a complete conversation flow in 4 steps:
1. Send text → TRANSCRIBED
2. Send mediated text → MEDIATED
3. Approve with OK → TEMPLATE_PROPOSED

### Run a Full Scenario (2 minutes)

```bash
cd editorBot
python -m bot.cli.simulate_full_workflow --scenario text_only
```

### Run All Scenarios (5 minutes)

```bash
python -m bot.cli.simulate_full_workflow --scenario all
```

## Available Scenarios

| Scenario | Description | Time | Complexity |
|----------|-------------|------|------------|
| `text_only` | Basic text conversation | ~30s | ⭐ Beginner |
| `voice_full` | Voice transcription workflow | ~1m | ⭐⭐ Intermediate |
| `text_edit` | Multiple text edits | ~1m | ⭐⭐ Intermediate |
| `template_flow` | Template selection | ~1m | ⭐⭐⭐ Advanced |
| `cancel` | Cancellation testing | ~30s | ⭐ Beginner |
| `inspection` | State debugging | ~30s | ⭐ Beginner |
| `all` | Complete suite | ~5m | ⭐⭐⭐ Advanced |

## Quick Commands

### Manual CLI Testing

```bash
# Send text
python -m bot.cli send-text "Hello bot"

# Show current state
python -m bot.cli show-state

# Show state as JSON
python -m bot.cli show-state --json

# Reset to IDLE
python -m bot.cli reset

# Interactive mode
python -m bot.cli
```

### Bash Script (Optional)

```bash
# Make executable (one time)
chmod +x bot/cli/simulate

# Run scenarios
./bot/cli/simulate text_only
./bot/cli/simulate all --verbose
```

## Understanding the Flow

### Basic Text Conversation

```
IDLE
  └─ [send text] → TRANSCRIBED
       └─ [send mediated text] → MEDIATED
            └─ [send "OK"] → TEMPLATE_PROPOSED
```

### With Voice

```
IDLE
  └─ [send voice] → AUDIO_RECEIVED
       └─ [transcribe] → TRANSCRIBED
            └─ [mediate] → MEDIATED
                 └─ [approve] → TEMPLATE_PROPOSED
```

### Edit Flow

```
MEDIATED
  └─ [send "EDITAR"] → EDITING_MEDIATED
       └─ [send new text] → SCRIPT_DRAFTED
            └─ [send "OK"] → FINAL_SCRIPT
```

## State Reference

| State | Description | Next Actions |
|-------|-------------|--------------|
| `idle` | Waiting for input | Send text or voice |
| `transcribed` | Text received | Send mediated version |
| `mediated` | Text mediated | OK, EDITAR, CANCELAR |
| `editing_mediated` | Editing mode | Send edited text |
| `script_drafted` | Draft created | OK, EDITAR, CANCELAR |
| `template_proposed` | Templates shown | Click template button |

## Interactive Testing

Start REPL mode for manual exploration:

```bash
python -m bot.cli

# Then type commands:
[idle] > text Hello, I want to make a video
[transcribed] > state
[transcribed] > text This is my mediated version
[mediated] > text OK
[template_proposed] > click template:explainer_slides
[select_soundtrack] > reset
[idle] > exit
```

## Debugging

### Enable Verbose Mode

```bash
# See all state transitions and payloads
python -m bot.cli --verbose send-text "Debug test"

# Or in simulations
python -m bot.cli.simulate_full_workflow --scenario text_only --verbose
```

### Check Logs

Structured JSON logs show every transition:

```json
{
  "ts": "2026-01-25T17:30:00Z",
  "level": "INFO",
  "message": "state_transition_complete",
  "from_state": "idle",
  "to_state": "transcribed",
  "event": "text_received"
}
```

### Inspect State

```bash
python -m bot.cli show-state --json
```

Output:
```json
{
  "state": "transcribed",
  "transcript": "Hello bot",
  "mediated_text": null,
  "template_id": null,
  "render_plan": null
}
```

## Common Issues

### "InvalidTransition" Error

**Cause:** Wrong event for current state

**Fix:**
1. Check state: `python -m bot.cli show-state`
2. See valid transitions in [SIMULATION_GUIDE.md](SIMULATION_GUIDE.md)
3. Send correct command

### "No templates found"

**Cause:** Template system not fully implemented

**Result:** State still advances correctly (TEMPLATE_PROPOSED)

This is expected behavior during development.

### Voice simulation fails

**Cause:** No audio file or Whisper not configured

**Fix:**
```bash
# Use inject-transcript instead
python -m bot.cli inject-transcript "Mock audio transcript"
```

## Next Steps

1. **Start Simple:**
   ```bash
   python quick_cli_test.py
   ```

2. **Try Interactive:**
   ```bash
   python -m bot.cli
   ```

3. **Run Full Scenario:**
   ```bash
   python -m bot.cli.simulate_full_workflow --scenario text_only --verbose
   ```

4. **Read Documentation:**
   - [SIMULATION_GUIDE.md](SIMULATION_GUIDE.md) - Complete reference
   - [bot/cli/README.md](README.md) - CLI tool documentation

5. **Create Custom Scenario:**
   Edit `simulate_full_workflow.py` and add your own test method

## File Structure

```
editorBot/
├── quick_cli_test.py                    # ← Minimal example (start here)
└── bot/
    └── cli/
        ├── __main__.py                   # Entry point for python -m bot.cli
        ├── simulate_full_workflow.py     # ← Full simulation engine
        ├── simulate                      # ← Bash wrapper (optional)
        ├── SIMULATION_GUIDE.md          # ← Complete documentation
        ├── README.md                     # CLI tool reference
        ├── commands.py                   # Command implementations
        ├── simulator.py                  # Mock Telegram objects
        └── inspector.py                  # State formatting utilities
```

## Examples

### Test Text Input

```bash
python -m bot.cli send-text "Create a video about AI"
```

### Test Voice (with audio file)

```bash
python -m bot.cli send-voice data/samples/test.ogg
```

### Test Without Whisper

```bash
python -m bot.cli inject-transcript "This is a test transcript"
```

### Test Button Click

```bash
python -m bot.cli click "template:explainer_slides"
```

### Complete Workflow

```bash
# Reset
python -m bot.cli reset

# Start conversation
python -m bot.cli send-text "I want to talk about blockchain"

# Check state
python -m bot.cli show-state

# Send mediated version
python -m bot.cli send-text "Blockchain revolutionizes data security"

# Approve
python -m bot.cli send-text "OK"

# Select template
python -m bot.cli click "template:explainer_slides"
```

## Integration

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

cd editorBot
python -m bot.cli.simulate_full_workflow --scenario text_only

if [ $? -ne 0 ]; then
  echo "❌ Simulation failed"
  exit 1
fi
```

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
- name: Run Bot Simulations
  run: |
    cd editorBot
    python -m bot.cli.simulate_full_workflow --scenario all
```

### Automated Testing

```bash
#!/bin/bash
# test_bot_scenarios.sh

scenarios=("text_only" "text_edit" "cancel" "inspection")

for scenario in "${scenarios[@]}"; do
  echo "Testing: $scenario"
  python -m bot.cli.simulate_full_workflow --scenario "$scenario"
  if [ $? -ne 0 ]; then
    echo "FAIL: $scenario"
    exit 1
  fi
done

echo "✅ All scenarios passed"
```

## Support

- **Documentation:** [SIMULATION_GUIDE.md](SIMULATION_GUIDE.md)
- **CLI Reference:** [README.md](README.md)
- **State Machine:** `bot/state/machine.py`
- **Handlers:** `bot/handlers/`

## Tips

1. **Always reset** before starting new test: `python -m bot.cli reset`
2. **Use verbose** when debugging: `--verbose` flag
3. **Check state** frequently: `python -m bot.cli show-state`
4. **Read logs** to understand transitions
5. **Start simple** with `quick_cli_test.py`
6. **Graduate to scenarios** with `simulate_full_workflow.py`
7. **Build custom tests** by editing scenario methods

---

**Created:** 2026-01-25
**Version:** 1.0.0
**Status:** ✅ Ready to use
