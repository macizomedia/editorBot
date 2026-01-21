"""
Template validation logic for script compatibility checking.
"""

from typing import Dict, List, Any
from .models import TemplateSpec


class ValidationResult:
    """Result of template validation."""

    def __init__(self):
        self.passed = True
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def add_error(self, message: str):
        """Add a validation error."""
        self.passed = False
        self.errors.append(message)

    def add_warning(self, message: str):
        """Add a validation warning."""
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'passed': self.passed,
            'errors': self.errors,
            'warnings': self.warnings
        }


def validate_script(script: Dict, template: TemplateSpec) -> ValidationResult:
    """
    Validate script against template constraints.

    Args:
        script: Script dictionary with beats, duration, structure_type
        template: TemplateSpec to validate against

    Returns:
        ValidationResult with pass/fail status and messages
    """
    result = ValidationResult()

    # 1. Check duration
    duration = script.get('total_duration', 0)
    if duration < template.duration.min_seconds:
        result.add_error(
            f"Duración {duration}s es menor al mínimo {template.duration.min_seconds}s"
        )
    elif duration > template.duration.max_seconds:
        result.add_error(
            f"Duración {duration}s excede el máximo {template.duration.max_seconds}s"
        )
    elif duration > template.duration.target_seconds:
        result.add_warning(
            f"Duración {duration}s supera el objetivo {template.duration.target_seconds}s"
        )

    # 2. Check structure type
    structure_type = script.get('structure_type')
    if structure_type not in template.script_structure.allowed_structure_types:
        result.add_error(
            f"Tipo de estructura '{structure_type}' no permitido. "
            f"Permitidos: {', '.join(template.script_structure.allowed_structure_types)}"
        )

    # 3. Check beat count
    beats = script.get('beats', [])
    beat_count = len(beats)
    if beat_count < template.script_structure.min_beats:
        result.add_error(
            f"Número de beats {beat_count} es menor al mínimo {template.script_structure.min_beats}"
        )
    elif beat_count > template.script_structure.max_beats:
        result.add_error(
            f"Número de beats {beat_count} excede el máximo {template.script_structure.max_beats}"
        )

    # 4. Check required roles
    script_roles = {beat.get('role') for beat in beats}
    for required_role in template.script_structure.required_roles:
        if required_role not in script_roles:
            result.add_error(
                f"Falta el beat requerido: '{required_role}'"
            )

    # 5. Check forbidden roles
    for role in script_roles:
        if role in template.script_structure.forbidden_roles:
            result.add_error(
                f"Beat prohibido presente: '{role}'"
            )

    return result
