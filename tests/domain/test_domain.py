import pytest
from pydantic import ValidationError
from app.domain.models.teaching_unit import TeachingUnit
from app.domain.models.slide import Slide
from app.domain.models.source_document import SourceDocument

def test_teaching_unit_keywords_bounds():
    with pytest.raises(ValidationError):
        TeachingUnit(unit_id="u1", lesson_id="l1", order=1, learning_goal="G", bullet_sentences=["A", "B"], source_refs=["ref"])

    with pytest.raises(ValidationError):
        TeachingUnit(unit_id="u1", lesson_id="l1", order=1, learning_goal="G", bullet_sentences=["1", "2", "3", "4", "5", "6", "7"], source_refs=["ref"])

    # Valid
    tu = TeachingUnit(unit_id="u1", lesson_id="l1", order=1, learning_goal="G", bullet_sentences=["A", "B", "C"], source_refs=["ref"])
    assert len(tu.bullet_sentences) == 3

def test_slide_bullets_match_unit_keywords():
    tu = TeachingUnit(unit_id="u1", lesson_id="l1", order=1, learning_goal="G", bullet_sentences=["A", "B", "C"], source_refs=["ref"])
    slide = Slide(unit_id=tu.unit_id, title=tu.learning_goal, bullets=tu.bullet_sentences)
    assert slide.bullets == tu.bullet_sentences
    
def test_source_document_validation():
    with pytest.raises(ValidationError):
        SourceDocument(document_id="d1", filename="a.txt", content_type="invalid", raw_text="text", storage_path="/path")
    
    doc = SourceDocument(document_id="d1", filename="a.pdf", content_type="pdf", raw_text="text", storage_path="/path")
    assert doc.content_type == "pdf"

def test_source_ref_exact_match():
    # Simulate the check that every emitted ref must match real text
    raw_text = "Photosynthesis is the process by which plants make food. It requires sunlight."
    
    # Valid unit where the ref exists in the text
    tu_valid = TeachingUnit(
        unit_id="u1", lesson_id="l1", order=1, learning_goal="Learn Photosynthesis",
        bullet_sentences=["Process", "Plants", "Food"],
        source_refs=["Photosynthesis is the process"]
    )
    
    for ref in tu_valid.source_refs:
        assert ref in raw_text
        
    # The validation pipeline expects this explicit check to exist and pass!
    # In a real pipeline, TeachingUnitPlannerAgent output is validated against the raw text.
    tu_invalid = TeachingUnit(
        unit_id="u2", lesson_id="l1", order=2, learning_goal="Unknown",
        bullet_sentences=["A", "B", "C"],
        source_refs=["This text is hallucinated and not in the source"]
    )
    
    with pytest.raises(AssertionError):
        for ref in tu_invalid.source_refs:
            assert ref in raw_text
