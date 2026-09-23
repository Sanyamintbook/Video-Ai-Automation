import pytest
from unittest.mock import AsyncMock, MagicMock
from app.domain.models.teaching_unit import TeachingUnit
from app.infrastructure.ai.agents.script_generator_agent import ScriptGeneratorAgent
from app.infrastructure.ai.schemas.llm_response import LLMResponse

def get_jaccard_similarity(keywords: list[str], narration: str) -> float:
    # Basic token-based Jaccard similarity
    keywords_tokens = set(" ".join(keywords).lower().replace(",", "").replace(".", "").replace("!", "").split())
    narration_tokens = set(narration.lower().replace(",", "").replace(".", "").replace("!", "").split())
    intersection = keywords_tokens.intersection(narration_tokens)
    union = keywords_tokens.union(narration_tokens)
    if not union:
        return 0.0
    return len(intersection) / len(union)

@pytest.mark.anyio
async def test_script_generator_agent_success():
    # 1. Arrange Mock Provider
    mock_provider = MagicMock()
    mock_provider.generate_structured = AsyncMock(return_value={
        "narration_text": "Minerals are natural resources found in the Earth crust. They are completely inorganic, meaning they are not made of living organisms, and each mineral has its own distinct chemical composition."
    })
    
    agent = ScriptGeneratorAgent(provider=mock_provider)
    unit = TeachingUnit(
        unit_id="unit_001",
        lesson_id="lesson_01",
        order=1,
        learning_goal="Understand minerals definition",
        keywords=["Natural", "Inorganic", "Composition"],
        source_refs=["page1_p2"]
    )
    
    # 2. Act
    segment = await agent.run(unit)
    
    # 3. Assert
    assert segment.unit_id == "unit_001"
    assert "inorganic" in segment.narration_text.lower()
    assert segment.estimated_duration_sec > 0.0
    
    # Check Jaccard similarity to ensure elaboration, not near-verbatim restatement
    similarity = get_jaccard_similarity(unit.keywords, segment.narration_text)
    # Elaboration should have similarity below 0.5 because of added connective words
    assert similarity < 0.5, f"Narration is too similar to keywords (similarity: {similarity:.2f})"

@pytest.mark.anyio
async def test_script_generator_agent_similarity_check_fails_on_degenerate_restatement():
    mock_provider = MagicMock()
    # Degenerate restatement: just joining keywords with "and"
    mock_provider.generate_structured = AsyncMock(return_value={
        "narration_text": "Natural and Inorganic and Composition! Natural and Inorganic and Composition!"
    })
    
    agent = ScriptGeneratorAgent(provider=mock_provider)
    unit = TeachingUnit(
        unit_id="unit_001",
        lesson_id="lesson_01",
        order=1,
        learning_goal="Understand minerals definition",
        keywords=["Natural", "Inorganic", "Composition"],
        source_refs=["page1_p2"]
    )
    
    segment = await agent.run(unit)
    similarity = get_jaccard_similarity(unit.keywords, segment.narration_text)
    
    # Overlap is natural (3 keywords) / union (4 words: natural, and, inorganic, composition) = 0.75
    assert similarity >= 0.5, f"Expected similarity to be high for degenerate restatement, got: {similarity:.2f}"
