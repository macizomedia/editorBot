"""
Unit tests for template module.
"""

import pytest
from unittest.mock import Mock, patch
from bot.templates.models import TemplateSpec, Duration, ScriptStructure
from bot.templates.validator import validate_script, ValidationResult
from bot.templates.client import TemplateClient


class TestTemplateModels:
    """Test template data models."""

    def test_template_from_dict(self):
        """Test creating TemplateSpec from dictionary."""
        data = {
            "id": "test_template",
            "name": "Test Template",
            "description": "Test description",
            "intent_profile": "opinion",
            "allowed_formats": ["REEL_VERTICAL"],
            "duration": {
                "min_seconds": 30,
                "target_seconds": 45,
                "max_seconds": 60
            },
            "script_structure": {
                "allowed_structure_types": ["linear_argument"],
                "min_beats": 3,
                "max_beats": 5,
                "required_roles": ["hook", "argument"],
                "optional_roles": ["conclusion"],
                "forbidden_roles": ["call_to_action"]
            },
            "audio_rules": {
                "voice_policy": "required",
                "music_allowed": True
            },
            "visual_rules": {
                "visual_strategy": "mixed",
                "visuals_required": True
            },
            "enforcement": {
                "strict": True,
                "violation_strategy": "reject"
            }
        }

        template = TemplateSpec.from_dict(data)

        assert template.id == "test_template"
        assert template.name == "Test Template"
        assert template.duration.min_seconds == 30
        assert template.duration.max_seconds == 60
        assert template.script_structure.min_beats == 3
        assert template.enforcement.strict is True

    def test_template_to_dict(self):
        """Test serializing TemplateSpec to dictionary."""
        data = {
            "id": "test_template",
            "name": "Test Template",
            "description": "Test",
            "intent_profile": "opinion",
            "allowed_formats": ["REEL_VERTICAL"],
            "duration": {"min_seconds": 30, "target_seconds": 45, "max_seconds": 60},
            "script_structure": {
                "allowed_structure_types": ["linear_argument"],
                "min_beats": 3, "max_beats": 5,
                "required_roles": ["hook"], "optional_roles": [], "forbidden_roles": []
            },
            "audio_rules": {"voice_policy": "required", "music_allowed": True},
            "visual_rules": {"visual_strategy": "mixed", "visuals_required": True},
            "enforcement": {"strict": True, "violation_strategy": "reject"}
        }

        template = TemplateSpec.from_dict(data)
        result = template.to_dict()

        assert result["id"] == data["id"]
        assert result["duration"]["min_seconds"] == 30


