#!/usr/bin/env python
"""Build paired RMTGuard-versus-official-Seurat annotation statistics.

Author: RMTGuard development team
Date: 2026-05-03
Purpose: Pair RMTGuard v3.3 repeated subsampling rows with official Seurat v5
fixed-PC/elbow/JackStraw rows on the same dataset/repeat split framework and summarize
annotation, batch, cluster-count, and runtime deltas.
Data source: results/ablation/realdata_ablation_annotation_detail.tsv and
results/submission/seurat_matched_pilot/seurat_matched_baseline_detail.tsv.
Method notes: Paired sign-flip tests are used on repeated subsampling deltas.
These are benchmark uncertainty estimates, not independent biological
replicates. Current default inputs target 20 matched repeats for RMTGuard and
official Seurat fixed-PC, elbow, and JackStraw comparators.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RMT_DETAIL = ROOT / "results" / "ablation" / "realdata_ablation_annotation_detail.tsv"
SEURAT_DETAIL = (
    ROOT
    / "results"
    / "submission"
    / "seurat_matched_baseline_detail.tsv"
)
OUT_DIR = ROOT / "results" / "submission"
OUT_DETAIL = OUT_DIR / "rmtguard_seurat_paired_detail.tsv"
OUT_STATS = OUT_DIR / "rmtguard_seurat_paired_stats.tsv"
OUT_STATUS = OUT_DIR / "rmtguard_seurat_paired_status.tsv"
DOC = ROOT / "docs" / "rmtguard_seurat_paired_statistics.md"
FIG_SOURCE = (
    ROOT
    / "results"
    / "figures"
    / "source_data"
    / "figure3_official_seurat_paired_label_delta.tsv"
)
FIG_DIR = ROOT / "figures" / "manuscript"
FIG_STEM = "figure3_official_seurat_paired_label_delta"

DEFAULT_RMT_RUN_LABEL = "subsample80_seurat_matched20"
DEFAULT_SEURAT_RUN_LABEL = "seurat_jackstraw_subsample80_20x20_mtx"
DEFAULT_RMT_ABLATION_ID = "default_v3_3"
SEURAT_METHODS = [
    "seurat_v5_fixed_30",
    "seurat_v5_fixed_50",
    "seurat_v5_elbow",
    "seurat_v5_jackstraw",
]
METRICS = ["label_ari", "batch_ari", "cluster_n", "runtime_seconds"]

DATASET_LABELS = {
    "baron_pancreas": "Baron pancreas",
    "kang_ifnb_pbmc": "Kang IFN-beta PBMC",
    "paul15_hematopoiesis": "Paul15 hematopoiesis",
    "pbmc68k_zheng2017": "PBMC68k/Zheng 2017",
    "pdac_gse263733": "PDAC GSE263733",
}

METHOD_LABELS = {
    "seurat_v5_fixed_30": "Seurat fixed 30 PCs",
    "seurat_v5_fixed_50": "Seurat fixed 50 PCs",
    "seurat_v5_elbow": "Seurat elbow",
    "seurat_v5_jackstraw": "Seurat JackStraw",
}

COLORS = {
    "rmtguard_higher": "#1B7837",
    "seurat_higher": "#B2182B",
    "uncertain_or_within_noise": "#6B7280",
    "grid": "#E6E8EB",
}


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _atomic_write_tsv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, sep="\t", index=False)
    tmp.replace(path)


def _atomic_write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _read_required(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required input table is missing: {path}")
    return pd.read_csv(path, sep="\t")


def _mean_ci(values: np.ndarray, rng: np.random.Generator, n_bootstrap: int) -> tuple[float, float, float]:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return math.nan, math.nan, math.nan
    mean = float(arr.mean())
    if arr.size == 1:
        return mean, mean, mean
    draws = rng.choice(arr, size=(n_bootstrap, arr.size), replace=True)
    means = draws.mean(axis=1)
    return mean, float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def _sign_flip_pvalue(values: np.ndarray, rng: np.random.Generator, n_permutations: int) -> float:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return math.nan
    observed = abs(float(arr.mean()))
    if arr.size <= 15:
        total = 2 ** arr.size
        extreme = 0
        for mask in range(total):
            signs = np.array([1 if (mask >> idx) & 1 else -1 for idx in range(arr.size)])
            extreme += abs(float((arr * signs).mean())) >= observed
        return float((extreme + 1) / (total + 1))
    extreme = 0
    for _ in range(n_permutations):
        signs = rng.choice([-1, 1], size=arr.size, replace=True)
        extreme += abs(float((arr * signs).mean())) >= observed
    return float((extreme + 1) / (n_permutations + 1))


def _bh_adjust(p_values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(p_values, errors="coerce")
    adjusted = pd.Series(np.nan, index=p_values.index, dtype=float)
    valid = numeric.dropna()
    if valid.empty:
        return adjusted
    order = valid.sort_values().index.to_list()
    m = len(order)
    previous = 1.0
    for rank, idx in reversed(list(enumerate(order, start=1))):
        value = min(previous, float(numeric.loc[idx]) * m / rank)
        adjusted.loc[idx] = min(value, 1.0)
        previous = value
    return adjusted


def _format_float(value: object, digits: int = 3) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "NA"
    if math.isnan(number):
        return "NA"
    return f"{number:.{digits}f}"


def build_paired_detail(
    rmt_run_label: str,
    seurat_run_label: str,
    rmt_ablation_id: str,
) -> pd.DataFrame:
    rmt = _read_required(RMT_DETAIL)
    seurat = _read_required(SEURAT_DETAIL)
    rmt = rmt[
        (rmt["run_label"] == rmt_run_label)
        & (rmt["ablation_id"] == rmt_ablation_id)
    ].copy()
    seurat = seurat[
        (seurat["run_label"] == seurat_run_label)
        & (seurat["method_id"].isin(SEURAT_METHODS))
    ].copy()
    if rmt.empty:
        raise ValueError(f"No RMTGuard rows found for run_label={rmt_run_label}.")
    if seurat.empty:
        raise ValueError(f"No Seurat rows found for run_label={seurat_run_label}.")

    rmt_cols = [
        "dataset_id",
        "repeat",
        "analysis_status",
        "no_call_reason",
        "label_ari",
        "label_nmi",
        "batch_ari",
        "batch_nmi",
        "cluster_n",
        "selected_pcs",
        "embedding_pcs",
        "runtime_seconds",
        "peak_memory_mb",
        "n_signal_pcs",
    ]
    rmt = rmt[[col for col in rmt_cols if col in rmt.columns]].rename(
        columns={
            "analysis_status": "rmtguard_analysis_status",
            "no_call_reason": "rmtguard_no_call_reason",
            "label_ari": "rmtguard_label_ari",
            "label_nmi": "rmtguard_label_nmi",
            "batch_ari": "rmtguard_batch_ari",
            "batch_nmi": "rmtguard_batch_nmi",
            "cluster_n": "rmtguard_cluster_n",
            "selected_pcs": "rmtguard_selected_pcs",
            "embedding_pcs": "rmtguard_embedding_pcs",
            "runtime_seconds": "rmtguard_runtime_seconds",
            "peak_memory_mb": "rmtguard_peak_memory_mb",
            "n_signal_pcs": "rmtguard_signal_pcs",
        }
    )
    seurat_cols = [
        "dataset_id",
        "repeat",
        "method_id",
        "method_label",
        "analysis_status",
        "label_ari",
        "label_nmi",
        "batch_ari",
        "batch_nmi",
        "cluster_n",
        "selected_pcs",
        "runtime_seconds",
        "peak_memory_mb",
    ]
    seurat = seurat[[col for col in seurat_cols if col in seurat.columns]].rename(
        columns={
            "method_id": "seurat_method_id",
            "method_label": "seurat_method_label",
            "analysis_status": "seurat_analysis_status",
            "label_ari": "seurat_label_ari",
            "label_nmi": "seurat_label_nmi",
            "batch_ari": "seurat_batch_ari",
            "batch_nmi": "seurat_batch_nmi",
            "cluster_n": "seurat_cluster_n",
            "selected_pcs": "seurat_selected_pcs",
            "runtime_seconds": "seurat_runtime_seconds",
            "peak_memory_mb": "seurat_peak_memory_mb",
        }
    )
    paired = rmt.merge(seurat, on=["dataset_id", "repeat"], how="inner")
    for metric in METRICS:
        paired[f"delta_{metric}"] = (
            pd.to_numeric(paired[f"rmtguard_{metric}"], errors="coerce")
            - pd.to_numeric(paired[f"seurat_{metric}"], errors="coerce")
        )
    paired["dataset_label"] = paired["dataset_id"].map(DATASET_LABELS).fillna(
        paired["dataset_id"]
    )
    paired["seurat_method_label"] = paired["seurat_method_id"].map(METHOD_LABELS).fillna(
        paired["seurat_method_id"]
    )
    paired["paired_evidence_level"] = "paired_overlap"
    ordered = [
        "dataset_id",
        "dataset_label",
        "repeat",
        "seurat_method_id",
        "seurat_method_label",
        "paired_evidence_level",
    ]
    ordered += [col for col in paired.columns if col not in ordered]
    return paired[ordered].sort_values(["dataset_id", "seurat_method_id", "repeat"])


def build_stats(
    paired: pd.DataFrame,
    n_bootstrap: int = 5000,
    n_permutations: int = 5000,
    random_state: int = 20260503,
) -> pd.DataFrame:
    rng = np.random.default_rng(random_state)
    rows: list[dict[str, object]] = []
    for (dataset_id, method_id), group in paired.groupby(["dataset_id", "seurat_method_id"]):
        for metric in METRICS:
            delta_col = f"delta_{metric}"
            rmt_col = f"rmtguard_{metric}"
            seurat_col = f"seurat_{metric}"
            deltas = pd.to_numeric(group[delta_col], errors="coerce").dropna().to_numpy()
            if deltas.size == 0:
                continue
            mean_delta, ci_low, ci_high = _mean_ci(deltas, rng, n_bootstrap)
            p_value = _sign_flip_pvalue(deltas, rng, n_permutations)
            rmt_mean = float(pd.to_numeric(group[rmt_col], errors="coerce").mean())
            seurat_mean = float(pd.to_numeric(group[seurat_col], errors="coerce").mean())
            interpretation = (
                "rmtguard_higher"
                if ci_low > 0
                else "seurat_higher"
                if ci_high < 0
                else "uncertain_or_within_noise"
            )
            if metric in {"batch_ari", "runtime_seconds"}:
                interpretation = (
                    "rmtguard_lower"
                    if ci_high < 0
                    else "seurat_lower"
                    if ci_low > 0
                    else "uncertain_or_within_noise"
                )
            rows.append(
                {
                    "dataset_id": dataset_id,
                    "dataset_label": DATASET_LABELS.get(dataset_id, dataset_id),
                    "seurat_method_id": method_id,
                    "seurat_method_label": METHOD_LABELS.get(method_id, method_id),
                    "metric": metric,
                    "paired_n": int(deltas.size),
                    "rmtguard_mean": rmt_mean,
                    "seurat_mean": seurat_mean,
                    "mean_delta_rmtguard_minus_seurat": mean_delta,
                    "bootstrap_ci_low": ci_low,
                    "bootstrap_ci_high": ci_high,
                    "sign_flip_pvalue": p_value,
                    "interpretation": interpretation,
                    "evidence_level": "paired20_manuscript_candidate"
                    if deltas.size >= 20
                    else "paired10_pilot"
                    if deltas.size >= 10
                    else "insufficient_overlap",
                }
            )
    stats = pd.DataFrame(rows)
    if stats.empty:
        return stats
    stats["bh_fdr_within_metric"] = np.nan
    for metric, idx in stats.groupby("metric").groups.items():
        stats.loc[idx, "bh_fdr_within_metric"] = _bh_adjust(
            stats.loc[idx, "sign_flip_pvalue"]
        )
    return stats.sort_values(["metric", "dataset_id", "seurat_method_id"])


def build_status(stats: pd.DataFrame, paired: pd.DataFrame) -> pd.DataFrame:
    label_stats = stats[stats["metric"] == "label_ari"].copy()
    datasets = set(label_stats["dataset_id"].astype(str)) if not label_stats.empty else set()
    methods = set(label_stats["seurat_method_id"].astype(str)) if not label_stats.empty else set()
    min_paired = int(label_stats["paired_n"].min()) if not label_stats.empty else 0
    rmt_repeats = (
        paired.groupby("dataset_id")["repeat"].nunique().min()
        if not paired.empty
        else 0
    )
    paired_status = (
        "paired20_manuscript_candidate"
        if len(datasets) >= 4 and len(methods) >= 4 and min_paired >= 20
        else "paired10_pilot_pass"
        if len(datasets) >= 4 and len(methods) >= 3 and min_paired >= 10
        else "incomplete"
    )
    rows = [
        {
            "check_id": "paired_overlap",
            "status": paired_status,
            "scope": f"{len(datasets)}_datasets_{len(methods)}_seurat_methods_min_paired_{min_paired}",
            "evidence": _rel(OUT_STATS),
            "remaining_work": "Freeze this paired table after final comparator decisions."
            if min_paired >= 20
            else "Scale RMTGuard repeated annotation rows to 20 repeats to match the official Seurat fixed-PC/elbow/JackStraw depth.",
        },
        {
            "check_id": "rmtguard_repeat_depth",
            "status": "pilot10_only" if int(rmt_repeats) < 20 else "manuscript_candidate",
            "scope": f"min_rmtguard_repeats_{int(rmt_repeats)}",
            "evidence": _rel(RMT_DETAIL),
            "remaining_work": "No repeat-depth blocker remains for fixed-PC/elbow/JackStraw paired statistics."
            if int(rmt_repeats) >= 20
            else "Run repeats 10-19 for RMTGuard default on the same split framework before claiming manuscript-grade paired statistics.",
        },
        {
            "check_id": "paired_statistics_claim_status",
            "status": "partial_not_manuscript_grade"
            if min_paired >= 10 and int(rmt_repeats) < 20
            else "manuscript_candidate"
            if min_paired >= 20
            else "blocked",
            "scope": "annotation_batch_cluster_runtime",
            "evidence": f"{_rel(OUT_DETAIL)};{_rel(OUT_STATS)}",
            "remaining_work": "Treat as manuscript-candidate for official Seurat fixed-PC, elbow, and JackStraw paired annotation statistics; additional datasets remain a separate blocker."
            if min_paired >= 20
            else "Use this table as reviewer-facing pilot evidence only; regenerate after RMTGuard reaches 20 repeats and comparator table is frozen.",
        },
    ]
    return pd.DataFrame(rows)


def render_label_delta(stats: pd.DataFrame) -> None:
    plot = stats[stats["metric"] == "label_ari"].copy()
    if plot.empty:
        return
    plot["row_label"] = (
        plot["dataset_label"].astype(str)
        + " | "
        + plot["seurat_method_label"].astype(str).str.replace("Seurat ", "", regex=False)
    )
    plot = plot.sort_values(["dataset_id", "seurat_method_id"], ascending=[True, True])
    y = np.arange(len(plot))
    mean = plot["mean_delta_rmtguard_minus_seurat"].astype(float).to_numpy()
    low = plot["bootstrap_ci_low"].astype(float).to_numpy()
    high = plot["bootstrap_ci_high"].astype(float).to_numpy()
    xerr = np.vstack([mean - low, high - mean])
    colors = [COLORS.get(item, COLORS["uncertain_or_within_noise"]) for item in plot["interpretation"]]

    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 8.5,
            "axes.titlesize": 10,
            "axes.labelsize": 8.8,
            "xtick.labelsize": 7.8,
            "ytick.labelsize": 7.4,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    fig_height = max(4.8, 0.34 * len(plot) + 1.4)
    fig, ax = plt.subplots(figsize=(7.2, fig_height), constrained_layout=True)
    ax.axvline(0, color="#111827", linewidth=1.0)
    ax.errorbar(
        mean,
        y,
        xerr=xerr,
        fmt="none",
        ecolor="#2F3437",
        elinewidth=1.0,
        capsize=2.5,
        zorder=1,
    )
    ax.scatter(mean, y, c=colors, s=34, edgecolor="#2F3437", linewidth=0.4, zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels(plot["row_label"])
    ax.invert_yaxis()
    ax.set_xlabel("Label ARI delta (RMTGuard minus official Seurat)")
    ax.set_title("Paired annotation recovery on matched subsampling repeats", loc="left")
    ax.grid(axis="x", color=COLORS["grid"], linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for suffix, dpi in [(".png", 300), (".pdf", 300), (".tiff", 300)]:
        path = FIG_DIR / f"{FIG_STEM}{suffix}"
        tmp = path.with_suffix(path.suffix + ".tmp")
        fig.savefig(tmp, format=suffix.lstrip("."), dpi=dpi, bbox_inches="tight", facecolor="white")
        tmp.replace(path)
    plt.close(fig)


def build_doc(
    stats: pd.DataFrame,
    status: pd.DataFrame,
    rmt_run_label: str,
    seurat_run_label: str,
) -> str:
    label_stats = stats[stats["metric"] == "label_ari"].copy()
    rows = [
        "# RMTGuard versus official Seurat paired statistics",
        "",
        "Generated by `python scripts/build_rmtguard_seurat_paired_statistics.py`.",
        "",
        "## Bottom Line",
        "",
        "- Direct comparison is now available for RMTGuard default v3.3 against official Seurat v5 fixed 30 PCs, fixed 50 PCs, elbow-rule PCs, and JackStraw PCs.",
        f"- RMTGuard run label: `{rmt_run_label}`.",
        f"- Official Seurat run label: `{seurat_run_label}`.",
        "- Evidence level is assigned from the minimum paired repeat depth recorded in the status table.",
        "",
        "## Status Checks",
        "",
        "| Check | Status | Scope | Remaining work |",
        "| --- | --- | --- | --- |",
    ]
    for row in status.to_dict("records"):
        rows.append(
            f"| {row['check_id']} | {row['status']} | {row['scope']} | {row['remaining_work']} |"
        )
    rows.extend(
        [
            "",
            "## Label ARI Paired Deltas",
            "",
            "| Dataset | Seurat method | n | RMTGuard mean | Seurat mean | Delta | 95% CI | FDR | Interpretation |",
            "| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | --- |",
        ]
    )
    for row in label_stats.to_dict("records"):
        rows.append(
            f"| {row['dataset_label']} | {row['seurat_method_label']} | {int(row['paired_n'])} | "
            f"{_format_float(row['rmtguard_mean'])} | {_format_float(row['seurat_mean'])} | "
            f"{_format_float(row['mean_delta_rmtguard_minus_seurat'])} | "
            f"{_format_float(row['bootstrap_ci_low'])}-{_format_float(row['bootstrap_ci_high'])} | "
            f"{_format_float(row['bh_fdr_within_metric'])} | {row['interpretation']} |"
        )
    rows.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "Positive deltas indicate higher annotation ARI for RMTGuard on the matched split; negative deltas indicate higher annotation ARI for Seurat. PBMC68k remains a diagnostic no-call stress context because both method families have weak absolute annotation recovery.",
            "",
            "## Source Artifacts",
            "",
            f"- Paired detail TSV: `{_rel(OUT_DETAIL)}`",
            f"- Paired statistics TSV: `{_rel(OUT_STATS)}`",
            f"- Status TSV: `{_rel(OUT_STATUS)}`",
            f"- Figure source data: `{_rel(FIG_SOURCE)}`",
            f"- Figure PNG/PDF/TIFF stem: `{_rel(FIG_DIR / FIG_STEM)}`",
        ]
    )
    return "\n".join(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rmt-run-label", default=DEFAULT_RMT_RUN_LABEL)
    parser.add_argument("--seurat-run-label", default=DEFAULT_SEURAT_RUN_LABEL)
    parser.add_argument("--rmt-ablation-id", default=DEFAULT_RMT_ABLATION_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paired = build_paired_detail(
        rmt_run_label=args.rmt_run_label,
        seurat_run_label=args.seurat_run_label,
        rmt_ablation_id=args.rmt_ablation_id,
    )
    stats = build_stats(paired)
    status = build_status(stats, paired)
    label_source = stats[stats["metric"] == "label_ari"].copy()
    _atomic_write_tsv(paired, OUT_DETAIL)
    _atomic_write_tsv(stats, OUT_STATS)
    _atomic_write_tsv(status, OUT_STATUS)
    _atomic_write_tsv(label_source, FIG_SOURCE)
    render_label_delta(stats)
    _atomic_write_text(
        build_doc(stats, status, args.rmt_run_label, args.seurat_run_label),
        DOC,
    )
    print(_rel(OUT_DETAIL))
    print(_rel(OUT_STATS))
    print(_rel(OUT_STATUS))
    print(_rel(FIG_SOURCE))
    print(_rel(DOC))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
