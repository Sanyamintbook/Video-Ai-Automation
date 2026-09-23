import json
import time
from typing import Any
from loguru import logger

from app.config.settings import get_settings
from app.core.exceptions import (
    AIProviderException,
    ProviderAuthenticationException,
    ProviderResponseException,
    ProviderTimeoutException,
)
from app.infrastructure.ai.providers.base import LLMProvider
from app.infrastructure.ai.schemas.llm_response import LLMResponse


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.openai_api_key
        self.model = settings.default_model if "gpt" in settings.default_model else "gpt-4o-mini"
        self.client = None
        if self.api_key:
            try:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI Client: {e}")

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        if not self.client:
            logger.warning("openai_request_failed provider=openai reason=missing-api-key")
            raise ProviderAuthenticationException("OpenAI API key is not configured.")

        start_time = time.perf_counter()
        logger.info("openai_request_started provider=openai model={model}", model=self.model)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )
        except Exception as exc:
            logger.exception("openai_request_failed provider=openai model={model} error={error}", model=self.model, error=type(exc).__name__)
            raise AIProviderException(f"OpenAI generation failed: {exc}") from exc

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        content = response.choices[0].message.content or ""
        logger.info(
            "openai_request_completed provider=openai model={model} latency_ms={latency_ms}",
            model=self.model,
            latency_ms=latency_ms,
        )
        return LLMResponse(
            provider="openai",
            model=self.model,
            content=content,
            latency_ms=float(latency_ms),
        )

    async def generate_structured(
        self,
        prompt: str,
        schema: dict,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> dict:
        kwargs["response_format"] = {"type": "json_object"}
        for attempt in range(2):
            raw_response = await self.generate(prompt, system_prompt=system_prompt, **kwargs)
            try:
                text = raw_response.content.strip()
                if text.startswith("```json"):
                    text = text[7:]
                elif text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
                parsed = json.loads(text)
            except json.JSONDecodeError:
                if attempt == 1:
                    raise ProviderResponseException("OpenAI returned invalid JSON for structured generation.")
                continue

            if not isinstance(parsed, dict):
                raise ProviderResponseException("OpenAI structured response was not a JSON object.")

            return parsed

        raise ProviderResponseException("OpenAI returned invalid JSON for structured generation.")

    async def health_check(self) -> bool:
        return self.client is not None
