"""Client A2A: permette di chiamare agenti remoti (o i nostri stessi agenti
quando girano su un'altra macchina)."""

from __future__ import annotations

from typing import Any

import httpx

from ..core.tools import Tool
from .schema import A2AMessage, A2AResponse, AgentCard


class A2AClient:
    """Client HTTP minimale per il protocollo A2A."""

    def __init__(self, base_url: str, timeout: float = 120.0, sender: str = "ai-agents-creator"):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.sender = sender

    def list_agents(self) -> list[AgentCard]:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}/a2a/agents")
            r.raise_for_status()
            return [AgentCard.model_validate(item) for item in r.json()]

    def invoke_agent(self, name: str, task: str, context: dict[str, Any] | None = None) -> A2AResponse:
        return self._post(f"/a2a/agents/{name}", task, context)

    def invoke_orchestrator(
        self, name: str, task: str, context: dict[str, Any] | None = None
    ) -> A2AResponse:
        return self._post(f"/a2a/orchestrators/{name}", task, context)

    def _post(self, path: str, task: str, context: dict[str, Any] | None) -> A2AResponse:
        message = A2AMessage(sender=self.sender, task=task, context=context or {})
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(f"{self.base_url}{path}", json=message.model_dump())
            r.raise_for_status()
            return A2AResponse.model_validate(r.json())


def a2a_tool(
    *,
    tool_name: str,
    description: str,
    base_url: str,
    remote_agent: str,
    is_orchestrator: bool = False,
) -> Tool:
    """Crea un ``Tool`` che un nostro agente può usare per invocare un agente
    remoto via A2A.

    Esempio:

    ```python
    translator = a2a_tool(
        tool_name="call_external_translator",
        description="Traduce testi usando un agente remoto",
        base_url="https://partner.example.com",
        remote_agent="translator",
    )
    my_agent = Agent(name="writer", ..., tools=[translator])
    ```
    """
    client = A2AClient(base_url=base_url)

    def runner(task: str, context: dict[str, Any] | None = None) -> str:
        if is_orchestrator:
            resp = client.invoke_orchestrator(remote_agent, task, context=context)
        else:
            resp = client.invoke_agent(remote_agent, task, context=context)
        if not resp.ok:
            return f"ERROR (A2A {remote_agent}): {resp.error}"
        return resp.output

    return Tool(
        name=tool_name,
        description=f"[A2A -> {remote_agent}@{base_url}] {description}",
        input_schema={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Consegna da inviare all'agente remoto"},
                "context": {
                    "type": "object",
                    "description": "Contesto strutturato opzionale (dict libero)",
                },
            },
            "required": ["task"],
        },
        func=runner,
        metadata={"a2a": True, "remote_agent": remote_agent, "base_url": base_url},
    )
