from __future__ import annotations

import time
from typing import Any, Literal

from loguru import logger

from app.core.exceptions import AgentException
from app.infrastructure.ai.prompts.loader import PromptLoader
from app.infrastructure.ai.providers.base import LLMProvider
from app.infrastructure.ai.providers.router import Router


class BaseAgent:
    """Shared infrastructure for all AI agents."""

    def __init__(self, provider: LLMProvider | None = None, prompt_loader: PromptLoader | None = None) -> None:
        self.router = Router()
        self.provider = provider
        self.prompt_loader = prompt_loader or PromptLoader()
        self.logger = logger

    def _build_prompt(self, prompt_name: str, context: dict[str, Any] | None = None) -> str:
        template = self.prompt_loader.load(prompt_name)
        if not context:
            return template

        return template.format(**context)

    async def generate_text(self, prompt_name: str, context: dict[str, Any] | None = None, **kwargs: Any) -> str:
        prompt = self._build_prompt(prompt_name, context)
        self.logger.info("agent_prompt_loaded agent={agent} prompt={prompt_name}", agent=self.__class__.__name__, prompt_name=prompt_name)
        
        retry_count = 0
        failure_type = None
        max_attempts = 4

        while retry_count < max_attempts:
            if self.provider:
                provider = self.provider
            else:
                provider = self.router.select_provider(self.__class__.__name__, retry_count, failure_type)

            try:
                start_time = time.perf_counter()
                response = await provider.generate(prompt, **kwargs)
                latency_ms = int((time.perf_counter() - start_time) * 1000)

                self.logger.info(
                    "ai_call_success agent={agent} provider={provider} model={model} latency_ms={latency} retry_count={retry_count} token_count=0",
                    agent=self.__class__.__name__,
                    provider=provider.__class__.__name__.replace("Provider", "").lower(),
                    model=getattr(provider, "model", "unknown"),
                    latency=latency_ms,
                    retry_count=retry_count
                )
                return response.content
            except Exception as e:
                err_msg = str(e).lower()
                is_unreachable = (
                    "connection" in err_msg 
                    or "unreachable" in err_msg 
                    or "refused" in err_msg 
                    or "503" in err_msg
                )

                failure_type = "unreachable" if is_unreachable else "schema"
                retry_count += 1

                if failure_type == "schema":
                    self.logger.info(
                        "ai_format_mismatch agent={agent} provider={provider} retry_count={retry_count} - AI format error, retrying naturally. Detail: {error}",
                        agent=self.__class__.__name__,
                        provider=provider.__class__.__name__.replace("Provider", "").lower(),
                        retry_count=retry_count,
                        error=str(e)
                    )
                else:
                    self.logger.warning(
                        "ai_call_failed agent={agent} provider={provider} retry_count={retry_count} failure_type={failure_type} error={error}",
                        agent=self.__class__.__name__,
                        provider=provider.__class__.__name__.replace("Provider", "").lower(),
                        retry_count=retry_count,
                        failure_type=failure_type,
                        error=str(e)
                    )

                if self.provider:
                    raise AgentException(f"Agent {self.__class__.__name__} failed to generate text: {str(e)}") from e

        raise AgentException(f"Agent {self.__class__.__name__} failed to generate text after {retry_count} retries.")

    async def generate_structured(
        self,
        prompt_name: str,
        schema: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        validator: Any = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        prompt = self._build_prompt(prompt_name, context)
        self.logger.info("agent_prompt_loaded agent={agent} prompt={prompt_name}", agent=self.__class__.__name__, prompt_name=prompt_name)
        
        retry_count = 0
        failure_type: Literal["schema", "unreachable"] | None = None
        max_attempts = 4

        while retry_count < max_attempts:
            if self.provider:
                provider = self.provider
            else:
                provider = self.router.select_provider(self.__class__.__name__, retry_count, failure_type)

            try:
                start_time = time.perf_counter()
                result = await provider.generate_structured(prompt, schema or {}, **kwargs)
                if validator:
                    validator(result)
                    
                latency_ms = int((time.perf_counter() - start_time) * 1000)

                self.logger.info(
                    "ai_call_success agent={agent} provider={provider} model={model} latency_ms={latency} retry_count={retry_count} token_count=0",
                    agent=self.__class__.__name__,
                    provider=provider.__class__.__name__.replace("Provider", "").lower(),
                    model=getattr(provider, "model", "unknown"),
                    latency=latency_ms,
                    retry_count=retry_count
                )
                return result
            except Exception as e:
                err_msg = str(e).lower()
                is_unreachable = (
                    "connection" in err_msg 
                    or "unreachable" in err_msg 
                    or "refused" in err_msg 
                    or "503" in err_msg
                )

                failure_type = "unreachable" if is_unreachable else "schema"
                retry_count += 1

                if failure_type == "schema":
                    self.logger.info(
                        "ai_format_mismatch agent={agent} provider={provider} retry_count={retry_count} - AI format error, retrying naturally. Detail: {error}",
                        agent=self.__class__.__name__,
                        provider=provider.__class__.__name__.replace("Provider", "").lower(),
                        retry_count=retry_count,
                        error=str(e)
                    )
                    prompt = prompt + f"\n\n[SYSTEM NOTICE]: Your previous attempt failed schema validation. Error: {str(e)}.\nPlease ensure you strictly follow the required format and fix this error."
                else:
                    self.logger.warning(
                        "ai_call_failed agent={agent} provider={provider} retry_count={retry_count} failure_type={failure_type} error={error}",
                        agent=self.__class__.__name__,
                        provider=provider.__class__.__name__.replace("Provider", "").lower(),
                        retry_count=retry_count,
                        failure_type=failure_type,
                        error=str(e)
                    )

                if self.provider:
                    raise AgentException(f"Agent {self.__class__.__name__} failed to generate structured data: {str(e)}") from e

        raise AgentException(f"Agent {self.__class__.__name__} failed to generate structured data after {retry_count} retries.")
