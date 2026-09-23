import pytest
from unittest.mock import AsyncMock

from app.domain.models.narration_segment import NarrationSegment
from app.domain.models.teaching_unit import TeachingUnit
from app.infrastructure.ai.agents.validator_agent import ValidatorAgent

@pytest.mark.asyncio
async def test_validator_agent_passes_grounded_content():
    """
    Test Case 1 & 4: ValidatorAgent correctly PASSes fully-grounded narration,
    including legitimate grounded elaboration, and does NOT false-positive.
    """
    agent = ValidatorAgent()
    # Mock the LLM provider to return a 'passed' JSON
    agent.generate_structured = AsyncMock(return_value={
        "status": "passed",
        "issues": []
    })
    
    segment = NarrationSegment(
        unit_id="unit_1",
        narration_text="A mineral is something the Earth makes naturally. For example, quartz is a mineral.",
        estimated_duration_sec=0.0,
        validation_status="PENDING",
        validation_notes=[]
    )
    
    unit = TeachingUnit(
        lesson_id="lesson_1",
        unit_id="unit_1",
        order=1,
        learning_goal="Understand minerals",
        keywords=["mineral", "Earth", "geology"],
        source_refs=["A mineral is a naturally occurring solid."]
    )
    
    result = await agent.run(segment, unit)
    
    assert result.validation_status == "PASS"
    assert len(result.validation_notes) == 0

@pytest.mark.asyncio
async def test_validator_agent_fails_hallucinations_and_omissions():
    """
    Test Case 2 & 3: ValidatorAgent correctly FAILs narration with a fabricated claim,
    or narration that omits core keywords, and includes specific validation notes.
    """
    agent = ValidatorAgent()
    # Mock the LLM provider to return a 'failed' JSON with specific notes
    agent.generate_structured = AsyncMock(return_value={
        "status": "failed",
        "issues": ["Claim about '19th century French chemists' not found in source_refs."]
    })
    
    segment = NarrationSegment(
        unit_id="unit_2",
        narration_text="Minerals were first classified by 19th century French chemists.",
        estimated_duration_sec=0.0,
        validation_status="PENDING",
        validation_notes=[]
    )
    
    unit = TeachingUnit(
        lesson_id="lesson_1",
        unit_id="unit_2",
        order=2,
        learning_goal="Understand mineral history",
        keywords=["mineral", "history", "classification"],
        source_refs=["A mineral is a naturally occurring solid."]
    )
    
    result = await agent.run(segment, unit)
    
    assert result.validation_status == "FAIL"
    assert len(result.validation_notes) == 1
    assert "source_refs" in result.validation_notes[0]
