import pytest
from app.infrastructure.validation.schema_validator import SchemaValidator
from app.domain.models.understanding import Understanding
from app.domain.models.lesson_plan import LessonPlan
from app.domain.models.teaching_unit import TeachingUnit
from app.domain.models.narration_segment import NarrationSegment

def test_schema_validator_understanding():
    validator = SchemaValidator()
    
    # Valid
    valid_dict = {
        "document_id": "doc_123",
        "chapter_title": "Ch 1",
        "main_topic": "Test main",
        "major_topics": ["Topic A"],
        "subtopics": ["Subtopic A"],
        "learning_objectives": ["Obj A"],
        "definitions": [{"word": "A", "def": "B"}],
        "examples": ["Ex A"],
        "summary": "This is a summary of the understanding document."
    }
    res = validator.validate(valid_dict, Understanding)
    assert res.is_valid is True
    assert len(res.errors) == 0

    # Invalid (missing main_topic, empty major_topics)
    invalid_dict = {
        "document_id": "doc_123",
        "chapter_title": "Ch 1",
        "major_topics": [],
        "subtopics": ["Subtopic A"],
        "learning_objectives": [],
        "definitions": [],
        "examples": [],
        "summary": ""
    }
    res = validator.validate(invalid_dict, Understanding)
    assert res.is_valid is False
    assert len(res.errors) > 0

def test_schema_validator_lesson_plan():
    validator = SchemaValidator()
    
    # Valid
    valid_dict = {
        "document_id": "doc_123",
        "lessons": [
            {"sequence": 1, "title": "L1", "objective": "Obj1", "estimated_minutes": 10}
        ]
    }
    res = validator.validate(valid_dict, LessonPlan)
    assert res.is_valid is True

    # Invalid
    invalid_dict = {
        "document_id": "doc_123",
        "lessons": []
    }
    res = validator.validate(invalid_dict, LessonPlan)
    assert res.is_valid is False

def test_schema_validator_teaching_unit_list():
    validator = SchemaValidator()
    
    # Valid list
    valid_list = [
        {
            "unit_id": "u1",
            "lesson_id": "l1",
            "order": 1,
            "learning_goal": "Goal1",
            "bullet_sentences": ["kw1", "kw2", "kw3"],
            "source_refs": ["ref1"]
        }
    ]
    res = validator.validate(valid_list, TeachingUnit)
    assert res.is_valid is True

    # Invalid list (bullet_sentences length too short)
    invalid_list = [
        {
            "unit_id": "u1",
            "lesson_id": "l1",
            "order": 1,
            "learning_goal": "Goal1",
            "bullet_sentences": ["kw1"],
            "source_refs": ["ref1"]
        }
    ]
    res = validator.validate(invalid_list, TeachingUnit)
    assert res.is_valid is False

def test_schema_validator_narration_segment_list():
    validator = SchemaValidator()
    
    # Valid
    valid_list = [
        {
            "unit_id": "u1",
            "narration_text": "This is a detailed classroom narration script explaining the unit keywords fully.",
            "estimated_duration_sec": 12.5,
            "validation_status": "PENDING",
            "validation_notes": []
        }
    ]
    res = validator.validate(valid_list, NarrationSegment)
    assert res.is_valid is True

    # Invalid (narration too short)
    invalid_list = [
        {
            "unit_id": "u1",
            "narration_text": "Too short",
            "estimated_duration_sec": 5.0
        }
    ]
    res = validator.validate(invalid_list, NarrationSegment)
    assert res.is_valid is False
