"""Esempio: crea un calendario editoriale da un topic + canali.

Uso:
    python examples/run_editorial_calendar.py --topic "AI agents" --days 14 \
        --channels linkedin,x
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

os.environ.setdefault("AGENT_PROGRESS", "1")

from ai_agents_creator.config import get_settings  # noqa: E402
from ai_agents_creator.agents.editorial_calendar import (  # noqa: E402
    build_editorial_orchestrator,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True, help="Topic del piano")
    parser.add_argument("--days", type=int, default=14, help="Quanti giorni coprire")
    parser.add_argument("--channels", default="linkedin,x", help="Canali comma-separated")
    args = parser.parse_args()

    channels = [c.strip() for c in args.channels.split(",") if c.strip()]

    settings = get_settings()
    print(f"[provider={settings.provider}] [model={settings.model_id}]")
    print(f"KB dir   : {settings.kb_output_dir.resolve()}")
    print(f"Output   : {settings.editorial_output_dir.resolve()}")
    print(
        "\nOrchestrator in esecuzione (molte chiamate LLM); la prima risposta "
        "può richiedere 1–2 minuti. Vedi righe [progress] su stderr.\n",
        flush=True,
    )

    orch = build_editorial_orchestrator()
    task = (
        f"Crea un calendario editoriale sul topic '{args.topic}' coprendo "
        f"{args.days} giorni a partire da oggi. Canali: {', '.join(channels)}. "
        "Usa gli agenti in sequenza: kb_researcher -> strategist -> planner -> "
        "copywriter. Salva il file finale via save_editorial_calendar."
    )
    result = orch.run(task)

    print("\n========== OUTPUT ORCHESTRATOR ==========\n")
    print(result.output_text)
    print(f"\n(tool calls: {len(result.tool_calls)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
