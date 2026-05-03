from __future__ import annotations

"""Render publication-style main figures for the RMTGuard manuscript package.

Author: RMTGuard development team
Date: 2026-05-01
Purpose: Regenerate Figures 1-5 from source-data tables using a consistent,
journal-style visual system with vector PDF and 300 dpi raster outputs.
Data source: `results/figures/source_data/*`.
Method notes: This script only changes visual presentation. It does not change
the underlying benchmark values or manuscript claims.
"""

import ast
import csv
import textwrap
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "results" / "figures" / "source_data"
OUT_DIR = ROOT / "figures" / "manuscript"
MANIFEST = OUT_DIR / "rendered_figure_manifest.tsv"

FIGURE_SPECS = [
    ("Figure 1", "figure1_rmtguard_algorithm_diagnostics"),
    ("Figure 2", "figure2_synthetic_benchmarks"),
    ("Figure 3", "figure3_public_benchmarks"),
    ("Figure 4", "figure4_pdac_tme_showcase"),
    ("Figure 5", "figure5_reproducibility_release_audit"),
]

COLORS = {
    "rmtguard": "#2E6F9E",
    "rmtguard_strict_signal": "#8FBAD9",
    "scanpy_default_like": "#7A7A7A",
    "fixed_pcs_30": "#5AAE61",
    "fixed_pcs_50": "#A6D96A",
    "elbow_rule": "#D55E00",
    "parallel_analysis": "#CC79A7",
    "jackstraw_like": "#6A51A3",
    "pass": "#1B7837",
    "pending": "#8073AC",
    "fail": "#B2182B",
    "borderline": "#E08214",
    "neutral": "#6B7280",
    "light_grid": "#E6E8EB",
}

METHOD_LABELS = {
    "rmtguard": "RMTGuard",
    "rmtguard_strict_signal": "RMTGuard\nstrict",
    "scanpy_default_like": "Scanpy-like",
    "fixed_pcs_30": "fixed 30 PCs",
    "fixed_pcs_50": "fixed 50 PCs",
    "elbow_rule": "elbow",
    "parallel_analysis": "parallel\nanalysis",
    "jackstraw_like": "JackStraw-like",
}

DECISION_LABELS = {
    "diagnostic_no_call": "diagnostic no-call",
    "callable_with_caveat": "callable with caveat",
    "callable_bounded": "callable",
    "positive_control_pass": "positive control",
    "stress_monitor": "stress monitor",
}

DECISION_COLORS = {
    "diagnostic_no_call": COLORS["pending"],
    "callable_with_caveat": COLORS["borderline"],
    "callable_bounded": COLORS["pass"],
    "positive_control_pass": COLORS["pass"],
    "stress_monitor": COLORS["neutral"],
}

DATASET_LABELS = {
    "pbmc3k_10x": "PBMC3k",
    "kang_ifnb_pbmc": "Kang IFN-beta\nPBMC",
    "baron_pancreas": "Baron\npancreas",
    "pbmc68k_zheng2017": "PBMC68k",
}

SCENARIO_LABELS = {
    "pure_null": "pure null",
    "planted_low_rank": "planted low-rank",
    "rare_state": "rare state",
    "batch_effect": "batch effect",
    "dropout_stress": "dropout stress",
    "continuous_trajectory": "continuous trajectory",
    "overclustering_stress": "overclustering stress",
}

PDAC_LABELS = {
    "pdac_gse154778": "GSE154778",
    "pdac_gse263733": "GSE263733",
}

MARKER_LABELS = {
    "b_plasma": "B/plasma",
    "caf_fibroblast": "CAF/fibroblast",
    "ductal_malignant_context": "ductal malignant",
    "endothelial": "endothelial",
    "immune_myeloid": "immune/myeloid",
    "t_nk": "T/NK",
}