class TestTemplateValidator:
    """Test template validation logic."""

    @pytest.fixture
    def template(self):
        """Create a test template."""
        data = {
            "id": "test_template",
            "name": "Test Template",
            "description": "Test",
            "intent_profile": "opinion",
            "allowed_formats": ["REEL_VERTICAL"],
            "duration": {"min_seconds": 30, "target_seconds": 45, "max_seconds": 60},
            "script_structure": {
                "allowed_structure_types": ["linear_argument"],
                "min_beats": 3, "max_beats": 5,
                "required_roles": ["hook", "argument"],
                "optional_roles": ["conclusion"],
                "forbidden_roles": ["call_to_action"]
            },
            "audio_rules": {"voice_policy": "required", "music_allowed": True},
            "visual_rules": {"visual_strategy": "mixed", "visuals_required": True},
            "enforcement": {"strict": True, "violation_strategy": "reject"}
        }
        return TemplateSpec.from_dict(data)

    def test_valid_script_passes(self, template):
        """Test that a valid script passes validation."""
        script = {
            'total_duration': 52,
            'structure_type': 'linear_argument',
            'beats': [
                {'role': 'hook', 'duration': 8},
                {'role': 'argument', 'duration': 35},
                {'role': 'conclusion', 'duration': 9}
            ]
        }

        result = validate_script(script, template)

        assert result.passed is True
        assert len(result.errors) == 0

    def test_duration_too_long_fails(self, template):
        """Test that exceeding max duration fails validation."""
        script = {
            'total_duration': 95,
            'structure_type': 'linear_argument',
            'beats': [
                {'role': 'hook', 'duration': 10},
                {'role': 'argument', 'duration': 85}
            ]
        }

        result = validate_script(script, template)

        assert result.passed is False
        assert len(result.errors) > 0
        assert "excede el máximo" in result.errors[0]

    def test_duration_too_short_fails(self, template):
        """Test that being under min duration fails validation."""
        script = {
            'total_duration': 20,
            'structure_type': 'linear_argument',
            'beats': [
                {'role': 'hook', 'duration': 10},
                {'role': 'argument', 'duration': 10}
            ]
        }

        result = validate_script(script, template)

        assert result.passed is False
        assert "menor al mínimo" in result.errors[0]

    def test_duration_above_target_warns(self, template):
        """Test that exceeding target (but not max) produces warning."""
        script = {
            'total_duration': 55,
            'structure_type': 'linear_argument',
            'beats': [
                {'role': 'hook', 'duration': 10},
                {'role': 'argument', 'duration': 40},
                {'role': 'conclusion', 'duration': 5}
            ]
        }

        result = validate_script(script, template)

        assert result.passed is True
        assert len(result.warnings) > 0
        assert "supera el objetivo" in result.warnings[0]

    def test_wrong_structure_type_fails(self, template):
        """Test that invalid structure type fails."""
        script = {
            'total_duration': 50,
            'structure_type': 'nested_exploration',
            'beats': [
                {'role': 'hook', 'duration': 10},
                {'role': 'argument', 'duration': 40}
            ]
        }

        result = validate_script(script, template)

        assert result.passed is False
        assert "no permitido" in result.errors[0]

    def test_too_few_beats_fails(self, template):
        """Test that too few beats fails validation."""
        script = {
            'total_duration': 40,
            'structure_type': 'linear_argument',
            'beats': [
                {'role': 'hook', 'duration': 10},
                {'role': 'argument', 'duration': 30}
            ]
        }

        result = validate_script(script, template)

        assert result.passed is False
        assert "menor al mínimo" in result.errors[0]

    def test_too_many_beats_fails(self, template):
        """Test that too many beats fails validation."""
        script = {
            'total_duration': 50,
            'structure_type': 'linear_argument',
            'beats': [
                {'role': 'hook', 'duration': 5},
                {'role': 'argument', 'duration': 10},
                {'role': 'argument', 'duration': 10},
                {'role': 'argument', 'duration': 10},
                {'role': 'argument', 'duration': 10},
                {'role': 'conclusion', 'duration': 5}
            ]
        }

        result = validate_script(script, template)

        assert result.passed is False
        assert "excede el máximo" in result.errors[0]

    def test_missing_required_role_fails(self, template):
        """Test that missing required role fails validation."""
        script = {
            'total_duration': 50,
            'structure_type': 'linear_argument',
            'beats': [
                {'role': 'hook', 'duration': 10},
                {'role': 'conclusion', 'duration': 40}
                # Missing 'argument' which is required
            ]
        }

        result = validate_script(script, template)

        assert result.passed is False
        assert "Falta el beat requerido" in result.errors[0]

    def test_forbidden_role_fails(self, template):
        """Test that forbidden role fails validation."""
        script = {
            'total_duration': 50,
            'structure_type': 'linear_argument',
            'beats': [
                {'role': 'hook', 'duration': 10},
                {'role': 'argument', 'duration': 30},
                {'role': 'call_to_action', 'duration': 10}  # Forbidden
            ]
        }

        result = validate_script(script, template)

        assert result.passed is False
        assert "prohibido" in result.errors[0]


class TestTemplateClient:
    """Test template API client."""

    @patch('bot.templates.client.requests.get')
    def test_list_templates_success(self, mock_get):
        """Test fetching template list."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'templates': [
                {'id': 'template1', 'name': 'Template 1'},
                {'id': 'template2', 'name': 'Template 2'}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = TemplateClient()
        templates = client.list_templates()

        assert len(templates) == 2
        assert templates[0]['id'] == 'template1'

    @patch('bot.templates.client.requests.get')
    def test_list_templates_error(self, mock_get):
        """Test handling error when fetching templates."""
        mock_get.side_effect = Exception("Network error")

        client = TemplateClient()
        templates = client.list_templates()

        assert templates == []

    @patch('bot.templates.client.requests.get')
    def test_get_template_success(self, mock_get):
        """Test fetching specific template."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'success': True,
            'template': {
                "id": "test_template",
                "name": "Test Template",
                "description": "Test",
                "intent_profile": "opinion",
                "allowed_formats": ["REEL_VERTICAL"],
                "duration": {"min_seconds": 30, "target_seconds": 45, "max_seconds": 60},
                "script_structure": {
                    "allowed_structure_types": ["linear_argument"],
                    "min_beats": 3, "max_beats": 5,
                    "required_roles": ["hook"], "optional_roles": [], "forbidden_roles": []
                },
                "audio_rules": {"voice_policy": "required", "music_allowed": True},
                "visual_rules": {"visual_strategy": "mixed", "visuals_required": True},
                "enforcement": {"strict": True, "violation_strategy": "reject"}
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = TemplateClient()
        template = client.get_template('test_template')

        assert template is not None
        assert template.id == 'test_template'
        assert template.name == 'Test Template'

    @patch('bot.templates.client.requests.get')
    def test_get_template_not_found(self, mock_get):
        """Test handling template not found."""
        mock_response = Mock()
        mock_response.json.return_value = {'success': False}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = TemplateClient()
        template = client.get_template('nonexistent')

        assert template is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
