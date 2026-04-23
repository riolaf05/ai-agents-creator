"""App FastAPI che espone webhook per invocare orchestrator/agent.

Avvio:

```bash
uvicorn ai_agents_creator.triggers.webhook:app --reload
```

Endpoint principali:

* ``POST /run/{orchestrator_name}`` -> invoca un orchestrator registrato.
* ``POST /run/agent/{agent_name}``  -> invoca un singolo agent.
* ``GET  /health``
* ``GET  /a2a/...`` -> protocollo A2A (vedi ``ai_agents_creator.a2a.server``).

L'header ``X-Webhook-Secret`` deve corrispondere a ``WEBHOOK_SECRET`` nel
``.env``.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from ..a2a.server import build_a2a_router, list_orchestrators, register_orchestrator
from ..config import get_settings
from ..core.registry import AgentRegistry
from ..use_cases import bootstrap_all

logger = logging.getLogger(__name__)

settings = get_settings()
bootstrap_all()  # registra use case di default (KB + Editorial)

app = FastAPI(
    title="AI Agents Creator",
    description="Webhook + A2A server per Claude agents",
    version="0.1.0",
)
app.include_router(build_a2a_router(base_url=settings.a2a_base_url))


class RunRequest(BaseModel):
    task: str = Field(..., description="Consegna per l'agente/orchestrator in linguaggio naturale")
    context: dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    ok: bool
    output: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


def _check_secret(secret: str | None) -> None:
    if secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="invalid webhook secret")


def _build_input(task: str, context: dict[str, Any]) -> str:
    if not context:
        return task
    ctx = "\n".join(f"- {k}: {v}" for k, v in context.items())
    return f"{task}\n\nContesto:\n{ctx}"


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "provider": settings.provider,
        "model": settings.model_id,
        "agents": [a.name for a in AgentRegistry.list()],
        "orchestrators": [o.name for o in list_orchestrators()],
    }


@app.post("/run/{orchestrator_name}", response_model=RunResponse)
def run_orchestrator(
    orchestrator_name: str,
    body: RunRequest,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
) -> RunResponse:
    _check_secret(x_webhook_secret)
    orch = next((o for o in list_orchestrators() if o.name == orchestrator_name), None)
    if orch is None:
        raise HTTPException(status_code=404, detail=f"orchestrator '{orchestrator_name}' non trovato")
    try:
        result = orch.run(_build_input(body.task, body.context))
        return RunResponse(ok=True, output=result.output_text, tool_calls=result.tool_calls)
    except Exception as exc:  # noqa: BLE001
        logger.exception("webhook orchestrator error")
        return RunResponse(ok=False, output="", error=str(exc))


@app.post("/run/agent/{agent_name}", response_model=RunResponse)
def run_agent(
    agent_name: str,
    body: RunRequest,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
) -> RunResponse:
    _check_secret(x_webhook_secret)
    try:
        agent = AgentRegistry.get(agent_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        result = agent.run(_build_input(body.task, body.context))
        return RunResponse(ok=True, output=result.output_text, tool_calls=result.tool_calls)
    except Exception as exc:  # noqa: BLE001
        logger.exception("webhook agent error")
        return RunResponse(ok=False, output="", error=str(exc))


__all__ = ["app", "register_orchestrator"]