def _apply_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 8.5,
            "axes.titlesize": 9.5,
            "axes.labelsize": 8.5,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.2,
            "figure.titlesize": 11,
            "axes.linewidth": 0.8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.dpi": 300,
        }
    )


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _atomic_save(fig: plt.Figure, path: Path, dpi: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    save_kwargs = {
        "format": path.suffix.lstrip("."),
        "dpi": dpi,
        "bbox_inches": "tight",
        "facecolor": "white",
    }
    if path.suffix.lower() != ".tiff":
        save_kwargs["metadata"] = {"Creator": "RMTGuard render_main_figures.py"}
    fig.savefig(tmp, **save_kwargs)
    tmp.replace(path)


def _save_figure(fig: plt.Figure, stem: str) -> tuple[Path, Path, Path]:
    png = OUT_DIR / f"{stem}.png"
    pdf = OUT_DIR / f"{stem}.pdf"
    tif = OUT_DIR / f"{stem}.tiff"
    _atomic_save(fig, png, dpi=300)
    _atomic_save(fig, pdf, dpi=300)
    _atomic_save(fig, tif, dpi=300)
    plt.close(fig)
    return png, pdf, tif


def _read_tsv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _num(values: Iterable[object]) -> list[float]:
    out = []
    for value in values:
        try:
            out.append(float(value))
        except (TypeError, ValueError):
            out.append(np.nan)
    return out


def _diagnostic_value(
    df: pd.DataFrame, group: str, metric: str, default: object = np.nan
) -> object:
    hit = df[(df["diagnostic_group"] == group) & (df["metric"] == metric)]
    if hit.empty:
        return default
    value = hit.iloc[0]["value"]
    if isinstance(value, str):
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value
    return value


def _status_color(status: str) -> str:
    return COLORS.get(str(status).lower(), COLORS["neutral"])


def _clean_axis(ax: plt.Axes, xgrid: bool = False) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#2F3437")
    ax.spines["bottom"].set_color("#2F3437")
    ax.grid(
        axis="x" if xgrid else "y",
        color=COLORS["light_grid"],
        linewidth=0.7,
        alpha=1,
    )
    ax.set_axisbelow(True)


def _panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.12,
        1.08,
        label,
        transform=ax.transAxes,
        fontsize=11,
        fontweight="bold",
        va="top",
        ha="left",
    )


def _title(fig: plt.Figure, text: str) -> None:
    # Journal figures usually carry the figure title in the caption. Keeping a
    # large in-panel title causes collisions with panel labels after tight
    # export, so this function intentionally leaves the canvas title-free.
    return None


def _label_methods(values: Iterable[str]) -> list[str]:
    return [
        METHOD_LABELS.get(str(value), str(value).replace("_", " ")) for value in values
    ]


def _label_datasets(values: Iterable[str]) -> list[str]:
    return [
        DATASET_LABELS.get(str(value), str(value).replace("_", " ")) for value in values
    ]


def _label_scenarios(values: Iterable[str]) -> list[str]:
    return [
        SCENARIO_LABELS.get(str(value), str(value).replace("_", " "))
        for value in values
    ]


def _label_pdac(values: Iterable[str]) -> list[str]:
    return [
        PDAC_LABELS.get(str(value), str(value).replace("_", " ")) for value in values
    ]


def _label_units(values: Iterable[str]) -> list[str]:
    return [
        textwrap.fill(str(value).replace("_", " "), width=18, break_long_words=False)
        for value in values
    ]


def _wrap(values: Iterable[str], width: int = 16) -> list[str]:
    return [
        textwrap.fill(str(value).replace("_", " "), width=width, break_long_words=False)
        for value in values
    ]


def _status_badge(ax: plt.Axes, x: float, y: float, text: str, status: str) -> None:
    ax.text(
        x,
        y,
        text,
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=8,
        color="white",
        bbox={
            "boxstyle": "round,pad=0.28,rounding_size=0.08",
            "facecolor": _status_color(status),
            "edgecolor": "none",
        },
    )


