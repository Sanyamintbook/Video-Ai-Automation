import pytest
from unittest.mock import AsyncMock, MagicMock
from app.infrastructure.ai.providers.openai_provider import OpenAIProvider
from app.core.exceptions import ProviderAuthenticationException, AIProviderException

@pytest.mark.anyio
async def test_openai_provider_missing_key():
    # When api_key is empty, it should raise ProviderAuthenticationException
    provider = OpenAIProvider()
    provider.client = None
    with pytest.raises(ProviderAuthenticationException):
        await provider.generate("hello")

@pytest.mark.anyio
async def test_openai_provider_generate_success():
    provider = OpenAIProvider()
    mock_client = MagicMock()
    mock_chat = MagicMock()
    mock_completions = AsyncMock()
    
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "Response content"
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    
    mock_completions.create.return_value = mock_response
    mock_chat.completions = mock_completions
    mock_client.chat = mock_chat
    provider.client = mock_client
    provider.model = "gpt-4o-mini"
    
    res = await provider.generate("hello")
    assert res.content == "Response content"
    assert res.provider == "openai"
