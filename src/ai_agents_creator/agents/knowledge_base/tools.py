"""Tool filesystem per il KB builder.

Volutamente minimali: leggere file, listare directory, scrivere/aggiornare file
markdown. Tutti i tool restringono le operazioni alle directory configurate in
``Settings`` (``kb_input_dir`` e ``kb_output_dir``) per evitare scritture fuori
dall'area di lavoro.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ...config import get_settings
from ...core.tools import Tool, tool

_TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".rst", ".html", ".htm", ".csv", ".json",
    ".log", ".py", ".js", ".ts", ".yaml", ".yml",
}


def _in_allowed_dir(path: Path, allowed: list[Path]) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for base in allowed:
        try:
            resolved.relative_to(base.resolve())
            return True
        except ValueError:
            continue
    return False


@tool(
    description="Elenca i file presenti in KB_INPUT_DIR (ricorsivo) con dimensione e tipo.",
    input_schema={"type": "object", "properties": {}},
)
def list_input_files() -> str:
    settings = get_settings()
    base = settings.kb_input_dir
    if not base.exists():
        return json.dumps({"files": [], "warning": f"{base} non esiste"}, ensure_ascii=False)
    entries = []
    for p in sorted(base.rglob("*")):
        if p.is_file():
            entries.append(
                {
                    "path": str(p.relative_to(base)),
                    "size": p.stat().st_size,
                    "ext": p.suffix.lower(),
                }
            )
    return json.dumps({"base": str(base), "files": entries}, ensure_ascii=False)


@tool(
    description=(
        "Legge il contenuto testuale di un file in KB_INPUT_DIR. "
        "Accetta path relativo alla input dir."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "relative_path": {"type": "string", "description": "Path relativo a KB_INPUT_DIR"},
            "max_chars": {"type": "integer", "description": "Tronca l'output", "default": 12000},
        },
        "required": ["relative_path"],
    },
)
def read_input_file(relative_path: str, max_chars: int = 12000) -> str:
    settings = get_settings()
    target = (settings.kb_input_dir / relative_path).resolve()
    if not _in_allowed_dir(target, [settings.kb_input_dir]):
        return "ERROR: path fuori da KB_INPUT_DIR"
    if not target.exists() or not target.is_file():
        return f"ERROR: file non trovato {relative_path}"
    if target.suffix.lower() not in _TEXT_EXTENSIONS:
        return f"ERROR: estensione non testuale: {target.suffix}"
    content = target.read_text(encoding="utf-8", errors="replace")
    if len(content) > max_chars:
        content = content[:max_chars] + "\n\n...[troncato]..."
    return content


@tool(
    description=(
        "Scrive o sovrascrive un file markdown nella KB sotto "
        "KB_OUTPUT_DIR/categories/<category>/<slug>.md. Crea le directory."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "Categoria (slug in kebab-case)"},
            "slug": {"type": "string", "description": "Slug del file senza estensione"},
            "title": {"type": "string", "description": "Titolo leggibile"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tag del documento",
            },
            "summary": {"type": "string", "description": "Sommario di 1-3 frasi"},
            "body_markdown": {"type": "string", "description": "Corpo markdown del documento"},
            "source_path": {
                "type": "string",
                "description": "Path relativo del file sorgente (opzionale)",
            },
        },
        "required": ["category", "slug", "title", "summary", "body_markdown"],
    },
)
def write_kb_document(
    category: str,
    slug: str,
    title: str,
    summary: str,
    body_markdown: str,
    tags: list[str] | None = None,
    source_path: str | None = None,
) -> str:
    settings = get_settings()
    category_slug = _slugify(category)
    slug = _slugify(slug)
    out_dir = settings.kb_output_dir / "categories" / category_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{slug}.md"
    if not _in_allowed_dir(out_file, [settings.kb_output_dir]):
        return "ERROR: path fuori da KB_OUTPUT_DIR"

    tags = tags or []
    frontmatter = [
        "---",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f"category: {category_slug}",
        f"tags: {json.dumps(tags, ensure_ascii=False)}",
        f"summary: {json.dumps(summary, ensure_ascii=False)}",
    ]
    if source_path:
        frontmatter.append(f"source: {json.dumps(source_path, ensure_ascii=False)}")
    frontmatter.append("---")
    content = "\n".join(frontmatter) + "\n\n# " + title + "\n\n" + body_markdown.strip() + "\n"
    out_file.write_text(content, encoding="utf-8")
    return f"Scritto {out_file.relative_to(settings.kb_output_dir)}"


@tool(
    description=(
        "Scansiona KB_OUTPUT_DIR/categories/** e rigenera INDEX.md con mappa "
        "categorie -> documenti (titolo, tags, summary, path)."
    ),
    input_schema={"type": "object", "properties": {}},
)
def rebuild_index() -> str:
    settings = get_settings()
    base = settings.kb_output_dir
    categories_dir = base / "categories"
    categories_dir.mkdir(parents=True, exist_ok=True)

    sections: list[str] = ["# Knowledge Base Index", ""]
    sections.append("Indice auto-generato. Usa questo file per caricare solo i `.md` rilevanti.")
    sections.append("")

    index_data: list[dict] = []

    for cat_dir in sorted([p for p in categories_dir.iterdir() if p.is_dir()]):
        sections.append(f"## {cat_dir.name}")
        sections.append("")
        for doc in sorted(cat_dir.glob("*.md")):
            meta = _parse_frontmatter(doc.read_text(encoding="utf-8"))
            rel = doc.relative_to(base).as_posix()
            title = meta.get("title") or doc.stem
            summary = meta.get("summary") or ""
            tags = meta.get("tags") or []
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except json.JSONDecodeError:
                    tags = [tags]
            tags_str = ", ".join(tags) if tags else "-"
            sections.append(f"- [{title}]({rel}) — tags: *{tags_str}* — {summary}")
            index_data.append(
                {
                    "category": cat_dir.name,
                    "title": title,
                    "summary": summary,
                    "tags": tags,
                    "path": rel,
                }
            )
        sections.append("")

    (base / "INDEX.md").write_text("\n".join(sections), encoding="utf-8")
    (base / "index.json").write_text(
        json.dumps({"documents": index_data}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return f"Indice rigenerato: {len(index_data)} documenti in {len({d['category'] for d in index_data})} categorie"


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "untitled"


def _parse_frontmatter(text: str) -> dict[str, object]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    block = text[3:end].strip()
    meta: dict[str, object] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        raw = raw.strip()
        try:
            meta[key.strip()] = json.loads(raw)
        except json.JSONDecodeError:
            meta[key.strip()] = raw
    return meta


KB_BUILDER_TOOLS: list[Tool] = [
    list_input_files,
    read_input_file,
    write_kb_document,
    rebuild_index,
]
