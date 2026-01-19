FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m appuser

# Copy both project directories (build context is repo root)
COPY dialect_mediator/ /app/dialect_mediator/
COPY editorBot/ /app/editorBot/

WORKDIR /app/editorBot

# Install dependencies - dialect_mediator FIRST, then editorBot
RUN pip install --no-cache-dir -e /app/dialect_mediator && \
    pip install --no-cache-dir -e .

# Use non-root user
USER appuser

# Run the bot
CMD ["python", "-m", "bot.bot"]
