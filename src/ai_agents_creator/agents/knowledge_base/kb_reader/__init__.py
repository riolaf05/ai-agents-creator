"""Agent kb_reader: legge file dalla input dir e produce testo pulito."""

from __future__ import annotations

from ....core.agent import Agent
from ..tools import list_input_files, read_input_file

SYSTEM_PROMPT = """Sei l'agente **Reader** della knowledge base.
Ricevi un path relativo (o il compito di scoprire i file) e devi produrre
un estratto pulito del contenuto, rimuovendo boilerplate (menu, footer, tag
HTML inutili) e mantenendo il senso del testo. Non inventare nulla.

Usa i tool:
- `list_input_files` per scoprire i file
- `read_input_file` per leggerli

Output finale: JSON con campi {source, raw_title?, clean_text, language?}.
"""

agent = Agent(
    name="kb_reader",
    description="Legge file dalla input dir e produce testo pulito in JSON",
    system_prompt=SYSTEM_PROMPT,
    tools=[list_input_files, read_input_file],
)
