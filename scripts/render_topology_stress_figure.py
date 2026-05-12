"""Render a publication-style topology stress benchmark figure.

Author: RMTGuard development team
Date: 2026-05-12
Purpose: Convert the CONCORD-style topology stress summary table into a
journal-ready draft figure.
Data source: results/submission/topology_stress_summary.tsv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "results" / "submission" / "topology_stress_summary.tsv"
DEFAULT_OUTDIR = ROOT / "figures" / "manuscript"
DEFAULT_MANIFEST = ROOT / "figures" / "manuscript" / "topology_stress_figure_manifest.tsv"

SCENARIO_LABELS = {
    "linear_trajectory": "Linear",
    "branching_trajectory": "Branch",
    "cyclic_loop": "Loop",
}

METHOD_LABELS = {
    "rmtguard": "RMTGuard",
    "rmtguard_strict_signal": "Strict signal",
    "fixed_pcs_30": "Fixed 30 PCs",
    "fixed_pcs_50": "Fixed 50 PCs",
}

METHOD_COLORS = {
    "rmtguard": "#2D6A4F",
    "rmtguard_strict_signal": "#74C69D",
    "fixed_pcs_30": "#6D597A",
    "fixed_pcs_50": "#B56576",
}

PANELS = [
    ("topology_knn_recall", "kNN recall", (0.0, 0.55)),
    ("topology_trustworthiness", "Trustworthiness", (0.65, 1.0)),
    ("topology_continuity", "Continuity", (0.60, 1.0)),
    ("pairwise_distance_spearman", "Distance rho", (0.0, 0.90)),
]


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _error_arrays(frame: pd.DataFrame, metric: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = frame[f"{metric}_mean"].astype(float).to_numpy()
    low = frame[f"{metric}_ci95_low"].astype(float).to_numpy()
    high = frame[f"{metric}_ci95_high"].astype(float).to_numpy()
    return mean, np.maximum(mean - low, 0.0), np.maximum(high - mean, 0.0)


def render(input_path: Path, outdir: Path, manifest: Path) -> list[dict[str, str]]:
    df = pd.read_csv(input_path, sep="\t")
    scenarios = [key for key in SCENARIO_LABELS if key in set(df["scenario_id"])]
    methods = [key for key in METHOD_LABELS if key in set(df["method"])]

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "axes.linewidth": 0.8,
        }
    )

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.1), constrained_layout=False)
    fig.subplots_adjust(left=0.08, right=0.99, bottom=0.09, top=0.82, wspace=0.26, hspace=0.45)
    axes = axes.ravel()
    x = np.arange(len(scenarios), dtype=float)
    width = 0.18
    offsets = (np.arange(len(methods)) - (len(methods) - 1) / 2.0) * width

    for ax, (metric, title, ylim) in zip(axes, PANELS):
        for method, offset in zip(methods, offsets):
            frame = (
                df[df["method"] == method]
                .set_index("scenario_id")
                .reindex(scenarios)
                .reset_index()
            )
            mean, err_low, err_high = _error_arrays(frame, metric)
            ax.bar(
                x + offset,
                mean,
                width=width,
                color=METHOD_COLORS[method],
                edgecolor="white",
                linewidth=0.5,
                label=METHOD_LABELS[method],
                zorder=3,
            )
            ax.errorbar(
                x + offset,
                mean,
                yerr=np.vstack([err_low, err_high]),
                fmt="none",
                ecolor="#2F2F2F",
                elinewidth=0.6,
                capsize=1.8,
                zorder=4,
            )
        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([SCENARIO_LABELS[item] for item in scenarios])
        ax.set_ylim(*ylim)
        ax.grid(axis="y", color="#D9D9D9", linewidth=0.6, zorder=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.58, 0.925))
    fig.suptitle(
        "Topology stress benchmark across synthetic trajectories",
        x=0.02,
        y=0.975,
        ha="left",
        fontsize=11,
        fontweight="bold",
    )

    outdir.mkdir(parents=True, exist_ok=True)
    outputs = [
        outdir / "figure_topology_stress.png",
        outdir / "figure_topology_stress.pdf",
        outdir / "figure_topology_stress.tiff",
    ]
    for path in outputs:
        if path.suffix == ".tiff":
            fig.savefig(path, dpi=300, pil_kwargs={"compression": "tiff_lzw"})
        elif path.suffix == ".png":
            fig.savefig(path, dpi=300)
        else:
            fig.savefig(path)
    plt.close(fig)

    rows = [
        {
            "asset": path.name,
            "path": _rel(path),
            "source_data": _rel(input_path),
            "status": "written",
        }
        for path in outputs
    ]
    manifest.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(manifest, sep="\t", index=False)
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = render(args.input, args.outdir, args.manifest)
    for row in rows:
        print(row["path"])
    print(args.manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
