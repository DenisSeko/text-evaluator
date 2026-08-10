"""OpenAI-backed LLM client with retry + JSON mode."""

from __future__ import annotations

import asyncio
from typing import Any

import openai
from openai import AsyncOpenAI

from .base import LLMClient, LLMError

_RETRYABLE_EXCEPTIONS = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.InternalServerError,
)

_MAX_ATTEMPTS = 3


class OpenAIProvider(LLMClient):
    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        temperature: float = 0.3,
        timeout: float = 60.0,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout)

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        json_mode: bool = False,
        temperature: float | None = None,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
        }
        if json_mode:
            # Strict JSON via structured-output-style response_format.
            kwargs["response_format"] = {"type": "json_object"}

        last_error: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = await self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                return content.strip()
            except _RETRYABLE_EXCEPTIONS as exc:  # pragma: no cover - exercised live only
                last_error = exc
                await asyncio.sleep(0.5 * (2**attempt))
        raise LLMError(f"OpenAI request failed after {_MAX_ATTEMPTS} attempts: {last_error}")
