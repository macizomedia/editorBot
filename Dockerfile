FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy both project directories
COPY dialect_mediator/ /app/dialect_mediator/
COPY editorBot/ /app/editorBot/

WORKDIR /app/editorBot

# Install dependencies - dialect_mediator FIRST, then editorBot
RUN pip install --no-cache-dir -e /app/dialect_mediator && \
    pip install --no-cache-dir -e .

# Set environment variables (can be overridden at runtime)
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "-m", "bot.bot"]
