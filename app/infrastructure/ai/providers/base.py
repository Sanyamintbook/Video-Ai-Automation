from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel
from app.infrastructure.ai.schemas.llm_response import LLMResponse

class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        pass
        
    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: dict,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> dict:
        pass
        
    @abstractmethod
    async def health_check(self) -> bool:
        pass
