from unittest.mock import AsyncMock

import pytest

from app.infrastructure.ai.providers.ollama_provider import OllamaProvider
from app.infrastructure.ai.schemas.llm_response import LLMResponse


@pytest.mark.asyncio
async def test_ollama_structured_generation_uses_json_mode_and_cleans_response():
    provider = OllamaProvider()
    provider.generate = AsyncMock(
        return_value=LLMResponse(
            provider="ollama",
            model="qwen3:8b",
            content='<think>working</think>```json\n{"chapter_title": "Minerals"}\n```',
            latency_ms=1.0,
        )
    )

    schema = {"type": "object"}
    result = await provider.generate_structured("prompt", schema=schema)

    assert result == {"chapter_title": "Minerals"}
    provider.generate.assert_awaited_once()
    assert provider.generate.await_args.kwargs["format"] == schema
    assert provider.generate.await_args.kwargs["temperature"] == 0


@pytest.mark.asyncio
async def test_ollama_structured_generation_wraps_list_responses():
    provider = OllamaProvider()
    provider.generate = AsyncMock(
        return_value=LLMResponse(
            provider="ollama",
            model="qwen3:8b",
            content='[{"learning_goal": "Topic"}]',
            latency_ms=1.0,
        )
    )

    result = await provider.generate_structured("prompt", schema={})

    assert result["items"] == [{"learning_goal": "Topic"}]
    assert result["units"] == [{"learning_goal": "Topic"}]
