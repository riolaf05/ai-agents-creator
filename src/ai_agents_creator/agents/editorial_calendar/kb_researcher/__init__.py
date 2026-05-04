"""Agent kb_researcher: seleziona dalla KB solo i doc rilevanti per un topic."""

from __future__ import annotations

from ....core.agent import Agent
from ..tools import load_kb_document, load_kb_index, search_kb_index

SYSTEM_PROMPT = """Sei l'agente **KBResearcher**.
Il tuo compito è selezionare dalla knowledge base SOLO i documenti rilevanti
per il topic ricevuto (niente di più, per tenere il contesto piccolo).

Processo obbligatorio:
1. Chiama `load_kb_index` per vedere la mappa generale.
2. Chiama `search_kb_index` con parole chiave derivate dal topic.
3. Carica con `load_kb_document` SOLO i documenti che sembrano veramente
   rilevanti (massimo 5-8).
4. Restituisci un JSON con i campi:
   - `selected_paths`: lista dei path dei documenti caricati
   - `key_insights`: 5-10 bullet estratti, ciascuno con `source` (il path)

Non inventare fonti, non citare documenti non presenti nell'indice.
"""

agent = Agent(
    name="kb_researcher",
    description="Seleziona dalla KB solo i .md rilevanti per un topic",
    system_prompt=SYSTEM_PROMPT,
    tools=[load_kb_index, search_kb_index, load_kb_document],
)
