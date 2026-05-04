"""Backward-compat: re-export da agents/."""

from ..agents import bootstrap_all  # noqa: F401

__all__ = ["bootstrap_all"]
