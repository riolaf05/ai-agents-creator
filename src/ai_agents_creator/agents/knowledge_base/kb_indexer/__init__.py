"""Agent kb_indexer: rigenera INDEX.md e index.json della knowledge base."""

from __future__ import annotations

from ....core.agent import Agent
from ..tools import rebuild_index

SYSTEM_PROMPT = """Sei l'agente **Indexer** della knowledge base.
Il tuo unico compito è invocare `rebuild_index` e riportare il risultato.
Non modificare documenti: occupati solo dell'indice.
"""

agent = Agent(
    name="kb_indexer",
    description="Rigenera INDEX.md e index.json della knowledge base",
    system_prompt=SYSTEM_PROMPT,
    tools=[rebuild_index],
)
