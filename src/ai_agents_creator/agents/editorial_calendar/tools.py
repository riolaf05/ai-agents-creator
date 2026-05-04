"""Tool di interrogazione della KB + salvataggio calendario editoriale.

Il pattern chiave richiesto: gli agenti **non** caricano l'intera KB. Leggono
prima ``INDEX.md`` (o ``index.json``) e poi **solo** i `.md` delle categorie
rilevanti. Questo è fondamentale per mantenere il contesto sotto controllo
anche con KB grandi.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ...config import get_settings
from ...core.tools import Tool, tool


def _read_index() -> list[dict]:
    settings = get_settings()
    index_json = settings.kb_output_dir / "index.json"
    if not index_json.exists():
        return []
    data = json.loads(index_json.read_text(encoding="utf-8"))
    return data.get("documents", [])


@tool(
    description=(
        "Restituisce l'indice della knowledge base: lista di documenti con "
        "category, title, tags, summary, path. NON carica il contenuto completo."
    ),
    input_schema={"type": "object", "properties": {}},
)
def load_kb_index() -> str:
    docs = _read_index()
    return json.dumps({"documents": docs}, ensure_ascii=False)


@tool(
    description=(
        "Cerca nell'indice i documenti rilevanti rispetto a parole chiave "
        "(match su title/tags/summary/category). Ritorna solo i metadata."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Parole chiave del topic",
            },
            "categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Opzionale: limita a queste categorie",
            },
            "limit": {"type": "integer", "default": 20},
        },
        "required": ["keywords"],
    },
)
def search_kb_index(
    keywords: list[str],
    categories: list[str] | None = None,
    limit: int = 20,
) -> str:
    kws = [k.lower() for k in keywords if k]
    cats = set((categories or []))
    results: list[tuple[int, dict]] = []
    for doc in _read_index():
        if cats and doc.get("category") not in cats:
            continue
        hay = " ".join(
            [
                str(doc.get("title", "")),
                str(doc.get("summary", "")),
                str(doc.get("category", "")),
                " ".join(doc.get("tags", []) or []),
            ]
        ).lower()
        score = sum(1 for k in kws if k in hay)
        if score > 0:
            results.append((score, doc))
    results.sort(key=lambda x: -x[0])
    out = [doc for _, doc in results[:limit]]
    return json.dumps({"matches": out}, ensure_ascii=False)


@tool(
    description=(
        "Carica il contenuto completo di uno specifico documento della KB "
        "dato il suo path (relativo a KB_OUTPUT_DIR)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path come riportato nell'indice"},
            "max_chars": {"type": "integer", "default": 8000},
        },
        "required": ["path"],
    },
)
def load_kb_document(path: str, max_chars: int = 8000) -> str:
    settings = get_settings()
    target = (settings.kb_output_dir / path).resolve()
    try:
        target.relative_to(settings.kb_output_dir.resolve())
    except ValueError:
        return "ERROR: path fuori dalla KB"
    if not target.exists() or target.suffix != ".md":
        return f"ERROR: documento non trovato: {path}"
    text = target.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n...[troncato]..."
    return text


@tool(
    description=(
        "Salva il calendario editoriale finale. Produce editorial_calendar.md "
        "(leggibile) ed editorial_calendar.json (strutturato) in "
        "EDITORIAL_OUTPUT_DIR."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "items": {
                "type": "array",
                "description": "Lista dei post del calendario",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "YYYY-MM-DD"},
                        "channel": {
                            "type": "string",
                            "description": "linkedin | x | instagram | ...",
                        },
                        "format": {
                            "type": "string",
                            "description": "post | carousel | reel | thread | ...",
                        },
                        "pillar": {"type": "string"},
                        "hook": {"type": "string"},
                        "body": {"type": "string"},
                        "cta": {"type": "string"},
                        "hashtags": {"type": "array", "items": {"type": "string"}},
                        "sources": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Path dei .md della KB usati",
                        },
                    },
                    "required": ["date", "channel", "hook", "body"],
                },
            },
        },
        "required": ["topic", "items"],
    },
)
def save_editorial_calendar(topic: str, items: list[dict]) -> str:
    settings = get_settings()
    out_dir = settings.editorial_output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"calendar_{timestamp}.json"
    md_path = out_dir / f"calendar_{timestamp}.md"

    payload = {
        "topic": topic,
        "generated_at": timestamp,
        "items": items,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [f"# Calendario editoriale - {topic}", "", f"Generato: {timestamp}", ""]
    for item in items:
        md_lines.append(f"## {item.get('date', '?')} · {item.get('channel', '?')}")
        if item.get("pillar"):
            md_lines.append(f"- **Pillar**: {item['pillar']}")
        if item.get("format"):
            md_lines.append(f"- **Formato**: {item['format']}")
        md_lines.append(f"- **Hook**: {item.get('hook', '')}")
        md_lines.append("")
        md_lines.append(item.get("body", ""))
        md_lines.append("")
        if item.get("cta"):
            md_lines.append(f"**CTA**: {item['cta']}")
        if item.get("hashtags"):
            md_lines.append("**Hashtag**: " + " ".join(f"#{h.lstrip('#')}" for h in item["hashtags"]))
        if item.get("sources"):
            md_lines.append("**Fonti KB**: " + ", ".join(item["sources"]))
        md_lines.append("")
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return json.dumps(
        {
            "markdown": str(md_path),
            "json": str(json_path),
            "items_count": len(items),
        },
        ensure_ascii=False,
    )


EDITORIAL_TOOLS: list[Tool] = [
    load_kb_index,
    search_kb_index,
    load_kb_document,
    save_editorial_calendar,
]
