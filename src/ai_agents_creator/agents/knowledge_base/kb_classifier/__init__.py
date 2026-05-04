"""Agent kb_classifier: assegna category, tags, title, summary a un contenuto."""

from __future__ import annotations

from ....core.agent import Agent
from ..tools import list_input_files, read_input_file

SYSTEM_PROMPT = """Sei l'agente **Classifier** della knowledge base.
Ricevi un testo pulito (o un path da leggere) e devi produrre:

- `category`: una categoria di alto livello in kebab-case (es. "ai-agents",
  "product-management", "python"). Riusa categorie esistenti se sensato.
- `tags`: 3-8 tag specifici in kebab-case.
- `title`: titolo naturale.
- `summary`: 1-3 frasi che descrivono il contenuto.

Puoi usare `read_input_file` e `list_input_files` se ti serve leggere.
Output finale: JSON puro con i campi sopra.
"""

agent = Agent(
    name="kb_classifier",
    description="Assegna category, tags, title, summary a un contenuto",
    system_prompt=SYSTEM_PROMPT,
    tools=[read_input_file, list_input_files],
)
