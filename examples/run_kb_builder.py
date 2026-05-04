"""Esempio: esegue il KB builder sulla cartella KB_INPUT_DIR.

Uso:
    python examples/run_kb_builder.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Permette di eseguire lo script senza `pip install -e .`
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

# Prima di caricare Settings: mostra avanzamento LLM su stderr (vedi AGENT_PROGRESS in .env)
os.environ.setdefault("AGENT_PROGRESS", "1")

from ai_agents_creator.config import get_settings  # noqa: E402
from ai_agents_creator.agents.knowledge_base import build_kb_orchestrator  # noqa: E402


def main() -> int:
    settings = get_settings()
    print(f"[provider={settings.provider}] [model={settings.model_id}]")
    print(f"Input dir : {settings.kb_input_dir.resolve()}")
    print(f"Output dir: {settings.kb_output_dir.resolve()}")
    print(
        "\nOrchestrator in esecuzione: molte chiamate a Bedrock (orchestrator + "
        "subagent + tool). La prima risposta può richiedere anche 1–2 minuti; "
        "non è bloccato se non compaiono errori.\n",
        flush=True,
    )

    orch = build_kb_orchestrator()
    task = (
        "Scansiona tutti i file presenti in KB_INPUT_DIR, aggiorna la knowledge "
        "base markdown in KB_OUTPUT_DIR categorizzando i contenuti e rigenera "
        "INDEX.md al termine. Riporta un riepilogo dei documenti creati."
    )
    result = orch.run(task)

    print("\n========== OUTPUT ORCHESTRATOR ==========\n")
    print(result.output_text)
    print(f"\n(tool calls: {len(result.tool_calls)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
