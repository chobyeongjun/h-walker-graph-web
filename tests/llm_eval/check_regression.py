#!/usr/bin/env python3
"""Regression check — run eval and fail if accuracy drops below threshold.

Usage:
  python check_regression.py                # use default thresholds
  python check_regression.py --min 0.90     # require >= 90%
  python check_regression.py --categories basic_force,sides  # subset

Exit codes:
  0 — passed (above threshold)
  1 — regression detected
  2 — test framework error
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from run_eval import load_test_cases, evaluate_case  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min", type=float, default=0.92, help="minimum accuracy (0-1)")
    parser.add_argument("--categories", type=str, default=None, help="comma-separated")
    parser.add_argument("--cases", type=str, default=None)
    parser.add_argument("--model", default="gemma4:e4b")
    parser.add_argument("--per-category-min", type=float, default=0.70,
                        help="no single category may drop below this")
    args = parser.parse_args()

    cases_path = Path(args.cases) if args.cases else (_HERE / "test_cases.yaml")
    cases = load_test_cases(cases_path)

    if args.categories:
        cats = set(args.categories.split(","))
        cases = [c for c in cases if c.get("category") in cats]

    if not cases:
        print("ERROR: no test cases loaded", file=sys.stderr)
        return 2

    print(f"Running {len(cases)} cases to check regression (threshold: {args.min:.0%})...")
    results = [evaluate_case(c, args.model) for c in cases]

    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    accuracy = passed / total

    # Per-category
    cats_stats = {}
    for r in results:
        c = r["category"]
        cats_stats.setdefault(c, [0, 0])
        cats_stats[c][1] += 1
        if r["pass"]:
            cats_stats[c][0] += 1

    print(f"\nOverall: {passed}/{total} ({accuracy:.1%})")
    print(f"Threshold: {args.min:.1%}")

    per_cat_failed = []
    for cat, (p, t) in sorted(cats_stats.items()):
        pct = p / t if t else 0
        mark = "✓" if pct >= args.per_category_min else "✗"
        print(f"  {mark} {cat:15s}: {p}/{t} ({pct:.0%})")
        if pct < args.per_category_min:
            per_cat_failed.append((cat, pct))

    if accuracy < args.min:
        print(f"\n❌ REGRESSION: {accuracy:.1%} < {args.min:.1%}", file=sys.stderr)
        return 1

    if per_cat_failed:
        print(f"\n❌ Categories below {args.per_category_min:.0%}: "
              f"{', '.join(f'{c}({p:.0%})' for c, p in per_cat_failed)}",
              file=sys.stderr)
        return 1

    print("\n✓ All checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
