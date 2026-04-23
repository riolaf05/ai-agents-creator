"""Orchestrator: un agent di alto livello che coordina dei subagent.

Il pattern ricalca quello usato da Claude Code quando delega task ai subagent:

* L'Orchestrator è esso stesso un ``Agent`` con un prompt di "director".
* Ha a disposizione **uno o più tool di delega**: ``delegate_to_agent``,
  ``list_agents``, e opzionalmente un tool ``finalize`` per chiudere il task.
* Quando il modello vuole far lavorare un subagent chiama il tool
  ``delegate_to_agent(agent_name, task)``, l'orchestrator esegue il subagent
  in-process e passa il risultato al modello.

Questa struttura è **espandibile**: basta registrare nuovi agenti nel
``AgentRegistry`` con lo stesso gruppo e l'orchestrator li vedrà subito.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from typing import Any

from ..config import Settings, get_settings
from .agent import Agent, AgentResult
from .registry import AgentRegistry
from .tools import Tool

logger = logging.getLogger(__name__)


ORCHESTRATOR_SYSTEM_TEMPLATE = """Sei un **Orchestrator** di agenti AI specializzati.

Il tuo compito è risolvere l'obiettivo fornito dall'utente **delegando** i
task giusti ai subagent disponibili, uno alla volta, nell'ordine corretto.

Regole:
- NON eseguire tu stesso operazioni di dominio: delega ai subagent.
- Usa `list_agents` se non ricordi chi è disponibile.
- Usa `delegate_to_agent(agent_name, task)` per invocare un subagent.
- Ogni subagent riceve UNA consegna in linguaggio naturale, ben specificata.
- Dopo ogni delega verifica il risultato e decidi il passo successivo.
- Quando hai completato il task produci una risposta finale sintetica.

Agenti disponibili in questo gruppo ({group}):
{agents_docs}
"""


@dataclass
class Orchestrator:
    """Coordina un gruppo di agent registrati nel ``AgentRegistry``."""

    name: str
    group: str
    mission: str
    extra_tools: list[Tool] = field(default_factory=list)
    model: str | None = None
    max_iterations: int | None = None

    def _subagents(self) -> list[Agent]:
        return AgentRegistry.list(self.group)

    def _build_system_prompt(self) -> str:
        docs_lines = []
        for a in self._subagents():
            docs_lines.append(f"- **{a.name}**: {a.description}")
        return (
            ORCHESTRATOR_SYSTEM_TEMPLATE.format(
                group=self.group,
                agents_docs="\n".join(docs_lines) if docs_lines else "(nessun subagent)",
            )
            + "\n\nMissione globale: "
            + self.mission
        )

    def _build_tools(self) -> list[Tool]:
        def list_agents() -> str:
            """Elenca gli agenti disponibili con descrizione."""
            return json.dumps(
                [
                    {"name": a.name, "description": a.description}
                    for a in self._subagents()
                ],
                ensure_ascii=False,
            )

        def delegate_to_agent(agent_name: str, task: str) -> str:
            """Delega un task in linguaggio naturale a un subagent per nome."""
            try:
                agent = AgentRegistry.get(agent_name)
            except KeyError as exc:
                return f"ERROR: {exc}"
            logger.info("[Orchestrator %s] -> %s", self.name, agent_name)
            settings = get_settings()
            if settings.agent_progress:
                print(
                    f"[progress] orchestrator={self.name} delega -> {agent_name}",
                    file=sys.stderr,
                    flush=True,
                )
            result: AgentResult = agent.run(task)
            return json.dumps(
                {
                    "agent": agent_name,
                    "output": result.output_text,
                    "tool_calls_count": len(result.tool_calls),
                },
                ensure_ascii=False,
            )

        list_tool = Tool(
            name="list_agents",
            description="Elenca i subagent disponibili (nome + descrizione).",
            input_schema={"type": "object", "properties": {}},
            func=list_agents,
        )
        delegate_tool = Tool(
            name="delegate_to_agent",
            description=(
                "Assegna un task in linguaggio naturale a uno dei subagent "
                "disponibili. 'agent_name' deve essere il nome esatto."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "agent_name": {"type": "string", "description": "Nome del subagent"},
                    "task": {"type": "string", "description": "Istruzione in linguaggio naturale"},
                },
                "required": ["agent_name", "task"],
            },
            func=delegate_to_agent,
        )
        return [list_tool, delegate_tool, *self.extra_tools]

    def _as_agent(self, settings: Settings) -> Agent:
        return Agent(
            name=self.name,
            description=f"Orchestrator per il gruppo {self.group}",
            system_prompt=self._build_system_prompt(),
            tools=self._build_tools(),
            model=self.model,
            max_iterations=self.max_iterations or settings.agent_max_iterations * 2,
        )

    def run(
        self,
        user_goal: str,
        *,
        settings: Settings | None = None,
    ) -> AgentResult:
        settings = settings or get_settings()
        agent = self._as_agent(settings)
        return agent.run(user_goal, settings=settings)
