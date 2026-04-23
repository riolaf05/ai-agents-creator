"""Avvia il server webhook + A2A con uvicorn da codice.

Equivalente a:
    uvicorn ai_agents_creator.triggers.webhook:app --reload --port 8000
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import uvicorn  # noqa: E402


if __name__ == "__main__":
    uvicorn.run(
        "ai_agents_creator.triggers.webhook:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