def figure1() -> tuple[plt.Figure, list[Path]]:
    diagnostics_path = SOURCE_DIR / "figure1_algorithm_diagnostics.tsv"
    pc_records_path = SOURCE_DIR / "figure1_embedding_pc_records.tsv"
    diag = _read_tsv(diagnostics_path)
    pcs = _read_tsv(pc_records_path)

    eigenvalues = _diagnostic_value(diag, "pc_diagnostics", "top_eigenvalues", [])
    mp_edge = float(_diagnostic_value(diag, "pc_diagnostics", "mp_edge"))
    tw_edge = float(_diagnostic_value(diag, "pc_diagnostics", "tw_edge"))
    selected_edge = float(_diagnostic_value(diag, "pc_diagnostics", "selected_edge"))
    hvg_grid = _diagnostic_value(diag, "hvg_diagnostics", "grid", [])
    signal_by_hvg = _diagnostic_value(diag, "hvg_diagnostics", "signal_pcs_by_hvg", [])

    fig = plt.figure(figsize=(7.2, 5.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.05])
    axes = np.array(
        [
            [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])],
            [fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])],
        ]
    )

    ax = axes[0, 0]
    pc_index = np.arange(1, len(eigenvalues) + 1)
    ax.plot(
        pc_index,
        eigenvalues,
        marker="o",
        markersize=3.8,
        linewidth=1.7,
        color=COLORS["rmtguard"],
    )
    ax.axhline(mp_edge, color="#4D4D4D", linestyle="--", linewidth=1.1, label="MP edge")
    ax.axhline(
        tw_edge,
        color=COLORS["elbow_rule"],
        linestyle=":",
        linewidth=1.5,
        label="TW proxy",
    )
    ax.axhline(
        selected_edge,
        color=COLORS["fixed_pcs_30"],
        linestyle="-.",
        linewidth=1.3,
        label="selected edge",
    )
    ax.set_title("Spectrum decision rule", loc="left")
    ax.set_xlabel("PC rank")
    ax.set_ylabel("Eigenvalue")
    ax.legend(frameon=False, loc="upper right", handlelength=2.5)
    _clean_axis(ax)
    _panel_label(ax, "A")

    ax = axes[0, 1]
    ax.bar(
        [str(x) for x in hvg_grid],
        signal_by_hvg,
        color="#8EC1DA",
        edgecolor="#497D99",
        linewidth=0.5,
    )
    ax.set_title("HVG spectral plateau", loc="left")
    ax.set_xlabel("HVG count")
    ax.set_ylabel("Signal PCs")
    _clean_axis(ax)
    _panel_label(ax, "B")

    ax = axes[1, 0]
    shown = pcs.head(20).copy()
    accepted = shown["accepted"].astype(str).str.lower() == "true"
    colors = np.where(accepted, COLORS["fixed_pcs_30"], "#C9CDD1")
    ax.bar(
        shown["pc"].astype(int),
        shown["stability"].astype(float),
        color=colors,
        width=0.78,
    )
    ax.axhline(0.75, color=COLORS["fail"], linestyle="--", linewidth=1.1)
    ax.text(
        20.2,
        0.75,
        "acceptance threshold",
        va="center",
        ha="right",
        fontsize=7.2,
        color=COLORS["fail"],
    )
    ax.set_title("Embedding PC reproducibility", loc="left")
    ax.set_xlabel("PC")
    ax.set_ylabel("Median absolute correlation")
    ax.set_ylim(0, 1.05)
    _clean_axis(ax)
    _panel_label(ax, "C")

    ax = axes[1, 1]
    ax.axis("off")
    rows = [
        (
            "Strict signal PCs",
            _diagnostic_value(diag, "embedding_diagnostics", "strict_signal_pcs"),
        ),
        (
            "Near-edge candidates",
            _diagnostic_value(diag, "embedding_diagnostics", "near_edge_candidate_pcs"),
        ),
        (
            "Accepted embedding PCs",
            _diagnostic_value(diag, "embedding_diagnostics", "accepted_embedding_pcs"),
        ),
        ("Selected HVGs", _diagnostic_value(diag, "hvg_diagnostics", "selected_hvg_n")),
        (
            "Bulk KS",
            f"{float(_diagnostic_value(diag, 'pc_diagnostics', 'bulk_ks')):.3f}",
        ),
    ]
    table = ax.table(
        cellText=[[key, value] for key, value in rows],
        colLabels=["Diagnostic", "Value"],
        loc="center",
        cellLoc="left",
        colLoc="left",
        bbox=[0.02, 0.05, 0.96, 0.78],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    for (r, _c), cell in table.get_celld().items():
        cell.set_edgecolor("#D1D5DB")
        if r == 0:
            cell.set_facecolor("#E8F1F6")
            cell.set_text_props(weight="bold")
    ax.set_title("Run diagnostics", loc="left")
    _status_badge(ax, 0.02, 0.91, "callable", "pass")
    _panel_label(ax, "D")

    _title(fig, "Figure 1. RMTGuard algorithm diagnostics")
    return fig, [diagnostics_path, pc_records_path]


def figure2() -> tuple[plt.Figure, list[Path]]:
    path = SOURCE_DIR / "figure2_synthetic_benchmark_summary.csv"
    no_call_path = SOURCE_DIR / "figure2_no_call_summary.tsv"
    df = _read_csv(path)
    no_call = _read_tsv(no_call_path)
    rmt = df[df["method"] == "rmtguard"].copy()
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 5.6), constrained_layout=True)

    ax = axes[0, 0]
    order = list(rmt["scenario"])
    ax.barh(
        _wrap(_label_scenarios(order), 18),
        _num(rmt["n_signal_pcs"]),
        color="#8EC1DA",
        edgecolor="#497D99",
        linewidth=0.5,
    )
    ax.set_title("Signal PCs admitted", loc="left")
    ax.set_xlabel("Signal PCs")
    _clean_axis(ax, xgrid=True)
    _panel_label(ax, "A")

    ax = axes[0, 1]
    ari = df.dropna(subset=["ari"]).copy()
    pivot = ari.pivot_table(
        index="scenario", columns="method", values="ari", aggfunc="first"
    )
    selected_methods = [
        m
        for m in ["rmtguard", "fixed_pcs_30", "scanpy_default_like"]
        if m in pivot.columns
    ]
    x = np.arange(len(pivot.index))
    width = 0.24
    for idx, method in enumerate(selected_methods):
        ax.bar(
            x + (idx - 1) * width,
            pivot[method].astype(float),
            width=width,
            label=METHOD_LABELS.get(method, method),
            color=COLORS.get(method, COLORS["neutral"]),
        )
    ax.set_xticks(x)
    ax.set_xticklabels(
        _wrap(_label_scenarios(pivot.index), 13), rotation=30, ha="right"
    )
    ax.set_title("Synthetic label recovery", loc="left")
    ax.set_ylabel("ARI")
    ax.set_ylim(0, 1.05)
    ax.legend(frameon=False, loc="upper left")
    _clean_axis(ax)
    _panel_label(ax, "B")

    ax = axes[1, 0]
    ax.barh(
        _wrap(_label_scenarios(order), 18),
        _num(rmt["cluster_n"]),
        color="#B9A6D3",
        edgecolor="#7B6AA6",
        linewidth=0.5,
    )
    ax.set_title("Cluster counts under stress", loc="left")
    ax.set_xlabel("Clusters")
    _clean_axis(ax, xgrid=True)
    _panel_label(ax, "C")

    ax = axes[1, 1]
    hard = no_call[
        no_call["expected_behavior"].isin(["diagnostic_no_call", "positive_call"])
    ].copy()
    decision_score = (
        hard["decision"].map({"pass": 1.0, "monitor": 0.5, "fail": 0.0}).fillna(0.0)
    )
    ax.barh(
        _wrap(_label_scenarios(hard["scenario"]), 18),
        decision_score,
        color=[_status_color(x) for x in hard["decision"]],
    )
    ax.set_title("Diagnostic no-call validation", loc="left")
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Pass score")
    _clean_axis(ax, xgrid=True)
    _panel_label(ax, "D")

    _title(fig, "Figure 2. Synthetic noise-control benchmarks")
    return fig, [path, no_call_path]


