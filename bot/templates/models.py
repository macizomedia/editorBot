"""
Template data models with type-safe dataclasses.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class Duration:
    """Duration constraints for a template."""
    min_seconds: int
    target_seconds: int
    max_seconds: int


@dataclass
class ScriptStructure:
    """Script structure constraints."""
    allowed_structure_types: List[str]
    min_beats: int
    max_beats: int
    required_roles: List[str]
    optional_roles: List[str]
    forbidden_roles: List[str]


@dataclass
class AudioRules:
    """Audio requirements for a template."""
    voice_policy: str  # "required" | "optional" | "forbidden"
    music_allowed: bool


@dataclass
class VisualRules:
    """Visual requirements for a template."""
    visual_strategy: str  # "subtitles_only" | "slides" | "mixed" | "optional"
    visuals_required: bool


@dataclass
class Enforcement:
    """Enforcement policy for template validation."""
    strict: bool
    violation_strategy: str  # "reject" | "suggest_adjustments"


@dataclass
class TemplateSpec:
    """Complete template specification."""
    id: str
    template_family: str  # "opinion" | "explainer" | "essay" | "story" | "prompt"
    name: str
    description: str
    intent_profile: str
    audience_relationship: str  # e.g. "speaker_to_audience", "guide_to_learner"
    allowed_formats: List[str]
    duration: Duration
    script_structure: ScriptStructure
    audio_rules: AudioRules
    visual_rules: VisualRules
    enforcement: Enforcement

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TemplateSpec':
        """Create TemplateSpec from JSON data."""
        return cls(
            id=data['id'],
            template_family=data['template_family'],
            name=data['name'],
            description=data['description'],
            intent_profile=data['intent_profile'],
            audience_relationship=data['audience_relationship'],
            allowed_formats=data['allowed_formats'],
            duration=Duration(**data['duration']),
            script_structure=ScriptStructure(**data['script_structure']),
            audio_rules=AudioRules(**data['audio_rules']),
            visual_rules=VisualRules(**data['visual_rules']),
            enforcement=Enforcement(**data['enforcement'])
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert TemplateSpec to dictionary for storage."""
        return {
            'id': self.id,
            'template_family': self.template_family,
            'name': self.name,
            'description': self.description,
            'intent_profile': self.intent_profile,
            'audience_relationship': self.audience_relationship,
            'allowed_formats': self.allowed_formats,
            'duration': {
                'min_seconds': self.duration.min_seconds,
                'target_seconds': self.duration.target_seconds,
                'max_seconds': self.duration.max_seconds
            },
            'script_structure': {
                'allowed_structure_types': self.script_structure.allowed_structure_types,
                'min_beats': self.script_structure.min_beats,
                'max_beats': self.script_structure.max_beats,
                'required_roles': self.script_structure.required_roles,
                'optional_roles': self.script_structure.optional_roles,
                'forbidden_roles': self.script_structure.forbidden_roles
            },
            'audio_rules': {
                'voice_policy': self.audio_rules.voice_policy,
                'music_allowed': self.audio_rules.music_allowed
            },
            'visual_rules': {
                'visual_strategy': self.visual_rules.visual_strategy,
                'visuals_required': self.visual_rules.visuals_required
            },
            'enforcement': {
                'strict': self.enforcement.strict,
                'violation_strategy': self.enforcement.violation_strategy
            }
        }
