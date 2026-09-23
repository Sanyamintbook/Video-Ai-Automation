import pytest
from pydantic import ValidationError
from app.domain.models.narration_segment import NarrationSegment

def test_valid_narration_segment():
    seg = NarrationSegment(
        unit_id="unit_123",
        narration_text="This is a valid narration script that is definitely longer than forty characters long to satisfy the constraint.",
        estimated_duration_sec=15.5
    )
    assert seg.unit_id == "unit_123"
    assert seg.validation_status == "PENDING"
    assert seg.validation_notes == []

def test_invalid_narration_segment_too_short():
    with pytest.raises(ValidationError) as exc_info:
        NarrationSegment(
            unit_id="unit_123",
            narration_text="Too short",
            estimated_duration_sec=5.0
        )
    assert "min_length" in str(exc_info.value) or "at least 40 characters" in str(exc_info.value)
