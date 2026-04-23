"""Server A2A: espone Orchestrator e Agent via HTTP JSON.

Questo modulo fornisce un ``APIRouter`` FastAPI che, una volta montato, espone:

* ``GET  /a2a/agents`` -> elenco ``AgentCard`` disponibili.
* ``GET  /a2a/agents/{name}`` -> card di un singolo agent.
* ``POST /a2a/agents/{name}`` -> invoca l'agent con un ``A2AMessage``.
* ``POST /a2a/orchestrators/{name}`` -> invoca un orchestrator registrato.

Gli orchestrator vengono registrati tramite ``register_orchestrator``.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from ..core.orchestrator import Orchestrator
from ..core.registry import AgentRegistry
from .schema import A2AMessage, A2AResponse, AgentCard

logger = logging.getLogger(__name__)

_ORCHESTRATORS: dict[str, Orchestrator] = {}


def register_orchestrator(orch: Orchestrator) -> None:
    _ORCHESTRATORS[orch.name] = orch


def list_orchestrators() -> list[Orchestrator]:
    return list(_ORCHESTRATORS.values())


def build_a2a_router(base_url: str = "") -> APIRouter:
    router = APIRouter(prefix="/a2a", tags=["a2a"])

    @router.get("/agents", response_model=list[AgentCard])
    def _list_agents() -> list[AgentCard]:
        cards: list[AgentCard] = []
        for a in AgentRegistry.list():
            cards.append(
                AgentCard(
                    name=a.name,
                    description=a.description,
                    skills=[t.name for t in a.tools],
                    endpoint=f"{base_url}/a2a/agents/{a.name}",
                )
            )
        for o in list_orchestrators():
            cards.append(
                AgentCard(
                    name=o.name,
                    description=f"Orchestrator gruppo '{o.group}': {o.mission[:120]}",
                    skills=["delegate_to_agent", "list_agents"],
                    endpoint=f"{base_url}/a2a/orchestrators/{o.name}",
                )
            )
        return cards

    @router.get("/agents/{name}", response_model=AgentCard)
    def _get_agent(name: str) -> AgentCard:
        try:
            a = AgentRegistry.get(name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return AgentCard(
            name=a.name,
            description=a.description,
            skills=[t.name for t in a.tools],
            endpoint=f"{base_url}/a2a/agents/{a.name}",
        )

    @router.post("/agents/{name}", response_model=A2AResponse)
    def _invoke_agent(name: str, message: A2AMessage) -> A2AResponse:
        try:
            a = AgentRegistry.get(name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        logger.info("A2A -> agent %s (sender=%s)", name, message.sender)
        try:
            result = a.run(_build_input(message))
            return A2AResponse(
                agent=name,
                output=result.output_text,
                artifacts={"tool_calls": result.tool_calls},
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Errore invocando %s via A2A", name)
            return A2AResponse(agent=name, output="", ok=False, error=str(exc))

    @router.post("/orchestrators/{name}", response_model=A2AResponse)
    def _invoke_orch(name: str, message: A2AMessage) -> A2AResponse:
        orch = _ORCHESTRATORS.get(name)
        if orch is None:
            raise HTTPException(status_code=404, detail=f"Orchestrator '{name}' non registrato")
        logger.info("A2A -> orchestrator %s (sender=%s)", name, message.sender)
        try:
            result = orch.run(_build_input(message))
            return A2AResponse(
                agent=name,
                output=result.output_text,
                artifacts={"tool_calls": result.tool_calls},
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Errore invocando orchestrator %s via A2A", name)
            return A2AResponse(agent=name, output="", ok=False, error=str(exc))

    return router


def _build_input(message: A2AMessage) -> str:
    if not message.context:
        return message.task
    context_block = "\n".join(f"- {k}: {v}" for k, v in message.context.items())
    return f"{message.task}\n\nContesto:\n{context_block}"
