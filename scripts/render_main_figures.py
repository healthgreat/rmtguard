from __future__ import annotations

import ast
import csv
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


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _atomic_save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    fig.savefig(tmp, format=path.suffix.lstrip("."), dpi=220, bbox_inches="tight")
    tmp.replace(path)


def _save_figure(fig: plt.Figure, stem: str) -> tuple[Path, Path]:
    png = OUT_DIR / f"{stem}.png"
    pdf = OUT_DIR / f"{stem}.pdf"
    _atomic_save(fig, png)
    _atomic_save(fig, pdf)
    plt.close(fig)
    return png, pdf


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


def _diagnostic_value(df: pd.DataFrame, group: str, metric: str, default: object = np.nan) -> object:
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


def _status_colors(statuses: Iterable[str]) -> list[str]:
    palette = {
        "pass": "#238b45",
        "borderline": "#d95f0e",
        "pending": "#756bb1",
        "fail": "#b30000",
        "ready": "#238b45",
        "missing": "#b30000",
    }
    return [palette.get(str(status).lower(), "#6b7280") for status in statuses]


def _clean_axis(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#d9d9d9", linewidth=0.7, alpha=0.7)


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

    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    ax = axes[0, 0]
    pc_index = np.arange(1, len(eigenvalues) + 1)
    ax.plot(pc_index, eigenvalues, marker="o", color="#1f77b4")
    ax.axhline(mp_edge, color="#636363", linestyle="--", label="MP edge")
    ax.axhline(tw_edge, color="#e6550d", linestyle=":", label="TW proxy")
    ax.axhline(selected_edge, color="#31a354", linestyle="-.", label="selected edge")
    ax.set_title("Spectrum decision rule")
    ax.set_xlabel("PC rank")
    ax.set_ylabel("Eigenvalue")
    ax.legend(frameon=False, fontsize=8)
    _clean_axis(ax)

    ax = axes[0, 1]
    ax.bar([str(x) for x in hvg_grid], signal_by_hvg, color="#6baed6")
    ax.set_title("HVG spectral plateau")
    ax.set_xlabel("HVG count")
    ax.set_ylabel("Signal PCs")
    _clean_axis(ax)

    ax = axes[1, 0]
    shown = pcs.head(20).copy()
    colors = np.where(shown["accepted"].astype(str).str.lower() == "true", "#238b45", "#bdbdbd")
    ax.bar(shown["pc"].astype(int), shown["stability"].astype(float), color=colors)
    ax.axhline(0.75, color="#b30000", linestyle="--", linewidth=1)
    ax.set_title("Embedding PC reproducibility")
    ax.set_xlabel("PC")
    ax.set_ylabel("Median absolute correlation")
    ax.set_ylim(0, 1.05)
    _clean_axis(ax)

    ax = axes[1, 1]
    ax.axis("off")
    rows = [
        ("strict signal PCs", _diagnostic_value(diag, "embedding_diagnostics", "strict_signal_pcs")),
        ("near-edge candidates", _diagnostic_value(diag, "embedding_diagnostics", "near_edge_candidate_pcs")),
        ("accepted embedding PCs", _diagnostic_value(diag, "embedding_diagnostics", "accepted_embedding_pcs")),
        ("HVG selected", _diagnostic_value(diag, "hvg_diagnostics", "selected_hvg_n")),
        ("bulk KS", f"{float(_diagnostic_value(diag, 'pc_diagnostics', 'bulk_ks')):.3f}"),
    ]
    text = "\n".join(f"{key}: {value}" for key, value in rows)
    ax.text(0, 0.95, text, va="top", ha="left", fontsize=11, linespacing=1.5)
    ax.set_title("Run diagnostics", loc="left")

    fig.suptitle("Figure 1. RMTGuard algorithm diagnostics", fontsize=14)
    fig.tight_layout()
    return fig, [diagnostics_path, pc_records_path]


def figure2() -> tuple[plt.Figure, list[Path]]:
    path = SOURCE_DIR / "figure2_synthetic_benchmark_summary.csv"
    no_call_path = SOURCE_DIR / "figure2_no_call_summary.tsv"
    df = _read_csv(path)
    no_call = _read_tsv(no_call_path)
    rmt = df[df["method"] == "rmtguard"].copy()
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))

    ax = axes[0, 0]
    ax.bar(rmt["scenario"], _num(rmt["n_signal_pcs"]), color="#3182bd")
    ax.set_title("RMTGuard signal PCs")
    ax.tick_params(axis="x", rotation=35)
    _clean_axis(ax)

    ax = axes[0, 1]
    ari = df.dropna(subset=["ari"]).copy()
    pivot = ari.pivot_table(index="scenario", columns="method", values="ari", aggfunc="first")
    pivot.plot(kind="bar", ax=ax, color=["#238b45", "#6baed6", "#9ecae1"], width=0.75)
    ax.set_title("Synthetic label recovery")
    ax.set_ylabel("ARI")
    ax.tick_params(axis="x", rotation=35)
    ax.legend(frameon=False, fontsize=8)
    _clean_axis(ax)

    ax = axes[1, 0]
    ax.bar(rmt["scenario"], _num(rmt["cluster_n"]), color="#756bb1")
    ax.set_title("Cluster count under stress tests")
    ax.tick_params(axis="x", rotation=35)
    _clean_axis(ax)

    ax = axes[1, 1]
    hard = no_call[no_call["expected_behavior"].isin(["diagnostic_no_call", "positive_call"])].copy()
    decision_score = hard["decision"].map({"pass": 1.0, "monitor": 0.5, "fail": 0.0}).fillna(0.0)
    ax.bar(hard["scenario"], decision_score, color=_status_colors(hard["decision"]))
    ax.set_title("Diagnostic no-call validation")
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Pass=1")
    ax.tick_params(axis="x", rotation=35)
    _clean_axis(ax)

    fig.suptitle("Figure 2. Synthetic noise-control benchmarks", fontsize=14)
    fig.tight_layout()
    return fig, [path, no_call_path]


