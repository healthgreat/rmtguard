#!/usr/bin/env python
"""Build a project-level Gantt chart for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-03
Purpose: Summarize completed, blocked, and planned work for the RMTGuard
publication package as a reproducible project-management artifact.
Data source: Current local project status, external-review action plan, and
the 12-week manuscript execution route.
Method notes: Dates after the run date are planning dates, not completed work.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TODAY = date.today()
OUT_DIR = ROOT / "results" / "project_management"
FIG_DIR = ROOT / "figures" / "project_management"
TSV = OUT_DIR / "rmtguard_project_gantt.tsv"
MD = OUT_DIR / "rmtguard_project_gantt.md"
PNG = FIG_DIR / "rmtguard_project_gantt.png"
PDF = FIG_DIR / "rmtguard_project_gantt.pdf"

STATUS_COLORS = {
    "done": "#1B7837",
    "partial": "#E08214",
    "blocked": "#B2182B",
    "planned": "#6B7280",
}


@dataclass(frozen=True)
class Task:
    phase: str
    task: str
    start: date
    end: date
    status: str
    progress_pct: int
    evidence: str
    note: str


TASKS = [
    Task(
        "Algorithm and diagnostics",
        "RMTGuard v3/v3.2 adaptive embedding and diagnostics",
        date(2026, 4, 27),
        date(2026, 5, 1),
        "done",
        100,
        "PROJECT_STATUS.md",
        "API, adaptive embedding, graph resolution, and diagnostics implemented locally.",
    ),
    Task(
        "Algorithm and diagnostics",
        "Synthetic no-call and rare-state benchmark",
        date(2026, 4, 28),
        date(2026, 4, 30),
        "done",
        100,
        "results/no_call_benchmarks/no_call_summary.tsv",
        "Pure null no-call and rare-state retention checks passed.",
    ),
    Task(
        "Algorithm and diagnostics",
        "Callability decision map for Figure 3",
        date(2026, 5, 1),
        date(2026, 5, 2),
        "done",
        100,
        "results/callability/no_call_decision_map.tsv",
        "Figure 3D now exposes callability/no-call decisions from explicit flags.",
    ),
    Task(
        "Algorithm and diagnostics",
        "Rare-state guard v3.3 calibration patch",
        date(2026, 5, 2),
        date(2026, 5, 2),
        "done",
        100,
        "results/calibration/rare_state_power_summary.tsv",
        "Adaptive rare-state split improves realistic rare-state power while preserving count-null no-call behavior.",
    ),
    Task(
        "Public benchmark",
        "Phase 1 public data preparation and benchmark",
        date(2026, 4, 29),
        date(2026, 4, 30),
        "done",
        100,
        "results/figures/source_data/figure3_public_benchmark_summary.tsv",
        "PBMC3k, Kang, Baron, and PBMC68k source-data tables generated.",
    ),
    Task(
        "Public benchmark",
        "Four-dataset stability gate diagnostics",
        date(2026, 4, 30),
        date(2026, 5, 1),
        "done",
        100,
        "results/stability_benchmarks/stability_gate_diagnostics.tsv",
        "Current stability_advantage gate remains failed against strongest comparators.",
    ),
    Task(
        "Manuscript package",
        "External pre-review triage and route reframe",
        date(2026, 5, 1),
        date(2026, 5, 2),
        "done",
        100,
        "results/submission/external_review_action_plan.tsv",
        "Nature Methods frozen as no-go until P0/P1 blockers are resolved; Genome Biology fallback reframed.",
    ),
    Task(
        "Manuscript package",
        "Publication-style figures, tables, and visual audit",
        date(2026, 5, 1),
        date(2026, 5, 2),
        "done",
        100,
        "results/submission/publication_visual_asset_audit.tsv",
        "Main figures rendered as PNG/PDF/TIFF; Word table pack generated; visual audit passes.",
    ),
    Task(
        "Journal route",
        "20-50 JIF distance and gap assessment",
        date(2026, 5, 2),
        date(2026, 5, 2),
        "done",
        100,
        "docs/jif20_50_gap_assessment.md",
        "Current strict 20-50 route is scored and remaining blockers are mapped to next supplements.",
    ),
    Task(
        "Journal route",
        "Nature Methods next-round science gate board",
        date(2026, 5, 4),
        date(2026, 5, 4),
        "done",
        100,
        "docs/nature_methods_next_round_gate_board.md",
        "Remaining 20-50 JIF blockers converted into P0/P1 gates with owners, pass criteria, stop conditions, and manual author inputs.",
    ),
    Task(
        "Release",
        "Public GitHub repository, release, and Zenodo DOI",
        date(2026, 5, 2),
        date(2026, 5, 4),
        "done",
        100,
        "results/release/release_readiness.tsv",
        "Public GitHub repository, v0.1.0 GitHub Release, and Zenodo DOI are complete.",
    ),
    Task(
        "Statistics",
        "Realistic null and rare-state power calibration",
        date(2026, 5, 2),
        date(2026, 5, 12),
        "partial",
        55,
        "docs/realistic_null_power_calibration.md",
        "Draft count-preserving nulls remain controlled; v3.3 improves rare-state power, but weak-effect/lowest-prevalence settings and manuscript-grade repeats remain open.",
    ),
    Task(
        "Public benchmark",
        "Manuscript-grade stability rerun and stronger baselines",
        date(2026, 5, 2),
        date(2026, 5, 19),
        "partial",
        99,
        "docs/manuscript_grade_stability_statistics.md",
        "Seven-dataset pairwise ARI output, CI/paired-delta report, local matched Python baseline pilot, official Seurat fixed30/fixed50/elbow/JackStraw 20-repeat rows, and paired20 RMTGuard-versus-official-Seurat statistics added; added-dataset matched Seurat rows remain.",
    ),
    Task(
        "Algorithm and diagnostics",
        "Full component ablation",
        date(2026, 5, 2),
        date(2026, 5, 17),
        "partial",
        85,
        "docs/realdata_ablation_annotation.md",
        "Resumable draft component-ablation benchmark now covers null, rare-state, synthetic batch-effect, full-data real annotation, and a four-dataset 10-repeat real-data pilot; final P0 20-50 repeat/CI and matched baselines remain pending.",
    ),
    Task(
        "Algorithm and diagnostics",
        "Real-data annotation repeated-split pilot",
        date(2026, 5, 2),
        date(2026, 5, 2),
        "done",
        100,
        "docs/realdata_ablation_annotation.md",
        "Kang IFN-beta PBMC, Baron pancreas, PBMC68k/Zheng 2017, and PDAC GSE263733 now have 80% subsampling, 10-repeat, 5-variant annotation/batch ablation checks.",
    ),
    Task(
        "Manuscript package",
        "Real-data ablation forest plot and supplemental table",
        date(2026, 5, 3),
        date(2026, 5, 3),
        "done",
        100,
        "docs/realdata_ablation_figure_table.md",
        "Four-dataset 10-repeat real-data ablation pilot is now packaged as source data, PNG/PDF/TIFF forest plot, Word supplemental table, and visual-audit manifests.",
    ),
    Task(
        "Public benchmark",
        "Matched Seurat/JackStraw baseline design",
        date(2026, 5, 3),
        date(2026, 5, 3),
        "done",
        100,
        "docs/matched_baseline_design.md",
        "Execution design exists for RMTGuard, Scanpy, Seurat v5, JackStraw, and permutation/parallel PCA on identical split logic; results are still pending.",
    ),
    Task(
        "Public benchmark",
        "Local matched Python baseline pilot",
        date(2026, 5, 3),
        date(2026, 5, 3),
        "done",
        100,
        "docs/matched_baseline_pilot.md",
        "RMTGuard rows imported from ablation pilot and local Scanpy-like, fixed-PC, elbow, parallel-analysis, and JackStraw-like proxy baselines executed on matched 80% subsampling repeats.",
    ),
    Task(
        "Public benchmark",
        "Official Seurat MTX bridge and smoke",
        date(2026, 5, 3),
        date(2026, 5, 3),
        "done",
        100,
        "docs/seurat_matched_baseline.md",
        "MatrixMarket bridge generated for four prepared datasets; official Seurat v5 rows execute on the shared 80% subsampling framework.",
    ),
    Task(
        "Public benchmark",
        "Official Seurat fixed-PC/elbow 20-repeat comparator",
        date(2026, 5, 3),
        date(2026, 5, 3),
        "done",
        100,
        "docs/seurat_matched_baseline.md",
        "Official Seurat v5 fixed30, fixed50, and elbow-rule rows now have 20 repeats across seven prepared public datasets.",
    ),
    Task(
        "Public benchmark",
        "Official Seurat JackStraw 20-repeat comparator",
        date(2026, 5, 3),
        date(2026, 5, 3),
        "done",
        100,
        "docs/seurat_jackstraw_feasibility.md",
        "Official Seurat JackStraw runs across seven prepared public datasets with 20 subsampling repeats and 20 JackStraw replicates.",
    ),
    Task(
        "Public benchmark",
        "Paired RMTGuard vs official Seurat statistics",
        date(2026, 5, 3),
        date(2026, 5, 3),
        "done",
        100,
        "docs/rmtguard_seurat_paired_statistics.md",
        "RMTGuard default was rerun with the same random_state seed logic as official Seurat; 20 repeats are paired against Seurat fixed30/fixed50/elbow/JackStraw rows on five labeled datasets with bootstrap CIs, sign-flip p values, FDR, and a Figure 3 forest-plot source table.",
    ),
    Task(
        "Public benchmark",
        "Added-dataset official Seurat rows",
        date(2026, 5, 3),
        date(2026, 5, 3),
        "done",
        100,
        "docs/seurat_matched_baseline.md",
        "PBMC3k and PDAC GSE154778 now have official Seurat fixed30/fixed50/elbow/JackStraw 20-repeat rows; they remain label-free stability/runtime evidence unless reliable annotations are added.",
    ),
    Task(
        "Biological application",
        "PDAC/TME showcase deepening or demotion",
        date(2026, 5, 12),
        date(2026, 5, 26),
        "planned",
        0,
        "docs/pdac_tme_showcase_depth.md",
        "Differential expression, pathway enrichment, trajectory/published-atlas validation, or supplement downgrade.",
    ),
    Task(
        "Public benchmark",
        "Additional public datasets",
        date(2026, 5, 3),
        date(2026, 5, 3),
        "done",
        100,
        "docs/manuscript_grade_stability_statistics.md",
        "Stability benchmark expanded from four to seven public datasets by adding Paul15 hematopoiesis, PDAC GSE154778, and PDAC GSE263733.",
    ),
    Task(
        "Manuscript package",
        "Final figure source data, captions, and reporting summary",
        date(2026, 6, 2),
        date(2026, 6, 16),
        "planned",
        0,
        "docs/nature_reporting_summary_draft.md",
        "Regenerate all source-data tables and final journal-resolution figures after benchmark freeze.",
    ),
    Task(
        "Release",
        "Post-release gates and reproducibility audit",
        date(2026, 5, 4),
        date(2026, 5, 4),
        "done",
        100,
        "results/submission/submission_guard.tsv",
        "Release readiness, public-release blockers, source audit, claim lint, and traceability checks pass; scientific submission guard remains separate.",
    ),
    Task(
        "Release",
        "Cross-project shared information package",
        date(2026, 5, 4),
        date(2026, 5, 4),
        "done",
        100,
        "docs/shared_info_export_manifest.md",
        "Reusable RMTGuard status, manual-action, release-evidence, and external-review templates exported to D:/99、共用信息 for other projects.",
    ),
    Task(
        "Journal route",
        "Nature Methods vs Genome Biology go/no-go",
        date(2026, 6, 21),
        date(2026, 7, 5),
        "planned",
        0,
        "results/submission/post_feedback_journal_route_gate.tsv",
        "Nature Methods only if gates pass; otherwise reframe for Genome Biology or lower-risk route.",
    ),
    Task(
        "Journal route",
        "Submission package freeze",
        date(2026, 7, 6),
        date(2026, 7, 19),
        "planned",
        0,
        "results/submission/presubmission_gatekeeper.tsv",
        "Final abstract, cover letter, checklist, data/code availability, and source-data package.",
    ),
]


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


def _atomic_write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def build_table() -> pd.DataFrame:
    rows = []
    for idx, task in enumerate(TASKS, start=1):
        duration = (task.end - task.start).days + 1
        rows.append(
            {
                "task_id": f"T{idx:02d}",
                "phase": task.phase,
                "task": task.task,
                "start": task.start.isoformat(),
                "end": task.end.isoformat(),
                "duration_days": duration,
                "status": task.status,
                "progress_pct": task.progress_pct,
                "evidence": task.evidence,
                "note": task.note,
            }
        )
    return pd.DataFrame(rows)


def render_gantt(df: pd.DataFrame) -> None:
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 8.5,
            "axes.titlesize": 12,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 7,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    plot_df = df.iloc[::-1].copy()
    fig_height = max(6.5, 0.34 * len(plot_df) + 1.6)
    fig, ax = plt.subplots(figsize=(11.0, fig_height), constrained_layout=True)

    y_positions = range(len(plot_df))
    for y, row in zip(y_positions, plot_df.itertuples(index=False)):
        start = mdates.date2num(pd.to_datetime(row.start).date())
        end = mdates.date2num(pd.to_datetime(row.end).date())
        width = end - start + 1
        color = STATUS_COLORS.get(row.status, "#6B7280")
        ax.barh(
            y,
            width,
            left=start,
            height=0.62,
            color=color,
            edgecolor="#2F3437",
            linewidth=0.5,
        )
        if row.progress_pct > 0 and row.progress_pct < 100:
            ax.barh(
                y,
                width * row.progress_pct / 100,
                left=start,
                height=0.28,
                color="#F4F4F4",
                edgecolor="none",
                alpha=0.75,
            )
        ax.text(
            start + width + 0.25,
            y,
            f"{row.status} ({row.progress_pct}%)",
            va="center",
            fontsize=7,
            color="#2F3437",
        )

    ax.axvline(
        mdates.date2num(TODAY),
        color="#111827",
        linestyle="--",
        linewidth=1.0,
        label=f"Today {TODAY.isoformat()}",
    )
    ax.set_yticks(list(y_positions))
    ax.set_yticklabels(plot_df["task"])
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.grid(axis="x", color="#E6E8EB", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title(
        f"RMTGuard Project Gantt Chart (status as of {TODAY.isoformat()})",
        loc="left",
    )
    ax.set_xlabel("Date in 2026")

    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, color=color, label=status)
        for status, color in STATUS_COLORS.items()
    ]
    ax.legend(handles=legend_handles, loc="lower right", frameon=False, ncol=4)

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for path in [PNG, PDF]:
        tmp = path.with_suffix(path.suffix + ".tmp")
        fig.savefig(
            tmp,
            format=path.suffix.lstrip("."),
            dpi=300,
            bbox_inches="tight",
            facecolor="white",
        )
        tmp.replace(path)
    plt.close(fig)


def build_markdown(df: pd.DataFrame) -> str:
    lines = [
        "# RMTGuard project Gantt chart",
        "",
        f"Generated by `python scripts/build_project_gantt.py` on {TODAY.isoformat()}.",
        "",
        f"Dates after {TODAY.isoformat()} are planned dates, not completed evidence.",
        "",
        f"- PNG: `{_rel(PNG)}`",
        f"- PDF: `{_rel(PDF)}`",
        f"- Source table: `{_rel(TSV)}`",
        "",
        "## Mermaid Gantt",
        "",
        "```mermaid",
        "gantt",
        f"    title RMTGuard project progress as of {TODAY.isoformat()}",
        "    dateFormat  YYYY-MM-DD",
        "    axisFormat  %m-%d",
    ]
    for phase, phase_df in df.groupby("phase", sort=False):
        lines.append(f"    section {phase}")
        for row in phase_df.itertuples(index=False):
            mermaid_status = (
                "done"
                if row.status == "done"
                else "active" if row.status in {"partial", "blocked"} else ""
            )
            prefix = f"{mermaid_status}, " if mermaid_status else ""
            safe_task = row.task.replace(":", "-").replace(",", ";")
            lines.append(
                f"    {safe_task} :{prefix}{row.task_id}, {row.start}, {row.duration_days}d"
            )
    lines.extend(
        [
            "```",
            "",
            "## Source Table",
            "",
            "| ID | Phase | Task | Start | End | Status | Progress | Evidence |",
            "| --- | --- | --- | --- | --- | --- | ---: | --- |",
        ]
    )
    for row in df.itertuples(index=False):
        lines.append(
            f"| {row.task_id} | {row.phase} | {row.task} | {row.start} | {row.end} | {row.status} | {row.progress_pct}% | `{row.evidence}` |"
        )
    lines.extend(
        [
            "",
            "## Current blockers",
            "",
            "- Public GitHub repository, GitHub Release, and Zenodo DOI are complete for v0.1.0.",
            "- Stability advantage remains failed against the strongest current comparator set.",
            "- Realistic count-preserving null calibration is drafted and rare-state power improved, but the full power grid and manuscript-grade repeats remain incomplete.",
            "- Component ablation now has an evidence/gap matrix plus a four-dataset 10-repeat annotation pilot, but the final 20-50 repeat experimental ablation suite is not complete.",
            "- Local matched Python baselines, official Seurat fixed30/fixed50/elbow/JackStraw 20-repeat rows across seven datasets, paired20 RMTGuard-versus-official-Seurat statistics across five labeled datasets, and seven-dataset stability breadth are now present; PBMC3k and PDAC GSE154778 remain label-free evidence unless annotations are added.",
            "- PDAC/TME remains a bounded showcase until deeper biology validation is added or it is demoted.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    df = build_table()
    _atomic_write_tsv(df, TSV)
    render_gantt(df)
    _atomic_write_text(build_markdown(df), MD)
    print(_rel(TSV))
    print(_rel(PNG))
    print(_rel(PDF))
    print(_rel(MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
