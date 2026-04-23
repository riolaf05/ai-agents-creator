"""Schemi del protocollo A2A (Agent-to-Agent).

Implementazione semplificata ispirata alla specifica A2A: ogni agente espone
una "agent card" descrittiva ed accetta richieste JSON su un endpoint HTTP.

Una richiesta A2A include:
* ``sender``     -> identificativo del chiamante (url o nome)
* ``task``       -> la consegna in linguaggio naturale
* ``context``    -> dati strutturati opzionali (dict libero)
* ``reply_to``   -> opzionale, URL a cui inviare una callback asincrona

La risposta include ``output`` (testo) + ``artifacts`` (dati strutturati).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentCard(BaseModel):
    """Descrizione pubblica di un agente o orchestrator esposto via A2A."""

    name: str
    description: str
    version: str = "0.1.0"
    skills: list[str] = Field(default_factory=list)
    endpoint: str


class A2AMessage(BaseModel):
    sender: str = "unknown"
    task: str
    context: dict[str, Any] = Field(default_factory=dict)
    reply_to: str | None = None


class A2AResponse(BaseModel):
    agent: str
    output: str
    artifacts: dict[str, Any] = Field(default_factory=dict)
    ok: bool = True
    error: str | None = None
