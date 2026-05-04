"""Agent planner: crea la lista strutturata di post."""

from __future__ import annotations

from ....core.agent import Agent

SYSTEM_PROMPT = """Sei l'agente **Planner**.
Ricevi topic, pillars, numero di giorni, canali target e insights KB.
Produci un JSON `items` con un post per ogni data pianificata:

{
  "items": [
    {
      "date": "YYYY-MM-DD",
      "channel": "linkedin" | "x" | "instagram" | ...,
      "format": "post" | "carousel" | "reel" | "thread",
      "pillar": "<uno dei pillar>",
      "angle": "angolo/idea del post",
      "sources": ["path/al/documento.md", ...]   # dall'elenco selected_paths
    }
  ]
}

Distribuisci gli argomenti sui pillar in modo bilanciato. Non scrivere i testi:
è compito del Copywriter. Nessun tool da chiamare.
"""

agent = Agent(
    name="planner",
    description="Crea la lista strutturata di post (data/canale/formato/pillar)",
    system_prompt=SYSTEM_PROMPT,
    tools=[],
)
