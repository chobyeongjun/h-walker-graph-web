"""
Statistical operations — Phase 2A real implementation.

Replaces the mock `statOps.ts` client-side stubs with SciPy-backed tests.
Every op returns a uniform payload:

    {
        "op":             str,                 # canonical op key
        "name":           str,                 # human-readable name
        "stat":           float,               # test statistic (t / F / r / U / W / Z)
        "stat_name":      str,                 # "t" / "F" / "r" / ...
        "p":              float,               # two-sided p-value
        "df":             float | list | None, # degrees of freedom
        "effect_size":    {"name": str, "value": float} | None,
        "ci95":           [float, float] | None,
        "n":              int | list[int],
        "assumption":     {"name": str, "p": float, "passed": bool} | None,
        "fallback_used":  bool,                # True if assumption failed → non-parametric
        "summary":        str,                 # short human string
    }

All series are expected as plain Python lists of floats (JSON-friendly).
"""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats


def _clean(a: list[float]) -> np.ndarray:
    arr = np.asarray(a, dtype=float)
    return arr[np.isfinite(arr)]


def _shapiro(x: np.ndarray) -> tuple[float, bool]:
    """Return (p_value, normal?). Too small / too large samples: assume normal."""
    n = len(x)
    if n < 3 or n > 5000:
        return 1.0, True
    try:
        _, p = stats.shapiro(x)
        return float(p), bool(p > 0.05)
    except Exception:
        return 1.0, True


def _pooled_sd(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return 0.0
    va = float(np.var(a, ddof=1))
    vb = float(np.var(b, ddof=1))
    return float(np.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2)))


def _cohens_d(a: np.ndarray, b: np.ndarray, paired: bool = False) -> float:
    if paired:
        d = a - b
        sd = float(np.std(d, ddof=1)) if len(d) > 1 else 0.0
        return float(np.mean(d) / sd) if sd > 0 else 0.0
    sp = _pooled_sd(a, b)
    return float((np.mean(a) - np.mean(b)) / sp) if sp > 0 else 0.0


def _cohen_magnitude(d: float) -> str:
    """Cohen (1988) rule-of-thumb magnitude label for |d|."""
    ad = abs(d)
    if ad < 0.2:
        return "negligible"
    if ad < 0.5:
        return "small"
    if ad < 0.8:
        return "medium"
    return "large"


def _diff_ci95(a: np.ndarray, b: np.ndarray, paired: bool) -> tuple[float, float] | None:
    if paired:
        d = a - b
        if len(d) < 2:
            return None
        m = float(np.mean(d))
        se = float(stats.sem(d))
        tcrit = float(stats.t.ppf(0.975, len(d) - 1))
        return (m - tcrit * se, m + tcrit * se)
    if len(a) < 2 or len(b) < 2:
        return None
    m = float(np.mean(a) - np.mean(b))
    # Welch-Satterthwaite df
    va, vb = np.var(a, ddof=1), np.var(b, ddof=1)
    na, nb = len(a), len(b)
    se = float(np.sqrt(va / na + vb / nb))
    df_num = (va / na + vb / nb) ** 2
    df_den = (va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1)
    df = float(df_num / df_den) if df_den > 0 else float(na + nb - 2)
    tcrit = float(stats.t.ppf(0.975, df))
    return (m - tcrit * se, m + tcrit * se)


# ============================================================
# Ops
# ============================================================


