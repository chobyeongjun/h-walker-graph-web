#!/usr/bin/env python3
"""Run eval on all test files (base + extra) and compare to last report.

Usage:
  python run_all.py           # run all, save report
  python run_all.py --diff    # compare to previous report
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from run_eval import load_test_cases, evaluate_case, print_summary, save_report  # noqa


def load_all_cases() -> list[dict]:
    cases = []
    for name in ("test_cases.yaml", "test_cases_extra.yaml"):
        p = _HERE / name
        if p.exists():
            cases.extend(load_test_cases(p))
    return cases


def load_last_report() -> dict | None:
    reports = sorted((_HERE / "reports").glob("eval-*.json"))
    if not reports:
        return None
    return json.loads(reports[-1].read_text())


def diff_reports(current: list[dict], previous: dict) -> None:
    prev_results = {r["id"]: r for r in previous.get("results", [])}
    changes = []
    for r in current:
        prev = prev_results.get(r["id"])
        if prev is None:
            continue
        if r["pass"] != prev["pass"]:
            arrow = "✓→✗" if prev["pass"] else "✗→✓"
            changes.append((r["id"], arrow, r["query"]))

    if not changes:
        print("\n  No regressions or improvements vs previous run")
        return

    print(f"\n  Changes vs previous run ({len(changes)}):")
    for cid, arrow, q in changes:
        print(f"    {arrow} [{cid}] {q[:50]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--diff", action="store_true", help="diff against last report")
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--model", default="gemma4:e4b")
    args = parser.parse_args()

    cases = load_all_cases()
    print(f"Running {len(cases)} total test cases with {args.model}...")

    results = []
    for i, case in enumerate(cases, 1):
        print(f"  [{i}/{len(cases)}] {case['id']}: {case['query'][:40]}...",
              end="", flush=True)
        r = evaluate_case(case, args.model)
        results.append(r)
        mark = "✓" if r["pass"] else "✗"
        print(f" {mark} ({r['elapsed']:.1f}s)")

    print_summary(results)

    if args.diff:
        prev = load_last_report()
        if prev:
            diff_reports(results, prev)

    if not args.no_save:
        report_path = save_report(results, _HERE / "reports")
        print(f"\n  Report saved: {report_path}")


if __name__ == "__main__":
    main()
