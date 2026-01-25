# CLI Simulation - Quick Reference Card

## 🚀 Instant Commands

```bash
# Minimal test (30 seconds)
python quick_cli_test.py

# Run scenario
python -m bot.cli.simulate_full_workflow --scenario text_only

# All scenarios
python -m bot.cli.simulate_full_workflow --scenario all

# Interactive mode
python -m bot.cli

# Manual commands
python -m bot.cli send-text "Your message"
python -m bot.cli show-state
python -m bot.cli reset
```

## 📚 Documentation Files

- **CLI_SIMULATION_README.md** - Quick start guide (300+ lines)
- **bot/cli/SIMULATION_GUIDE.md** - Complete reference (650+ lines)
- **CLI_SIMULATION_IMPLEMENTATION.md** - Implementation summary (400+ lines)

## 🎯 Available Scenarios

| Scenario | Level | Time | Command |
|----------|-------|------|---------|
| text_only | ⭐ Beginner | 30s | `--scenario text_only` |
| voice_full | ⭐⭐ Intermediate | 1m | `--scenario voice_full` |
| text_edit | ⭐⭐ Intermediate | 1m | `--scenario text_edit` |
| template_flow | ⭐⭐⭐ Advanced | 1m | `--scenario template_flow` |
| cancel | ⭐ Beginner | 30s | `--scenario cancel` |
| inspection | ⭐ Beginner | 30s | `--scenario inspection` |
| all | ⭐⭐⭐ Advanced | 5m | `--scenario all` |

## 🔄 State Flow

```
IDLE → TRANSCRIBED → MEDIATED → TEMPLATE_PROPOSED
         ↓              ↓
    AUDIO_RECEIVED  EDITING_MEDIATED
                        ↓
                   SCRIPT_DRAFTED
```

## 🎓 Learning Path

1. **Start:** `python quick_cli_test.py`
2. **Explore:** `python -m bot.cli` (interactive)
3. **Test:** `python -m bot.cli.simulate_full_workflow --scenario text_only`
4. **Read:** Open `CLI_SIMULATION_README.md`
5. **Advanced:** Try other scenarios with `--verbose`

## 🐛 Debugging

```bash
# Verbose mode
python -m bot.cli --verbose send-text "Debug"

# Show state
python -m bot.cli show-state --json

# Check specific scenario
python -m bot.cli.simulate_full_workflow --scenario text_only --verbose
```

## ✅ Status

- **Files:** 6 created (1710+ lines)
- **Scenarios:** 6 implemented and tested
- **Testing:** ✅ All passing
- **Docs:** ✅ Complete
- **Commits:** ✅ Pushed to remote

## 📝 Quick Example

```python
# quick_cli_test.py
cli = CLICommands(chat_id=12345)
reset_conversation(12345)              # → IDLE
await cli.send_text("Test message")    # → TRANSCRIBED
await cli.send_text("Mediated text")   # → MEDIATED
await cli.send_text("OK")              # → TEMPLATE_PROPOSED
```

## 🔗 Files

```
editorBot/
├── quick_cli_test.py                    ← Start here!
├── CLI_SIMULATION_README.md             ← Quick reference
├── CLI_SIMULATION_IMPLEMENTATION.md     ← Implementation details
└── bot/cli/
    ├── simulate_full_workflow.py        ← Main engine
    ├── SIMULATION_GUIDE.md              ← Complete docs
    └── simulate                         ← Bash wrapper
```

---
**Date:** 2026-01-25 | **Version:** 1.0.0 | **Status:** ✅ Complete
