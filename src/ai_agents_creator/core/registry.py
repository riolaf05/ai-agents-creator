"""Registry globale degli agenti.

Permette di registrare agenti una volta sola e poi recuperarli per nome dall'
orchestrator, dai webhook e dal server A2A. Supporta anche "gruppi" (utile per
raggruppare gli agenti di uno stesso use case).
"""

from __future__ import annotations

from typing import Iterable

from .agent import Agent


class AgentRegistry:
    _agents: dict[str, Agent] = {}
    _groups: dict[str, list[str]] = {}

    @classmethod
    def register(cls, agent: Agent, *, group: str | None = None) -> None:
        cls._agents[agent.name] = agent
        if group:
            cls._groups.setdefault(group, [])
            if agent.name not in cls._groups[group]:
                cls._groups[group].append(agent.name)

    @classmethod
    def register_many(cls, agents: Iterable[Agent], *, group: str | None = None) -> None:
        for a in agents:
            cls.register(a, group=group)

    @classmethod
    def get(cls, name: str) -> Agent:
        if name not in cls._agents:
            raise KeyError(
                f"Agent '{name}' non registrato. Registrati: {list(cls._agents)}"
            )
        return cls._agents[name]

    @classmethod
    def list(cls, group: str | None = None) -> list[Agent]:
        if group is None:
            return list(cls._agents.values())
        names = cls._groups.get(group, [])
        return [cls._agents[n] for n in names if n in cls._agents]

    @classmethod
    def clear(cls) -> None:
        cls._agents.clear()
        cls._groups.clear()
