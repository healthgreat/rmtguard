#!/usr/bin/env python
"""Build the 48-hour Nature Methods execution packet for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-04
Purpose: Convert the immediate Nature Methods science gates into concrete
claim-control, ablation, calibration, and annotation-boundary artifacts.
Data source: Current local RMTGuard benchmark summaries and submission gates.
Method notes: This script writes planning/run-sheet artifacts only. It does
not run long benchmarks, download data, or alter archived public releases.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKET_TSV = ROOT / "results" / "submission" / "nature_methods_48h_execution_packet.tsv"
PACKET_MD = ROOT / "docs" / "nature_methods_48h_execution_packet.md"
CLAIM_MD = ROOT / "manuscript" / "claim_scope_final.md"
CLAIM_AUDIT_TSV = ROOT / "results" / "submission" / "claim_scope_final_audit.tsv"
ABLATION_TSV = ROOT / "results" / "ablation" / "p0_component_ablation_run_sheet.tsv"
ABLATION_MD = ROOT / "docs" / "p0_component_ablation_run_sheet.md"
NULL_POWER_TSV = (
    ROOT / "results" / "calibration" / "manuscript_grade_null_power_grid_design.tsv"
)
NULL_POWER_MD = ROOT / "docs" / "manuscript_grade_null_power_grid_design.md"
ANNOTATION_TSV = ROOT / "results" / "submission" / "added_dataset_annotation_boundary.tsv"
ANNOTATION_MD = ROOT / "docs" / "added_dataset_annotation_boundary.md"


@dataclass(frozen=True)
class PacketStep:
    step_id: str
    gate_id: str
    status: str
    owner: str
    output_artifact: str
    next_command: str
    pass_criterion: str
    stop_condition: str


@dataclass(frozen=True)
class ClaimRow:
    claim_id: str
    allowed_claim: str
    evidence_path: str
    forbidden_upgrade: str
    manuscript_location: str
    status: str


@dataclass(frozen=True)
class AblationRow:
    run_id: str
    component: str
    comparison: str
    data_layer: str
    repeat_count_planned: int
    primary_metrics: str
    planned_command: str
    checkpoint_policy: str
    pass_interpretation: str
    stop_condition: str


@dataclass(frozen=True)
class NullPowerRow:
    grid_id: str
    scenario: str
    prevalence: str
    effect_size: str
    dropout_rate: str
    batch_structure: str
    n_repeats_planned: int
    expected_output: str
    pass_criterion: str
    stop_condition: str


@dataclass(frozen=True)
class AnnotationBoundaryRow:
    dataset_id: str
    evidence_role: str
    label_status: str
    allowed_metric: str
    forbidden_metric_or_claim: str
    required_action_before_upgrade: str


PACKET_STEPS = [
    PacketStep(
        "48H-01",
        "NM-G01",
        "done",
        "Codex",
        "manuscript/claim_scope_final.md",
        "python scripts/build_nature_methods_48h_execution_packet.py",
        "Claim scope is locked to callability-aware random-matrix noise control.",
        "Stop Nature Methods wording if any text claims broad stability superiority.",
    ),
    PacketStep(
        "48H-02",
        "NM-G02",
        "run_sheet_ready",
        "Codex",
        "results/ablation/p0_component_ablation_run_sheet.tsv",
        "Use the run sheet to launch 20-50 repeat ablations when compute window is available.",
        "Every P0 component has a repeat count, metric, checkpoint policy, and stop condition.",
        "Do not promote any component to main claim without CI and real-data annotation checks.",
    ),
    PacketStep(
        "48H-03",
        "NM-G03",
        "grid_design_ready",
        "Codex",
        "results/calibration/manuscript_grade_null_power_grid_design.tsv",
        "Use the grid design to scale realistic null and rare-state power calibration.",
        "The grid covers prevalence, effect size, dropout, and batch structures.",
        "Do not cite one favorable rare-state setting as general power.",
    ),
    PacketStep(
        "48H-04",
        "NM-G07",
        "boundary_table_ready",
        "Codex",
        "results/submission/added_dataset_annotation_boundary.tsv",
        "Use the boundary table when writing Figure 3 and benchmark text.",
        "Every dataset is typed as labeled annotation evidence or label-free evidence.",
        "Do not report annotation ARI for label-free datasets.",
    ),
    PacketStep(
        "48H-05",
        "NM-G04",
        "waiting_author_decision",
        "Chongfa Chen + corresponding authors",
        "metadata/pdac_tme_route_decision.tsv",
        "Author reply required: deepen PDAC/TME as main figure or demote to supplement.",
        "A written decision exists before Figure 4 is rebuilt.",
        "Do not spend additional compute on PDAC/TME main-figure analysis before this decision.",
    ),
]


CLAIM_ROWS = [
    ClaimRow(
        "C01",
        "RMTGuard is a callability-aware random-matrix noise-control workflow for scRNA-seq cell-state discovery.",
        "docs/jif20_50_gap_assessment.md",
        "Do not claim universal superiority over Seurat, Scanpy, fixed-PC, or elbow-rule baselines.",
        "Abstract; Results paragraph 1; Figure 1 caption",
        "locked",
    ),
    ClaimRow(
        "C02",
        "The current public release and DOI engineering gate is complete for v0.1.0.",
        "docs/public_release_blocker_report.md",
        "Do not imply the current post-release main branch is the immutable DOI snapshot.",
        "Code Availability; Methods software section",
        "locked",
    ),
    ClaimRow(
        "C03",
        "Pure-null and rare-state synthetic checks support noise-control and rare-state retention under tested settings.",
        "results/calibration/rare_state_power_summary.tsv",
        "Do not generalize rare-state power beyond the tested prevalence/effect-size grid.",
        "Results synthetic benchmark; Figure 2 caption",
        "locked",
    ),
    ClaimRow(
        "C04",
        "PBMC3k and PDAC GSE154778 are label-free stability/runtime evidence unless reliable annotations are added.",
        "results/submission/added_dataset_annotation_boundary.tsv",
        "Do not report annotation ARI or biological discovery claims for label-free datasets.",
        "Figure 3; Supplementary benchmark tables",
        "locked",
    ),
    ClaimRow(
        "C05",
        "PDAC/TME is a bounded public-data showcase until authors choose and complete a stronger validation route.",
        "docs/nature_methods_next_round_gate_board.md",
        "Do not write PDAC/TME as a clinical or mechanistic discovery from marker-smoke evidence alone.",
        "Figure 4; Discussion limitations",
        "waiting_author_decision",
    ),
]


ABLATION_ROWS = [
    AblationRow(
        "AB-P0-01",
        "MP edge",
        "mp_edge_on_vs_off",
        "pure_null;realistic_null;rare_state;real_data_labeled",
        50,
        "false_signal_pc_rate;null_no_call_rate;rare_ari;annotation_ari_delta",
        "python scripts/run_component_ablation_benchmark.py --n-repeats 50 --force",
        "Use existing script checkpoints and rerun only missing/forced rows.",
        "Keep if false-signal control improves without lowering rare-state/real-data recovery.",
        "Drop or demote if it only improves pure-null metrics while harming labeled real data.",
    ),
    AblationRow(
        "AB-P0-02",
        "Tracy-Widom proxy",
        "mp_tw_vs_mp_only",
        "pure_null;realistic_null;rare_state",
        50,
        "false_signal_pc_rate;selected_pc_count;rare_ari",
        "python scripts/run_component_ablation_benchmark.py --n-repeats 50 --n-permutations 50 --force",
        "Use fixed random_state family; record all PC diagnostics.",
        "Keep if finite-sample edge control improves without power loss.",
        "Demote to supplement if effect is negligible against MP-only.",
    ),
    AblationRow(
        "AB-P0-03",
        "Permutation calibration",
        "permutation_on_vs_tw_proxy",
        "realistic_null;rare_state",
        20,
        "false_signal_pc_rate;runtime;memory;rare_ari",
        "python scripts/run_realistic_null_power_calibration.py --n-repeats 20 --pc-rule mp_tw_permutation --n-permutations 100",
        "Record runtime/memory because calibration may be expensive.",
        "Keep as optional if it improves calibration but costs runtime.",
        "Do not make it default if runtime prevents workstation-scale use.",
    ),
    AblationRow(
        "AB-P0-04",
        "HVG spectral plateau",
        "hvg_plateau_vs_fixed_hvg",
        "rare_state;real_data_labeled",
        20,
        "accepted_hvg_count;rare_ari;annotation_ari_delta;cluster_count_variance",
        "python scripts/run_realdata_ablation_annotation.py --n-repeats 20 --subsample-fraction 0.8 --run-label p0_hvg",
        "Run on the five labeled datasets only.",
        "Keep if it reduces parameter dependence without annotation penalty.",
        "Demote if fixed HVG is non-inferior and simpler.",
    ),
    AblationRow(
        "AB-P0-05",
        "Adaptive near-edge embedding",
        "adaptive_embedding_vs_strict_signal",
        "rare_state;real_data_labeled",
        20,
        "embedding_pc_count;pc_stability;pairwise_ari;annotation_ari_delta",
        "python scripts/run_realdata_ablation_annotation.py --n-repeats 20 --subsample-fraction 0.8 --run-label p0_embedding",
        "Pair repeats with the same seed family as official Seurat baselines.",
        "Keep if stability/annotation Pareto improves or remains defensible.",
        "Do not claim stability advantage if strongest baseline remains higher.",
    ),
    AblationRow(
        "AB-P0-06",
        "Rare-state guard",
        "rare_state_guard_on_vs_off",
        "rare_state_grid;real_data_labeled",
        50,
        "rare_ari;rare_f1;over_split_rate;annotation_ari_delta",
        "python scripts/run_realistic_null_power_calibration.py --n-repeats 50 --rare-state-guard adaptive_binary_split",
        "Report full power curve by prevalence/effect, not only the best cell.",
        "Keep if rare-state recovery improves without overclustering.",
        "Demote if weak-effect/low-prevalence settings are unstable.",
    ),
    AblationRow(
        "AB-P0-07",
        "Diagnostic no-call contract",
        "no_call_contract_on_vs_forced_call",
        "pure_null;low_signal_real_data",
        50,
        "false_cluster_rate;no_call_rate;annotation_ari_when_called",
        "python scripts/run_component_ablation_benchmark.py --n-repeats 50 --false-signal-pc-floor 1",
        "Separate no-call correctness from forced-clustering performance.",
        "Keep as a core claim if false-cluster control is clearly improved.",
        "Do not frame no-call as failure if the null/low-signal contract is met.",
    ),
    AblationRow(
        "AB-P0-08",
        "Batch residualization",
        "batch_aware_vs_unaware",
        "synthetic_batch;Kang IFN-beta PBMC",
        20,
        "batch_pc_fraction;annotation_ari_delta;batch_mixing_delta",
        "python scripts/run_realdata_ablation_annotation.py --datasets kang_ifnb_pbmc --n-repeats 20 --run-label p0_batch",
        "Use public batch/covariate fields only.",
        "Keep if batch-driven PCs decrease without biological signal loss.",
        "Demote if residualization removes condition/state biology.",
    ),
]


NULL_POWER_ROWS = [
    NullPowerRow(
        "NP-GRID-01",
        "count_preserving_null",
        "0",
        "0",
        "empirical",
        "none",
        50,
        "results/calibration/manuscript_grade_null_power_grid.tsv",
        "False signal PC rate is near preset alpha and false cluster rate is low.",
        "Stop if pure null or count-preserving null repeatedly produces stable clusters.",
    ),
    NullPowerRow(
        "NP-GRID-02",
        "rare_state_low_prevalence_weak_effect",
        "0.005;0.01",
        "0.4;0.6",
        "0.2;0.4",
        "none",
        50,
        "results/calibration/manuscript_grade_null_power_grid.tsv",
        "Report power as low/limited if recovery is weak; do not hide the failure mode.",
        "Stop Nature Methods rare-state claim if this is central and remains weak.",
    ),
    NullPowerRow(
        "NP-GRID-03",
        "rare_state_moderate_prevalence",
        "0.02;0.05",
        "0.8;1.2",
        "0.2;0.4",
        "none",
        50,
        "results/calibration/manuscript_grade_null_power_grid.tsv",
        "Rare-state ARI/F1 meets prespecified thresholds with CI.",
        "Do not extrapolate to smaller prevalence without showing the curve.",
    ),
    NullPowerRow(
        "NP-GRID-04",
        "batch_effect_null",
        "0",
        "0",
        "empirical",
        "library_size_plus_batch",
        50,
        "results/calibration/manuscript_grade_null_power_grid.tsv",
        "Batch-aware mode lowers batch-driven PCs without producing false biological clusters.",
        "Stop batch-aware claim if residualization creates false structure.",
    ),
    NullPowerRow(
        "NP-GRID-05",
        "dropout_stress_rare_state",
        "0.01;0.02;0.05",
        "0.8;1.2",
        "0.5;0.7",
        "none",
        50,
        "results/calibration/manuscript_grade_null_power_grid.tsv",
        "Power degradation is quantified and shown as a stress-test limit.",
        "Do not claim dropout robustness if recovery collapses.",
    ),
]


ANNOTATION_ROWS = [
    AnnotationBoundaryRow(
        "kang_ifnb_pbmc",
        "labeled_annotation_and_stability",
        "public_labels_available",
        "annotation_ARI;NMI;pairwise_ARI;cluster_count_variance;runtime",
        "none if labels and preprocessing are documented",
        "Keep label source and preprocessing table in supplement.",
    ),
    AnnotationBoundaryRow(
        "baron_pancreas",
        "labeled_annotation_and_stability",
        "public_labels_available",
        "annotation_ARI;NMI;pairwise_ARI;cluster_count_variance;runtime",
        "none if labels and preprocessing are documented",
        "Keep label source and preprocessing table in supplement.",
    ),
    AnnotationBoundaryRow(
        "pbmc68k_zheng2017",
        "labeled_annotation_but_diagnostic_no_call_boundary",
        "public_labels_available_but_low_signal_result",
        "annotation_ARI_when_called;no_call_rate;runtime",
        "Do not call it a positive discovery or stability win.",
        "Keep diagnostic-no-call wording.",
    ),
    AnnotationBoundaryRow(
        "paul15_hematopoiesis",
        "labeled_annotation_and_stability",
        "public_labels_available",
        "annotation_ARI;NMI;pairwise_ARI;cluster_count_variance;runtime",
        "none if labels and preprocessing are documented",
        "Keep label source and preprocessing table in supplement.",
    ),
    AnnotationBoundaryRow(
        "pdac_gse263733",
        "labeled_external_pdac_validation",
        "public_labels_or_marker_annotations_available",
        "annotation_ARI;marker_consistency;pairwise_ARI;runtime",
        "Do not overstate clinical or mechanism validation from labels alone.",
        "Use as external support only with bounded PDAC/TME wording.",
    ),
    AnnotationBoundaryRow(
        "pbmc3k",
        "label_free_stability_runtime_only",
        "no_reliable_label_source_in_current_package",
        "pairwise_ARI;cluster_count_variance;runtime;memory",
        "Do not report annotation ARI.",
        "Add reliable documented labels before upgrading.",
    ),
    AnnotationBoundaryRow(
        "pdac_gse154778",
        "label_free_pdac_showcase_stability_runtime_only",
        "no_reliable_label_source_in_current_package",
        "pairwise_ARI;cluster_count_variance;marker_smoke_only;runtime",
        "Do not report annotation ARI or biological discovery claims.",
        "Add DE/GSEA/trajectory/external validation before main-figure upgrade.",
    ),
]


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _rows(items: list[object]) -> list[dict[str, str]]:
    return [item.__dict__.copy() for item in items]


def _markdown_table(rows: list[dict[str, str]], columns: list[str]) -> list[str]:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row[col]) for col in columns) + " |")
    return lines


def build_claim_markdown(claims: list[dict[str, str]]) -> str:
    lines = [
        "# RMTGuard Final Claim Scope Lock",
        "",
        "Generated by `python scripts/build_nature_methods_48h_execution_packet.py`.",
        "",
        "## Locked Narrative",
        "",
        "RMTGuard should be described as a callability-aware random-matrix noise-control workflow for scRNA-seq cell-state discovery. The current evidence supports transparent noise diagnostics, diagnostic no-call behavior, release reproducibility, and bounded synthetic/real-data benchmark claims. The current evidence does not support broad stability superiority over the strongest Seurat/Scanpy/fixed-PC/elbow comparators.",
        "",
        "## Allowed And Forbidden Claim Boundaries",
        "",
    ]
    lines.extend(
        _markdown_table(
            claims,
            [
                "claim_id",
                "allowed_claim",
                "evidence_path",
                "forbidden_upgrade",
                "status",
            ],
        )
    )
    lines.extend(
        [
            "",
            "## Submission Rule",
            "",
            "Do not submit to Nature Methods until this claim scope remains consistent with every main-text result, figure caption, abstract sentence, cover-letter paragraph, and source-data table.",
        ]
    )
    return "\n".join(lines)


def build_packet_markdown(packet_rows: list[dict[str, str]]) -> str:
    lines = [
        "# RMTGuard Nature Methods 48-Hour Execution Packet",
        "",
        "Generated by `python scripts/build_nature_methods_48h_execution_packet.py`.",
        "",
        "## Bottom Line",
        "",
        "- Acceptance guarantee: `impossible`.",
        "- Current strict 20-50 JIF status remains `not ready`.",
        "- This packet completes the immediate planning artifacts for NM-G01, NM-G02, NM-G03, and NM-G07.",
        "- NM-G04 still requires an author decision on PDAC/TME.",
        "",
        "## Step Table",
        "",
    ]
    lines.extend(
        _markdown_table(
            packet_rows,
            [
                "step_id",
                "gate_id",
                "status",
                "owner",
                "output_artifact",
                "pass_criterion",
                "stop_condition",
            ],
        )
    )
    lines.extend(
        [
            "",
            "## Manual Author Decision Still Blocking",
            "",
            "```text",
            "PDAC/TME route: deepen as main figure",
            "```",
            "",
            "or",
            "",
            "```text",
            "PDAC/TME route: demote to supplement",
            "```",
        ]
    )
    return "\n".join(lines)


def build_ablation_markdown(rows: list[dict[str, str]]) -> str:
    lines = [
        "# P0 Component Ablation Run Sheet",
        "",
        "Generated by `python scripts/build_nature_methods_48h_execution_packet.py`.",
        "",
        "This is a manuscript-grade run plan, not proof that the final ablations have been executed.",
        "",
    ]
    lines.extend(
        _markdown_table(
            rows,
            [
                "run_id",
                "component",
                "comparison",
                "repeat_count_planned",
                "primary_metrics",
                "pass_interpretation",
                "stop_condition",
            ],
        )
    )
    return "\n".join(lines)


def build_null_power_markdown(rows: list[dict[str, str]]) -> str:
    lines = [
        "# Manuscript-Grade Null And Rare-State Power Grid Design",
        "",
        "Generated by `python scripts/build_nature_methods_48h_execution_packet.py`.",
        "",
        "The final manuscript should report power curves and false-signal control across this grid rather than a single favorable setting.",
        "",
    ]
    lines.extend(
        _markdown_table(
            rows,
            [
                "grid_id",
                "scenario",
                "prevalence",
                "effect_size",
                "dropout_rate",
                "batch_structure",
                "n_repeats_planned",
                "pass_criterion",
                "stop_condition",
            ],
        )
    )
    return "\n".join(lines)


def build_annotation_markdown(rows: list[dict[str, str]]) -> str:
    lines = [
        "# Added-Dataset Annotation Boundary",
        "",
        "Generated by `python scripts/build_nature_methods_48h_execution_packet.py`.",
        "",
        "This table prevents label-free datasets from being accidentally promoted into annotation-recovery or biological-discovery evidence.",
        "",
    ]
    lines.extend(
        _markdown_table(
            rows,
            [
                "dataset_id",
                "evidence_role",
                "label_status",
                "allowed_metric",
                "forbidden_metric_or_claim",
            ],
        )
    )
    return "\n".join(lines)


def main() -> int:
    packet_rows = _rows(PACKET_STEPS)
    claim_rows = _rows(CLAIM_ROWS)
    ablation_rows = _rows(ABLATION_ROWS)
    null_power_rows = _rows(NULL_POWER_ROWS)
    annotation_rows = _rows(ANNOTATION_ROWS)

    _write_tsv(PACKET_TSV, packet_rows)
    _write_text(PACKET_MD, build_packet_markdown(packet_rows))
    _write_tsv(CLAIM_AUDIT_TSV, claim_rows)
    _write_text(CLAIM_MD, build_claim_markdown(claim_rows))
    _write_tsv(ABLATION_TSV, ablation_rows)
    _write_text(ABLATION_MD, build_ablation_markdown(ablation_rows))
    _write_tsv(NULL_POWER_TSV, null_power_rows)
    _write_text(NULL_POWER_MD, build_null_power_markdown(null_power_rows))
    _write_tsv(ANNOTATION_TSV, annotation_rows)
    _write_text(ANNOTATION_MD, build_annotation_markdown(annotation_rows))

    outputs = [
        PACKET_TSV,
        PACKET_MD,
        CLAIM_MD,
        CLAIM_AUDIT_TSV,
        ABLATION_TSV,
        ABLATION_MD,
        NULL_POWER_TSV,
        NULL_POWER_MD,
        ANNOTATION_TSV,
        ANNOTATION_MD,
    ]
    for output in outputs:
        print(output)
    print("manual_author_decisions_open\t1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
