"""Agent strategist: definisce audience, pillar, tone, obiettivi."""

from __future__ import annotations

from ....core.agent import Agent

SYSTEM_PROMPT = """Sei l'agente **Strategist**.
Ricevi topic + insights dalla KB e definisci:
- `audience`
- `pillars`: 3-5 pillar tematici
- `tone_of_voice`
- `objectives`: 2-3 obiettivi misurabili

Output JSON con i campi sopra. Nessun tool da chiamare.
"""

agent = Agent(
    name="strategist",
    description="Definisce audience, pillar, tone, obiettivi",
    system_prompt=SYSTEM_PROMPT,
    tools=[],
)
