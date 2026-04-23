"""Definizione dei Tool utilizzabili dagli agenti.

I tool sono funzioni Python decorate con ``@tool`` oppure istanze di ``Tool``.
Ogni tool espone:

* ``name``          -> nome esposto al modello
* ``description``   -> descrizione naturale
* ``input_schema``  -> JSON schema (stile Anthropic tool use)
* ``run(**kwargs)`` -> esecuzione sincrona

La conversione verso il formato richiesto dall'SDK Anthropic avviene in
``to_anthropic()``.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Tool:
    """Wrapper di una funzione Python che un agente può invocare."""

    name: str
    description: str
    input_schema: dict[str, Any]
    func: Callable[..., Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def run(self, **kwargs: Any) -> Any:
        return self.func(**kwargs)

    def to_anthropic(self) -> dict[str, Any]:
        """Formato atteso dall'SDK Anthropic per il parametro ``tools``."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


def tool(
    name: str | None = None,
    *,
    description: str | None = None,
    input_schema: dict[str, Any] | None = None,
) -> Callable[[Callable[..., Any]], Tool]:
    """Decoratore per trasformare una funzione Python in ``Tool``.

    Se ``input_schema`` non è specificato viene costruito un JSON schema molto
    semplice ispezionando la firma della funzione (solo str / int / float /
    bool / list / dict). Per schemi più precisi passare esplicitamente uno
    schema.
    """

    def decorator(func: Callable[..., Any]) -> Tool:
        final_name = name or func.__name__
        final_desc = description or (func.__doc__ or final_name).strip().splitlines()[0]
        final_schema = input_schema or _schema_from_signature(func)
        return Tool(
            name=final_name,
            description=final_desc,
            input_schema=final_schema,
            func=func,
        )

    return decorator


_TYPE_MAP: dict[Any, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _schema_from_signature(func: Callable[..., Any]) -> dict[str, Any]:
    sig = inspect.signature(func)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for pname, param in sig.parameters.items():
        if pname in ("self", "cls"):
            continue
        json_type = _TYPE_MAP.get(param.annotation, "string")
        properties[pname] = {"type": json_type, "description": f"Parametro {pname}"}
        if param.default is inspect.Parameter.empty:
            required.append(pname)
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema
