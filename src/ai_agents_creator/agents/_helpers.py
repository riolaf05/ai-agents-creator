"""Helper per creare una FastAPI app standalone per un singolo agent.

Ogni agent puo' essere deployato come microservizio indipendente usando:

    uvicorn ai_agents_creator.agents.knowledge_base.kb_reader.server:app --port 8001

L'app espone:
- POST /run   -> invoca l'agent con un task
- GET  /health -> info agent
- GET  /a2a/agents -> AgentCard compatibile A2A
- POST /a2a/agents/{name} -> invocazione A2A standard
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ..a2a.schema import A2AMessage, A2AResponse, AgentCard
from ..core.agent import Agent


class RunRequest(BaseModel):
    task: str = Field(..., description="Consegna in linguaggio naturale")
    context: dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    ok: bool
    output: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


def _build_input(task: str, context: dict[str, Any]) -> str:
    if not context:
        return task
    ctx = "\n".join(f"- {k}: {v}" for k, v in context.items())
    return f"{task}\n\nContesto:\n{ctx}"


def standalone_app(agent: Agent, *, title: str | None = None) -> FastAPI:
    """Crea una FastAPI app pronta per il deploy standalone di un singolo agent."""
    app = FastAPI(
        title=title or f"Agent: {agent.name}",
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "agent": agent.name,
            "description": agent.description,
            "tools": [t.name for t in agent.tools],
        }

    @app.post("/run", response_model=RunResponse)
    def run(body: RunRequest) -> RunResponse:
        try:
            result = agent.run(_build_input(body.task, body.context))
            return RunResponse(ok=True, output=result.output_text, tool_calls=result.tool_calls)
        except Exception as exc:  # noqa: BLE001
            return RunResponse(ok=False, output="", error=str(exc))

    @app.get("/a2a/agents", response_model=list[AgentCard])
    def a2a_list() -> list[AgentCard]:
        return [
            AgentCard(
                name=agent.name,
                description=agent.description,
                skills=[t.name for t in agent.tools],
                endpoint=f"/a2a/agents/{agent.name}",
            )
        ]

    @app.post("/a2a/agents/{name}", response_model=A2AResponse)
    def a2a_invoke(name: str, message: A2AMessage) -> A2AResponse:
        if name != agent.name:
            return A2AResponse(agent=name, output="", ok=False, error=f"Agent '{name}' non trovato")
        try:
            result = agent.run(_build_input(message.task, message.context))
            return A2AResponse(
                agent=agent.name,
                output=result.output_text,
                artifacts={"tool_calls": result.tool_calls},
            )
        except Exception as exc:  # noqa: BLE001
            return A2AResponse(agent=agent.name, output="", ok=False, error=str(exc))

    return app