def figure3() -> tuple[plt.Figure, list[Path]]:
    public_path = SOURCE_DIR / "figure3_public_benchmark_summary.tsv"
    stability_path = SOURCE_DIR / "figure3_pbmc3k_stability_summary.tsv"
    decision_path = SOURCE_DIR / "figure3_callability_decision_map.tsv"
    public = _read_tsv(public_path)
    stability = _read_tsv(stability_path)
    decisions = _read_tsv(decision_path)
    fig, axes = plt.subplots(2, 2, figsize=(7.6, 5.9), constrained_layout=True)

    ax = axes[0, 0]
    ari = public.dropna(subset=["ari"]).copy()
    wanted = ["rmtguard", "fixed_pcs_30", "elbow_rule", "scanpy_default_like"]
    ari = ari[ari["method"].isin(wanted)]
    pivot = ari.pivot_table(
        index="dataset_id", columns="method", values="ari", aggfunc="first"
    ).reindex(columns=wanted)
    im = ax.imshow(
        pivot.to_numpy(dtype=float), aspect="auto", cmap="YlGnBu", vmin=0, vmax=1
    )
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels(_label_datasets(pivot.index))
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels(_label_methods(pivot.columns), rotation=35, ha="right")
    ax.set_title("Annotation recovery", loc="left")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            value = pivot.iloc[i, j]
            if pd.notna(value):
                ax.text(
                    j,
                    i,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=7.2,
                    color="#1F2933",
                )
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03, label="ARI")
    _panel_label(ax, "A")

    ax = axes[0, 1]
    stab = stability.copy()
    heat = stab.pivot_table(
        index="dataset_id",
        columns="method",
        values="mean_pairwise_ari",
        aggfunc="first",
    )
    methods = [
        m
        for m in [
            "rmtguard",
            "fixed_pcs_30",
            "elbow_rule",
            "scanpy_default_like",
            "jackstraw_like",
        ]
        if m in heat.columns
    ]
    heat = heat.reindex(columns=methods)
    im = ax.imshow(
        heat.to_numpy(dtype=float), aspect="auto", cmap="RdYlGn", vmin=0, vmax=1
    )
    ax.set_yticks(np.arange(len(heat.index)))
    ax.set_yticklabels(_label_datasets(heat.index))
    ax.set_xticks(np.arange(len(heat.columns)))
    ax.set_xticklabels(_label_methods(heat.columns), rotation=35, ha="right")
    ax.set_title("Subsampling stability", loc="left")
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            value = heat.iloc[i, j]
            if pd.notna(value):
                ax.text(
                    j,
                    i,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=7.2,
                    color="#111827",
                )
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03, label="mean pairwise ARI")
    _panel_label(ax, "B")

    ax = axes[1, 0]
    rmt = public[public["method"] == "rmtguard"].copy()
    y = np.arange(len(rmt))
    ax.barh(
        y - 0.18,
        _num(rmt["n_signal_pcs"]),
        height=0.34,
        label="strict signal PCs",
        color=COLORS["rmtguard"],
    )
    ax.barh(
        y + 0.18,
        _num(rmt["accepted_embedding_pcs"]),
        height=0.34,
        label="embedding PCs",
        color=COLORS["fixed_pcs_30"],
    )
    ax.set_yticks(y)
    ax.set_yticklabels(_label_datasets(rmt["dataset_id"]))
    ax.set_xlabel("PC count")
    ax.set_title("RMTGuard PC decisions", loc="left")
    ax.legend(frameon=False, loc="lower right")
    _clean_axis(ax, xgrid=True)
    _panel_label(ax, "C")

    ax = axes[1, 1]
    real_decisions = decisions[decisions["unit_type"] == "real_public"].copy()
    order = list(rmt["dataset_id"])
    real_decisions["_order"] = real_decisions["unit_id"].map(
        {unit_id: idx for idx, unit_id in enumerate(order)}
    )
    real_decisions = real_decisions.sort_values("_order")
    y = np.arange(len(real_decisions))
    colors = [
        DECISION_COLORS.get(str(decision), COLORS["neutral"])
        for decision in real_decisions["decision"]
    ]
    scores = real_decisions["decision_score"].astype(float)
    ax.barh(y, scores, color=colors)
    ax.axvline(0.50, color="#6B7280", linestyle=":", linewidth=1.0)
    for i, row in enumerate(real_decisions.itertuples(index=False)):
        label = DECISION_LABELS.get(
            str(row.decision), str(row.decision).replace("_", " ")
        )
        x = min(float(row.decision_score) + 0.03, 0.92)
        ax.text(x, i, label, va="center", fontsize=7.0)
    ax.set_yticks(y)
    ax.set_yticklabels(_label_datasets(real_decisions["unit_id"]))
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Decision score")
    ax.set_title("Callability decision map", loc="left")
    _clean_axis(ax, xgrid=True)
    _panel_label(ax, "D")

    _title(fig, "Figure 3. Public real-data benchmarks")
    return fig, [public_path, stability_path, decision_path]


