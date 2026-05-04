"""Knowledge Base: orchestrator + registrazione agenti.

Supporta due modalita':
- **locale** (default): gli agenti girano in-process, come prima.
- **distribuita**: se imposti env vars come KB_READER_URL=http://host:8001,
  l'orchestrator chiama quell'agente via A2A HTTP invece di eseguirlo in-process.
"""

from __future__ import annotations

import os

from ...a2a.client import a2a_tool
from ...core.agent import Agent
from ...core.orchestrator import Orchestrator
from ...core.registry import AgentRegistry
from ...core.tools import Tool

GROUP = "knowledge_base"

_AGENT_URL_VARS = {
    "kb_reader": "KB_READER_URL",
    "kb_classifier": "KB_CLASSIFIER_URL",
    "kb_writer": "KB_WRITER_URL",
    "kb_indexer": "KB_INDEXER_URL",
}

KB_MISSION = """Mantenere aggiornata la knowledge base markdown:
1. Scoprire i file di input in KB_INPUT_DIR.
2. Per ogni file nuovo o modificato:
   - delegare a `kb_reader` per ottenere testo pulito,
   - delegare a `kb_classifier` per category/tags/title/summary,
   - delegare a `kb_writer` per scrivere il .md nella categoria giusta.
3. Alla fine delegare a `kb_indexer` per rigenerare INDEX.md e index.json.
4. Riportare un riepilogo dei file creati/aggiornati e categorie usate.
"""


def _get_local_agents() -> list[Agent]:
    from .kb_classifier import agent as classifier
    from .kb_indexer import agent as indexer
    from .kb_reader import agent as reader
    from .kb_writer import agent as writer
    return [reader, classifier, writer, indexer]


def _remote_agent_tools() -> list[Tool]:
    """Se qualche URL e' configurato, crea tool A2A per quegli agenti."""
    tools: list[Tool] = []
    for agent_name, env_var in _AGENT_URL_VARS.items():
        url = os.environ.get(env_var, "").strip()
        if url:
            tools.append(
                a2a_tool(
                    tool_name=f"delegate_to_{agent_name}",
                    description=f"Chiama l'agente remoto {agent_name} via A2A",
                    base_url=url,
                    remote_agent=agent_name,
                )
            )
    return tools


def register_kb_agents() -> None:
    """Registra nel registry globale solo gli agenti locali (non remoti)."""
    for agent in _get_local_agents():
        if not os.environ.get(_AGENT_URL_VARS.get(agent.name, ""), "").strip():
            AgentRegistry.register(agent, group=GROUP)


def build_kb_orchestrator() -> Orchestrator:
    register_kb_agents()
    remote_tools = _remote_agent_tools()
    return Orchestrator(
        name="knowledge_base",
        group=GROUP,
        mission=KB_MISSION,
        extra_tools=remote_tools,
    )
