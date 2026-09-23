from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.models.source_document import SourceDocument
from app.domain.models.teaching_unit import TeachingUnit
from app.infrastructure.ai.agents.content_understanding_agent import ContentUnderstandingAgent
from app.infrastructure.ai.agents.script_generator_agent import ScriptGeneratorAgent


@pytest.mark.asyncio
async def test_content_understanding_falls_back_when_llm_fails():
    provider = MagicMock()
    provider.generate_structured = AsyncMock(side_effect=Exception("timeout"))
    agent = ContentUnderstandingAgent(provider=provider)
    content = SourceDocument(
        document_id="doc-1",
        filename="Ch 1 Minerals.pdf",
        content_type="pdf",
        raw_text=(
            "CHAPTER 1\n"
            "Minerals and Rocks\n"
            "Learning Objectives:\n"
            "Understand how minerals and rocks are formed.\n"
            "Minerals are naturally occurring substances found in Earth's crust.\n"
            "For example, quartz and mica are common minerals."
        ),
        storage_path="uploads/doc-1/file.pdf",
    )

    result = await agent.run(content)

    assert result.document_id == "doc-1"
    assert result.chapter_title == "Minerals and Rocks"
    assert result.major_topics
    assert result.learning_objectives
    assert "quartz" in " ".join(result.examples).lower()


@pytest.mark.asyncio
async def test_script_generator_falls_back_when_llm_fails():
    provider = MagicMock()
    provider.generate_structured = AsyncMock(side_effect=Exception("timeout"))
    agent = ScriptGeneratorAgent(provider=provider)
    unit = TeachingUnit(
        unit_id="unit-1",
        lesson_id="lesson-1",
        order=1,
        learning_goal="Natural resources",
        keywords=[
            "Natural resources are useful materials that people obtain from the environment.",
            "Some resources are renewable, while others can be exhausted by overuse.",
            "Careful use of resources helps protect the needs of future generations.",
        ],
        source_refs=["document"],
    )

    result = await agent.run(unit, source_context="long textbook text")

    assert result.unit_id == "unit-1"
    assert result.narration_text
    assert "Natural resources" in result.narration_text
