import pytest
from unittest.mock import MagicMock, patch
from app.infrastructure.audio.openai_tts_provider import OpenAITTSProvider
from app.core.exceptions import ProviderAuthenticationException, AIProviderException

def test_openai_tts_provider_success():
    with patch("app.infrastructure.audio.openai_tts_provider.OpenAI") as mock_openai_class:
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Mock speech create response
        mock_response = MagicMock()
        mock_response.content = b"fake-audio-bytes"
        mock_client.audio.speech.create.return_value = mock_response
        
        # Override settings for the test
        with patch("app.infrastructure.audio.openai_tts_provider.get_settings") as mock_settings:
            mock_set = MagicMock()
            mock_set.openai_api_key = "fake-key"
            mock_set.tts_voice = "alloy"
            mock_settings.return_value = mock_set
            
            provider = OpenAITTSProvider()
            assert provider.client == mock_client
            
            result = provider.synthesize("Hello world")
            assert result == b"fake-audio-bytes"
            mock_client.audio.speech.create.assert_called_once_with(
                model="tts-1",
                voice="alloy",
                input="Hello world"
            )

def test_openai_tts_provider_missing_key():
    with patch("app.infrastructure.audio.openai_tts_provider.get_settings") as mock_settings:
        mock_set = MagicMock()
        mock_set.openai_api_key = ""
        mock_settings.return_value = mock_set
        
        provider = OpenAITTSProvider()
        assert provider.client is None
        
        with patch("gtts.gTTS", side_effect=Exception("gTTS error")):
            with pytest.raises(ProviderAuthenticationException):
                provider.synthesize("Hello world")

def test_openai_tts_provider_api_error():
    with patch("app.infrastructure.audio.openai_tts_provider.OpenAI") as mock_openai_class:
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.audio.speech.create.side_effect = Exception("API connection error")
        
        with patch("app.infrastructure.audio.openai_tts_provider.get_settings") as mock_settings:
            mock_set = MagicMock()
            mock_set.openai_api_key = "fake-key"
            mock_settings.return_value = mock_set
            
            provider = OpenAITTSProvider()
            with patch("gtts.gTTS", side_effect=Exception("gTTS error")):
                with pytest.raises(AIProviderException) as excinfo:
                    provider.synthesize("Hello world")
                assert "API connection error" in str(excinfo.value)
