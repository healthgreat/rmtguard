#!/usr/bin/env python
"""Build manuscript-facing stability confidence intervals and paired deltas.

Author: RMTGuard development team
Date: 2026-05-02
Purpose: Convert per-pair subsampling ARI records into confidence intervals,
paired diagnostic tests, and a manuscript-grade stability gap report.
Data source: `benchmarks/run_stability_benchmark.py` pairwise output.
Method notes: Pairwise ARIs from overlapping subsampling runs are diagnostic
rather than independent biological replicates. They should be reported as
benchmark uncertainty estimates, not as clinical or biological inference.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDIR = ROOT / "results" / "manuscript_stability_benchmarks"
OUT_STATS = DEFAULT_INDIR / "manuscript_stability_statistics.tsv"
OUT_DELTAS = DEFAULT_INDIR / "manuscript_stability_paired_deltas.tsv"
OUT_MD = ROOT / "docs" / "manuscript_grade_stability_statistics.md"
BASELINE_METHODS = [
    "scanpy_default_like",
    "fixed_pcs_30",
    "fixed_pcs_50",
    "elbow_rule",
    "parallel_analysis",
    "jackstraw_like",
]


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_tsv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _fmt(value: float) -> str:
    if not np.isfinite(value):
        return "nan"
    return f"{value:.6f}"


def _bootstrap_ci(values: np.ndarray, rng: np.random.Generator, n_bootstrap: int) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return float("nan"), float("nan")
    if values.size == 1:
        return float(values[0]), float(values[0])
    draws = rng.choice(values, size=(n_bootstrap, values.size), replace=True)
    means = draws.mean(axis=1)
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def _sign_flip_pvalue(values: np.ndarray, rng: np.random.Generator, n_permutations: int) -> float:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return float("nan")
    observed = abs(float(values.mean()))
    if values.size <= 15:
        # Exhaustive sign flips are small enough and deterministic here.
        total = 2 ** values.size
        extreme = 0
        for mask in range(total):
            signs = np.array([1 if (mask >> i) & 1 else -1 for i in range(values.size)])
            extreme += abs(float((values * signs).mean())) >= observed
        return float((extreme + 1) / (total + 1))
    extreme = 0
    for _ in range(n_permutations):
        signs = rng.choice([-1, 1], size=values.size, replace=True)
        extreme += abs(float((values * signs).mean())) >= observed
    return float((extreme + 1) / (n_permutations + 1))


def _metadata_by_dataset(summary_rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    return {
        (row.get("dataset_id", ""), row.get("method", "")): row
        for row in summary_rows
    }


def build_statistics(
    summary_rows: list[dict[str, str]],
    pairwise_rows: list[dict[str, str]],
    n_bootstrap: int,
    n_permutations: int,
    random_state: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rng = np.random.default_rng(random_state)
    summary_lookup = _metadata_by_dataset(summary_rows)
    grouped: dict[tuple[str, str], list[float]] = {}
    pair_lookup: dict[tuple[str, str, str], float] = {}
    for row in pairwise_rows:
        dataset_id = row.get("dataset_id", "")
        method = row.get("method", "")
        pair_key = row.get("pair_key", "")
        value = _float(row.get("pairwise_ari", "nan"))
        grouped.setdefault((dataset_id, method), []).append(value)
        pair_lookup[(dataset_id, method, pair_key)] = value

    stats_rows: list[dict[str, object]] = []
    for (dataset_id, method), values in sorted(grouped.items()):
        arr = np.asarray(values, dtype=float)
        ci_low, ci_high = _bootstrap_ci(arr, rng, n_bootstrap)
        meta = summary_lookup.get((dataset_id, method), {})
        stats_rows.append(
            {
                "dataset_id": dataset_id,
                "method": method,
                "n_repeats": meta.get("n_repeats", ""),
                "sample_fraction": meta.get("sample_fraction", ""),
                "pairwise_n": int(np.isfinite(arr).sum()),
                "mean_pairwise_ari": _fmt(float(np.nanmean(arr))),
                "bootstrap_ci_low": _fmt(ci_low),
                "bootstrap_ci_high": _fmt(ci_high),
                "mean_cluster_n": meta.get("mean_cluster_n", ""),
                "mean_n_cells": meta.get("mean_n_cells", ""),
            }
        )

    dataset_methods: dict[str, set[str]] = {}
    dataset_pairs: dict[str, set[str]] = {}
    for dataset_id, method, pair_key in pair_lookup:
        dataset_methods.setdefault(dataset_id, set()).add(method)
        dataset_pairs.setdefault(dataset_id, set()).add(pair_key)

    delta_rows: list[dict[str, object]] = []
    for dataset_id in sorted(dataset_methods):
        if "rmtguard" not in dataset_methods[dataset_id]:
            continue
        for baseline in BASELINE_METHODS:
            if baseline not in dataset_methods[dataset_id]:
                continue
            deltas = []
            for pair_key in sorted(dataset_pairs.get(dataset_id, set())):
                rmt_value = pair_lookup.get((dataset_id, "rmtguard", pair_key), float("nan"))
                baseline_value = pair_lookup.get((dataset_id, baseline, pair_key), float("nan"))
                if np.isfinite(rmt_value) and np.isfinite(baseline_value):
                    deltas.append(rmt_value - baseline_value)
            arr = np.asarray(deltas, dtype=float)
            if arr.size == 0:
                continue
            ci_low, ci_high = _bootstrap_ci(arr, rng, n_bootstrap)
            p_value = _sign_flip_pvalue(arr, rng, n_permutations)
            delta_rows.append(
                {
                    "dataset_id": dataset_id,
                    "comparison": f"rmtguard_minus_{baseline}",
                    "baseline_method": baseline,
                    "paired_n": int(arr.size),
                    "mean_delta_pairwise_ari": _fmt(float(arr.mean())),
                    "bootstrap_ci_low": _fmt(ci_low),
                    "bootstrap_ci_high": _fmt(ci_high),
                    "sign_flip_pvalue": _fmt(p_value),
                    "interpretation": (
                        "rmtguard_higher"
                        if ci_low > 0
                        else "baseline_higher"
                        if ci_high < 0
                        else "uncertain_or_within_noise"
                    ),
                }
            )
    return stats_rows, delta_rows


def _status_line(stats_rows: list[dict[str, object]], delta_rows: list[dict[str, object]]) -> str:
    datasets = sorted({str(row["dataset_id"]) for row in stats_rows})
    repeats = [
        int(row["n_repeats"])
        for row in stats_rows
        if str(row.get("method", "")) == "rmtguard" and str(row.get("n_repeats", "")).isdigit()
    ]
    min_repeats = min(repeats) if repeats else 0
    if len(datasets) >= 4 and min_repeats >= 10:
        return "manuscript_grade_dataset_count_reached"
    if datasets and min_repeats >= 10:
        return f"pilot_partial_{len(datasets)}_of_4_10_repeat_reached"
    if datasets:
        return "pilot_partial_repeat_count_low"
    return "missing_pairwise_input"


def build_markdown(
    stats_rows: list[dict[str, object]],
    delta_rows: list[dict[str, object]],
    indir: Path,
) -> str:
    datasets = sorted({str(row["dataset_id"]) for row in stats_rows})
    status = _status_line(stats_rows, delta_rows)
    if status == "manuscript_grade_dataset_count_reached":
        missing_items = [
            "1. Add final Seurat v5 and JackStraw/parallel-analysis baselines where computationally feasible.",
            "2. Keep PBMC68k/Zheng 2017 as a diagnostic no-call or stress-test context unless annotation recovery is independently improved.",
            "3. Repeat the same paired-CI table after any algorithm change; do not compare old and new summaries across different splits.",
            "4. Report cluster-number variance alongside stability and annotation recovery.",
        ]
    else:
        missing_items = [
            "1. Extend this report to all four Phase 1 datasets with at least 10 repeats.",
            "2. Add final Seurat v5 and JackStraw/parallel-analysis baselines where computationally feasible.",
            "3. Repeat the same paired-CI table after any algorithm change; do not compare old and new summaries across different splits.",
            "4. Report cluster-number variance alongside stability and annotation recovery.",
        ]
    lines = [
        "# Manuscript-Grade Stability Statistical Report",
        "",
        "Generated by `python scripts/build_manuscript_stability_statistical_report.py`.",
        "",
        "## Status",
        "",
        f"- Current status: `{status}`.",
        f"- Datasets included: `{', '.join(datasets) if datasets else 'none'}`.",
        "- Interpretation boundary: these are benchmark uncertainty estimates from repeated subsampling, not independent biological replicates.",
        "",
        "## RMTGuard Rows",
        "",
    ]
    for row in stats_rows:
        if row["method"] != "rmtguard":
            continue
        lines.append(
            "- `{dataset_id}`: mean pairwise ARI `{mean_pairwise_ari}` "
            "[`{bootstrap_ci_low}`, `{bootstrap_ci_high}`], "
            "n_repeats `{n_repeats}`, pairwise_n `{pairwise_n}`, "
            "mean clusters `{mean_cluster_n}`.".format(**row)
        )
    lines.extend(["", "## Strongest Baseline Deltas", ""])
    by_dataset: dict[str, list[dict[str, object]]] = {}
    for row in delta_rows:
        by_dataset.setdefault(str(row["dataset_id"]), []).append(row)
    for dataset_id, rows in sorted(by_dataset.items()):
        strongest = min(rows, key=lambda row: float(row["mean_delta_pairwise_ari"]))
        lines.append(
            "- `{dataset_id}` hardest comparison: `{comparison}` mean delta "
            "`{mean_delta_pairwise_ari}` CI [`{bootstrap_ci_low}`, `{bootstrap_ci_high}`], "
            "p `{sign_flip_pvalue}`, call `{interpretation}`.".format(**strongest)
        )
    lines.extend(
        [
            "",
            "## Missing Before 20-50 JIF Route",
            "",
            *missing_items,
            "",
            "## Source Artifacts",
            "",
            f"- Input directory: `{_rel(indir)}`",
            f"- Statistics TSV: `{_rel(OUT_STATS)}`",
            f"- Paired deltas TSV: `{_rel(OUT_DELTAS)}`",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--indir", type=Path, default=DEFAULT_INDIR)
    parser.add_argument("--n-bootstrap", type=int, default=2000)
    parser.add_argument("--n-permutations", type=int, default=5000)
    parser.add_argument("--random-state", type=int, default=20260427)
    args = parser.parse_args()

    summary_rows = _read_tsv(args.indir / "stability_summary.tsv")
    pairwise_rows = _read_tsv(args.indir / "stability_pairwise.tsv")
    stats_rows, delta_rows = build_statistics(
        summary_rows,
        pairwise_rows,
        n_bootstrap=args.n_bootstrap,
        n_permutations=args.n_permutations,
        random_state=args.random_state,
    )
    _write_tsv(
        OUT_STATS,
        stats_rows,
        [
            "dataset_id",
            "method",
            "n_repeats",
            "sample_fraction",
            "pairwise_n",
            "mean_pairwise_ari",
            "bootstrap_ci_low",
            "bootstrap_ci_high",
            "mean_cluster_n",
            "mean_n_cells",
        ],
    )
    _write_tsv(
        OUT_DELTAS,
        delta_rows,
        [
            "dataset_id",
            "comparison",
            "baseline_method",
            "paired_n",
            "mean_delta_pairwise_ari",
            "bootstrap_ci_low",
            "bootstrap_ci_high",
            "sign_flip_pvalue",
            "interpretation",
        ],
    )
    _write_text(OUT_MD, build_markdown(stats_rows, delta_rows, args.indir))
    print(_rel(OUT_STATS))
    print(_rel(OUT_DELTAS))
    print(_rel(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