def ttest_paired(a: list[float], b: list[float]) -> dict[str, Any]:
    x_all, y_all = _clean(a), _clean(b)
    n = min(len(x_all), len(y_all))
    if n < 3:
        raise ValueError(f"paired t-test needs ≥3 pairs (got {n})")
    trimmed = max(len(x_all), len(y_all)) - n
    x, y = x_all[:n], y_all[:n]
    diff = x - y
    sh_p, normal = _shapiro(diff)
    if not normal:
        # fallback: Wilcoxon signed-rank
        res = stats.wilcoxon(x, y, zero_method="wilcox", alternative="two-sided")
        return {
            "op": "ttest_paired",
            "name": "Wilcoxon signed-rank (Shapiro failed)",
            "stat": float(res.statistic),
            "stat_name": "W",
            "p": float(res.pvalue),
            "df": None,
            "effect_size": {"name": "r", "value": _rank_biserial(x, y)},
            "ci95": None,
            "n": int(n),
            "assumption": {"name": "Shapiro-Wilk (diff)", "p": sh_p, "passed": False},
            "fallback_used": True,
            "summary": f"Wilcoxon W={res.statistic:.2f}, p={res.pvalue:.3g}, n={n}",
        }
    t_stat, p_val = stats.ttest_rel(x, y)
    d = _cohens_d(x, y, paired=True)
    ci = _diff_ci95(x, y, paired=True)
    warn = (
        f"{trimmed} unpaired value(s) dropped — inputs had unequal length"
        if trimmed else None
    )
    return {
        "op": "ttest_paired",
        "name": "Paired t-test",
        "stat": float(t_stat),
        "stat_name": "t",
        "p": float(p_val),
        "df": float(n - 1),
        "effect_size": {"name": "Cohen's d", "value": d,
                        "label": _cohen_magnitude(d)},
        "ci95": list(ci) if ci else None,
        "n": int(n),
        "assumption": {"name": "Shapiro-Wilk (diff)", "p": sh_p, "passed": True},
        "fallback_used": False,
        "warning": warn,
        "summary": f"t({n-1})={t_stat:.2f}, p={p_val:.3g}, d={d:.2f}",
    }


def ttest_welch(a: list[float], b: list[float]) -> dict[str, Any]:
    x, y = _clean(a), _clean(b)
    if len(x) < 2 or len(y) < 2:
        raise ValueError(f"Welch t-test needs ≥2 per group (got {len(x)}, {len(y)})")
    sh_px, nx = _shapiro(x)
    sh_py, ny = _shapiro(y)
    both_normal = nx and ny
    if not both_normal:
        res = stats.mannwhitneyu(x, y, alternative="two-sided")
        return {
            "op": "ttest_welch",
            "name": "Mann-Whitney U (Shapiro failed)",
            "stat": float(res.statistic),
            "stat_name": "U",
            "p": float(res.pvalue),
            "df": None,
            "effect_size": {"name": "r", "value": _mwu_rank_biserial(res.statistic, len(x), len(y))},
            "ci95": None,
            "n": [int(len(x)), int(len(y))],
            "assumption": {"name": "Shapiro-Wilk (min group)", "p": min(sh_px, sh_py), "passed": False},
            "fallback_used": True,
            "summary": f"U={res.statistic:.0f}, p={res.pvalue:.3g}, n=({len(x)},{len(y)})",
        }
    t_stat, p_val = stats.ttest_ind(x, y, equal_var=False)
    d = _cohens_d(x, y, paired=False)
    d_label = _cohen_magnitude(d)
    ci = _diff_ci95(x, y, paired=False)
    # Welch df
    va, vb = np.var(x, ddof=1), np.var(y, ddof=1)
    na, nb = len(x), len(y)
    df_num = (va / na + vb / nb) ** 2
    df_den = (va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1)
    df = float(df_num / df_den) if df_den > 0 else float(na + nb - 2)
    return {
        "op": "ttest_welch",
        "name": "Welch's t-test",
        "stat": float(t_stat),
        "stat_name": "t",
        "p": float(p_val),
        "df": df,
        "effect_size": {"name": "Cohen's d", "value": d, "label": d_label},
        "ci95": list(ci) if ci else None,
        "n": [int(na), int(nb)],
        "assumption": {"name": "Shapiro-Wilk (min group)", "p": min(sh_px, sh_py), "passed": True},
        "fallback_used": False,
        "summary": f"t({df:.1f})={t_stat:.2f}, p={p_val:.3g}, d={d:.2f}",
    }


