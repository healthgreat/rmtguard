from __future__ import annotations

"""Render a strengthened Figure 4 PDAC/TME public-data showcase.

Author: RMTGuard development team
Date: 2026-05-11
Purpose: Create a source-data-driven, publication-style Figure 4 draft from
the claim-bounded PDAC/TME evidence board.
Data source: PDAC/TME marker, external-signature, pathway/atlas, and stability
tables generated from public GSE154778 and GSE263733 inputs.
Method notes: This script changes visual presentation only. It does not create
mechanistic, clinical, prognosis, therapy-response, spatial, protein, or
patient-level validation claims.
"""

import csv
import math
import textwrap
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

BOARD_TSV = ROOT / "results" / "submission" / "pdac_tme_figure4_strengthening_board.tsv"
MARKER_SUMMARY = (
    ROOT / "results" / "figures" / "source_data" / "figure4_pdac_tme_cluster_marker_summary.tsv"
)
EXTERNAL_SIGNATURE = (
    ROOT / "results" / "pdac_tme" / "deep_validation" / "pdac_external_signature_validation.tsv"
)
PATHWAY_ATLAS_SOURCE = (
    ROOT / "results" / "figures" / "source_data" / "figure4_pdac_tme_pathway_atlas_source.tsv"
)
ATLAS_MAPPING = (
    ROOT
    / "results"
    / "pdac_tme"
    / "pathway_atlas_validation"
    / "pdac_atlas_marker_citation_mapping.tsv"
)
PDAC154_STABILITY = (
    ROOT
    / "results"
    / "manuscript_stability_benchmarks"
    / "pdac_gse154778_stability_summary.tsv"
)
PDAC263_STABILITY = (
    ROOT
    / "results"
    / "manuscript_stability_benchmarks"
    / "pdac_gse263733_stability_summary.tsv"
)

OUT_DIR = ROOT / "figures" / "manuscript"
OUT_STEM = "figure4_pdac_tme_strengthened"
OUT_PNG = OUT_DIR / f"{OUT_STEM}.png"
OUT_PDF = OUT_DIR / f"{OUT_STEM}.pdf"
OUT_TIFF = OUT_DIR / f"{OUT_STEM}.tiff"
OUT_MANIFEST = OUT_DIR / f"{OUT_STEM}_manifest.tsv"
OUT_SOURCE = ROOT / "results" / "figures" / "source_data" / f"{OUT_STEM}_source.tsv"

COLORS = {
    "rmtguard": "#2E6F9E",
    "baseline": "#8A8F94",
    "support": "#1B7837",
    "partial": "#E08214",
    "pending": "#8073AC",
    "boundary": "#B2182B",
    "neutral": "#6B7280",
    "grid": "#E6E8EB",
    "ductal": "#2E6F9E",
    "immune": "#5AAE61",
    "t_nk": "#7B4FA1",
    "caf": "#D55E00",
}

PDAC_LABELS = {
    "pdac_gse154778": "GSE154778",
    "pdac_gse263733": "GSE263733",
}

MARKER_LABELS = {
    "score_b_plasma": "B/plasma",
    "score_caf_fibroblast": "CAF/fibroblast",
    "score_ductal_malignant_context": "ductal",
    "score_endothelial": "endothelial",
    "score_immune_myeloid": "myeloid",
    "score_t_nk": "T/NK",
}

SIGNATURE_COLORS = {
    "ductal_malignant_context": COLORS["ductal"],
    "immune_myeloid": COLORS["immune"],
    "t_nk": COLORS["t_nk"],
    "caf_fibroblast": COLORS["caf"],
}


def _apply_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 8.0,
            "axes.titlesize": 9.0,
            "axes.labelsize": 8.0,
            "xtick.labelsize": 7.2,
            "ytick.labelsize": 7.2,
            "legend.fontsize": 7.0,
            "axes.linewidth": 0.75,
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


def _read_tsv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "panel",
        "item",
        "group",
        "metric",
        "value",
        "status",
        "source_path",
        "notes",
    ]
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _atomic_save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    kwargs = {
        "format": path.suffix.lstrip("."),
        "dpi": 300,
        "bbox_inches": "tight",
        "facecolor": "white",
    }
    if path.suffix.lower() != ".tiff":
        kwargs["metadata"] = {"Creator": "RMTGuard render_figure4_strengthened.py"}
    fig.savefig(tmp, **kwargs)
    tmp.replace(path)


def _wrap(value: object, width: int = 22) -> str:
    return textwrap.fill(str(value).replace("_", " "), width=width, break_long_words=False)


def _clean_axis(ax: plt.Axes, xgrid: bool = False, ygrid: bool = True) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#2F3437")
    ax.spines["bottom"].set_color("#2F3437")
    axis = "x" if xgrid else "y"
    if ygrid or xgrid:
        ax.grid(axis=axis, color=COLORS["grid"], linewidth=0.7)
    ax.set_axisbelow(True)


def _panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.13,
        1.08,
        label,
        transform=ax.transAxes,
        fontsize=11,
        fontweight="bold",
        va="top",
        ha="left",
    )


def _status_color(status: str) -> str:
    status = str(status).lower()
    if "partial" in status or "caution" in status:
        return COLORS["partial"]
    if "pending" in status or "author" in status:
        return COLORS["pending"]
    if "missing" in status or status == "no":
        return COLORS["boundary"]
    if "pass" in status or "supported" in status or status == "yes":
        return COLORS["support"]
    return COLORS["neutral"]


def _sig_label(value: object) -> str:
    labels = {
        "ductal_malignant_context": "ductal",
        "immune_myeloid": "myeloid",
        "t_nk": "T/NK",
        "caf_fibroblast": "CAF",
        "b_plasma": "B/plasma",
    }
    return labels.get(str(value), str(value).replace("_", " "))


def _stability_rows(path: Path, dataset_id: str) -> list[dict[str, object]]:
    df = _read_tsv(path)
    rows: list[dict[str, object]] = []
    rmt = df[df["method"] == "rmtguard"].copy()
    if not rmt.empty:
        rows.append(
            {
                "dataset_id": dataset_id,
                "method": "RMTGuard",
                "mean_pairwise_ari": float(rmt.iloc[0]["mean_pairwise_ari"]),
                "kind": "rmtguard",
            }
        )
    baseline = df[~df["method"].astype(str).str.startswith("rmtguard")].copy()
    if not baseline.empty:
        best = baseline.sort_values("mean_pairwise_ari", ascending=False).iloc[0]
        rows.append(
            {
                "dataset_id": dataset_id,
                "method": f"best baseline\n{best['method']}",
                "mean_pairwise_ari": float(best["mean_pairwise_ari"]),
                "kind": "baseline",
            }
        )
    return rows


