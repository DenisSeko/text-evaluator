"""LLM provider layer.

A thin abstraction so the rest of the pipeline never touches a specific vendor
SDK. Only OpenAI is implemented today; Anthropic/Gemini/Ollama can be added by
implementing the same ``LLMClient`` interface.
"""

from __future__ import annotations

from ..config import Settings
from .base import LLMClient, LLMError
from .mock_provider import MockProvider
from .openai_provider import OpenAIProvider

__all__ = ["LLMClient", "LLMError", "OpenAIProvider", "MockProvider", "build_client"]


def build_client(
    settings: Settings, *, dry_run: bool = False, model: str | None = None
) -> LLMClient:
    """Build the LLM client for a run.

    ``dry_run=True`` returns a deterministic mock (no API key, no network) — used
    by tests and ``--dry-run``. Otherwise a real OpenAI client is required.
    """
    if dry_run:
        return MockProvider()

    if not settings.has_api_key():
        raise LLMError(
            "OPENAI_API_KEY is not set (or is a placeholder). "
            "Copy .env.example to .env and fill in the real key — never commit it."
        )

    return OpenAIProvider(
        api_key=settings.openai_api_key,
        model=model or settings.model,
        temperature=settings.temperature,
        timeout=settings.request_timeout,
    )
