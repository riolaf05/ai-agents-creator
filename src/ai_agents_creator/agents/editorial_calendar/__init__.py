"""Editorial Calendar: orchestrator + registrazione agenti.

Supporta due modalita':
- **locale** (default): gli agenti girano in-process.
- **distribuita**: se imposti env vars come KB_RESEARCHER_URL=http://host:8011,
  l'orchestrator chiama quell'agente via A2A HTTP invece di eseguirlo in-process.
"""

from __future__ import annotations

import os

from ...a2a.client import a2a_tool
from ...core.agent import Agent
from ...core.orchestrator import Orchestrator
from ...core.registry import AgentRegistry
from ...core.tools import Tool

GROUP = "editorial_calendar"

_AGENT_URL_VARS = {
    "kb_researcher": "KB_RESEARCHER_URL",
    "strategist": "STRATEGIST_URL",
    "planner": "PLANNER_URL",
    "copywriter": "COPYWRITER_URL",
}

EDITORIAL_MISSION = """Generare un calendario editoriale per i social basato
su un topic fornito dall'utente e sulla knowledge base interna.

Pipeline obbligatoria:
1. `kb_researcher`  -> ritorna selected_paths + key_insights dalla KB.
2. `strategist`     -> ritorna audience, pillars, tone_of_voice, objectives.
3. `planner`        -> ritorna items (data/canale/formato/pillar/sources).
4. `copywriter`     -> scrive hook/body/cta/hashtags e salva il calendario
                       chiamando save_editorial_calendar.

Passa esplicitamente tra agenti: topic, numero giorni, canali richiesti, e
gli output intermedi (insights, pillars, items). Non saltare step.
Alla fine riporta il path del file generato e un breve recap.
"""


def _get_local_agents() -> list[Agent]:
    from .copywriter import agent as copywriter
    from .kb_researcher import agent as researcher
    from .planner import agent as planner
    from .strategist import agent as strategist
    return [researcher, strategist, planner, copywriter]


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


def register_editorial_agents() -> None:
    """Registra nel registry globale solo gli agenti locali (non remoti)."""
    for agent in _get_local_agents():
        if not os.environ.get(_AGENT_URL_VARS.get(agent.name, ""), "").strip():
            AgentRegistry.register(agent, group=GROUP)


def build_editorial_orchestrator() -> Orchestrator:
    register_editorial_agents()
    remote_tools = _remote_agent_tools()
    return Orchestrator(
        name="editorial_calendar",
        group=GROUP,
        mission=EDITORIAL_MISSION,
        extra_tools=remote_tools,
    )