def figure3() -> tuple[plt.Figure, list[Path]]:
    public_path = SOURCE_DIR / "figure3_public_benchmark_summary.tsv"
    stability_path = SOURCE_DIR / "figure3_pbmc3k_stability_summary.tsv"
    public = _read_tsv(public_path)
    stability = _read_tsv(stability_path)
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))

    ax = axes[0, 0]
    ari = public.dropna(subset=["ari"]).copy()
    pivot = ari.pivot_table(index="dataset_id", columns="method", values="ari", aggfunc="first")
    pivot.plot(kind="bar", ax=ax, width=0.75)
    ax.set_title("Annotation recovery")
    ax.set_ylabel("ARI")
    ax.tick_params(axis="x", rotation=25)
    ax.legend(frameon=False, fontsize=7)
    _clean_axis(ax)

    ax = axes[0, 1]
    stability.plot.bar(x="method", y="mean_pairwise_ari", ax=ax, color="#74c476", legend=False)
    ax.axhline(0.80, color="#b30000", linestyle="--", linewidth=1)
    ax.set_title("PBMC3k subsampling stability")
    ax.set_ylabel("Mean pairwise ARI")
    ax.tick_params(axis="x", rotation=30)
    _clean_axis(ax)

    ax = axes[1, 0]
    rmt = public[public["method"] == "rmtguard"].copy()
    x = np.arange(len(rmt))
    ax.bar(x - 0.18, _num(rmt["n_signal_pcs"]), width=0.36, label="strict signal PCs", color="#3182bd")
    ax.bar(x + 0.18, _num(rmt["accepted_embedding_pcs"]), width=0.36, label="embedding PCs", color="#31a354")
    ax.set_xticks(x)
    ax.set_xticklabels(rmt["dataset_id"], rotation=25, ha="right")
    ax.set_title("RMTGuard PC decisions")
    ax.legend(frameon=False, fontsize=8)
    _clean_axis(ax)

    ax = axes[1, 1]
    ax.bar(rmt["dataset_id"], _num(rmt["cluster_n"]), color="#9e9ac8")
    ax.set_title("RMTGuard cluster counts")
    ax.tick_params(axis="x", rotation=25)
    _clean_axis(ax)

    fig.suptitle("Figure 3. Public real-data benchmarks", fontsize=14)
    fig.tight_layout()
    return fig, [public_path, stability_path]


