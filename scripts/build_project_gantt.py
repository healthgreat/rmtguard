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
    "done_with_limit": "#4D9221",
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
        date(2026, 5, 12),
        "done",
        100,
        "docs/no_call_decision_map.md",
        "Figure 3 callability/no-call map now has auditable source data plus PNG/PDF/TIFF assets and a render manifest.",
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
        "Journal route",
        "Nature Methods 48-hour execution packet",
        date(2026, 5, 4),
        date(2026, 5, 4),
        "done",
        100,
        "docs/nature_methods_48h_execution_packet.md",
        "Claim lock, P0 ablation run sheet, null/power grid design, and annotation-boundary table generated for the next sprint.",
    ),
    Task(
        "Biological application",
        "PDAC/TME route decision packet",
        date(2026, 5, 4),
        date(2026, 5, 4),
        "done",
        100,
        "docs/pdac_tme_route_decision_packet.md",
        "Main-figure versus supplement decision criteria, pass/stop gates, and exact author reply templates are generated without falsely completing the author decision.",
    ),
    Task(
        "Biological application",
        "PDAC/TME dual-route preflight and runbook",
        date(2026, 5, 4),
        date(2026, 5, 4),
        "done",
        100,
        "docs/pdac_tme_dual_route_preflight.md",
        "Primary and validation AnnData inputs, label/covariate availability, formal DE/GSEA gaps, and both route execution steps are documented.",
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
        date(2026, 5, 4),
        "done",
        100,
        "docs/realistic_null_power_calibration.md",
        "50-repeat count-preserving null and rare-state power curves are complete; lowest-prevalence weak-effect settings remain a claim-boundary limitation.",
    ),
    Task(
        "Statistics",
        "Rare-state weak-regime claim boundary",
        date(2026, 5, 4),
        date(2026, 5, 4),
        "done",
        100,
        "docs/rare_state_claim_boundary.md",
        "Power is strong for moderate settings but weak at prevalence 0.02/effect 2.5; a claim-boundary table now blocks universal rare-state recovery wording.",
    ),
    Task(
        "Public benchmark",
        "Manuscript-grade stability rerun and stronger baselines",
        date(2026, 5, 2),
        date(2026, 5, 19),
        "partial",
        99,
        "docs/manuscript_grade_stability_statistics.md",
        "Seven-dataset pairwise ARI output, CI/paired-delta report, local matched Python baseline pilot, official Seurat fixed30/fixed50/elbow/JackStraw 20-repeat rows, paired20 RMTGuard-versus-official-Seurat statistics, and added-dataset matched Seurat rows are present.",
    ),
    Task(
        "Algorithm and diagnostics",
        "Full component ablation",
        date(2026, 5, 2),
        date(2026, 5, 17),
        "partial",
        95,
        "docs/p0_science_sprint_status.md",
        "Synthetic and labeled real-data component-ablation layers now reach 20 repeats with CI columns; 50-repeat realistic null/power calibration is complete and claim-bounded.",
    ),
    Task(
        "Algorithm and diagnostics",
        "P0 synthetic component ablation 20-repeat CI layer",
        date(2026, 5, 4),
        date(2026, 5, 4),
        "done",
        100,
        "docs/component_ablation_benchmark.md",
        "Synthetic null, rare-state, and batch-effect component ablations rerun to 20 repeats with CI columns and source data.",
    ),
    Task(
        "Algorithm and diagnostics",
        "Real-data annotation repeated-split pilot",
        date(2026, 5, 2),
        date(2026, 5, 4),
        "done",
        100,
        "docs/realdata_ablation_annotation.md",
        "Kang IFN-beta PBMC, Baron pancreas, PBMC68k/Zheng 2017, and PDAC GSE263733 now have 80% subsampling, 20-repeat, 7-variant annotation/batch ablation checks.",
    ),
    Task(
        "Algorithm and diagnostics",
        "P0 real-data component ablation 20-repeat layer",
        date(2026, 5, 4),
        date(2026, 5, 4),
        "done",
        100,
        "docs/realdata_ablation_annotation.md",
        "Four labeled public datasets x seven variants reached 20 repeats with label-ARI, batch-ARI, no-call, and CI summaries.",
    ),
    Task(
        "Manuscript package",
        "Real-data ablation forest plot and supplemental table",
        date(2026, 5, 3),
        date(2026, 5, 4),
        "done",
        100,
        "docs/realdata_ablation_figure_table.md",
        "Four-dataset real-data ablation checks are packaged as source data, PNG/PDF/TIFF forest plot, Word supplemental table, and visual-audit manifests.",
    ),
    Task(
        "Manuscript package",
        "Current evidence-freeze manifest",
        date(2026, 5, 12),
        date(2026, 5, 12),
        "done",
        100,
        "docs/current_evidence_freeze_2026-05-12.md",
        "Manuscript-facing figures, source-data tables, reports, checksums, claim boundaries, and next actions are frozen for the current evidence state.",
    ),
    Task(
        "Manuscript package",
        "Freeze-aligned Results and figure legends",
        date(2026, 5, 12),
        date(2026, 5, 12),
        "done",
        100,
        "manuscript/results_freeze_aligned_draft.md",
        "Results paragraphs, figure legends, and text-level claim audit generated from the current evidence freeze.",
    ),
    Task(
        "Manuscript package",
        "External review Word packet",
        date(2026, 5, 12),
        date(2026, 5, 12),
        "done",
        100,
        "output/doc/RMTGuard_external_review_packet_2026-05-12.docx",
        "Reviewer-facing DOCX packet built from the evidence freeze, gap assessment, Results draft, figure legends, audit table, Gantt snapshot, and manual-action checklist.",
    ),
    Task(
        "Manuscript package",
        "Nature reporting-summary worksheet refresh",
        date(2026, 5, 12),
        date(2026, 5, 12),
        "done",
        100,
        "docs/nature_reporting_summary_draft.md",
        "Reporting-summary worksheet refreshed to reflect completed public GitHub/Zenodo evidence and remaining version-coverage/manual-author checks.",
    ),
    Task(
        "Manuscript package",
        "Author declaration confirmation packet",
        date(2026, 5, 12),
        date(2026, 5, 12),
        "blocked",
        75,
        "docs/author_declaration_confirmation_packet.md",
        "Funding, competing interests, ethics/public-data wording, postal code, CRediT roles, title-page metadata, reporting-summary verification, and Figure 4 acknowledgement are converted into exact author-confirmation questions.",
    ),
    Task(
        "Manuscript package",
        "High-impact submission dashboard",
        date(2026, 5, 12),
        date(2026, 5, 12),
        "done_with_limit",
        90,
        "docs/high_impact_submission_dashboard.md",
        "Single dashboard now merges 20-50 JIF distance, Nature Methods go/no-go, v0.1.1 preflight, author blockers, Figure 4 acknowledgement, reporting summary, claim integrity, and remaining science gaps.",
    ),
    Task(
        "Manuscript package",
        "Figure-caption-source audit and Figure 5 layout decision",
        date(2026, 5, 12),
        date(2026, 5, 12),
        "done",
        100,
        "docs/figure_caption_source_audit.md",
        "All intended display items have rendered assets, source data and frozen legends; Figure 5 is fixed as main release/runtime/PBMC3k ablation, with real-data ablation moved to Extended Data.",
    ),
    Task(
        "Release",
        "Post-release version coverage audit",
        date(2026, 5, 12),
        date(2026, 5, 12),
        "done_with_limit",
        90,
        "docs/post_release_version_coverage_audit.md",
        "v0.1.0 remains immutable; current manuscript-facing branch requires a future v0.1.1 if these post-release files are used in submission, but tagging waits for author-controlled blockers.",
    ),
    Task(
        "Release",
        "v0.1.1 no-action release preflight",
        date(2026, 5, 12),
        date(2026, 5, 12),
        "blocked",
        70,
        "docs/v0_1_1_release_preflight.md",
        "Preflight gate created and intentionally blocks release until author declarations, Figure 4 acknowledgement, reporting-summary verification, and final version coverage are resolved.",
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
        "Public benchmark",
        "Direct scLENSpy n_rand_matrix=20 comparator",
        date(2026, 5, 12),
        date(2026, 5, 12),
        "done",
        100,
        "docs/sclens_stability_nrand20_2026-05-12.md",
        "Direct scLENSpy comparator completed on PBMC3k and Kang with 10 subsampling repeats and n_rand_matrix=20.",
    ),
    Task(
        "Public benchmark",
        "CONCORD-style topology stress benchmark",
        date(2026, 5, 12),
        date(2026, 5, 12),
        "done",
        100,
        "docs/topology_stress_benchmark_2026-05-12.md",
        "Line, branch, and loop topology stress tests completed with 20 repeats and journal-ready source data/figure assets.",
    ),
    Task(
        "Public benchmark",
        "Paul15 real-data topology monitor",
        date(2026, 5, 12),
        date(2026, 5, 12),
        "done_with_limit",
        90,
        "docs/realdata_topology_benchmark_2026-05-12.md",
        "Paul15 annotation-derived topology monitor completed with 10 repeats; it supports bounded trade-off wording rather than broad topology superiority.",
    ),
    Task(
        "Biological application",
        "PDAC/TME deep validation first pass",
        date(2026, 5, 10),
        date(2026, 5, 10),
        "done_with_limit",
        75,
        "docs/pdac_tme_deep_validation.md",
        "FDR-controlled marker DE, marker-set enrichment, external signature transfer, and Figure 4 source data are complete; pathway/atlas upgrade and bounded wording now control the final claim.",
    ),
    Task(
        "Biological application",
        "PDAC/TME pathway and atlas upgrade",
        date(2026, 5, 10),
        date(2026, 5, 10),
        "done_with_limit",
        85,
        "docs/pdac_tme_pathway_atlas_validation.md",
        "Rank-based MSigDB Hallmark/Reactome enrichment, manuscript-interpretable pathway labeling, atlas marker citation mapping, and Figure 4 pathway/atlas source data are complete.",
    ),
    Task(
        "Biological application",
        "PDAC/TME final Figure 4 wording freeze",
        date(2026, 5, 10),
        date(2026, 5, 10),
        "done_with_limit",
        90,
        "docs/figure4_pdac_tme_wording_freeze.md",
        "Bounded Figure 4 title, caption, allowed wording, forbidden wording, and source-data wording are frozen; formal corresponding-author acknowledgement remains before external submission.",
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
        "Nature Methods presubmission go/no-go packet",
        date(2026, 5, 10),
        date(2026, 5, 10),
        "done_with_limit",
        90,
        "docs/nature_methods_go_no_go_final.md",
        "Full Nature Methods submission remains no-go; presubmission inquiry is conditionally go after corresponding-author Figure 4 acknowledgement.",
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
            "- Nature Methods claim scope is now locked to callability-aware random-matrix noise control; broad stability-superiority language remains disallowed.",
            "- A 48-hour execution packet now exists for P0 component ablations, realistic null/power grids, and added-dataset annotation boundaries.",
            "- Synthetic and labeled real-data component ablations have reached 20-repeat depth with CI columns.",
            "- Stability advantage remains failed against the strongest current comparator set.",
            "- Realistic count-preserving null calibration and rare-state power grids have reached 50-repeat manuscript-grade depth; low-prevalence weak-effect settings remain an explicit claim-boundary limitation.",
            "- Component ablation now has synthetic 20-repeat CI evidence and four-dataset labeled real-data 20-repeat annotation checks; remaining ablation risk is interpretation, not missing repeat depth.",
            "- Local matched Python baselines, official Seurat fixed30/fixed50/elbow/JackStraw 20-repeat rows across seven datasets, paired20 RMTGuard-versus-official-Seurat statistics across five labeled datasets, and seven-dataset stability breadth are now present; PBMC3k and PDAC GSE154778 remain label-free evidence unless annotations are added.",
            "- PDAC/TME deep validation, pathway/atlas upgrade, bounded Figure 4 wording freeze, and Nature Methods presubmission go/no-go packet are complete with limits; formal corresponding-author acknowledgement remains before external submission.",
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
