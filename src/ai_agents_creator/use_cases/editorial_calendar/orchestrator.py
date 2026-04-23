"""Orchestrator del calendario editoriale."""

from __future__ import annotations

from ...core.orchestrator import Orchestrator
from .agents import GROUP, register_editorial_agents


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


def build_editorial_orchestrator() -> Orchestrator:
    register_editorial_agents()
    return Orchestrator(
        name="editorial_calendar",
        group=GROUP,
        mission=EDITORIAL_MISSION,
    )
