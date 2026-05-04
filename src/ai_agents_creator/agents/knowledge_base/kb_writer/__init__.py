"""Agent kb_writer: scrive il documento markdown definitivo nella KB."""

from __future__ import annotations

from ....core.agent import Agent
from ..tools import write_kb_document

SYSTEM_PROMPT = """Sei l'agente **Writer** della knowledge base.
Ricevi metadata (title, category, tags, summary) + testo pulito e devi:

1. Riformattare il testo in markdown chiaro con intestazioni, liste, esempi.
2. Invocare `write_kb_document` passando: category, slug (kebab-case derivato
   dal titolo), title, tags, summary, body_markdown, source_path.

Conferma alla fine il path del file creato.
"""

agent = Agent(
    name="kb_writer",
    description="Scrive il documento markdown definitivo nella KB",
    system_prompt=SYSTEM_PROMPT,
    tools=[write_kb_document],
)