def anova1(groups: list[list[float]]) -> dict[str, Any]:
    cleaned = [_clean(g) for g in groups]
    cleaned = [g for g in cleaned if len(g) >= 2]
    if len(cleaned) < 2:
        raise ValueError(f"one-way ANOVA needs ≥2 groups with ≥2 samples")
    ns = [len(g) for g in cleaned]
    shapiros = [_shapiro(g) for g in cleaned]
    all_normal = all(n for _, n in shapiros)
    if not all_normal:
        res = stats.kruskal(*cleaned)
        return {
            "op": "anova1",
            "name": "Kruskal-Wallis (Shapiro failed)",
            "stat": float(res.statistic),
            "stat_name": "H",
            "p": float(res.pvalue),
            "df": float(len(cleaned) - 1),
            "effect_size": None,
            "ci95": None,
            "n": ns,
            "assumption": {"name": "Shapiro-Wilk (worst group)", "p": min(p for p, _ in shapiros), "passed": False},
            "fallback_used": True,
            "summary": f"H({len(cleaned)-1})={res.statistic:.2f}, p={res.pvalue:.3g}",
        }
    F, p = stats.f_oneway(*cleaned)
    # eta-squared
    all_vals = np.concatenate(cleaned)
    grand = np.mean(all_vals)
    ss_between = sum(len(g) * (np.mean(g) - grand) ** 2 for g in cleaned)
    ss_total = float(np.sum((all_vals - grand) ** 2))
    eta2 = float(ss_between / ss_total) if ss_total > 0 else 0.0
    df_between = len(cleaned) - 1
    df_within = sum(ns) - len(cleaned)
    return {
        "op": "anova1",
        "name": "One-way ANOVA",
        "stat": float(F),
        "stat_name": "F",
        "p": float(p),
        "df": [df_between, df_within],
        "effect_size": {"name": "η²", "value": eta2},
        "ci95": None,
        "n": ns,
        "assumption": {"name": "Shapiro-Wilk (worst group)", "p": min(p for p, _ in shapiros), "passed": True},
        "fallback_used": False,
        "summary": f"F({df_between},{df_within})={F:.2f}, p={p:.3g}, η²={eta2:.3f}",
    }


def pearson(a: list[float], b: list[float]) -> dict[str, Any]:
    x, y = _clean(a), _clean(b)
    n = min(len(x), len(y))
    if n < 3:
        raise ValueError(f"Pearson correlation needs ≥3 pairs (got {n})")
    x, y = x[:n], y[:n]
    sh_px, nx = _shapiro(x)
    sh_py, ny = _shapiro(y)
    both_normal = nx and ny
    if not both_normal:
        rho, p = stats.spearmanr(x, y)
        return {
            "op": "pearson",
            "name": "Spearman ρ (Shapiro failed)",
            "stat": float(rho),
            "stat_name": "ρ",
            "p": float(p),
            "df": float(n - 2),
            "effect_size": {"name": "ρ²", "value": float(rho * rho)},
            "ci95": None,
            "n": int(n),
            "assumption": {"name": "Shapiro-Wilk (both)", "p": min(sh_px, sh_py), "passed": False},
            "fallback_used": True,
            "summary": f"ρ={rho:.3f}, p={p:.3g}, n={n}",
        }
    r, p = stats.pearsonr(x, y)
    # Fisher z CI
    if abs(r) < 0.9999 and n > 3:
        z = 0.5 * np.log((1 + r) / (1 - r))
        se = 1 / np.sqrt(n - 3)
        z_lo, z_hi = z - 1.96 * se, z + 1.96 * se
        ci_lo = float((np.exp(2 * z_lo) - 1) / (np.exp(2 * z_lo) + 1))
        ci_hi = float((np.exp(2 * z_hi) - 1) / (np.exp(2 * z_hi) + 1))
        ci = [ci_lo, ci_hi]
    else:
        ci = None
    return {
        "op": "pearson",
        "name": "Pearson correlation",
        "stat": float(r),
        "stat_name": "r",
        "p": float(p),
        "df": float(n - 2),
        "effect_size": {"name": "r²", "value": float(r * r)},
        "ci95": ci,
        "n": int(n),
        "assumption": {"name": "Shapiro-Wilk (both)", "p": min(sh_px, sh_py), "passed": True},
        "fallback_used": False,
        "summary": f"r({n-2})={r:.3f}, p={p:.3g}, r²={r*r:.3f}",
    }


