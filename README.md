# EditorBot - Telegram Dialect Mediation Bot

A Telegram bot that mediates text dialects to standardized Spanish using the dialect-mediator module and Gemini AI.

## Prerequisites

- Python 3.10+
- Telegram Bot Token (from @BotFather)
- Google Gemini API Key

## Quick Start

### Local Development

1. **Clone and setup:**
   ```bash
   cd editorBot
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dialect_mediator FIRST (it has no external deps)
   pip install -e ../dialect_mediator

   # Then install editorBot and its dependencies
   pip install -e .

   # (Optional) enable local Whisper-family transcription support
   pip install -e '.[local-transcription]'
   ```

2. **Create .env file:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   export $(cat .env | xargs)
   ```

3. **Run the bot:**
   ```bash
   python -m bot.bot
   ```

### Docker Deployment

1. **Build and run:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   docker-compose up --build
   ```

2. **Docker manual:**
   ```bash
   docker build -t editorbot .
   docker run --env-file .env editorbot
   ```

### EC2 Deployment

1. **Connect to EC2:**
   ```bash
   ssh -i your_key.pem ubuntu@your_ec2_ip
   ```

2. **Setup environment:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3.11 python3-venv git ffmpeg
   cd /home/ubuntu
   git clone your_repo
   cd your_repo/editorBot
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install and run:**
   ```bash
   # Install dialect_mediator FIRST (from parent directory)
   pip install -e ../dialect_mediator

   # Then install editorBot with all dependencies
   pip install -e .

   # Set environment variables
   export TELEGRAM_BOT_TOKEN=your_token
   export GEMINI_API_KEY=your_key

   # Run with nohup or systemd
   nohup python -m bot.bot > bot.log 2>&1 &
   ```

4. **Systemd service (recommended):**
   ```bash
   sudo nano /etc/systemd/system/editorbot.service
   ```

   ```ini
   [Unit]
   Description=Telegram EditorBot
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/editorBot
   Environment="PATH=/home/ubuntu/editorBot/venv/bin"
   EnvironmentFile=/home/ubuntu/editorBot/.env
   ExecStart=/home/ubuntu/editorBot/venv/bin/python -m bot.bot
   Restart=on-failure
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable editorbot
   sudo systemctl start editorbot
   sudo systemctl status editorbot
   ```

## Project Structure

```
editorBot/
├── bot/
│   ├── handlers/         # Telegram message handlers
│   ├── services/         # Business logic (transcription, mediation)
│   ├── state/           # State machine for conversations
│   └── bot.py           # Main bot entry point
├── tests/               # Unit tests
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Docker Compose setup
├── pyproject.toml       # Python package configuration
└── requirements.txt     # Python dependencies
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| TELEGRAM_BOT_TOKEN | ✅ | Token from BotFather |
| GEMINI_API_KEY | ✅ | Google Gemini API key |
| GEMINI_MODEL | ❌ | Model name (default: gemini-2.0-pro) |
| GEMINI_TEMPERATURE | ❌ | Temperature for responses (default: 0.3) |

## Credential & Environment Management

### Local & Docker
- Copy `.env.example` to `.env`, then fill in your secrets (never commit `.env`).
- Docker Compose automatically loads values from `editorBot/.env` via `--env-file`.
- For local testing you can export on the fly: `export $(grep -v '^#' .env | xargs)`.

### Control EC2 (Always-on CPU)
- `scripts/ec2_deploy.sh` writes the runtime `.env` to `/opt/editorbot/editorBot/.env`.
- Choose how to hydrate the file by setting `EDITORBOT_ENV_MODE` before running the script:
   - `template` (default): copy `.env.example` so you can edit manually over SSH.
   - `file`: copy a prepared file by providing `EDITORBOT_ENV_SOURCE=/path/to/.env`.
   - `ssm`: pull secrets from AWS Systems Manager Parameter Store. Set
      `TELEGRAM_BOT_TOKEN_PARAM` and `GEMINI_API_KEY_PARAM` to the parameter names.
- The script also creates `/opt/editorbot/secure/` (chmod 700) for sensitive JSONs;
   point `GOOGLE_APPLICATION_CREDENTIALS` at that directory if you upload a file.

### GPU Burst Node
- Use a separate `.env` (for example `/opt/editorbot/gpu/.env`) that only contains
   the image-generation keys required on the temporary GPU instance.
- Fetch secrets via Parameter Store in the same way or copy them just-in-time, then
   terminate the GPU node so the file disappears with the instance.

### General Guidance
- Prefer IAM roles + SSM/Secrets Manager over baking keys into AMIs or user data.
- Keep `.env` files out of version control (already enforced via `.gitignore`).
- Rotate credentials regularly and revoke any accidental exposures immediately.

## Troubleshooting

### Missing dependencies
```bash
pip install -r requirements.txt
pip install -e ../dialect_mediator
```

### API Key errors
- Verify `.env` file exists and is properly formatted
- Check that environment variables are exported: `echo $GEMINI_API_KEY`
- Ensure API keys are valid and have proper permissions

### Module import errors
- Ensure you're in a virtual environment
- Reinstall dialect_mediator: `pip install -e ../dialect_mediator`
- Check Python version: `python --version` (requires 3.10+)

## Development

### Running tests:
```bash
pip install -r requirements-dev.txt
pytest tests/
```

### Code formatting:
```bash
black bot/
ruff check bot/ --fix
```
