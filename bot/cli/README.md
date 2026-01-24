# EditorBot CLI Debugger

A command-line tool for testing and debugging EditorBot without needing Telegram.

## Installation

### Dependencies

All dependencies should already be installed. If not:

```bash
cd editorbot-stack/editorBot
pip install -r requirements.txt
pip install audioop-lts  # For Python 3.14+
```

### Shell Wrapper (Recommended)

For convenience, use the `editorbot-cli` wrapper script:

```bash
# From editorBot directory
./editorbot-cli --help

# Or install globally (choose one):

# Option 1: User-local (no sudo required)
mkdir -p ~/.local/bin
ln -s $(pwd)/editorbot-cli ~/.local/bin/editorbot-cli
# Add to PATH if needed: export PATH="$HOME/.local/bin:$PATH"

# Option 2: System-wide
sudo ln -s $(pwd)/editorbot-cli /usr/local/bin/editorbot-cli

# Then use from anywhere:
editorbot-cli --help
editorbot-cli --verbose show-state
```

The wrapper automatically:
- Finds the Python virtual environment
- Activates it
- Runs the CLI with correct working directory

## Quick Start

### Interactive Mode

```bash
python -m bot.cli
```

This opens an interactive REPL where you can send commands:

```
╔══════════════════════════════════════════╗
║      EditorBot CLI Debugger v0.1         ║
╚══════════════════════════════════════════╝

Chat ID: 12345
Verbose: OFF

Commands:
  voice <path>     - Send voice message
  text <message>   - Send text message
  click <data>     - Click inline button
  state            - Show conversation state
  state --json     - Show state as JSON
  log on/off       - Toggle verbose logging
  reset            - Reset to IDLE
  help             - Show this help
  exit             - Quit

[idle] > state
╔══════════════════════════════════════════╗
║        CONVERSATION STATE                ║
╚══════════════════════════════════════════╝

🔄 State: idle

[idle] > text "Hello"
📤 Sending text: Hello
...
```

### Single Command Mode

Run individual commands without interactive mode:

```bash
# Show current state
python -m bot.cli show-state

# Show state as JSON
python -m bot.cli show-state --json

# Send voice message
python -m bot.cli send-voice path/to/audio.wav

# Send text message
python -m bot.cli send-text "Hello world"

# Click inline button
python -m bot.cli click "template:explainer"

# Reset conversation
python -m bot.cli reset
```

### Verbose Mode

Enable verbose logging to see all JSON data and state transitions:

```bash
# Interactive with verbose logging
python -m bot.cli --verbose

# Single command with verbose
python -m bot.cli --verbose send-text "Test"
```

## Usage Examples

### Test Full Workflow

```bash
# Start interactive mode with verbose logging
python -m bot.cli --verbose

# In the REPL:
[idle] > voice samples/test_audio.wav
# ... transcription and mediation happens ...

[mediated] > text "ok"
# ... script generation ...

[script_drafted] > text "ok"
# ... moves to template selection ...

[template_proposed] > click "template:explainer"
# ... template selected ...

[select_soundtrack] > click "music:lofi1"
# ... render plan generated ...

[ready_for_render] > state
# Shows final render plan
```

### Debug Specific Handler

```bash
# Test voice handler
python -m bot.cli --verbose send-voice audio.wav

# Test template selection
python -m bot.cli --verbose click "template:explainer"
```

### Inspect State

```bash
# Human-readable format
python -m bot.cli show-state

# JSON format (for scripts)
python -m bot.cli show-state --json
```

## Commands Reference

### Interactive Commands

| Command | Description | Example |
|---------|-------------|---------|
| `voice <path>` | Send voice message | `voice sample.wav` |
| `text <message>` | Send text message | `text "Hello"` |
| `click <data>` | Click inline button | `click "template:explainer"` |
| `state` | Show current state | `state` |
| `state --json` | Show state as JSON | `state --json` |
| `log on/off` | Toggle verbose mode | `log on` |
| `reset` | Reset to IDLE | `reset` |
| `exit` | Quit CLI | `exit` |

### CLI Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--verbose`, `-v` | Show all JSON data and logs | Off |
| `--json` | Output as JSON (for show-state) | Off |
| `--chat-id <id>` | Use specific chat ID | 12345 |

## Architecture

```
bot/cli/
├── __init__.py       # Package init
├── __main__.py       # Entry point
├── main.py           # Argument parsing and main loop
├── commands.py       # Command implementations
├── simulator.py      # Mock Telegram objects
└── inspector.py      # State inspection and formatting
```

### How It Works

1. **Simulator** creates mock Telegram `Update` and `Context` objects
2. **Commands** call actual bot handlers with mocked objects
3. **Inspector** formats and displays conversation state
4. Bot handlers run normally, just with fake Telegram API

## Debugging Tips

### Enable Verbose Logging

```bash
python -m bot.cli --verbose
```

Shows:
- State before/after handler execution
- All JSON data structures
- Full render plans
- Error tracebacks

### Test Error Scenarios

```bash
# Invalid state transition
[idle] > text "ok"  # Should fail (no transcript yet)

# Missing file
[idle] > voice nonexistent.wav  # Shows error message
```

### Inspect Render Plan

After generating a render plan:

```bash
[ready_for_render] > state

# Shows:
📋 Render Plan
─────────────────
ID:       rp-abc123...
Duration: 45.5s
Size:     1080x1920 @ 30fps

🎵 Audio Tracks: 2
   - audio-voice: vol=1.0
   - audio-music: vol=0.3

🎬 Scenes: 5
   0: 0.0s → 8.5s
      Cinematic wide shot of...
   ...
```

## Use Cases

1. **Test bot logic** without Telegram overhead
2. **Debug state machine** transitions
3. **Inspect JSON structures** at each step
4. **Reproduce bugs** with specific inputs
5. **Validate render plans** before deployment
6. **Script automated tests** using single commands

## Next Steps

Now that the CLI is working, you can:

1. **Add logging** to bot handlers (see where data flows)
2. **Create test fixtures** (sample audio, scripts, templates)
3. **Write integration tests** using the CLI programmatically
4. **Add more commands** (e.g., load/save conversation state)

## Notes

- Uses chat ID 12345 by default (change with `--chat-id`)
- State is persisted in bot's normal storage
- Mock Telegram objects don't actually hit Telegram API
- Voice files must exist locally (no download simulation yet)
