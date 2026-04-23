"""Implementazione dell'oggetto ``Agent``.

Un Agent = prompt + modello + tool + (eventualmente) mini-loop agentic che:

1. invia i messaggi a Claude,
2. se Claude chiede di usare un tool lo esegue,
3. rimanda il risultato al modello,
4. ripete finché Claude non produce una risposta finale o si raggiunge il
   limite di iterazioni.

Questo comportamento è volutamente simile al pattern *subagent* di Claude
Code: ogni agente è un executor specializzato e indipendente.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from typing import Any

from ..config import Settings, get_settings
from ..providers.factory import complete
from .tools import Tool

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Risultato finale dell'esecuzione di un agent."""

    output_text: str
    messages: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "output": self.output_text,
            "tool_calls": self.tool_calls,
            "stop_reason": self.stop_reason,
        }


@dataclass
class Agent:
    """Agente specializzato, analogo a un *subagent* di Claude Code."""

    name: str
    description: str
    system_prompt: str
    tools: list[Tool] = field(default_factory=list)
    model: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    max_iterations: int | None = None

    def _tools_payload(self) -> list[dict[str, Any]]:
        return [t.to_anthropic() for t in self.tools]

    def _find_tool(self, name: str) -> Tool | None:
        for t in self.tools:
            if t.name == name:
                return t
        return None

    def run(
        self,
        user_input: str | list[dict[str, Any]],
        *,
        settings: Settings | None = None,
    ) -> AgentResult:
        """Esegue l'agente su un input utente e restituisce la risposta.

        ``user_input`` può essere una stringa (un singolo turno user) o una
        lista già formata di messaggi (history multi-turno).
        """
        settings = settings or get_settings()
        max_iters = self.max_iterations or settings.agent_max_iterations

        messages: list[dict[str, Any]]
        if isinstance(user_input, str):
            messages = [{"role": "user", "content": user_input}]
        else:
            messages = list(user_input)

        tool_calls_log: list[dict[str, Any]] = []
        final_text = ""
        stop_reason: str | None = None

        for iteration in range(max_iters):
            if settings.agent_progress:
                print(
                    f"[progress] agent={self.name} round={iteration + 1}/{max_iters}",
                    file=sys.stderr,
                    flush=True,
                )
            response = complete(
                messages=messages,
                system=self.system_prompt,
                tools=self._tools_payload() or None,
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                settings=settings,
            )
            stop_reason = getattr(response, "stop_reason", None)
            assistant_content = [
                _block_to_dict(block) for block in response.content
            ]
            messages.append({"role": "assistant", "content": assistant_content})

            tool_uses = [b for b in response.content if getattr(b, "type", None) == "tool_use"]

            if not tool_uses:
                final_text = _extract_text(response.content)
                break

            if settings.agent_progress:
                names = ", ".join(tu.name for tu in tool_uses)
                print(
                    f"[progress] agent={self.name} esegue tool: {names}",
                    file=sys.stderr,
                    flush=True,
                )

            tool_results_content: list[dict[str, Any]] = []
            for tu in tool_uses:
                tool_name = tu.name
                tool_input = tu.input or {}
                tool_obj = self._find_tool(tool_name)
                if tool_obj is None:
                    result_text = f"ERROR: tool '{tool_name}' non registrato"
                    is_error = True
                else:
                    try:
                        raw = tool_obj.run(**tool_input)
                        result_text = _to_text(raw)
                        is_error = False
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("Tool %s ha sollevato eccezione", tool_name)
                        result_text = f"ERROR: {exc}"
                        is_error = True

                tool_calls_log.append(
                    {
                        "iteration": iteration,
                        "tool": tool_name,
                        "input": tool_input,
                        "output": result_text,
                        "is_error": is_error,
                    }
                )
                tool_results_content.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": result_text,
                        "is_error": is_error,
                    }
                )

            messages.append({"role": "user", "content": tool_results_content})
        else:
            logger.warning("Agent %s ha raggiunto max_iterations=%d", self.name, max_iters)
            final_text = _extract_text_from_messages(messages)

        return AgentResult(
            output_text=final_text,
            messages=messages,
            tool_calls=tool_calls_log,
            stop_reason=stop_reason,
        )


def _extract_text(content_blocks: list[Any]) -> str:
    chunks: list[str] = []
    for block in content_blocks:
        if getattr(block, "type", None) == "text":
            chunks.append(block.text)
    return "\n".join(chunks).strip()


def _extract_text_from_messages(messages: list[dict[str, Any]]) -> str:
    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [
                c.get("text", "")
                for c in content
                if isinstance(c, dict) and c.get("type") == "text"
            ]
            if parts:
                return "\n".join(parts).strip()
    return ""


def _block_to_dict(block: Any) -> dict[str, Any]:
    btype = getattr(block, "type", None)
    if btype == "text":
        return {"type": "text", "text": block.text}
    if btype == "tool_use":
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input,
        }
    if hasattr(block, "model_dump"):
        return block.model_dump()
    return {"type": btype or "unknown"}


def _to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        return str(value)
