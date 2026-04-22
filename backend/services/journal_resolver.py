"""Journal style resolver: preset JSON + Gemma 4 fallback via Ollama."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
import httpx
from pydantic import BaseModel

STYLES_DIR = Path(__file__).parent.parent / "journal_styles"
CACHE_DIR = STYLES_DIR / "cached"


class JournalStyle(BaseModel):
    name: str
    key: str
    font_family: str
    font_size: float
    line_width: float
    figure_width_mm: float
    figure_height_mm: float
    dpi: int
    legend_frameon: bool
    color_cycle: list[str]
    spine_linewidth: float
    tick_direction: str
    tick_labelsize: float
    axes_labelsize: float
    title_size: float
    pad_inches: float


def _normalize_key(name: str) -> str:
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    return name


def load_preset(journal_key: str) -> dict | None:
    """Loads a preset by exact key match. Returns None if not found."""
    json_path = STYLES_DIR / f"{journal_key}.json"
    if json_path.exists():
        return json.loads(json_path.read_text())

    for p in STYLES_DIR.glob("*.json"):
        if p.parent == CACHE_DIR:
            continue
        try:
            data = json.loads(p.read_text())
            if data.get("key") == journal_key:
                return data
        except (json.JSONDecodeError, KeyError):
            continue

    return None


def _fuzzy_match(journal_name: str) -> dict | None:
    normalized = _normalize_key(journal_name)
    best_score = 0
    best_match = None

    for p in STYLES_DIR.glob("*.json"):
        if p.parent == CACHE_DIR:
            continue
        try:
            data = json.loads(p.read_text())
        except (json.JSONDecodeError, KeyError):
            continue

        candidate_key = data.get("key", "")
        candidate_name = _normalize_key(data.get("name", ""))

        def bigrams(s: str) -> set[str]:
            return {s[i: i + 2] for i in range(len(s) - 1)}

        target_bi = bigrams(normalized)
        key_bi = bigrams(candidate_key)
        name_bi = bigrams(candidate_name)

        score = len(target_bi & (key_bi | name_bi))
        if score > best_score:
            best_score = score
            best_match = data

    return best_match if best_score >= 2 else None


def _call_gemma4(journal_name: str, model: str) -> dict:
    schema = JournalStyle.model_json_schema()

    prompt = (
        f"You are a scientific publishing expert. Generate matplotlib figure style parameters "
        f"for the journal '{journal_name}'. "
        f"Base your answer on the journal's official author guidelines for figure formatting. "
        f"Return ONLY a valid JSON object matching this schema: {json.dumps(schema)}"
    )

    response = httpx.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "format": schema,
            "stream": False,
        },
        timeout=60.0,
    )
    response.raise_for_status()

    result_text = response.json().get("response", "{}")
    style_data = json.loads(result_text)
    validated = JournalStyle(**style_data)
    return validated.model_dump()


def resolve_journal(
    journal_name: str,
    model: str = "gemma4:e4b",
) -> dict:
    """Resolution order: exact key -> fuzzy match -> Gemma 4 (cached)."""
    key = _normalize_key(journal_name)
    preset = load_preset(key)
    if preset:
        return preset

    fuzzy = _fuzzy_match(journal_name)
    if fuzzy:
        return fuzzy

    # Check Gemma 4 cache
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())

    # Call Gemma 4
    style = _call_gemma4(journal_name, model)
    cache_file.write_text(json.dumps(style, indent=2))
    return style


def apply_to_figure(fig: matplotlib.figure.Figure, style: dict) -> None:
    """Applies journal style to a matplotlib figure in-place."""
    MM_TO_INCH = 1 / 25.4
    w_mm = style.get("figure_width_mm", 88)
    h_mm = style.get("figure_height_mm", 66)
    fig.set_size_inches(w_mm * MM_TO_INCH, h_mm * MM_TO_INCH)

    font_size = style.get("font_size", 8)
    line_width = style.get("line_width", 1.0)
    color_cycle = style.get("color_cycle", ["#000000"])
    spine_lw = style.get("spine_linewidth", 0.5)
    tick_dir = style.get("tick_direction", "in")

    for ax in fig.get_axes():
        ax.tick_params(
            direction=tick_dir,
            labelsize=style.get("tick_labelsize", font_size - 1),
        )
        ax.xaxis.label.set_size(style.get("axes_labelsize", font_size))
        ax.yaxis.label.set_size(style.get("axes_labelsize", font_size))
        ax.title.set_size(style.get("title_size", font_size))
        for spine in ax.spines.values():
            spine.set_linewidth(spine_lw)
        ax.set_prop_cycle(color=color_cycle)
        for line in ax.get_lines():
            line.set_linewidth(line_width)

    if not style.get("legend_frameon", False):
        for ax in fig.get_axes():
            leg = ax.get_legend()
            if leg:
                leg.set_frame_on(False)
