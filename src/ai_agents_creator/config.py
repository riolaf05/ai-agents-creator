"""Caricamento configurazione da ambiente / .env."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

ProviderName = Literal["anthropic", "bedrock", "vertex"]


class Settings(BaseModel):
    """Configurazione globale dell'applicazione."""

    provider: ProviderName = "anthropic"

    anthropic_api_key: str | None = None
    # ID documentati: https://docs.anthropic.com/en/docs/about-claude/models
    anthropic_model: str = "claude-sonnet-4-6"

    aws_region: str = "eu-west-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None
    # Base model o inference profile (es. eu.anthropic.claude-sonnet-4-6)
    bedrock_model: str = "anthropic.claude-sonnet-4-6"

    vertex_project_id: str | None = None
    vertex_region: str = "europe-west1"
    # Vertex usa gli stessi id modello dell'API Anthropic (es. claude-sonnet-4-6)
    vertex_model: str = "claude-sonnet-4-6"

    default_max_tokens: int = 4096
    default_temperature: float = 0.3
    agent_max_iterations: int = 8
    # Se True, stampa su stderr passi LLM/agent (utile in CLI; disattiva su webhook).
    agent_progress: bool = False

    a2a_base_url: str = "http://localhost:8000"
    webhook_secret: str = "change-me"

    kb_input_dir: Path = Field(default=Path("./data/input"))
    kb_output_dir: Path = Field(default=Path("./data/knowledge_base"))
    editorial_output_dir: Path = Field(default=Path("./data/editorial"))

    mcp_servers: list[str] = Field(default_factory=list)

    @property
    def model_id(self) -> str:
        """Restituisce l'id modello corretto per il provider attivo."""
        if self.provider == "bedrock":
            return self.bedrock_model
        if self.provider == "vertex":
            return self.vertex_model
        return self.anthropic_model


def _parse_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_str(key: str, default: str | None = None) -> str | None:
    """Legge una variabile d'ambiente e tratta stringa vuota come assente.

    Evita che chiavi AWS o token STS vuoti vengano passati all'SDK (causa tipica
    di ``PermissionDeniedError: The security token included in the request is
    invalid`` con Bedrock).
    """
    raw = os.getenv(key, default)
    if raw is None:
        return None
    stripped = raw.strip()
    return stripped if stripped else None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Carica (una sola volta) le impostazioni dal file .env + env vars."""
    load_dotenv(override=False)

    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    if provider not in ("anthropic", "bedrock", "vertex"):
        raise ValueError(f"LLM_PROVIDER non valido: {provider}")

    return Settings(
        provider=provider,  # type: ignore[arg-type]
        anthropic_api_key=_env_str("ANTHROPIC_API_KEY"),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        aws_region=os.getenv("AWS_REGION", "eu-west-1"),
        aws_access_key_id=_env_str("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=_env_str("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=_env_str("AWS_SESSION_TOKEN"),
        bedrock_model=os.getenv("BEDROCK_MODEL", "anthropic.claude-sonnet-4-6"),
        vertex_project_id=_env_str("VERTEX_PROJECT_ID"),
        vertex_region=os.getenv("VERTEX_REGION", "europe-west1"),
        vertex_model=os.getenv("VERTEX_MODEL", "claude-sonnet-4-6"),
        default_max_tokens=int(os.getenv("DEFAULT_MAX_TOKENS", "4096")),
        default_temperature=float(os.getenv("DEFAULT_TEMPERATURE", "0.3")),
        agent_max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "8")),
        agent_progress=_env_bool("AGENT_PROGRESS", default=False),
        a2a_base_url=os.getenv("A2A_BASE_URL", "http://localhost:8000"),
        webhook_secret=os.getenv("WEBHOOK_SECRET", "change-me"),
        kb_input_dir=Path(os.getenv("KB_INPUT_DIR", "./data/input")),
        kb_output_dir=Path(os.getenv("KB_OUTPUT_DIR", "./data/knowledge_base")),
        editorial_output_dir=Path(os.getenv("EDITORIAL_OUTPUT_DIR", "./data/editorial")),
        mcp_servers=_parse_list(os.getenv("MCP_SERVERS")),
    )


def clear_settings_cache() -> None:
    """Svuota la cache di ``get_settings()`` (utile dopo modifiche al file ``.env``)."""
    get_settings.cache_clear()
