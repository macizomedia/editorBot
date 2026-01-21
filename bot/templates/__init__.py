"""
Template management module for content pipeline.

This module provides:
- Template fetching from Lambda API
- Template validation against scripts
- Type-safe template models
"""

from .models import TemplateSpec, Duration, ScriptStructure, AudioRules, VisualRules, Enforcement
from .validator import validate_script, ValidationResult

# Lazy import for client to avoid requests dependency during testing
def get_client():
    """Get TemplateClient (lazy import)."""
    from .client import TemplateClient
    return TemplateClient

__all__ = [
    'TemplateSpec',
    'Duration',
    'ScriptStructure',
    'AudioRules',
    'VisualRules',
    'Enforcement',
    'get_client',
    'validate_script',
    'ValidationResult',
]
