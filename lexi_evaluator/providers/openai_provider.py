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

# Reasoning models (gpt-5 / o-series) accept only the default temperature.
_REASONING_MODEL_PREFIXES = ("gpt-5", "o1", "o3", "o4", "o5")


def _supports_temperature(model: str) -> bool:
    """Reasoning models only support the default temperature (param must be omitted)."""
    return not model.lower().startswith(_REASONING_MODEL_PREFIXES)


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
        temperature_value = self.temperature if temperature is None else temperature
        # Reasoning models (e.g. gpt-5) reject a custom temperature — omit it there.
        send_temperature = _supports_temperature(self.model)

        last_error: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            kwargs: dict[str, Any] = {"model": self.model, "messages": messages}
            if send_temperature:
                kwargs["temperature"] = temperature_value
            if json_mode:
                # Strict JSON via structured-output-style response_format.
                kwargs["response_format"] = {"type": "json_object"}

            try:
                response = await self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                return content.strip()
            except _RETRYABLE_EXCEPTIONS as exc:  # pragma: no cover - exercised live only
                last_error = exc
                await asyncio.sleep(0.5 * (2**attempt))
            except openai.BadRequestError as exc:
                # Safety net: some models reject a custom temperature. Retry without it.
                if send_temperature and "temperature" in str(getattr(exc, "message", exc)):
                    send_temperature = False
                    last_error = exc
                    continue
                # Non-transient API error — surface as LLMError so the orchestrator
                # isolates this failure instead of crashing the whole run.
                raise LLMError(f"OpenAI request failed: {exc}") from exc

        raise LLMError(f"OpenAI request failed after {_MAX_ATTEMPTS} attempts: {last_error}")
