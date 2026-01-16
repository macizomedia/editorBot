from dialect_mediator.core.mediator import Mediator
from dialect_mediator.core.models import Text
from dialect_mediator.profiles.venezuelan import VenezuelanDialectProfile
from dialect_mediator.llm.openai_client import OpenAIClient  # or GeminiClient
import os

def mediate_text(raw_text: str) -> str:
    mediator = Mediator(
        profile=VenezuelanDialectProfile(),
        llm=OpenAIClient(api_key=os.environ["OPENAI_API_KEY"]),
    )

    result = mediator.mediate(Text(content=raw_text))
    return result.mediated_text