def figure4() -> tuple[plt.Figure, list[Path]]:
    summary_path = SOURCE_DIR / "figure4_pdac_tme_showcase_summary.tsv"
    marker_path = SOURCE_DIR / "figure4_pdac_tme_cluster_marker_summary.tsv"
    summary = _read_tsv(summary_path)
    markers = _read_tsv(marker_path)
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 5.8), constrained_layout=True)

    ax = axes[0, 0]
    y = np.arange(len(summary))
    ax.barh(
        y - 0.18,
        summary["cluster_n"].astype(float),
        height=0.34,
        label="clusters",
        color=COLORS["parallel_analysis"],
    )
    ax.barh(
        y + 0.18,
        summary["accepted_embedding_pcs"].astype(float),
        height=0.34,
        label="embedding PCs",
        color=COLORS["fixed_pcs_30"],
    )
    ax.set_yticks(y)
    ax.set_yticklabels(_wrap(_label_pdac(summary["dataset_id"]), 16))
    ax.set_xlabel("Count")
    ax.set_title("PDAC/TME run summary", loc="left")
    ax.legend(frameon=False, loc="lower right")
    _clean_axis(ax, xgrid=True)
    _panel_label(ax, "A")

    ax = axes[0, 1]
    ari = pd.to_numeric(summary["label_ari"].replace("nan", np.nan), errors="coerce")
    nmi = pd.to_numeric(summary["label_nmi"].replace("nan", np.nan), errors="coerce")
    x = np.arange(len(summary))
    ax.bar(x - 0.18, ari.fillna(0), width=0.34, label="ARI", color=COLORS["rmtguard"])
    ax.bar(x + 0.18, nmi.fillna(0), width=0.34, label="NMI", color="#8EC1DA")
    ax.set_xticks(x)
    ax.set_xticklabels(
        _wrap(_label_pdac(summary["dataset_id"]), 14), rotation=25, ha="right"
    )
    ax.set_ylim(0, 1.05)
    ax.set_title("External label validation", loc="left")
    ax.legend(frameon=False, loc="upper left")
    _clean_axis(ax)
    _panel_label(ax, "B")

    ax = axes[1, 0]
    score_cols = [col for col in markers.columns if col.startswith("score_")]
    heat = markers[score_cols].astype(float).to_numpy()
    im = ax.imshow(heat, aspect="auto", cmap="viridis")
    ax.set_yticks(np.arange(len(markers)))
    ax.set_yticklabels(
        [
            f"{PDAC_LABELS.get(str(d), str(d))} C{c}"
            for d, c in zip(markers["dataset_id"], markers["cluster"])
        ],
        fontsize=6.2,
    )
    ax.set_xticks(np.arange(len(score_cols)))
    ax.set_xticklabels(
        [
            MARKER_LABELS.get(
                col.replace("score_", ""), col.replace("score_", "").replace("_", " ")
            )
            for col in score_cols
        ],
        rotation=35,
        ha="right",
    )
    ax.set_title("Cluster marker signatures", loc="left")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03, label="mean score")
    _panel_label(ax, "C")

    ax = axes[1, 1]
    ax.scatter(
        markers["n_cells"].astype(float),
        markers["metastasis_fraction"].astype(float),
        s=42,
        color=COLORS["elbow_rule"],
        edgecolor="white",
        linewidth=0.7,
    )
    ax.set_xlabel("Cluster cells")
    ax.set_ylabel("Metastasis fraction")
    ax.set_title("Primary/metastasis composition", loc="left")
    _clean_axis(ax)
    _panel_label(ax, "D")

    _title(fig, "Figure 4. PDAC/TME public showcase")
    return fig, [summary_path, marker_path]