def figure4() -> tuple[plt.Figure, list[Path]]:
    summary_path = SOURCE_DIR / "figure4_pdac_tme_showcase_summary.tsv"
    marker_path = SOURCE_DIR / "figure4_pdac_tme_cluster_marker_summary.tsv"
    summary = _read_tsv(summary_path)
    markers = _read_tsv(marker_path)
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))

    ax = axes[0, 0]
    x = np.arange(len(summary))
    ax.bar(x - 0.18, summary["cluster_n"].astype(float), width=0.36, label="clusters", color="#756bb1")
    ax.bar(x + 0.18, summary["accepted_embedding_pcs"].astype(float), width=0.36, label="embedding PCs", color="#31a354")
    ax.set_xticks(x)
    ax.set_xticklabels(summary["dataset_id"], rotation=20, ha="right")
    ax.set_title("PDAC/TME run summary")
    ax.legend(frameon=False, fontsize=8)
    _clean_axis(ax)

    ax = axes[0, 1]
    ari = summary["label_ari"].replace("nan", np.nan).astype(float)
    nmi = summary["label_nmi"].replace("nan", np.nan).astype(float)
    ax.bar(x - 0.18, ari.fillna(0), width=0.36, label="ARI", color="#3182bd")
    ax.bar(x + 0.18, nmi.fillna(0), width=0.36, label="NMI", color="#9ecae1")
    ax.set_xticks(x)
    ax.set_xticklabels(summary["dataset_id"], rotation=20, ha="right")
    ax.set_title("External label validation")
    ax.legend(frameon=False, fontsize=8)
    _clean_axis(ax)

    ax = axes[1, 0]
    score_cols = [col for col in markers.columns if col.startswith("score_")]
    heat = markers[score_cols].astype(float).to_numpy()
    im = ax.imshow(heat, aspect="auto", cmap="viridis")
    ax.set_yticks(np.arange(len(markers)))
    ax.set_yticklabels([f"{d}:C{c}" for d, c in zip(markers["dataset_id"], markers["cluster"])], fontsize=7)
    ax.set_xticks(np.arange(len(score_cols)))
    ax.set_xticklabels([col.replace("score_", "") for col in score_cols], rotation=35, ha="right", fontsize=8)
    ax.set_title("Cluster marker signatures")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    ax = axes[1, 1]
    ax.scatter(markers["n_cells"].astype(float), markers["metastasis_fraction"].astype(float), s=55, color="#e6550d")
    ax.set_xlabel("Cluster cells")
    ax.set_ylabel("Metastasis fraction")
    ax.set_title("Primary vs metastasis composition")
    _clean_axis(ax)

    fig.suptitle("Figure 4. PDAC/TME public showcase", fontsize=14)
    fig.tight_layout()
    return fig, [summary_path, marker_path]


def figure5() -> tuple[plt.Figure, list[Path]]:
    runtime_path = SOURCE_DIR / "figure5_runtime_memory_summary.tsv"
    gates_path = SOURCE_DIR / "figure5_gate_evidence.tsv"
    ablation_path = SOURCE_DIR / "figure5_ablation_stability_summary.tsv"
    runtime = _read_tsv(runtime_path)
    gates = _read_tsv(gates_path)
    ablation = _read_tsv(ablation_path)
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))

    ax = axes[0, 0]
    ax.bar(runtime["unit_id"], runtime["runtime_seconds"].astype(float), color="#fdae6b")
    ax.set_title("Runtime by benchmark unit")
    ax.set_ylabel("Seconds")
    ax.tick_params(axis="x", rotation=35)
    _clean_axis(ax)

    ax = axes[0, 1]
    ax.bar(runtime["unit_id"], runtime["peak_memory_mb"].astype(float), color="#9ecae1")
    ax.set_title("Peak memory by benchmark unit")
    ax.set_ylabel("MB")
    ax.tick_params(axis="x", rotation=35)
    _clean_axis(ax)

    ax = axes[1, 0]
    counts = gates["status"].value_counts().reindex(["pass", "borderline", "pending", "fail"]).dropna()
    ax.bar(counts.index, counts.values, color=_status_colors(counts.index))
    ax.set_title("Submission gate status")
    ax.set_ylabel("Gate count")
    _clean_axis(ax)

    ax = axes[1, 1]
    labels = ablation["ablation_id"] + "\n" + ablation["method"]
    ax.bar(labels, ablation["mean_pairwise_ari"].astype(float), color="#74c476")
    ax.axhline(0.80, color="#b30000", linestyle="--", linewidth=1)
    ax.set_title("PBMC3k stability ablations")
    ax.set_ylabel("Mean pairwise ARI")
    ax.tick_params(axis="x", rotation=35)
    _clean_axis(ax)

    fig.suptitle("Figure 5. Reproducibility, runtime, and release gates", fontsize=14)
    fig.tight_layout()
    return fig, [runtime_path, gates_path, ablation_path]


def render_all() -> list[dict[str, str]]:
    renderers = [figure1, figure2, figure3, figure4, figure5]
    manifest_rows: list[dict[str, str]] = []
    for (figure_id, stem), renderer in zip(FIGURE_SPECS, renderers):
        fig, inputs = renderer()
        png, pdf = _save_figure(fig, stem)
        manifest_rows.append(
            {
                "figure_id": figure_id,
                "png_path": _rel(png),
                "pdf_path": _rel(pdf),
                "input_paths": ";".join(_rel(path) for path in inputs),
                "regeneration_command": "python scripts/render_main_figures.py",
                "status": "rendered" if png.exists() and pdf.exists() else "missing",
                "notes": "Draft manuscript figure generated from source-data tables; requires design review before submission.",
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
            print(f"missing: {row['figure_id']} -> {row['png_path']} / {row['pdf_path']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
