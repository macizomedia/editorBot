from dialect_mediator.core.mediator import Mediator
from dialect_mediator.core.models import Text
from dialect_mediator.profiles.venezuelan import VenezuelanDialectProfile
from dialect_mediator.llm.gemini_client import GeminiClient
import os

def mediate_text(raw_text: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY environment variable")
    
    mediator = Mediator(
        profile=VenezuelanDialectProfile(),
        llm=GeminiClient(api_key=api_key),
    )

    result = mediator.mediate(Text(content=raw_text))
    return result.mediated_text

