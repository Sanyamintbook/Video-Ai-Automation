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


class GeminiProvider(LLMProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.google_api_key
        self.model = settings.default_model
        if "gemini" not in self.model.lower():
            self.model = "gemini-2.5-pro"
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Gemini Client: {e}")

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        if not self.client:
            logger.warning("gemini_request_failed provider=gemini reason=missing-api-key")
            raise ProviderAuthenticationException("Gemini API key is not configured.")

        start_time = time.perf_counter()
        logger.info("gemini_request_started provider=gemini model={model}", model=self.model)
        
        max_attempts = 4
        attempt = 0
        response = None
        
        while attempt < max_attempts:
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={"system_instruction": system_prompt} if system_prompt else None,
                )
                if hasattr(response, "__await__"):
                    response = await response
                break
            except Exception as exc:
                err_msg = str(exc).lower()
                is_rate_limit = "429" in err_msg or "resource_exhausted" in err_msg or "quota" in err_msg
                if is_rate_limit and attempt < max_attempts - 1:
                    attempt += 1
                    logger.warning(f"Gemini API rate limit (429) hit. Retrying in 18s (attempt {attempt}/{max_attempts - 1})...")
                    import asyncio
                    await asyncio.sleep(18)
                else:
                    logger.exception("gemini_request_failed provider=gemini model={model} error={error}", model=self.model, error=type(exc).__name__)
                    if isinstance(exc, TimeoutError):
                        raise ProviderTimeoutException("Gemini request timed out.") from exc
                    raise AIProviderException(f"Gemini generation failed: {exc}") from exc

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        text = getattr(response, "text", "")
        if not text and hasattr(response, "candidates"):
            text = ""
            for candidate in response.candidates:
                text += getattr(candidate, "content", "")
        if not text and hasattr(response, "response"):
            text = getattr(response.response, "text", "")
        logger.info(
            "gemini_request_completed provider=gemini model={model} latency_ms={latency_ms}",
            model=self.model,
            latency_ms=latency_ms,
        )
        return LLMResponse(
            provider="gemini",
            model=self.model,
            content=text,
            latency_ms=float(latency_ms),
        )

    async def generate_structured(
        self,
        prompt: str,
        schema: dict,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> dict:
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
                    raise ProviderResponseException("Gemini returned invalid JSON for structured generation.")
                continue

            if isinstance(parsed, list):
                parsed = {"units": parsed, "lessons": parsed, "items": parsed}

            if not isinstance(parsed, dict):
                raise ProviderResponseException(f"Gemini structured response was not a JSON object or list. Got type: {type(parsed).__name__}")

            return parsed

        raise ProviderResponseException("Gemini returned invalid JSON for structured generation.")

    async def health_check(self) -> bool:
        return self.client is not None