def _build_source_rows(
    board: pd.DataFrame,
    markers: pd.DataFrame,
    transfer: pd.DataFrame,
    pathways: pd.DataFrame,
    atlas: pd.DataFrame,
    stability: pd.DataFrame,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for _, row in board.iterrows():
        rows.append(
            {
                "panel": "A_evidence_board",
                "item": str(row["evidence_layer"]),
                "group": str(row["supports_methods_figure4"]),
                "metric": "status",
                "value": str(row["current_status"]),
                "status": str(row["supports_pdac_mechanism_claim"]),
                "source_path": _rel(BOARD_TSV),
                "notes": str(row["allowed_wording"]),
            }
        )
    score_cols = [col for col in markers.columns if col.startswith("score_")]
    for _, row in markers.iterrows():
        cluster_id = f"{row['dataset_id']}_C{row['cluster']}"
        for col in score_cols:
            rows.append(
                {
                    "panel": "B_marker_signature_heatmap",
                    "item": cluster_id,
                    "group": MARKER_LABELS.get(col, col),
                    "metric": "mean_marker_score",
                    "value": f"{float(row[col]):.6g}",
                    "status": str(row.get("top_signature", "")),
                    "source_path": _rel(MARKER_SUMMARY),
                    "notes": "Plotted marker signature score.",
                }
            )
    for _, row in transfer.iterrows():
        rows.append(
            {
                "panel": "C_external_signature_transfer",
                "item": f"C{row['primary_cluster']}",
                "group": str(row["primary_top_signature"]),
                "metric": "validation_public_label_score",
                "value": f"{float(row['top_validation_public_label_score']):.6g}",
                "status": str(row["public_label_support"]),
                "source_path": _rel(EXTERNAL_SIGNATURE),
                "notes": str(row["top_validation_public_label"]),
            }
        )
    for _, row in pathways.iterrows():
        rows.append(
            {
                "panel": "D_pathway_layer",
                "item": str(row["pathway_name"]),
                "group": str(row["cluster_top_signature"]),
                "metric": "minus_log10_bh_fdr",
                "value": f"{float(row['minus_log10_fdr']):.6g}",
                "status": str(row["pathway_priority_label"]),
                "source_path": _rel(PATHWAY_ATLAS_SOURCE),
                "notes": str(row["collection"]),
            }
        )
    for _, row in atlas.iterrows():
        rows.append(
            {
                "panel": "E_atlas_marker_overlap",
                "item": f"{row['dataset_id']}_C{row['cluster']}",
                "group": str(row["expected_cluster_label"]),
                "metric": "overlap_n",
                "value": str(row["overlap_n"]),
                "status": str(row["support_status"]),
                "source_path": _rel(ATLAS_MAPPING),
                "notes": str(row["reference"]),
            }
        )
    for _, row in stability.iterrows():
        rows.append(
            {
                "panel": "F_stability_boundary",
                "item": str(row["dataset_id"]),
                "group": str(row["method"]),
                "metric": "mean_pairwise_ari",
                "value": f"{float(row['mean_pairwise_ari']):.6g}",
                "status": str(row["kind"]),
                "source_path": f"{_rel(PDAC154_STABILITY)};{_rel(PDAC263_STABILITY)}",
                "notes": "Context only; not a stability-superiority claim.",
            }
        )
    return rows


def _plot_panel_a(ax: plt.Axes, board: pd.DataFrame) -> None:
    keep = [
        "FDR_controlled_cluster_DE",
        "external_signature_transfer",
        "rank_based_pathway_layer",
        "published_atlas_marker_overlap",
        "subsampling_stability_context",
        "bounded_wording_freeze",
    ]
    labels = {
        "FDR_controlled_cluster_DE": "DE markers",
        "external_signature_transfer": "signature transfer",
        "rank_based_pathway_layer": "pathway layer",
        "published_atlas_marker_overlap": "atlas markers",
        "subsampling_stability_context": "stability boundary",
        "bounded_wording_freeze": "author sign-off",
    }
    subset = board[board["evidence_layer"].isin(keep)].copy()
    subset["order"] = subset["evidence_layer"].map({key: i for i, key in enumerate(keep)})
    subset = subset.sort_values("order")
    y = np.arange(len(subset))[::-1]
    colors = [_status_color(s) for s in subset["current_status"]]
    ax.scatter([0.08] * len(subset), y, s=150, color=colors, edgecolor="white", linewidth=0.8)
    for yi, (_, row) in zip(y, subset.iterrows()):
        ax.text(
            0.18,
            yi,
            labels[row["evidence_layer"]],
            ha="left",
            va="center",
            fontsize=7.4,
            color="#1F2933",
        )
    ax.text(
        0.98,
        0.02,
        "Public-data showcase only; no mechanism or clinical claim.",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.2,
        color=COLORS["neutral"],
    )
    ax.set_ylim(-0.75, len(subset) - 0.25)
    ax.set_xlim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Claim-bounded evidence layers", loc="left")
    for spine in ax.spines.values():
        spine.set_visible(False)
    _panel_label(ax, "A")


def _plot_panel_b(ax: plt.Axes, markers: pd.DataFrame) -> None:
    score_cols = [col for col in markers.columns if col.startswith("score_")]
    shown = markers.sort_values(["dataset_id", "cluster"]).copy()
    shown = shown[shown["n_cells"].astype(float) >= 10].copy()
    heat = shown[score_cols].astype(float).to_numpy()
    im = ax.imshow(heat, aspect="auto", cmap="YlGnBu", vmin=0)
    row_labels = [
        f"{PDAC_LABELS.get(str(d), str(d))} C{c}"
        for d, c in zip(shown["dataset_id"], shown["cluster"])
    ]
    ax.set_yticks(np.arange(len(shown)))
    ax.set_yticklabels(row_labels, fontsize=6.4)
    ax.set_xticks(np.arange(len(score_cols)))
    ax.set_xticklabels([MARKER_LABELS.get(col, col) for col in score_cols], rotation=35, ha="right")
    ax.set_title("Marker program scores", loc="left")
    cb = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
    cb.set_label("mean score")
    _panel_label(ax, "B")


def _plot_panel_c(ax: plt.Axes, transfer: pd.DataFrame) -> None:
    shown = transfer.copy()
    shown["label"] = shown.apply(
        lambda r: f"C{int(r['primary_cluster'])} {_sig_label(r['primary_top_signature'])}",
        axis=1,
    )
    shown = shown.sort_values(["public_label_support", "top_validation_public_label_score"], ascending=[True, True])
    colors = [
        SIGNATURE_COLORS.get(str(sig), COLORS["neutral"])
        if str(ok).lower() == "true"
        else "#C7CBD1"
        for sig, ok in zip(shown["primary_top_signature"], shown["public_label_support"])
    ]
    y = np.arange(len(shown))
    scores = shown["top_validation_public_label_score"].astype(float)
    ax.barh(y, scores, color=colors, height=0.64)
    for i, ok in enumerate(shown["public_label_support"]):
        ax.text(scores.iloc[i] + 0.05, i, "match" if str(ok).lower() == "true" else "no match", va="center", fontsize=6.5)
    ax.set_yticks(y)
    ax.set_yticklabels(shown["label"], fontsize=6.6)
    ax.set_xlabel("External label score")
    ax.set_title("Signature transfer to GSE263733", loc="left")
    _clean_axis(ax, xgrid=True)
    _panel_label(ax, "C")


def _plot_panel_d(ax: plt.Axes, pathways: pd.DataFrame) -> None:
    shown = pathways.copy()
    shown = shown.sort_values(["minus_log10_fdr", "auc_delta"], ascending=[False, False])
    shown = shown.drop_duplicates("pathway_name", keep="first").head(8)
    shown = shown.sort_values("minus_log10_fdr", ascending=True)
    shown["short_name"] = shown["pathway_name"].str.replace("HALLMARK_", "", regex=False)
    shown["short_name"] = shown["short_name"].str.replace("REACTOME_", "", regex=False)
    y = np.arange(len(shown))
    colors = [SIGNATURE_COLORS.get(str(sig), COLORS["rmtguard"]) for sig in shown["cluster_top_signature"]]
    ax.barh(y, shown["minus_log10_fdr"].astype(float), color=colors, height=0.64)
    ax.set_yticks(y)
    ax.set_yticklabels([_wrap(name, 24) for name in shown["short_name"]], fontsize=6.3)
    ax.set_xlabel("-log10(BH-FDR)")
    ax.set_title("Interpretable pathway layer", loc="left")
    _clean_axis(ax, xgrid=True)
    _panel_label(ax, "D")


def _plot_panel_e(ax: plt.Axes, atlas: pd.DataFrame) -> None:
    shown = atlas.copy()
    shown["label"] = [
        f"{PDAC_LABELS.get(str(d), str(d))} C{c}\n{_wrap(lbl, 18)}"
        for d, c, lbl in zip(shown["dataset_id"], shown["cluster"], shown["expected_cluster_label"])
    ]
    shown = shown.sort_values("overlap_n", ascending=True)
    y = np.arange(len(shown))
    colors = [_status_color(s) for s in shown["support_status"]]
    ax.barh(y, shown["overlap_n"].astype(float), color=colors, height=0.62)
    ax.set_yticks(y)
    ax.set_yticklabels(shown["label"], fontsize=6.0)
    ax.set_xlabel("Overlapping atlas markers")
    ax.set_title("Published atlas marker overlap", loc="left")
    _clean_axis(ax, xgrid=True)
    _panel_label(ax, "E")


def _plot_panel_f(ax: plt.Axes, stability: pd.DataFrame) -> None:
    datasets = ["pdac_gse154778", "pdac_gse263733"]
    x = np.arange(len(datasets))
    width = 0.34
    rmt = [
        float(stability[(stability["dataset_id"] == ds) & (stability["kind"] == "rmtguard")]["mean_pairwise_ari"].iloc[0])
        for ds in datasets
    ]
    base = [
        float(stability[(stability["dataset_id"] == ds) & (stability["kind"] == "baseline")]["mean_pairwise_ari"].iloc[0])
        for ds in datasets
    ]
    ax.bar(x - width / 2, rmt, width=width, color=COLORS["rmtguard"], label="RMTGuard")
    ax.bar(x + width / 2, base, width=width, color=COLORS["baseline"], label="best baseline")
    for i, (r, b) in enumerate(zip(rmt, base)):
        ax.text(i - width / 2, r + 0.02, f"{r:.2f}", ha="center", fontsize=6.8)
        ax.text(i + width / 2, b + 0.02, f"{b:.2f}", ha="center", fontsize=6.8)
    ax.set_xticks(x)
    ax.set_xticklabels([PDAC_LABELS[ds] for ds in datasets])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Mean pairwise ARI")
    ax.set_title("Stability reported as boundary context", loc="left")
    ax.legend(frameon=False, loc="upper left")
    _clean_axis(ax)
    _panel_label(ax, "F")


def render() -> list[dict[str, str]]:
    _apply_style()
    board = _read_tsv(BOARD_TSV)
    markers = _read_tsv(MARKER_SUMMARY)
    transfer = _read_tsv(EXTERNAL_SIGNATURE)
    pathways = _read_tsv(PATHWAY_ATLAS_SOURCE)
    pathways = pathways[
        (pathways["panel"] == "figure4_pathway_interpretable_hits")
        & (pathways["significant_fdr_0_05"].astype(str).str.lower() == "true")
    ].copy()
    pathways["p_adj_bh"] = pd.to_numeric(pathways["p_adj_bh"], errors="coerce")
    pathways["auc_delta"] = pd.to_numeric(pathways["auc_delta"], errors="coerce")
    pathways["minus_log10_fdr"] = pathways["p_adj_bh"].map(
        lambda value: -math.log10(max(float(value), 1e-300))
        if pd.notna(value)
        else np.nan
    )
    atlas = _read_tsv(ATLAS_MAPPING)
    stability = pd.DataFrame(
        _stability_rows(PDAC154_STABILITY, "pdac_gse154778")
        + _stability_rows(PDAC263_STABILITY, "pdac_gse263733")
    )

    source_rows = _build_source_rows(board, markers, transfer, pathways, atlas, stability)
    _write_tsv(OUT_SOURCE, source_rows)

    fig = plt.figure(figsize=(7.4, 8.8), constrained_layout=True)
    gs = fig.add_gridspec(3, 2, height_ratios=[0.82, 1.28, 1.12])
    axes = [
        fig.add_subplot(gs[0, 0]),
        fig.add_subplot(gs[0, 1]),
        fig.add_subplot(gs[1, 0]),
        fig.add_subplot(gs[1, 1]),
        fig.add_subplot(gs[2, 0]),
        fig.add_subplot(gs[2, 1]),
    ]

    _plot_panel_a(axes[0], board)
    _plot_panel_f(axes[1], stability)
    _plot_panel_b(axes[2], markers)
    _plot_panel_c(axes[3], transfer)
    _plot_panel_d(axes[4], pathways)
    _plot_panel_e(axes[5], atlas)

    _atomic_save(fig, OUT_PNG)
    _atomic_save(fig, OUT_PDF)
    _atomic_save(fig, OUT_TIFF)
    plt.close(fig)

    rows = [
        {
            "figure_id": "Figure 4 strengthened",
            "png_path": _rel(OUT_PNG),
            "pdf_path": _rel(OUT_PDF),
            "tiff_path": _rel(OUT_TIFF),
            "source_data_path": _rel(OUT_SOURCE),
            "input_paths": ";".join(
                _rel(path)
                for path in [
                    BOARD_TSV,
                    MARKER_SUMMARY,
                    EXTERNAL_SIGNATURE,
                    PATHWAY_ATLAS_SOURCE,
                    ATLAS_MAPPING,
                    PDAC154_STABILITY,
                    PDAC263_STABILITY,
                ]
            ),
            "status": "rendered",
            "notes": "Strengthened bounded public-data PDAC/TME showcase; no mechanism or clinical claim.",
        }
    ]
    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_MANIFEST.with_suffix(OUT_MANIFEST.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "figure_id",
                "png_path",
                "pdf_path",
                "tiff_path",
                "source_data_path",
                "input_paths",
                "status",
                "notes",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(OUT_MANIFEST)
    return rows


def main() -> int:
    rows = render()
    print(_rel(OUT_MANIFEST))
    print(_rel(OUT_SOURCE))
    for row in rows:
        print(row["png_path"])
        print(row["pdf_path"])
        print(row["tiff_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
