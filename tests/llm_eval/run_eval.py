#!/usr/bin/env python3
"""
LLM Evaluation Runner — measures parsing accuracy for H-Walker Graph App.

Usage:
    python run_eval.py              # run all test cases, print summary
    python run_eval.py --verbose    # show each case result
    python run_eval.py --category force  # run only one category
    python run_eval.py --save       # save report to reports/

Compares LLM output against expected fields. A case passes if:
  - action matches (plot vs clarify)
  - for action=plot: analysis_type, sides, normalize_gcp, compare_mode all match
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import yaml

# Add project root to path
_HERE = Path(__file__).resolve().parent
_APP_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_APP_ROOT))
sys.path.insert(0, str(_APP_ROOT.parent.parent))

from backend.services.llm_client import parse_command


def load_test_cases(path: Path) -> list[dict]:
    with path.open() as f:
        return yaml.safe_load(f)


def check_field(actual: dict, expected: dict, field: str) -> bool:
    """Return True if actual[field] matches expected[field].

    Supports `{field}_any_of: [...]` for accepting multiple valid values.
    """
    any_of_key = f"{field}_any_of"
    if any_of_key in expected:
        return actual.get(field) in expected[any_of_key]

    if field not in expected:
        return True
    exp_val = expected[field]
    act_val = actual.get(field)
    if isinstance(exp_val, list):
        return sorted(act_val or []) == sorted(exp_val)
    return act_val == exp_val


def evaluate_case(case: dict, model: str = "gemma4:e4b") -> dict:
    """Run one case and return result dict."""
    t0 = time.time()
    try:
        result = parse_command(case["query"], model=model)
        elapsed = time.time() - t0
    except Exception as e:
        return {
            "id": case["id"],
            "category": case["category"],
            "query": case["query"],
            "pass": False,
            "error": str(e),
            "elapsed": time.time() - t0,
        }

    expect = case["expect"]
    action_ok = result.get("action") == expect.get("action")

    if expect.get("action") == "clarify":
        # For clarify, only action needs to match
        passed = action_ok
        mismatches = [] if passed else ["action"]
    else:
        # For plot, check all expected fields
        req = result.get("analysis_request") or {}
        checks = {
            "action": action_ok,
            "analysis_type": check_field(req, expect, "analysis_type"),
            "sides": check_field(req, expect, "sides"),
            "normalize_gcp": check_field(req, expect, "normalize_gcp"),
            "compare_mode": check_field(req, expect, "compare_mode"),
        }
        passed = all(checks.values())
        mismatches = [k for k, v in checks.items() if not v]

    return {
        "id": case["id"],
        "category": case["category"],
        "query": case["query"],
        "expected": expect,
        "actual": {
            "action": result.get("action"),
            "analysis_request": result.get("analysis_request"),
            "message": result.get("message", "")[:80],
        },
        "pass": passed,
        "mismatches": mismatches,
        "elapsed": elapsed,
    }


def print_summary(results: list[dict]) -> None:
    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    avg_time = sum(r["elapsed"] for r in results) / max(total, 1)

    print(f"\n{'=' * 60}")
    print(f"  Evaluation Summary")
    print(f"{'=' * 60}")
    print(f"  Total:        {total}")
    print(f"  Passed:       {passed} ({passed/total*100:.1f}%)")
    print(f"  Failed:       {total - passed}")
    print(f"  Avg latency:  {avg_time:.2f}s")

    # By category
    cats = {}
    for r in results:
        c = r["category"]
        cats.setdefault(c, {"pass": 0, "total": 0})
        cats[c]["total"] += 1
        if r["pass"]:
            cats[c]["pass"] += 1

    print(f"\n  By Category:")
    for c, s in sorted(cats.items()):
        pct = s["pass"] / s["total"] * 100
        print(f"    {c:15s}: {s['pass']}/{s['total']} ({pct:.0f}%)")

    # Failures detail
    failures = [r for r in results if not r["pass"]]
    if failures:
        print(f"\n  Failed cases ({len(failures)}):")
        for f in failures[:15]:  # show first 15
            mm = ",".join(f.get("mismatches", ["error"]))
            print(f"    [{f['id']}] {f['query'][:40]:40s} → mismatches: {mm}")
            if f.get("error"):
                print(f"              error: {f['error'][:100]}")


def print_verbose(results: list[dict]) -> None:
    for r in results:
        mark = "✓" if r["pass"] else "✗"
        print(f"  {mark} [{r['id']}] {r['query'][:50]}")
        if not r["pass"]:
            print(f"      expected: {r['expected']}")
            print(f"      actual:   {r['actual']}")


def save_report(results: list[dict], reports_dir: Path) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    report_path = reports_dir / f"eval-{stamp}.json"

    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    avg_time = sum(r["elapsed"] for r in results) / max(total, 1)

    report = {
        "timestamp": int(time.time()),
        "summary": {
            "total": total,
            "passed": passed,
            "accuracy": passed / total if total else 0,
            "avg_latency_s": avg_time,
        },
        "results": results,
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return report_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--category", type=str, help="run only this category")
    parser.add_argument("--save", action="store_true", help="save report to reports/")
    parser.add_argument("--model", default="gemma4:e4b")
    parser.add_argument("--cases", type=str, default=None, help="test cases yaml path")
    args = parser.parse_args()

    cases_path = Path(args.cases) if args.cases else (_HERE / "test_cases.yaml")
    cases = load_test_cases(cases_path)

    if args.category:
        cases = [c for c in cases if c.get("category") == args.category]

    print(f"Running {len(cases)} test cases with model={args.model}...")

    results = []
    for i, case in enumerate(cases, 1):
        print(f"  [{i}/{len(cases)}] {case['id']}: {case['query'][:40]}...", end="", flush=True)
        r = evaluate_case(case, args.model)
        results.append(r)
        mark = "✓" if r["pass"] else "✗"
        print(f" {mark} ({r['elapsed']:.1f}s)")

    if args.verbose:
        print_verbose(results)

    print_summary(results)

    if args.save:
        report_path = save_report(results, _HERE / "reports")
        print(f"\n  Report saved: {report_path}")


if __name__ == "__main__":
    main()
