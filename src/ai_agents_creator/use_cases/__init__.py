"""Bootstrap centralizzato degli use case: registra agenti + orchestrator."""

from __future__ import annotations

from ..a2a.server import register_orchestrator


_BOOTSTRAPPED = False


def bootstrap_all() -> None:
    """Registra tutti gli agenti e gli orchestrator dei due use case built-in.

    Idempotente: chiamarlo più volte non crea duplicati.
    """
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    from .knowledge_base.orchestrator import build_kb_orchestrator
    from .editorial_calendar.orchestrator import build_editorial_orchestrator

    register_orchestrator(build_kb_orchestrator())
    register_orchestrator(build_editorial_orchestrator())

    _BOOTSTRAPPED = True


__all__ = ["bootstrap_all"]
