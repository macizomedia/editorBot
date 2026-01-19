import os
import io

# Optional: Whisper (local) support
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except Exception:
    WhisperModel = None
    FASTER_WHISPER_AVAILABLE = False

try:
    import whisper
    WHISPER_AVAILABLE = True
except Exception:
    whisper = None
    WHISPER_AVAILABLE = False

from pydub import AudioSegment
import logging

logger = logging.getLogger(__name__)


def transcribe_audio(file_path: str) -> str:
    """
    Transcribe audio file using local Whisper (faster-whisper preferred).

    Takes a local audio file path (WAV, MP3, OGG, FLAC, etc.).
    Returns raw transcription text in Spanish.

    Local transcription requires optional dependencies:
    pip install -e '.[local-transcription]'
    """
    try:
        # Validate file exists
        if not os.path.exists(file_path):
            logger.error(f"Audio file not found: {file_path}")
            return "[Error: Audio file not found]"

        # Check file size (must be > 0)
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            logger.error(f"Audio file is empty: {file_path}")
            return "[Error: Audio file is empty]"

        logger.debug(f"Processing audio file: {file_path} (size: {file_size} bytes)")

        # Local transcription only (faster_whisper -> whisper)
        if FASTER_WHISPER_AVAILABLE:
            try:
                model_name = os.environ.get("WHISPER_MODEL", "small")
                logger.info(f"Using faster_whisper model '{model_name}' for local transcription")
                model = WhisperModel(model_name)
                segments, info = model.transcribe(file_path, beam_size=5, language=os.environ.get("WHISPER_LANG", "es"))
                text = " ".join([seg.text for seg in segments]).strip()
                if text:
                    logger.info("faster_whisper transcription successful")
                    return text
                else:
                    logger.warning("faster_whisper returned empty transcription, falling back")
            except Exception as werr:
                logger.warning(f"faster_whisper transcription failed: {werr}; falling back")

        if WHISPER_AVAILABLE:
            try:
                model_name = os.environ.get("WHISPER_MODEL", "small")
                logger.info(f"Using Whisper model '{model_name}' for local transcription")
                model = whisper.load_model(model_name)
                # whisper handles format conversion via ffmpeg
                result = model.transcribe(file_path, language=os.environ.get("WHISPER_LANG", "es"))
                text = result.get("text", "").strip()
                if text:
                    logger.info("Whisper transcription successful")
                    return text
                else:
                    logger.warning("Whisper returned empty transcription, falling back")
            except Exception as werr:
                logger.warning(f"Whisper transcription failed: {werr}")

        logger.error("No local Whisper backend available. Install extras: pip install -e '.[local-transcription]'")
        return "[Error: Local transcription unavailable]"

    except Exception as e:
        logger.error(f"Transcription error: {type(e).__name__}: {str(e)}", exc_info=True)
        return f"[Error: {str(e)}]"

