import os
import pytest
from app.infrastructure.presentation.pptx_builder import PptxBuilder
from app.domain.models.teaching_unit import TeachingUnit
from app.domain.models.narration_segment import NarrationSegment
from pptx import Presentation

def test_pptx_builder_creates_file():
    units = [
        TeachingUnit(unit_id="u1", lesson_id="l1", order=1, learning_goal="Goal 1", bullet_sentences=["A", "B", "C"], source_refs=["ref"]),
        TeachingUnit(unit_id="u2", lesson_id="l1", order=2, learning_goal="Goal 2", bullet_sentences=["D", "E", "F"], source_refs=["ref"])
    ]
    
    narration_segments = [
        NarrationSegment(unit_id="u1", narration_text="This is the narration text for teaching unit 1, which has enough length to pass validation.", estimated_duration_sec=10.0),
        NarrationSegment(unit_id="u2", narration_text="This is the narration text for teaching unit 2, which also has enough length to pass validation.", estimated_duration_sec=12.0)
    ]
    
    builder = PptxBuilder()
    slides, path = builder.build(units, narration_segments, output_dir="test_outputs")
    
    assert os.path.exists(path)
    assert len(slides) == 2
    
    prs = Presentation(path)
    assert len(prs.slides) == 2
    
    # Assert slide 1 bullets match
    slide1 = prs.slides[0]
    tf = slide1.placeholders[1].text_frame
    bullets = [p.text for p in tf.paragraphs if p.text]
    assert bullets == units[0].bullet_sentences
    
    # Assert slide 1 speaker notes match verbatim
    assert slide1.notes_slide.notes_text_frame.text == narration_segments[0].narration_text
    assert slides[0].speaker_notes == narration_segments[0].narration_text

    # Cleanup test outputs
    try:
        if os.path.exists(path):
            os.remove(path)
        if os.path.exists("test_outputs"):
            os.rmdir("test_outputs")
    except Exception:
        pass

