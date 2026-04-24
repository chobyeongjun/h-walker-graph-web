"""Contract tests for the Claude tool schema.

Catches the "LLM claims support for template X but renderer crashes"
class of bugs. Every template / metric advertised to the LLM must have
a corresponding backend renderer spec and a frontend mock, otherwise a
user request like '힘 시계열 보여줘' routes to an unknown template.
"""
from __future__ import annotations

from backend.routers.claude import (
    GRAPH_TEMPLATES,
    COMPUTE_METRICS,
    STAT_OPS,
    JOURNAL_PRESETS,
    TOOLS,
)
from backend.services.publication_engine import GRAPH_SPECS, JOURNAL_PRESETS as PUB_PRESETS


# ---------------------------------------------------------------
# Tool-schema sanity
# ---------------------------------------------------------------

def test_every_graph_template_has_a_renderer():
    """If the LLM can ask for it, the backend must be able to draw it."""
    missing = [t for t in GRAPH_TEMPLATES if t not in GRAPH_SPECS]
    assert not missing, (
        f"GRAPH_TEMPLATES advertises {missing} but GRAPH_SPECS can't render them. "
        "Either add a spec in publication_engine.py or remove from the enum."
    )


def test_every_journal_preset_is_implemented():
    """The LLM's journal enum must match the publication engine's."""
    missing = [p for p in JOURNAL_PRESETS if p not in PUB_PRESETS]
    assert not missing, (
        f"Advertised presets {missing} are not in publication_engine.JOURNAL_PRESETS."
    )


def test_tool_definitions_are_consistent():
    """Every tool in TOOLS has a name, description, and a valid input_schema."""
    names = set()
    for tool in TOOLS:
        assert tool["name"] and tool["name"] not in names, (
            f"Duplicate or empty tool name: {tool.get('name')!r}"
        )
        names.add(tool["name"])
        assert tool["description"].strip()
        assert tool["input_schema"]["type"] == "object"


def test_add_graph_cell_enum_covers_core_templates():
    """Scalar-first policy still requires the bookshelf to expose key
    time-series graphs — the LLM must be able to reach them."""
    for tool in TOOLS:
        if tool["name"] == "add_graph_cell":
            enum = set(tool["input_schema"]["properties"]["template"]["enum"])
            break
    else:
        raise AssertionError("add_graph_cell tool missing")

    for essential in ("imu", "stride_time_trend", "debug_ts", "force", "imu_avg"):
        assert essential in enum, (
            f"LLM cannot create '{essential}' — user requests like "
            "'MATLAB 처럼 raw 신호 봐' will fail to route."
        )


def test_cadence_and_stride_length_remain_compute_metrics():
    """Whole-trial averages must be compute metrics, not graph templates —
    ensures the LLM routes 'cadence 얼마야' to add_compute_cell, not
    add_graph_cell."""
    assert "cadence" in COMPUTE_METRICS
    assert "stride_length" in COMPUTE_METRICS
    # And they must NOT accidentally appear in the graph enum (that would
    # let the LLM produce bogus time-series plots).
    assert "cadence" not in GRAPH_TEMPLATES
    assert "stride_length" not in GRAPH_TEMPLATES


def test_stat_ops_nonempty():
    assert STAT_OPS, "STAT_OPS enum is empty — stat tool will reject everything."
