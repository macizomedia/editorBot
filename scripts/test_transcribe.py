#!/usr/bin/env python3
"""
Test helper: convert an audio file (OGG/Opus from Telegram) to 16-bit 16kHz WAV
and optionally call the transcription function.

Usage:
  python scripts/test_transcribe.py /path/to/file.ogg

Outputs:
 - Prints original audio metadata
 - Writes converted WAV to a temp file and prints its WAV header info
 - Optionally calls transcribe_audio() and prints result (requires GCP credentials)
"""
import sys
import wave
import os
import tempfile

from bot.services.transcription import _convert_audio_to_linear16, transcribe_audio


def print_wav_info(data: bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as f:
        f.write(data)
        tmp_path = f.name
    try:
        with wave.open(tmp_path, 'rb') as wf:
            print(f"WAV channels: {wf.getnchannels()}")
            print(f"WAV sample width (bytes): {wf.getsampwidth()}")
            print(f"WAV frame rate (Hz): {wf.getframerate()}")
            print(f"WAV nframes: {wf.getnframes()}")
    finally:
        os.unlink(tmp_path)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_transcribe.py /path/to/audio.ogg")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"File not found: {path}")
        sys.exit(1)

    print(f"Converting: {path}")
    data = _convert_audio_to_linear16(path)
    print(f"Converted bytes: {len(data)}")
    print_wav_info(data)

    # Optional: run transcription if GCP credentials are configured
    if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
        print("Running cloud transcription (may incur cost)...")
        print(transcribe_audio(path))
    else:
        print("GOOGLE_APPLICATION_CREDENTIALS not set — skipping cloud transcription test")


if __name__ == '__main__':
    main()
