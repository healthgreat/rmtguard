#!/usr/bin/env python
"""Render calibration figures for realistic null and rare-state power tests.

Author: RMTGuard development team
Date: 2026-05-02
Purpose: Visualize count-preserving null false-positive control and rare-state
power behavior from the draft calibration run.
Data source: results/calibration/realistic_null_summary.tsv and
results/calibration/rare_state_power_summary.tsv.
Method notes: This figure is a diagnostic calibration artifact, not a main
manuscript claim unless rerun with manuscript-grade repeats.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CALIBRATION_DIR = ROOT / "results" / "calibration"
FIG_DIR = ROOT / "figures" / "calibration"
MANIFEST = FIG_DIR / "calibration_figure_manifest.tsv"
PNG = FIG_DIR / "realistic_null_power_calibration.png"
PDF = FIG_DIR / "realistic_null_power_calibration.pdf"
TIFF = FIG_DIR / "realistic_null_power_calibration.tiff"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _atomic_write_tsv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, sep="\t", index=False, quoting=csv.QUOTE_MINIMAL)
    tmp.replace(path)


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    kwargs = {
        "format": path.suffix.lstrip("."),
        "dpi": 300,
        "bbox_inches": "tight",
        "facecolor": "white",
    }
    if path.suffix.lower() != ".tiff":
        kwargs["metadata"] = {"Creator": "RMTGuard render_calibration_figures.py"}
    fig.savefig(tmp, **kwargs)
    tmp.replace(path)


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 8.5,
            "axes.titlesize": 9.5,
            "axes.labelsize": 8.5,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.2,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _clean_axis(ax: plt.Axes, xgrid: bool = False) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x" if xgrid else "y", color="#E6E8EB", linewidth=0.7)
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


def _heatmap(
    ax: plt.Axes,
    table: pd.DataFrame,
    value_col: str,
    title: str,
    cmap: str,
    vmin: float,
    vmax: float,
) -> None:
    pivot = table.pivot_table(
        index="prevalence",
        columns="effect_size",
        values=value_col,
        aggfunc="first",
    )
    im = ax.imshow(
        pivot.to_numpy(dtype=float), aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax
    )
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels([f"{x:g}" for x in pivot.columns])
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels([f"{x:.2f}" for x in pivot.index])
    ax.set_xlabel("Rare-state effect size")
    ax.set_ylabel("Prevalence")
    ax.set_title(title, loc="left")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            value = pivot.iloc[i, j]
            if pd.notna(value):
                ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=7.0)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.03)


def render() -> None:
    null_path = CALIBRATION_DIR / "realistic_null_summary.tsv"
    power_path = CALIBRATION_DIR / "rare_state_power_summary.tsv"
    null = pd.read_csv(null_path, sep="\t")
    power = pd.read_csv(power_path, sep="\t")
    _style()
    fig, axes = plt.subplots(2, 2, figsize=(7.6, 5.8), constrained_layout=True)

    ax = axes[0, 0]
    y = np.arange(len(null))
    ax.barh(
        y - 0.18,
        null["false_signal_rate"],
        height=0.34,
        label="false signal",
        color="#B2182B",
    )
    ax.barh(
        y + 0.18,
        null["false_call_rate"],
        height=0.34,
        label="false call",
        color="#E08214",
    )
    ax.set_yticks(y)
    ax.set_yticklabels([x.replace("_", " ") for x in null["null_model"]])
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("Rate")
    ax.set_title("Count-preserving null false positives", loc="left")
    ax.legend(frameon=False, loc="lower right")
    _clean_axis(ax, xgrid=True)
    _panel_label(ax, "A")

    ax = axes[0, 1]
    ax.barh(
        [x.replace("_", " ") for x in null["null_model"]],
        null["no_call_rate"],
        color="#8073AC",
    )
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("No-call rate")
    ax.set_title("Null no-call behavior", loc="left")
    _clean_axis(ax, xgrid=True)
    _panel_label(ax, "B")

    ax = axes[1, 0]
    _heatmap(
        ax,
        power,
        "mean_rare_f1",
        "RMTGuard rare-state F1",
        cmap="YlOrRd",
        vmin=0,
        vmax=1,
    )
    _panel_label(ax, "C")

    ax = axes[1, 1]
    _heatmap(
        ax,
        power,
        "mean_fixed30_rare_f1",
        "fixed 30 PC rare-state F1",
        cmap="YlGnBu",
        vmin=0,
        vmax=1,
    )
    _panel_label(ax, "D")

    for path in [PNG, PDF, TIFF]:
        _save(fig, path)
    plt.close(fig)
    manifest = pd.DataFrame(
        [
            {
                "figure_id": "Calibration Figure 1",
                "png_path": _rel(PNG),
                "pdf_path": _rel(PDF),
                "tiff_path": _rel(TIFF),
                "input_paths": f"{_rel(null_path)};{_rel(power_path)}",
                "regeneration_command": "python scripts/render_calibration_figures.py",
                "status": "rendered",
                "notes": "Diagnostic calibration figure; values are draft local calibration outputs.",
            }
        ]
    )
    _atomic_write_tsv(manifest, MANIFEST)
    print(_rel(MANIFEST))


if __name__ == "__main__":
    render()