def cohens_d(a: list[float], b: list[float], paired: bool = False) -> dict[str, Any]:
    x, y = _clean(a), _clean(b)
    if paired:
        n = min(len(x), len(y))
        if n < 2:
            raise ValueError(f"Cohen's d (paired) needs ≥2 pairs")
        x, y = x[:n], y[:n]
        d = _cohens_d(x, y, paired=True)
        sd_diff = float(np.std(x - y, ddof=1))
        se = sd_diff / np.sqrt(n) if sd_diff > 0 else 0.0
    else:
        if len(x) < 2 or len(y) < 2:
            raise ValueError("Cohen's d needs ≥2 per group")
        d = _cohens_d(x, y, paired=False)
        # SE(d) via Hedges formula approximation
        na, nb = len(x), len(y)
        se = float(np.sqrt((na + nb) / (na * nb) + d * d / (2 * (na + nb))))
    ci = [d - 1.96 * se, d + 1.96 * se] if se > 0 else None
    magnitude = (
        "negligible" if abs(d) < 0.2 else
        "small" if abs(d) < 0.5 else
        "medium" if abs(d) < 0.8 else
        "large"
    )
    return {
        "op": "cohens_d",
        "name": "Cohen's d" + (" (paired)" if paired else ""),
        "stat": float(d),
        "stat_name": "d",
        "p": None,
        "df": None,
        "effect_size": {"name": "magnitude", "value": d, "label": magnitude},
        "ci95": ci,
        "n": [int(len(x)), int(len(y))],
        "assumption": None,
        "fallback_used": False,
        "summary": f"d={d:.2f} ({magnitude})",
    }


def shapiro_test(a: list[float]) -> dict[str, Any]:
    x = _clean(a)
    n = len(x)
    if n < 3 or n > 5000:
        raise ValueError(f"Shapiro-Wilk needs 3 ≤ n ≤ 5000 (got {n})")
    W, p = stats.shapiro(x)
    return {
        "op": "shapiro",
        "name": "Shapiro-Wilk normality",
        "stat": float(W),
        "stat_name": "W",
        "p": float(p),
        "df": None,
        "effect_size": None,
        "ci95": None,
        "n": int(n),
        "assumption": None,
        "fallback_used": False,
        "summary": f"W={W:.3f}, p={p:.3g} ({'normal' if p > 0.05 else 'not normal'})",
    }


# ============================================================
# Effect-size helpers for rank-based fallbacks
# ============================================================


def _rank_biserial(a: np.ndarray, b: np.ndarray) -> float:
    diffs = a - b
    pos = np.sum(diffs > 0)
    neg = np.sum(diffs < 0)
    n = pos + neg
    return float((pos - neg) / n) if n > 0 else 0.0


def _mwu_rank_biserial(u: float, n1: int, n2: int) -> float:
    return float(1 - 2 * u / (n1 * n2)) if n1 > 0 and n2 > 0 else 0.0


# ============================================================
# Dispatcher
# ============================================================


OP_REGISTRY = {
    "ttest_paired": ttest_paired,
    "ttest_welch": ttest_welch,
    "anova1": anova1,
    "pearson": pearson,
    "cohens_d": cohens_d,
    "shapiro": shapiro_test,
}


def run(op: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Dispatch by op key. Payload shape depends on op:
        ttest_paired / ttest_welch / pearson / cohens_d: {a: [...], b: [...]}
        anova1:                                           {groups: [[...], [...], ...]}
        shapiro:                                          {a: [...]}
    """
    if op not in OP_REGISTRY:
        raise ValueError(f"Unknown op '{op}'. Known: {sorted(OP_REGISTRY.keys())}")
    fn = OP_REGISTRY[op]
    if op == "anova1":
        return fn(payload.get("groups") or [])
    if op == "shapiro":
        return fn(payload.get("a") or [])
    if op == "cohens_d":
        return fn(payload.get("a") or [], payload.get("b") or [],
                  paired=bool(payload.get("paired", False)))
    return fn(payload.get("a") or [], payload.get("b") or [])
