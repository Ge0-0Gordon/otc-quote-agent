"""Environment-based runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigurationError(ValueError):
    """Raised when runtime LLM configuration is incomplete."""


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_timeout_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
        defaults = {
            "openai": "https://api.openai.com/v1",
            "ollama": "http://localhost:11434",
        }
        settings = cls(
            llm_provider=provider,
            llm_base_url=os.getenv("LLM_BASE_URL", defaults.get(provider, "")).rstrip("/"),
            llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
            llm_model=os.getenv("LLM_MODEL", "").strip(),
            llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.llm_provider not in {"openai", "ollama"}:
            raise ConfigurationError(
                "LLM_PROVIDER must be 'openai' or 'ollama'. "
                "DeepSeek, Kimi and vLLM use the OpenAI-compatible provider."
            )
        if not self.llm_base_url:
            raise ConfigurationError("LLM_BASE_URL is required.")
        if not self.llm_model:
            raise ConfigurationError("LLM_MODEL is required.")
        if self.llm_timeout_seconds <= 0:
            raise ConfigurationError("LLM_TIMEOUT_SECONDS must be positive.")
