"""Load domain knowledge from ~/.hw_graph/knowledge/*.md at runtime.

Knowledge files are Markdown documents that get injected into the LLM
system prompt. They can be edited in Obsidian vault and changes take
effect without restarting the server.
"""
from __future__ import annotations

from pathlib import Path

KNOWLEDGE_DIR = Path("~/.hw_graph/knowledge").expanduser()


def load_knowledge() -> str:
    """Read all .md files from the knowledge directory and concatenate."""
    if not KNOWLEDGE_DIR.is_dir():
        return ""

    parts: list[str] = []
    for md_file in sorted(KNOWLEDGE_DIR.glob("*.md")):
        try:
            parts.append(md_file.read_text(encoding="utf-8"))
        except Exception:
            continue

    return "\n\n".join(parts)


# In-memory cache of uploaded CSV columns: {path: [col1, col2, ...]}
_csv_column_cache: dict[str, list[str]] = {}


def register_csv_columns(path: str, columns: list[str]) -> None:
    """Store CSV column names for LLM context injection."""
    _csv_column_cache[path] = columns


def get_all_csv_columns() -> dict[str, list[str]]:
    """Return all registered CSV column maps."""
    return dict(_csv_column_cache)


def get_csv_columns_text() -> str:
    """Format registered CSV columns as text for LLM prompt injection."""
    if not _csv_column_cache:
        return ""

    lines = ["## Currently Loaded CSV Files"]
    for path, cols in _csv_column_cache.items():
        name = Path(path).name
        lines.append(f"\n### {name}")
        lines.append(f"Columns ({len(cols)}): {', '.join(cols)}")
    return "\n".join(lines)
