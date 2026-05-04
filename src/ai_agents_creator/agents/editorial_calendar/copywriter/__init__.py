"""Agent copywriter: scrive hook/body/cta/hashtag per ogni post e salva il calendario."""

from __future__ import annotations

from ....core.agent import Agent
from ..tools import save_editorial_calendar

SYSTEM_PROMPT = """Sei l'agente **Copywriter**.
Ricevi gli `items` pianificati + insights KB e per ciascuno scrivi:
- `hook` (prima riga forte)
- `body` (testo completo adatto al canale)
- `cta`
- `hashtags` (5-10)

Importante: quando scrivi un post cita nel body SOLO informazioni supportate
dagli insights forniti (no allucinazioni). Alla fine chiama il tool
`save_editorial_calendar(topic, items)` passando la lista completa arricchita
con hook/body/cta/hashtags (mantieni i campi date/channel/format/pillar/sources).

Riporta in chiusura il path del file creato.
"""

agent = Agent(
    name="copywriter",
    description="Scrive hook/body/cta/hashtag per ogni post e salva il calendario",
    system_prompt=SYSTEM_PROMPT,
    tools=[save_editorial_calendar],
)
