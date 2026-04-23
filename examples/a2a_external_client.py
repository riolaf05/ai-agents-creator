"""Esempio A2A: come comunicare con agenti (locali o remoti) via protocollo A2A.

Scenari mostrati:

1. Elencare gli agenti esposti dal server (`/a2a/agents`).
2. Invocare un orchestrator locale via A2A come se fosse remoto.
3. Creare un `Agent` che usa un `a2a_tool` per chiamare un agente esterno.

Prima di eseguirlo avvia il server:

    uvicorn ai_agents_creator.triggers.webhook:app --reload

poi in un altro terminale:

    python examples/a2a_external_client.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ai_agents_creator.a2a import A2AClient, a2a_tool  # noqa: E402
from ai_agents_creator.core import Agent  # noqa: E402


BASE_URL = "http://localhost:8000"


def demo_1_list_agents() -> None:
    client = A2AClient(base_url=BASE_URL)
    cards = client.list_agents()
    print("Agenti esposti dal server:")
    for c in cards:
        print(f"- {c.name}: {c.description}  [skills: {', '.join(c.skills[:5])}]")


def demo_2_invoke_orchestrator_remotely() -> None:
    client = A2AClient(base_url=BASE_URL, sender="partner-system")
    resp = client.invoke_orchestrator(
        "editorial_calendar",
        task="Crea un mini calendario di 3 post su 'AI agents' per LinkedIn",
        context={"days": 3, "channels": ["linkedin"]},
    )
    print("Risposta orchestrator editorial_calendar:")
    print(json.dumps(resp.model_dump(), ensure_ascii=False, indent=2))


def demo_3_local_agent_using_remote_a2a_tool() -> None:
    """Mostra come un nostro agent può CHIAMARE un agente esterno.

    Qui usiamo come "agente esterno" lo stesso server locale, ma in produzione
    BASE_URL sarà l'endpoint del partner (es. https://partner.com).
    """
    translator_tool = a2a_tool(
        tool_name="ask_external_summarizer",
        description=(
            "Invia un testo all'agente esterno `kb_classifier` e ricevi "
            "categoria/tag/summary"
        ),
        base_url=BASE_URL,
        remote_agent="kb_classifier",
        is_orchestrator=False,
    )
    my_agent = Agent(
        name="meta_writer",
        description="Scrive un mini-post dopo aver chiesto al classifier esterno",
        system_prompt=(
            "Sei un copywriter. Prima usa `ask_external_summarizer` per capire "
            "categoria/tag del testo fornito, poi scrivi un post di 3 frasi "
            "citando la categoria identificata."
        ),
        tools=[translator_tool],
    )
    result = my_agent.run(
        "Testo: 'Gli AI agents stanno cambiando il modo di costruire automazioni "
        "complesse, combinando LLM e tool MCP.'"
    )
    print("\nRisposta meta_writer (che ha chiamato un agente esterno via A2A):")
    print(result.output_text)


if __name__ == "__main__":
    print("== Demo 1: list_agents ==")
    demo_1_list_agents()
    print("\n== Demo 2: invoke orchestrator via A2A ==")
    demo_2_invoke_orchestrator_remotely()
    print("\n== Demo 3: local agent usa a2a_tool per chiamare un agente esterno ==")
    demo_3_local_agent_using_remote_a2a_tool()
