"""
/api/claude/complete — Phase 2C tool_use.

Claude Haiku 4.5 now acts as a workspace agent. It can reply in plain
prose OR emit structured `tool_use` blocks that the frontend dispatches
to Zustand actions — the "말로 그래프 만들기" flow.

Available tools (all operate on the active workspace):
    add_graph_cell      { template, preset?, variant?, stride_avg? }
    add_compute_cell    { metric }
    add_stat_cell       { op, a_col, b_col?, paired? }
    apply_recipe        { }                 → re-runs default recipes
    set_journal_preset  { preset }           → flips current preset
    set_mode            { mode }             → "quick" | "pub"
    run_all             { }                  → re-renders every bound cell
    export_bundle       { format?, variant? }

Korean in → Korean reply. English in → English reply. Model: Haiku 4.5.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.config import (
    LLM_PROVIDER, ANTHROPIC_API_KEY, ANTHROPIC_MODEL, ANTHROPIC_MAX_TOKENS,
)


router = APIRouter(prefix="/api/claude", tags=["claude"])


class ClaudeContext(BaseModel):
    cells: list[dict[str, Any]] = []
    active_dataset_id: Optional[str] = None


class ClaudeCompleteRequest(BaseModel):
    prompt: str
    context: ClaudeContext = ClaudeContext()


class ToolUseBlock(BaseModel):
    type: str = "tool_use"
    id: str
    name: str
    input: dict[str, Any]


class ClaudeCompleteResponse(BaseModel):
    reply: str
    tool_uses: list[ToolUseBlock] = []
    suggested_cells: list[dict[str, Any]] = []   # legacy field


# ============================================================
# Tool definitions
# ============================================================

GRAPH_TEMPLATES = ["force", "force_avg", "asymmetry", "peak_box", "cop", "trials", "imu", "cv_bar"]
COMPUTE_METRICS = ["per_stride", "impulse", "loading_rate", "rom", "cadence", "target_dev"]
STAT_OPS = ["ttest_paired", "ttest_welch", "anova1", "pearson", "cohens_d", "shapiro"]
JOURNAL_PRESETS = ["ieee", "nature", "apa", "elsevier", "mdpi", "jner"]

TOOLS = [
    {
        "name": "add_graph_cell",
        "description": (
            "Add a graph cell to the workspace, bound to the active dataset. "
            "Use when the user asks for any plot, chart, waveform, profile, "
            "or visualization of their data. The cell auto-renders via the "
            "publication engine (real data when possible)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "template": {"type": "string", "enum": GRAPH_TEMPLATES,
                             "description": "Which graph template to use."},
                "preset":   {"type": "string", "enum": JOURNAL_PRESETS,
                             "description": "Journal preset override (optional)."},
                "variant":  {"type": "string", "enum": ["col1", "col2", "onehalf"],
                             "description": "Column width (optional; defaults to col2)."},
                "stride_avg": {"type": "boolean",
                               "description": "For 'force', flip to mean±SD across strides."},
            },
            "required": ["template"],
        },
    },
    {
        "name": "add_compute_cell",
        "description": (
            "Add a compute (table) cell that reports a specific gait metric. "
            "Use when the user asks for numeric values, tables, cadence, stride "
            "length, impulse, loading rate, range of motion, target deviation, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "enum": COMPUTE_METRICS},
            },
            "required": ["metric"],
        },
    },
    {
        "name": "add_stat_cell",
        "description": (
            "Add a statistical test cell bound to dataset columns. Use when the "
            "user asks for significance tests, comparisons, correlations, or "
            "effect sizes. `a_col` and `b_col` must be exact column names."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "op":     {"type": "string", "enum": STAT_OPS},
                "a_col":  {"type": "string", "description": "Column name for input A."},
                "b_col":  {"type": "string", "description": "Column for input B (omit for shapiro/anova1)."},
                "paired": {"type": "boolean", "description": "Only used by cohens_d."},
            },
            "required": ["op", "a_col"],
        },
    },
    {
        "name": "apply_recipe",
        "description": (
            "Re-apply the default canonical recipes (graph + compute cells) "
            "for the active dataset. Use for 'give me the standard analysis', "
            "'run default set', 'analyze everything', etc."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "set_journal_preset",
        "description": "Change the global journal preset (IEEE, Nature, APA, ...).",
        "input_schema": {
            "type": "object",
            "properties": {"preset": {"type": "string", "enum": JOURNAL_PRESETS}},
            "required": ["preset"],
        },
    },
    {
        "name": "set_mode",
        "description": "Flip the workspace to QUICK or PUBLICATION mode.",
        "input_schema": {
            "type": "object",
            "properties": {"mode": {"type": "string", "enum": ["quick", "pub"]}},
            "required": ["mode"],
        },
    },
    {
        "name": "run_all",
        "description": "Re-run analyze + compute + graph render for every bound cell.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "export_bundle",
        "description": "Download a ZIP bundle of all graphs at the current journal preset.",
        "input_schema": {
            "type": "object",
            "properties": {
                "format":  {"type": "string", "enum": ["svg", "pdf", "eps", "png", "tiff"]},
                "variant": {"type": "string", "enum": ["col1", "col2", "onehalf"]},
            },
        },
    },
]


SYSTEM = (
    "You are the agent inside H-Walker CORE, a gait-analysis workspace for "
    "cable-driven walking rehabilitation research. The user has an active "
    "dataset and some cells already on canvas. When the user asks you to "
    "CREATE something (graph, table, stat, full analysis), CALL THE RELEVANT "
    "TOOL — do not describe it in prose. When the user asks a CONCEPTUAL or "
    "QUANTITATIVE question about existing data, reply in ≤3 sentences with "
    "specific numbers if you can read them from context. You MAY both call "
    "tools AND reply with a short confirmation sentence in the same turn. "
    "Korean in → Korean reply. English in → English reply. Never fabricate "
    "numbers. Never use markdown headers."
)


def _context_block(ctx: ClaudeContext) -> str:
    cells_summary = ", ".join(
        f"{c.get('id', '?')}:{c.get('type', '?')}"
        + f"/{c.get('graph') or c.get('op') or c.get('metric') or ''}"
        for c in ctx.cells[:20]
    ) or "(no cells yet)"
    return (
        f"Active dataset: {ctx.active_dataset_id or '(none)'}\n"
        f"Cells: {cells_summary}"
    )


@router.post("/complete", response_model=ClaudeCompleteResponse)
def complete(req: ClaudeCompleteRequest) -> ClaudeCompleteResponse:
    if LLM_PROVIDER != "anthropic":
        raise HTTPException(
            status_code=503,
            detail=f"LLM_PROVIDER={LLM_PROVIDER}; set it to 'anthropic' for /api/claude/complete.",
        )
    if not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=503,
            detail=(
                "ANTHROPIC_API_KEY is not set. Export it before running "
                "`python3 run.py` so the Claude proxy can authenticate."
            ),
        )

    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="anthropic SDK not installed. Run: pip install anthropic",
        ) from exc

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    user_msg = f"{_context_block(req.context)}\n\nUser: {req.prompt}"

    try:
        msg = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=ANTHROPIC_MAX_TOKENS,
            system=SYSTEM,
            tools=TOOLS,
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Anthropic API: {exc}") from exc

    parts: list[str] = []
    tool_uses: list[ToolUseBlock] = []
    for block in msg.content:
        btype = getattr(block, "type", None)
        if btype == "text":
            text = getattr(block, "text", "") or ""
            if text.strip():
                parts.append(text)
        elif btype == "tool_use":
            tool_uses.append(ToolUseBlock(
                id=getattr(block, "id", ""),
                name=getattr(block, "name", ""),
                input=dict(getattr(block, "input", {}) or {}),
            ))

    reply = "\n".join(parts).strip()
    if not reply and tool_uses:
        names = ", ".join(t.name for t in tool_uses)
        reply = f"(ran {len(tool_uses)} tool call{'s' if len(tool_uses) != 1 else ''}: {names})"
    elif not reply:
        reply = "(empty)"

    return ClaudeCompleteResponse(reply=reply, tool_uses=tool_uses, suggested_cells=[])


@router.get("/health")
def claude_health() -> dict[str, Any]:
    return {
        "provider": LLM_PROVIDER,
        "model": ANTHROPIC_MODEL,
        "key_present": bool(ANTHROPIC_API_KEY),
        "tools": [t["name"] for t in TOOLS],
    }


@router.get("/tools")
def list_tools() -> dict[str, Any]:
    """Expose tool schema for frontend dispatch wiring / debugging."""
    return {"tools": TOOLS}


# Keep import-only json used above to stop unused-import warning
_ = json
