import time
from typing import Literal
from app.config.settings import get_settings
from app.infrastructure.ai.providers.base import LLMProvider
from app.infrastructure.ai.providers.gemini_provider import GeminiProvider
from app.infrastructure.ai.providers.ollama_provider import OllamaProvider

# Simple global cache for Ollama health check status to avoid repeated 5s connection timeouts
_ollama_status_cache = {
    "is_unreachable": False,
    "last_checked": 0.0
}

class Router:
    async def is_ollama_unreachable(self) -> bool:
        now = time.time()
        # Cache health check result for 60 seconds
        if now - _ollama_status_cache["last_checked"] < 60.0:
            return _ollama_status_cache["is_unreachable"]
            
        ollama = OllamaProvider()
        is_unreachable = not await ollama.health_check()
        
        _ollama_status_cache["is_unreachable"] = is_unreachable
        _ollama_status_cache["last_checked"] = now
        return is_unreachable

    def select_provider(
        self,
        agent_name: str,
        retry_count: int = 0,
        failure_type: Literal["schema", "unreachable"] | None = None
    ) -> LLMProvider:
        from app.infrastructure.ai.providers.provider_factory import ProviderFactory
        settings = get_settings()
        provider_name = getattr(settings, "default_provider", "ollama")
        try:
            return ProviderFactory.create(provider_name)
        except Exception:
            return OllamaProvider()
