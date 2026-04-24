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


class ClaudeTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ClaudeContext(BaseModel):
    cells: list[dict[str, Any]] = []
    active_dataset_id: Optional[str] = None
    # Phase 2G: multi-turn memory — prior user/assistant exchanges.
    history: list[ClaudeTurn] = []
    # Phase 2I: analysis summary per dataset — so Claude can diagnose
    # anomalies and ground its answers in actual numbers.
    datasets: list[dict[str, Any]] = []


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

GRAPH_TEMPLATES = [
    # Force / kinetic
    "force", "force_avg", "force_lr_subplot",
    "asymmetry", "peak_box", "cop", "trials", "cv_bar",
    # Motion / kinematic (Phase 0)
    "imu", "imu_avg", "cyclogram", "stride_time_trend",
    "stance_swing_bar", "rom_bar", "symmetry_radar",
    # Debug · Phase 2I
    "debug_ts",
]
COMPUTE_METRICS = [
    "per_stride", "impulse", "loading_rate", "rom", "cadence", "target_dev",
    # Phase 0 motion metrics
    "stride_length", "stance_time", "swing_time", "fatigue_index", "symmetry_summary",
]
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
                "title": {"type": "string",
                          "description": "Optional figure caption (journal style: below the plot in the manuscript). Leave empty for no title."},
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
    {
        "name": "run_paper",
        "description": (
            "Export the complete paper bundle — figures (PDF+SVG), stat "
            "tables (CSV + APA LaTeX), captions, a main.tex skeleton, "
            "and a README provenance log. Use for '논문 준비해줘' / "
            "'paper 뽑아줘' / 'export the manuscript' type requests."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "analyze_study",
        "description": (
            "Batch analyze a group of CSV files in a local directory. "
            "Discovers the study, groups files by condition/subject, "
            "runs full analysis, and generates a research summary report."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Absolute path to the folder containing CSVs."},
                "name":      {"type": "string", "description": "Display name for the study."}
            },
            "required": ["directory", "name"],
        },
    },
    {
        "name": "gate_split",
        "description": (
            "Split a dataset into per-trial sub-CSVs based on analog sync "
            "HIGH gate regions (A7/Sync/TrigIn column). Use when the user "
            "says '각 trial 나눠줘', 'sync 기준으로 잘라', '각 시행별로 "
            "분리해', 'split by trigger'. Each HIGH region becomes a new "
            "independent dataset."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string", "description": "Source dataset id. Omit to use active dataset."},
                "min_gate_width_s": {"type": "number", "description": "Reject HIGH regions shorter than this (default 2.0s)."},
                "threshold_rel": {"type": "number", "description": "HIGH/LOW boundary as fraction of signal range (default 0.5)."},
            },
        },
    },
    {
        "name": "edge_trim",
        "description": (
            "Trim the first N and last N footfalls from a dataset to remove "
            "start-up / stop transients. Use when there is NO analog sync "
            "column and the user wants clean steady-state data. Typical "
            "requests: '앞뒤 걸음 잘라줘', '과도기 제거', 'drop warm-up steps'. "
            "Creates a new <name>_trimmed.csv."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string", "description": "Source dataset id. Omit to use active dataset."},
                "n_edge": {"type": "integer", "description": "Number of footfalls to remove from each end (default 3)."},
            },
        },
    },
    {
        "name": "sync_align",
        "description": (
            "Cross-source alignment: crop every loaded dataset to its own "
            "sync window and resample to a common rate. Use when the user "
            "has Loadcell + Robot (or multiple acquisition systems) loaded "
            "and says 'Loadcell과 Robot sync 맞춰서', '여러 센서 동기화', "
            "'크로스 소스 정렬', 'align all sources'. The output is new "
            "_synced datasets, ready for overlay / comparison."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target_hz": {"type": "number", "description": "Target sample rate (Hz). Omit to use max input rate."},
            },
        },
    },
    {
        "name": "create_comparison_room",
        "description": (
            "Create a new workspace room containing specific datasets for "
            "side-by-side comparison. Use when the user wants to group "
            "several datasets for a comparison plot: '이 데이터들 같이 "
            "비교할 방 만들어줘', '이 trial들 묶어줘', 'compare these in "
            "one room'. Provide dataset name substrings to match — the "
            "tool will find matching datasets and create the room."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Display name for the new room."},
                "dataset_patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Substrings to match dataset names. E.g. ['trial_01', 'trial_02'] or ['Pre_imu', 'Post_imu']. Case-insensitive.",
                },
            },
            "required": ["name", "dataset_patterns"],
        },
    },
]


