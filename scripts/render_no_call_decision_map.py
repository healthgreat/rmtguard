"""Render a publication-style no-call decision map.

Author: RMTGuard development team
Date: 2026-05-12
Purpose: Convert the RMTGuard callability/no-call decision table into a
Figure 3-ready visual audit.
Data source: results/callability/no_call_decision_map.tsv
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "results" / "callability" / "no_call_decision_map.tsv"
DEFAULT_OUTDIR = ROOT / "figures" / "manuscript"
DEFAULT_MANIFEST = ROOT / "figures" / "manuscript" / "no_call_decision_map_manifest.tsv"

DECISION_COLORS = {
    "positive_control_pass": "#2D6A4F",
    "callable_bounded": "#40916C",
    "callable_with_caveat": "#DDA15E",
    "stress_monitor": "#7B8FA1",
    "diagnostic_no_call": "#BC4749",
}

DECISION_LABELS = {
    "positive_control_pass": "Positive",
    "callable_bounded": "Bounded",
    "callable_with_caveat": "Caveat",
    "stress_monitor": "Monitor",
    "diagnostic_no_call": "No-call",
}

COLUMNS = [
    ("decision", "Decision"),
    ("n_signal_pcs", "Signal\nPCs"),
    ("accepted_embedding_pcs", "Embedding\nPCs"),
    ("annotation_ari", "Annotation\nARI"),
    ("stability_gap_to_best", "Stability\ngap"),
]


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _num(value: object) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return math.nan
    return out if math.isfinite(out) else math.nan


def _metric_color(column: str, value: float) -> str:
    if math.isnan(value):
        return "#F2F2F2"
    if column in {"n_signal_pcs", "accepted_embedding_pcs"}:
        if value <= 1:
            return "#F4B6B6"
        if value <= 3:
            return "#F2D0A4"
        return "#B7E4C7"
    if column == "annotation_ari":
        if value >= 0.70:
            return "#B7E4C7"
        if value >= 0.40:
            return "#F2D0A4"
        return "#F4B6B6"
    if column == "stability_gap_to_best":
        if value <= 0.05:
            return "#B7E4C7"
        if value <= 0.12:
            return "#F2D0A4"
        return "#F4B6B6"
    return "#FFFFFF"


def _metric_text(column: str, value: object) -> str:
    number = _num(value)
    if math.isnan(number):
        return "NA"
    if column in {"n_signal_pcs", "accepted_embedding_pcs"}:
        return f"{number:.0f}"
    return f"{number:.3f}"


def _sort_rows(df: pd.DataFrame) -> pd.DataFrame:
    type_order = {"synthetic": 0, "real_public": 1}
    decision_order = {
        "diagnostic_no_call": 0,
        "callable_with_caveat": 1,
        "stress_monitor": 2,
        "positive_control_pass": 3,
        "callable_bounded": 4,
    }
    out = df.copy()
    out["_type_order"] = out["unit_type"].map(type_order).fillna(9)
    out["_decision_order"] = out["decision"].map(decision_order).fillna(9)
    return out.sort_values(["_type_order", "_decision_order", "unit_label"]).drop(
        columns=["_type_order", "_decision_order"]
    )


def render(input_path: Path, outdir: Path, manifest: Path) -> list[dict[str, str]]:
    df = _sort_rows(pd.read_csv(input_path, sep="\t").fillna("NA"))
    n_rows = len(df)
    n_cols = len(COLUMNS)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.titlesize": 10,
            "axes.labelsize": 8,
        }
    )

    fig_h = max(5.2, 0.36 * n_rows + 2.2)
    fig, ax = plt.subplots(figsize=(8.3, fig_h))
    ax.set_xlim(-2.9, n_cols)
    ax.set_ylim(-0.8, n_rows + 1.80)
    ax.axis("off")

    ax.text(
        -2.9,
        n_rows + 1.48,
        "RMTGuard callability and no-call decision map",
        fontsize=12,
        fontweight="bold",
        ha="left",
        va="center",
    )
    ax.text(
        -2.9,
        n_rows + 1.06,
        "Red no-call rows are excluded from discovery claims; caveat rows are reported only with explicit limits.",
        fontsize=8,
        color="#4A4A4A",
        ha="left",
        va="center",
    )

    for col_idx, (_column, label) in enumerate(COLUMNS):
        ax.text(
            col_idx + 0.5,
            n_rows + 0.28,
            label,
            ha="center",
            va="bottom",
            fontsize=8,
            fontweight="bold",
        )

    for row_idx, row in enumerate(df.itertuples(index=False)):
        y = n_rows - row_idx - 1
        if row_idx % 2 == 0:
            ax.add_patch(
                patches.Rectangle(
                    (-2.9, y - 0.02),
                    n_cols + 2.9,
                    0.92,
                    facecolor="#FAFAFA",
                    edgecolor="none",
                    zorder=0,
                )
            )
        unit_type = str(row.unit_type).replace("_", " ")
        ax.text(-2.82, y + 0.45, str(row.unit_label), ha="left", va="center", fontsize=8.2)
        ax.text(-1.18, y + 0.45, unit_type, ha="left", va="center", fontsize=7.2, color="#666666")

        for col_idx, (column, _label) in enumerate(COLUMNS):
            if column == "decision":
                decision = str(row.decision)
                color = DECISION_COLORS.get(decision, "#D9D9D9")
                text = DECISION_LABELS.get(decision, decision)
            else:
                value = getattr(row, column)
                color = _metric_color(column, _num(value))
                text = _metric_text(column, value)
            ax.add_patch(
                patches.FancyBboxPatch(
                    (col_idx + 0.05, y + 0.12),
                    0.90,
                    0.64,
                    boxstyle="round,pad=0.02,rounding_size=0.025",
                    linewidth=0.4,
                    edgecolor="#FFFFFF",
                    facecolor=color,
                )
            )
            text_color = "#FFFFFF" if column == "decision" and row.decision != "stress_monitor" else "#222222"
            ax.text(
                col_idx + 0.5,
                y + 0.44,
                text,
                ha="center",
                va="center",
                fontsize=7.6,
                color=text_color,
                fontweight="bold" if column == "decision" else "normal",
            )

    legend_y = -0.30
    legend_items = [
        ("No-call", DECISION_COLORS["diagnostic_no_call"]),
        ("Caveat", DECISION_COLORS["callable_with_caveat"]),
        ("Monitor", DECISION_COLORS["stress_monitor"]),
        ("Positive/bounded", DECISION_COLORS["positive_control_pass"]),
    ]
    for idx, (label, color) in enumerate(legend_items):
        x = -2.9 + idx * 1.35
        ax.add_patch(patches.Rectangle((x, legend_y), 0.18, 0.18, facecolor=color, edgecolor="none"))
        ax.text(x + 0.24, legend_y + 0.09, label, ha="left", va="center", fontsize=7.3)

    outdir.mkdir(parents=True, exist_ok=True)
    outputs = [
        outdir / "figure_no_call_decision_map.png",
        outdir / "figure_no_call_decision_map.pdf",
        outdir / "figure_no_call_decision_map.tiff",
    ]
    for path in outputs:
        if path.suffix == ".tiff":
            fig.savefig(path, dpi=300, bbox_inches="tight", pil_kwargs={"compression": "tiff_lzw"})
        elif path.suffix == ".png":
            fig.savefig(path, dpi=300, bbox_inches="tight")
        else:
            fig.savefig(path, bbox_inches="tight")
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
