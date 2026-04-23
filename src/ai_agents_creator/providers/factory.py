"""Factory che crea un client Anthropic (API diretta o AWS Bedrock).

Entrambe le classi espongono la stessa API `messages.create(...)` grazie all'SDK
ufficiale `anthropic` che fornisce sia ``Anthropic`` (API cloud) sia
``AnthropicBedrock`` (AWS Bedrock). Questo modulo nasconde la scelta del
provider dietro ``build_client()`` e ``complete()``.
"""

from __future__ import annotations

import sys
from typing import Any

from anthropic import Anthropic, AnthropicBedrock

from ..config import Settings, get_settings


def _validate_model_for_provider(settings: Settings) -> None:
    """Evita errori 400 per modelId incoerente col provider."""
    mid = settings.model_id
    if settings.provider == "anthropic":
        if mid.startswith("anthropic.") or mid.startswith(("eu.", "us.", "global.", "ap.", "au.", "jp.")):
            raise ValueError(
                f"ANTHROPIC_MODEL={mid!r} sembra un id Bedrock/inference profile. "
                "Per l'API Anthropic usa es. claude-sonnet-4-6 oppure "
                "claude-sonnet-4-5-20250929; oppure imposta LLM_PROVIDER=bedrock "
                "e BEDROCK_MODEL."
            )
    elif settings.provider == "bedrock":
        if mid.startswith("claude-"):
            raise ValueError(
                f"BEDROCK_MODEL={mid!r} è un id API Anthropic, non valido su Bedrock. "
                "Usa es. anthropic.claude-sonnet-4-6 oppure "
                "eu.anthropic.claude-sonnet-4-6 (inference profile EU)."
            )


def build_client(settings: Settings | None = None):
    """Crea un client Claude compatibile col provider configurato."""
    settings = settings or get_settings()

    if settings.provider == "bedrock":
        # Non passare session token se assente: una riga vuota in .env può far
        # fallire la firma AWS con "The security token ... is invalid".
        bedrock_kwargs: dict[str, Any] = {
            "aws_region": settings.aws_region,
            "aws_access_key": settings.aws_access_key_id,
            "aws_secret_key": settings.aws_secret_access_key,
        }
        if settings.aws_session_token:
            bedrock_kwargs["aws_session_token"] = settings.aws_session_token
        return AnthropicBedrock(**bedrock_kwargs)

    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY non impostata: configura .env oppure usa "
            "LLM_PROVIDER=bedrock."
        )
    return Anthropic(api_key=settings.anthropic_api_key)


def complete(
    messages: list[dict[str, Any]],
    *,
    system: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    settings: Settings | None = None,
) -> Any:
    """Wrapper minimale su ``messages.create`` che usa il provider attivo.

    Ritorna l'oggetto messaggio "grezzo" dell'SDK (con ``content``,
    ``stop_reason``, ``usage``, ecc.) così può essere usato direttamente dai
    loop agentici.
    """
    settings = settings or get_settings()
    _validate_model_for_provider(settings)
    client = build_client(settings)

    kwargs: dict[str, Any] = {
        "model": model or settings.model_id,
        "max_tokens": max_tokens or settings.default_max_tokens,
        "temperature": settings.default_temperature if temperature is None else temperature,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools

    if settings.agent_progress:
        n_tools = len(tools) if tools else 0
        print(
            f"[progress] LLM {settings.provider} model={kwargs['model']} "
            f"tools={n_tools} (attendi, Bedrock può richiedere 10–60s per round)…",
            file=sys.stderr,
            flush=True,
        )

    return client.messages.create(**kwargs)