SYSTEM = (
    "You are the agent inside H-Walker CORE, a gait-analysis workspace for "
    "cable-driven walking rehabilitation research. The user has an active "
    "dataset and some cells already on canvas.\n\n"
    "When the user asks you to CREATE something (graph, table, stat, full "
    "analysis), CALL THE RELEVANT TOOL — do not describe it in prose. Never "
    "reply 'this template isn't supported' — every template in the "
    "add_graph_cell schema is available; pick the best match.\n\n"
    "Template hints for common requests:\n"
    "  L/R 서브플롯 · L vs R subplot · GCP 기반 좌우 비교 → force_lr_subplot\n"
    "  힘 평균곡선 · GRF waveform · mean ± SD         → force_avg\n"
    "  L vs R overlay (같은 축) · raw force           → force\n"
    "  피크 박스플롯 · peak boxplot                   → peak_box\n"
    "  비대칭 · asymmetry per stride                  → asymmetry\n"
    "  논문 전체 · 모든 figure 한번에                 → apply_recipe\n"
    "  조인트 각도 시계열                             → imu\n"
    "  관절 각도 평균±SD (사이클)                     → imu_avg\n"
    "  ROM 바                                          → rom_bar\n"
    "  stance/swing %                                  → stance_swing_bar\n"
    "  대칭성 radar                                    → symmetry_radar\n"
    "  디버깅 · raw 시계열 · 어디서 이상한가            → debug_ts\n"
    "  연구 자동화 · 배치 분석 · 폴더 내 모든 파일 분석    → analyze_study\n\n"
    "DATA preparation workflows (call these tools AUTOMATICALLY, don't ask):\n"
    "  sync 기준으로 trial 분할 · 각 녹화 잘라줘             → gate_split\n"
    "  앞뒤 걸음 제거 · warm-up/cool-down 자른 데이터        → edge_trim\n"
    "  Loadcell과 Robot sync 맞춰 · 다중 센서 정렬           → sync_align\n"
    "  이 데이터들 비교할 방 만들어 · 특정 trial 묶어        → create_comparison_room\n"
    "When the user asks to 'cut', 'split', 'sync', 'align', 'compare these',\n"
    "you MUST call the appropriate tool rather than asking for clarification.\n"
    "You have the dataset list in context — match names by substring.\n\n"
    "You now have access to advanced biomechanical metrics (using foot-mounted IMU):\n"
    "  - Foot Pitch ROM: Range of motion of the foot instep during gait.\n"
    "  - Force Bias: Mean tracking error (Act - Des). Positive means robot provides more force than target.\n\n"
    "When the user asks a CONCEPTUAL or QUANTITATIVE question about existing "
    "data, reply in ≤3 sentences with specific numbers if you can read them "
    "from context. You MAY both call tools AND reply with a short confirmation "
    "in the same turn. Korean in → Korean reply. English in → English reply. "
    "Never fabricate numbers. Never use markdown headers."
)