def figure5() -> tuple[plt.Figure, list[Path]]:
    runtime_path = SOURCE_DIR / "figure5_runtime_memory_summary.tsv"
    gates_path = SOURCE_DIR / "figure5_gate_evidence.tsv"
    ablation_path = SOURCE_DIR / "figure5_ablation_stability_summary.tsv"
    runtime = _read_tsv(runtime_path)
    gates = _read_tsv(gates_path)
    ablation = _read_tsv(ablation_path)
    fig, axes = plt.subplots(2, 2, figsize=(7.6, 5.8), constrained_layout=True)

    ax = axes[0, 0]
    runtime_sorted = runtime.sort_values("runtime_seconds", ascending=True)
    ax.barh(
        _label_units(runtime_sorted["unit_id"]),
        runtime_sorted["runtime_seconds"].astype(float),
        color="#F4A261",
    )
    ax.set_title("Runtime by benchmark unit", loc="left")
    ax.set_xlabel("Seconds")
    _clean_axis(ax, xgrid=True)
    _panel_label(ax, "A")

    ax = axes[0, 1]
    mem_sorted = runtime.sort_values("peak_memory_mb", ascending=True)
    ax.barh(
        _label_units(mem_sorted["unit_id"]),
        mem_sorted["peak_memory_mb"].astype(float),
        color="#9CC9DD",
    )
    ax.set_title("Peak memory by benchmark unit", loc="left")
    ax.set_xlabel("MB")
    _clean_axis(ax, xgrid=True)
    _panel_label(ax, "B")

    ax = axes[1, 0]
    counts = (
        gates["status"]
        .value_counts()
        .reindex(["pass", "pending", "fail", "borderline"])
        .dropna()
    )
    ax.bar(counts.index, counts.values, color=[_status_color(x) for x in counts.index])
    for i, value in enumerate(counts.values):
        ax.text(i, value + 0.08, str(int(value)), ha="center", va="bottom", fontsize=8)
    ax.set_title("Submission gate status", loc="left")
    ax.set_ylabel("Gate count")
    _clean_axis(ax)
    _panel_label(ax, "C")

    ax = axes[1, 1]
    subset = ablation[
        (ablation["dataset_id"] == "pbmc3k_10x")
        & (
            (
                (ablation["ablation_id"] == "strict_signal_embedding")
                & (
                    ablation["method"].isin(
                        [
                            "rmtguard",
                            "scanpy_default_like",
                            "fixed_pcs_30",
                            "elbow_rule",
                        ]
                    )
                )
            )
            | (
                (
                    ablation["ablation_id"].isin(
                        ["min_embedding_pcs_10", "consensus_clustering"]
                    )
                )
                & (ablation["method"] == "rmtguard")
            )
        )
    ].copy()

    def _ablation_label(row: pd.Series) -> str:
        if row["ablation_id"] == "min_embedding_pcs_10":
            return "min PCs=10"
        if row["ablation_id"] == "consensus_clustering":
            return "consensus"
        return METHOD_LABELS.get(
            str(row["method"]), str(row["method"]).replace("_", " ")
        )

    subset["label"] = subset.apply(_ablation_label, axis=1)
    subset = subset.sort_values("mean_pairwise_ari")
    ax.barh(
        subset["label"],
        subset["mean_pairwise_ari"].astype(float),
        color=[COLORS.get(m, "#74C476") for m in subset["method"]],
    )
    ax.axvline(0.80, color=COLORS["fail"], linestyle="--", linewidth=1.1)
    ax.text(0.805, -0.6, "0.80 gate", color=COLORS["fail"], fontsize=7.2)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Mean pairwise ARI")
    ax.set_title("PBMC3k stability ablations", loc="left")
    ax.tick_params(axis="y", labelsize=7.0)
    _clean_axis(ax, xgrid=True)
    _panel_label(ax, "D")

    _title(fig, "Figure 5. Reproducibility, runtime, and release gates")
    return fig, [runtime_path, gates_path, ablation_path]


