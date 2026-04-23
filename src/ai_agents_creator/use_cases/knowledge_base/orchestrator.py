"""Orchestrator del KB builder."""

from __future__ import annotations

from ...core.orchestrator import Orchestrator
from .agents import GROUP, register_kb_agents


KB_MISSION = """Mantenere aggiornata la knowledge base markdown:
1. Scoprire i file di input in KB_INPUT_DIR.
2. Per ogni file nuovo o modificato:
   - delegare a `kb_reader` per ottenere testo pulito,
   - delegare a `kb_classifier` per category/tags/title/summary,
   - delegare a `kb_writer` per scrivere il .md nella categoria giusta.
3. Alla fine delegare a `kb_indexer` per rigenerare INDEX.md e index.json.
4. Riportare un riepilogo dei file creati/aggiornati e categorie usate.
"""


def build_kb_orchestrator() -> Orchestrator:
    register_kb_agents()
    return Orchestrator(
        name="knowledge_base",
        group=GROUP,
        mission=KB_MISSION,
    )
