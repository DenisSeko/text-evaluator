"""Application settings loaded from environment / `.env` (pydantic-settings)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Values come from environment variables or a local `.env`.

    Every secret (OPENAI_API_KEY) is loaded from the environment and never hardcoded.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        protected_namespaces=("settings_",),
    )

    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    model: str = Field(default="gpt-4.1-mini", validation_alias="LEXI_MODEL")
    model_synth: str = Field(default="gpt-5-mini", validation_alias="LEXI_MODEL_SYNTH")
    max_chars: int = Field(default=40000, validation_alias="LEXI_MAX_CHARS")
    temperature: float = Field(default=0.3, validation_alias="LEXI_TEMPERATURE")
    weight_structure: float = Field(default=0.30, validation_alias="LEXI_WEIGHT_STRUCTURE")
    weight_rubric: float = Field(default=0.30, validation_alias="LEXI_WEIGHT_RUBRIC")
    weight_psychology: float = Field(default=0.25, validation_alias="LEXI_WEIGHT_PSYCHOLOGY")
    weight_humanity: float = Field(default=0.15, validation_alias="LEXI_WEIGHT_HUMANITY")
    cache_dir: str = Field(default=".cache", validation_alias="LEXI_CACHE_DIR")
    request_timeout: float = Field(default=60.0, validation_alias="LEXI_REQUEST_TIMEOUT")
    user_agent: str = Field(
        default="lexi-evaluator/0.1 (job-task demo; contact: support@lexi.hr)",
        validation_alias="LEXI_USER_AGENT",
    )

    def agent_weights(self) -> dict[str, float]:
        """Per-agent aggregation weights (agent id -> weight)."""
        return {
            "structure": self.weight_structure,
            "rubric": self.weight_rubric,
            "psychology": self.weight_psychology,
            "humanity": self.weight_humanity,
        }

    def has_api_key(self) -> bool:
        key = self.openai_api_key or ""
        return bool(key.startswith("sk-") and "REPLACE_ME" not in key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
