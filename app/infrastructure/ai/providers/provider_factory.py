from app.config.settings import get_settings
from app.core.exceptions import AIProviderException
from app.infrastructure.ai.providers.base import LLMProvider
from app.infrastructure.ai.providers.gemini_provider import GeminiProvider
from app.infrastructure.ai.providers.ollama_provider import OllamaProvider


class ProviderFactory:
    @staticmethod
    def create(provider_name: str | None = None) -> LLMProvider:
        settings = get_settings()
        resolved_name = (provider_name or settings.default_provider).lower()

        if resolved_name == "gemini":
            return GeminiProvider()

        if resolved_name == "openai":
            from app.infrastructure.ai.providers.openai_provider import OpenAIProvider
            return OpenAIProvider()

        if resolved_name == "ollama":
            return OllamaProvider()

        raise AIProviderException(f"Unsupported provider: {resolved_name}")