def render_all() -> list[dict[str, str]]:
    _apply_style()
    renderers = [figure1, figure2, figure3, figure4, figure5]
    manifest_rows: list[dict[str, str]] = []
    for (figure_id, stem), renderer in zip(FIGURE_SPECS, renderers):
        fig, inputs = renderer()
        png, pdf, tif = _save_figure(fig, stem)
        manifest_rows.append(
            {
                "figure_id": figure_id,
                "png_path": _rel(png),
                "pdf_path": _rel(pdf),
                "tiff_path": _rel(tif),
                "input_paths": ";".join(_rel(path) for path in inputs),
                "regeneration_command": "python scripts/render_main_figures.py",
                "status": (
                    "rendered"
                    if png.exists() and pdf.exists() and tif.exists()
                    else "missing"
                ),
                "notes": "Publication-style draft figure; values are unchanged from source-data tables.",
            }
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(MANIFEST.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "figure_id",
                "png_path",
                "pdf_path",
                "tiff_path",
                "input_paths",
                "regeneration_command",
                "status",
                "notes",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(manifest_rows)
    tmp.replace(MANIFEST)
    return manifest_rows


def main() -> int:
    manifest = render_all()
    print(_rel(MANIFEST))
    failures = [row for row in manifest if row["status"] != "rendered"]
    if failures:
        for row in failures:
            print(
                f"missing: {row['figure_id']} -> {row['png_path']} / {row['pdf_path']} / {row['tiff_path']}"
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
