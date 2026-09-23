import pytest
from unittest.mock import MagicMock, patch
from app.infrastructure.ai.providers.gemini_provider import GeminiProvider

@pytest.mark.anyio
async def test_gemini_provider_generate_success():
    mock_response = MagicMock()
    mock_response.text = "This is a response from Gemini"
    
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    
    mock_settings = MagicMock()
    mock_settings.google_api_key = "mock_key"
    mock_settings.default_model = "gemini-2.5-pro"
    
    with patch("google.genai.Client", return_value=mock_client), \
         patch("app.infrastructure.ai.providers.gemini_provider.get_settings", return_value=mock_settings):
        provider = GeminiProvider()
        response = await provider.generate(prompt="Hello", system_prompt="Test")
        assert response.content == "This is a response from Gemini"
        assert response.provider == "gemini"

@pytest.mark.anyio
async def test_gemini_provider_generate_structured_success():
    mock_response = MagicMock()
    mock_response.text = '{"output": "structured_data"}'
    
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    
    mock_settings = MagicMock()
    mock_settings.google_api_key = "mock_key"
    mock_settings.default_model = "gemini-2.5-pro"
    
    with patch("google.genai.Client", return_value=mock_client), \
         patch("app.infrastructure.ai.providers.gemini_provider.get_settings", return_value=mock_settings):
        provider = GeminiProvider()
        response = await provider.generate_structured(prompt="Hello", schema={})
        assert response == {"output": "structured_data"}
