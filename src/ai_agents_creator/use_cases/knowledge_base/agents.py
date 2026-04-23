"""Agenti specializzati per il KB builder."""

from __future__ import annotations

from ...core.agent import Agent
from ...core.registry import AgentRegistry
from .tools import (
    list_input_files,
    read_input_file,
    rebuild_index,
    write_kb_document,
)

GROUP = "knowledge_base"


READER_PROMPT = """Sei l'agente **Reader** della knowledge base.
Ricevi un path relativo (o il compito di scoprire i file) e devi produrre
un estratto pulito del contenuto, rimuovendo boilerplate (menu, footer, tag
HTML inutili) e mantenendo il senso del testo. Non inventare nulla.

Usa i tool:
- `list_input_files` per scoprire i file
- `read_input_file` per leggerli

Output finale: JSON con campi {source, raw_title?, clean_text, language?}.
"""

CLASSIFIER_PROMPT = """Sei l'agente **Classifier** della knowledge base.
Ricevi un testo pulito (o un path da leggere) e devi produrre:

- `category`: una categoria di alto livello in kebab-case (es. "ai-agents",
  "product-management", "python"). Riusa categorie esistenti se sensato.
- `tags`: 3-8 tag specifici in kebab-case.
- `title`: titolo naturale.
- `summary`: 1-3 frasi che descrivono il contenuto.

Puoi usare `read_input_file` e `list_input_files` se ti serve leggere.
Output finale: JSON puro con i campi sopra.
"""

WRITER_PROMPT = """Sei l'agente **Writer** della knowledge base.
Ricevi metadata (title, category, tags, summary) + testo pulito e devi:

1. Riformattare il testo in markdown chiaro con intestazioni, liste, esempi.
2. Invocare `write_kb_document` passando: category, slug (kebab-case derivato
   dal titolo), title, tags, summary, body_markdown, source_path.

Conferma alla fine il path del file creato.
"""

INDEXER_PROMPT = """Sei l'agente **Indexer** della knowledge base.
Il tuo unico compito è invocare `rebuild_index` e riportare il risultato.
Non modificare documenti: occupati solo dell'indice.
"""


def build_kb_agents() -> list[Agent]:
    reader = Agent(
        name="kb_reader",
        description="Legge file dalla input dir e produce testo pulito in JSON",
        system_prompt=READER_PROMPT,
        tools=[list_input_files, read_input_file],
    )
    classifier = Agent(
        name="kb_classifier",
        description="Assegna category, tags, title, summary a un contenuto",
        system_prompt=CLASSIFIER_PROMPT,
        tools=[read_input_file, list_input_files],
    )
    writer = Agent(
        name="kb_writer",
        description="Scrive il documento markdown definitivo nella KB",
        system_prompt=WRITER_PROMPT,
        tools=[write_kb_document],
    )
    indexer = Agent(
        name="kb_indexer",
        description="Rigenera INDEX.md e index.json della knowledge base",
        system_prompt=INDEXER_PROMPT,
        tools=[rebuild_index],
    )
    return [reader, classifier, writer, indexer]


def register_kb_agents() -> None:
    AgentRegistry.register_many(build_kb_agents(), group=GROUP)