def _context_block(ctx: ClaudeContext) -> str:
    cells_summary = ", ".join(
        f"{c.get('id', '?')}:{c.get('type', '?')}"
        + f"/{c.get('graph') or c.get('op') or c.get('metric') or ''}"
        for c in ctx.cells[:20]
    ) or "(no cells yet)"

    lines = [
        f"Active dataset: {ctx.active_dataset_id or '(none)'}",
        f"Cells on canvas: {cells_summary}",
    ]
    if ctx.datasets:
        lines.append("")
        lines.append("Dataset analysis summaries:")
        for d in ctx.datasets[:6]:
            L = d.get('L') or {}
            R = d.get('R') or {}
            sym = d.get('symmetry') or {}
            fat = d.get('fatigue') or {}
            tag = f" [{d.get('group')}]" if d.get('group') else ""
            if 'n_samples' in d:
                lines.append(
                    f"  · {d.get('name', d.get('id'))}{tag}: "
                    f"{d.get('duration_s', '?')}s @ {d.get('sample_rate', '?')}Hz, "
                    f"L={L.get('n_strides', 0)} strides "
                    f"(cadence {L.get('cadence', 0):.1f}, stride_T {L.get('stride_time_mean', 0):.3f}s, "
                    f"Joint ROM {L.get('joint', {}).get('rom', 0):.1f}°, "
                    f"Force Bias {L.get('force_tracking', {}).get('bias', 0):.2f}N), "
                    f"R={R.get('n_strides', 0)} strides "
                    f"(Joint ROM {R.get('joint', {}).get('rom', 0):.1f}°, "
                    f"Force Bias {R.get('force_tracking', {}).get('bias', 0):.2f}N), "
                    f"symmetry stride_T {sym.get('stride_time', 0):.1f}% "
                    f"force {sym.get('force', 0):.1f}%, "
                    f"fatigue L {fat.get('left_pct_change', 0):+.1f}% R {fat.get('right_pct_change', 0):+.1f}%"
                )
            else:
                lines.append(f"  · {d.get('name', d.get('id'))}{tag} (generic mode, no gait metrics)")
    return "\n".join(lines)


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

    # Multi-turn memory: prior user/assistant pairs first, then the new
    # user message with the freshest workspace snapshot prepended.
    messages: list[dict[str, Any]] = []
    for turn in req.context.history:
        role = "user" if turn.role == "user" else "assistant"
        content = (turn.content or "").strip()
        if content:
            messages.append({"role": role, "content": content})

    # Final user turn carries the workspace context block so Claude always
    # sees the current state of the canvas + active dataset.
    user_msg = f"{_context_block(req.context)}\n\nUser: {req.prompt}"
    messages.append({"role": "user", "content": user_msg})

    try:
        msg = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=ANTHROPIC_MAX_TOKENS,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
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


class ApiKeyRequest(BaseModel):
    api_key: str


@router.post("/set-key")
def set_key(req: ApiKeyRequest) -> dict[str, Any]:
    """Write the user's Anthropic API key to ~/.hwalker.env so the launcher
    (H-Walker CORE.command) picks it up on every restart. Also mutates the
    current process env so the next /complete call works without restart.
    """
    import os, re
    key = req.api_key.strip()
    if not key:
        raise HTTPException(status_code=422, detail="api_key is empty")
    if not re.match(r'^sk-ant-[A-Za-z0-9_\-]{20,}$', key):
        raise HTTPException(
            status_code=422,
            detail="Key must look like 'sk-ant-api03-…' (Anthropic format).",
        )

    env_path = os.path.expanduser("~/.hwalker.env")
    # Merge: preserve other vars in the file, update/insert ANTHROPIC_API_KEY
    lines: list[str] = []
    if os.path.isfile(env_path):
        with open(env_path) as f:
            lines = [ln.rstrip("\n") for ln in f if not ln.strip().startswith("ANTHROPIC_API_KEY=")]
    lines.append(f"ANTHROPIC_API_KEY={key}")
    try:
        with open(env_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        os.chmod(env_path, 0o600)  # user-only readable — it's a secret
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"write failed: {exc}") from exc

    # Live-update: mutate process env + rebind the module-level constant so
    # the next /complete call uses this key immediately.
    os.environ["ANTHROPIC_API_KEY"] = key
    import backend.services.config as _cfg
    _cfg.ANTHROPIC_API_KEY = key
    globals()["ANTHROPIC_API_KEY"] = key

    return {
        "ok": True,
        "path": env_path,
        "note": "Key persisted to ~/.hwalker.env (chmod 600) and loaded into the running server.",
    }


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
