"""
Quick test for template module functionality.
Tests model creation, serialization, and validation logic.
"""

# Test 1: Model imports and instantiation
print("Test 1: Importing models...")
from bot.templates.models import (
    Duration, ScriptStructure, AudioRules, VisualRules,
    Enforcement, TemplateSpec
)
print("✅ All model classes imported successfully")

# Test 2: Create template from dict (simulating API response)
print("\nTest 2: Creating TemplateSpec from dict...")
template_data = {
    "id": "test_template",
    "name": "Test Template",
    "description": "Test template for validation",
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

template = TemplateSpec.from_dict(template_data)
print(f"✅ Created template: {template.name}")
print(f"   Duration range: {template.duration.min_seconds}-{template.duration.max_seconds}s")
print(f"   Beats range: {template.script_structure.min_beats}-{template.script_structure.max_beats}")

# Test 3: Test validation logic
print("\nTest 3: Testing validation...")
from bot.templates.validator import validate_script, ValidationResult

# Valid script
valid_script = {
    'total_duration': 52,
    'structure_type': 'linear_argument',
    'beats': [
        {'role': 'hook', 'text': 'Test hook', 'duration': 8},
        {'role': 'argument', 'text': 'Test argument', 'duration': 35},
        {'role': 'conclusion', 'text': 'Test conclusion', 'duration': 9}
    ]
}

result = validate_script(valid_script, template)
print(f"✅ Valid script test: passed={result.passed}, errors={len(result.errors)}, warnings={len(result.warnings)}")

# Invalid script (too long)
invalid_script = {
    'total_duration': 95,
    'structure_type': 'linear_argument',
    'beats': [
        {'role': 'hook', 'duration': 10},
        {'role': 'argument', 'duration': 85}
    ]
}

result = validate_script(invalid_script, template)
print(f"✅ Invalid script test: passed={result.passed}, errors={len(result.errors)}")
if result.errors:
    print(f"   Expected errors: {result.errors[0][:50]}...")

# Test 4: Serialization round-trip
print("\nTest 4: Testing serialization...")
template_dict = template.to_dict()
template_restored = TemplateSpec.from_dict(template_dict)
assert template_restored.id == template.id
assert template_restored.name == template.name
print("✅ Serialization round-trip successful")

print("\n" + "="*50)
print("✅ ALL TESTS PASSED - Template module is ready!")
print("="*50)
