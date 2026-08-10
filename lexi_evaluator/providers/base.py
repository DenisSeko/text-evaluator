"""Abstract LLM client interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMError(RuntimeError):
    """Raised when the LLM provider fails (network, API, auth, ...)."""


class LLMParseError(LLMError):
    """Raised when the model output cannot be parsed as valid structured data."""


class LLMClient(ABC):
    """Minimal async interface every provider must implement."""

    name: str = "base"

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        json_mode: bool = False,
        temperature: float | None = None,
    ) -> str:
        """Send a chat completion and return the message text.

        ``json_mode=True`` asks the provider to return strict JSON (via
        ``response_format``) — the model still needs the schema in the prompt.
        """
        raise NotImplementedError
