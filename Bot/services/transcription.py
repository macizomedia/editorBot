import os
import io
import tempfile
from google.cloud import speech_v1
from google.api_core import exceptions as google_exceptions

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


def _convert_audio_to_linear16(file_path: str) -> bytes:
    """
    Convert audio file to LINEAR16 format (16-bit PCM) at 16kHz.
    
    Supports: WAV, MP3, OGG, FLAC, etc. (anything pydub supports)
    Returns: Raw LINEAR16 audio bytes
    """
    try:
        # Load audio with pydub (auto-detects format)
        audio = AudioSegment.from_file(file_path)
        
        logger.debug(f"Audio loaded - channels: {audio.channels}, frame_rate: {audio.frame_rate}, duration: {len(audio)}ms")
        
        # Convert to mono 16kHz if needed
        if audio.channels != 1:
            audio = audio.set_channels(1)

        if audio.frame_rate != 16000:
            audio = audio.set_frame_rate(16000)

        # Ensure 16-bit samples (sample width = 2 bytes)
        if audio.sample_width != 2:
            audio = audio.set_sample_width(2)

        # Export as WAV (16-bit PCM) into memory
        pcm_io = io.BytesIO()
        audio.export(pcm_io, format="wav")
        pcm_io.seek(0)
        return pcm_io.read()
    
    except Exception as e:
        logger.error(f"Audio conversion error: {str(e)}")
        raise


def transcribe_audio(file_path: str) -> str:
    """
    Transcribe audio file using Google Cloud Speech-to-Text API.
    
    Takes a local audio file path (WAV, MP3, OGG, FLAC, etc.).
    Automatically converts to required format (LINEAR16, 16kHz).
    Returns raw transcription text in Spanish.
    
    Requires: GOOGLE_APPLICATION_CREDENTIALS environment variable
    pointing to service account JSON key file.
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

        # If local transcription available, prefer faster_whisper -> whisper
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
                logger.warning(f"Whisper transcription failed: {werr}; falling back to cloud")

        # Convert audio to LINEAR16 format at 16kHz for cloud API
        audio_content = _convert_audio_to_linear16(file_path)

        if len(audio_content) == 0:
            logger.error("Converted audio content is empty")
            return "[Error: Converted audio is empty]"

        logger.debug(f"Converted audio size: {len(audio_content)} bytes")

        # Initialize client
        client = speech_v1.SpeechClient()
        
        # Prepare audio for recognition
        audio = speech_v1.RecognitionAudio(content=audio_content)
        
        # Configure recognition request (start with Venezuelan locale)
        language = "es-VE"
        config = speech_v1.RecognitionConfig(
            encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=language,
            enable_automatic_punctuation=True,
            model="latest_long",
        )

        logger.debug(f"Sending to Google Cloud Speech-to-Text API (lang={language})...")

        # Perform transcription with fallback in case model/language unsupported
        try:
            response = client.recognize(config=config, audio=audio)
        except google_exceptions.InvalidArgument as e:
            msg = str(e)
            logger.warning(f"Recognition InvalidArgument: {msg}")
            # If the requested model is not supported for the locale, retry with a
            # more widely supported Spanish locale (es-ES) and omit explicit model.
            if "not supported for language" in msg or "not supported for language" in getattr(e, 'message', ''):
                fallback_language = "es-ES"
                logger.info(f"Retrying transcription with fallback language {fallback_language}")
                config = speech_v1.RecognitionConfig(
                    encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=16000,
                    language_code=fallback_language,
                    enable_automatic_punctuation=True,
                )
                try:
                    response = client.recognize(config=config, audio=audio)
                except Exception as e2:
                    logger.error(f"Fallback transcription failed: {type(e2).__name__}: {e2}")
                    raise
            else:
                # Re-raise other InvalidArgument errors
                raise
        
        logger.debug(f"Response received - {len(response.results)} result(s)")
        
        # Extract transcript
        transcript = ""
        for i, result in enumerate(response.results):
            logger.debug(f"Result {i}: confidence={result.results[0].confidence if result.results else 'N/A'}")
            if result.alternatives:
                text = result.alternatives[0].transcript
                transcript += text + " "
                logger.debug(f"  Transcript: {text}")
        
        if not transcript.strip():
            logger.warning("No speech detected in audio")
            return "[No speech detected]"
        
        logger.info(f"Transcription successful: {len(transcript)} chars")
        return transcript.strip()
        
    except FileNotFoundError:
        logger.error(f"Audio file not found: {file_path}")
        return "[Error: Audio file not found]"
    except Exception as e:
        logger.error(f"Transcription error: {type(e).__name__}: {str(e)}", exc_info=True)
        return f"[Error: {str(e)}]"

