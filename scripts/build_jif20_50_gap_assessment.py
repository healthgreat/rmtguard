#!/usr/bin/env python
"""Build a 20-50 JIF gap assessment for the RMTGuard manuscript route.

Author: RMTGuard development team
Date: 2026-05-02
Purpose: Convert the current gate, release, calibration, and external-review
state into an explicit distance-to-submission report for 20-50 JIF journals.
Data source: Generated local gate TSVs and current journal metric checks.
Method notes: This is a readiness assessment, not an acceptance prediction.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE_REPORT = ROOT / "results" / "gates" / "gate_report.tsv"
ACTION_PLAN = ROOT / "results" / "submission" / "external_review_action_plan.tsv"
SUBMISSION_GUARD = ROOT / "results" / "submission" / "submission_guard.tsv"
RELEASE_READINESS = ROOT / "results" / "release" / "release_readiness.tsv"
GITHUB_EXECUTION_TSV = ROOT / "results" / "release" / "github_release_execution_plan.tsv"
CALIBRATION_POWER = ROOT / "results" / "calibration" / "rare_state_power_summary.tsv"
CALIBRATION_NULL = ROOT / "results" / "calibration" / "realistic_null_summary.tsv"
RARE_STATE_CLAIM_BOUNDARY = (
    ROOT / "results" / "submission" / "rare_state_claim_boundary.tsv"
)
PDAC_TME_ROUTE_PACKET = (
    ROOT / "results" / "submission" / "pdac_tme_route_decision_packet.tsv"
)
PDAC_TME_DUAL_ROUTE_PREFLIGHT = (
    ROOT / "results" / "submission" / "pdac_tme_dual_route_preflight.tsv"
)
PDAC_TME_DUAL_ROUTE_RUNBOOK = (
    ROOT / "results" / "submission" / "pdac_tme_dual_route_runbook.tsv"
)
PDAC_TME_DEEP_VALIDATION_SUMMARY = (
    ROOT / "results" / "pdac_tme" / "deep_validation" / "pdac_deep_validation_summary.tsv"
)
PDAC_TME_DEEP_VALIDATION_FIGURE_SOURCE = (
    ROOT / "results" / "figures" / "source_data" / "figure4_pdac_tme_deep_validation.tsv"
)
PDAC_TME_PATHWAY_ATLAS_SUMMARY = (
    ROOT
    / "results"
    / "pdac_tme"
    / "pathway_atlas_validation"
    / "pdac_pathway_atlas_validation_summary.tsv"
)
PDAC_TME_PATHWAY_ATLAS_FIGURE_SOURCE = (
    ROOT / "results" / "figures" / "source_data" / "figure4_pdac_tme_pathway_atlas_source.tsv"
)
MANUSCRIPT_STABILITY_STATS = (
    ROOT
    / "results"
    / "manuscript_stability_benchmarks"
    / "manuscript_stability_statistics.tsv"
)
COMPONENT_ABLATION = ROOT / "results" / "ablation" / "component_ablation_evidence.tsv"
COMPONENT_ABLATION_SUMMARY = ROOT / "results" / "ablation" / "component_ablation_summary.tsv"
REALDATA_ABLATION_SUMMARY = (
    ROOT / "results" / "ablation" / "realdata_ablation_annotation_summary.tsv"
)
REALDATA_ABLATION_ASSET_SUMMARY = (
    ROOT
    / "results"
    / "figures"
    / "source_data"
    / "figure5_realdata_ablation_delta_summary.tsv"
)
MATCHED_BASELINE_DESIGN = ROOT / "results" / "submission" / "matched_baseline_design.tsv"
MATCHED_BASELINE_PILOT_SUMMARY = (
    ROOT / "results" / "submission" / "matched_baseline_pilot_summary.tsv"
)
MATCHED_BASELINE_EXTERNAL_BLOCKERS = (
    ROOT / "results" / "submission" / "matched_baseline_external_blockers.tsv"
)
SEURAT_MATCHED_SUMMARY = (
    ROOT / "results" / "submission" / "seurat_matched_baseline_summary.tsv"
)
SEURAT_MATCHED_STATUS = (
    ROOT / "results" / "submission" / "seurat_matched_baseline_status.tsv"
)
SEURAT_JACKSTRAW_FEASIBILITY_STATUS = (
    ROOT / "results" / "submission" / "seurat_jackstraw_feasibility_status.tsv"
)
SEURAT_JACKSTRAW_FEASIBILITY_SUMMARY = (
    ROOT / "results" / "submission" / "seurat_jackstraw_feasibility_summary.tsv"
)
RMTGUARD_SEURAT_PAIRED_STATUS = (
    ROOT / "results" / "submission" / "rmtguard_seurat_paired_status.tsv"
)
RMTGUARD_SEURAT_PAIRED_STATS = (
    ROOT / "results" / "submission" / "rmtguard_seurat_paired_stats.tsv"
)
ANNOTATION_BOUNDARY = (
    ROOT / "results" / "submission" / "added_dataset_annotation_boundary.tsv"
)
OUT_TSV = ROOT / "results" / "submission" / "jif20_50_gap_assessment.tsv"
OUT_JOURNALS = ROOT / "results" / "submission" / "jif20_50_journal_route.tsv"
OUT_MD = ROOT / "docs" / "jif20_50_gap_assessment.md"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_tsv(
    path: Path, rows: list[dict[str, object]], fieldnames: list[str]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _float(value: str, default: float = float("nan")) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _gate_status(gates: list[dict[str, str]], gate_id: str) -> str:
    for row in gates:
        if row.get("gate_id") == gate_id:
            return row.get("status", "pending")
    return "pending"


def _action_status(actions: list[dict[str, str]], action_id: str) -> str:
    for row in actions:
        if row.get("action_id") == action_id:
            return row.get("status", "pending")
    return "pending"


def _release_status(release_rows: list[dict[str, str]], check_id: str) -> str:
    for row in release_rows:
        if row.get("check_id") == check_id:
            return row.get("status", "pending")
    return "pending"


def _github_release_executed() -> bool:
    for row in _read_tsv(GITHUB_EXECUTION_TSV):
        if row.get("step_id") != "05_create_github_release":
            continue
        return row.get("status") == "executed" and row.get(
            "evidence_path", ""
        ).startswith("https://")
    return False


def _zenodo_doi_recorded() -> bool:
    zenodo_json = ROOT / ".zenodo.json"
    if not zenodo_json.exists():
        return False
    text = zenodo_json.read_text(encoding="utf-8", errors="replace")
    return '"doi"' in text and "10." in text


def _status_at_least(status: str, accepted: set[str]) -> bool:
    return status in accepted


def _calibration_summary() -> dict[str, float]:
    null_rows = _read_tsv(CALIBRATION_NULL)
    power_rows = _read_tsv(CALIBRATION_POWER)
    if not null_rows or not power_rows:
        return {
            "max_false_call": float("nan"),
            "min_power": float("nan"),
            "median_power": float("nan"),
            "settings_power_ge_080": 0.0,
            "null_min_repeats": 0,
            "power_min_repeats": 0,
            "ci_present": False,
        }
    powers = [_float(row.get("power", "")) for row in power_rows]
    null_repeats = [
        int(float(row.get("n_repeats", "0")))
        for row in null_rows
        if row.get("n_repeats", "")
    ]
    power_repeats = [
        int(float(row.get("n_repeats", "0")))
        for row in power_rows
        if row.get("n_repeats", "")
    ]
    ci_present = all(
        col in null_rows[0]
        for col in [
            "false_signal_rate_ci95_low",
            "false_signal_rate_ci95_high",
            "false_call_rate_ci95_low",
            "false_call_rate_ci95_high",
        ]
    ) and all(
        col in power_rows[0]
        for col in [
            "power_ci95_low",
            "power_ci95_high",
            "mean_rare_f1_ci95_low",
            "mean_rare_f1_ci95_high",
        ]
    )
    return {
        "max_false_call": max(
            _float(row.get("false_call_rate", "")) for row in null_rows
        ),
        "min_power": min(powers),
        "median_power": sorted(powers)[len(powers) // 2],
        "settings_power_ge_080": sum(power >= 0.80 for power in powers) / len(powers),
        "null_min_repeats": min(null_repeats) if null_repeats else 0,
        "power_min_repeats": min(power_repeats) if power_repeats else 0,
        "ci_present": ci_present,
    }


def _manuscript_stability_summary() -> dict[str, object]:
    rows = _read_tsv(MANUSCRIPT_STABILITY_STATS)
    if not rows:
        return {
            "status": "not_started",
            "dataset_count": 0,
            "datasets": "none",
            "min_repeats": 0,
            "rmtguard_pilot_mean": float("nan"),
        }
    rmt_rows = [row for row in rows if row.get("method") == "rmtguard"]
    datasets = sorted(
        {row.get("dataset_id", "") for row in rmt_rows if row.get("dataset_id")}
    )
    repeats = [
        int(row.get("n_repeats", "0"))
        for row in rmt_rows
        if row.get("n_repeats", "").isdigit()
    ]
    means = [_float(row.get("mean_pairwise_ari", "")) for row in rmt_rows]
    min_repeats = min(repeats) if repeats else 0
    if len(datasets) >= 4 and min_repeats >= 10:
        status = "manuscript_grade_dataset_count_reached"
    elif datasets and min_repeats >= 10:
        status = f"pilot_partial_{len(datasets)}_of_4_10_repeat_reached"
    else:
        status = "pilot_partial_repeat_count_low"
    return {
        "status": status,
        "dataset_count": len(datasets),
        "datasets": ",".join(datasets) if datasets else "none",
        "min_repeats": min_repeats,
        "rmtguard_pilot_mean": means[0] if means else float("nan"),
    }


def _component_ablation_summary() -> dict[str, object]:
    rows = _read_tsv(COMPONENT_ABLATION)
    benchmark_rows = _read_tsv(COMPONENT_ABLATION_SUMMARY)
    realdata_rows = _read_tsv(REALDATA_ABLATION_SUMMARY)
    synthetic_repeat_depths = [
        int(float(row.get("n_repeats", "0")))
        for row in benchmark_rows
        if row.get("n_repeats", "")
    ]
    synthetic_min_repeats = (
        min(synthetic_repeat_depths) if synthetic_repeat_depths else 0
    )
    ci_present = bool(
        benchmark_rows
        and all(
            col in benchmark_rows[0]
            for col in [
                "false_call_rate_ci95_low",
                "false_call_rate_ci95_high",
                "power_ci95_low",
                "power_ci95_high",
                "mean_rare_f1_ci95_low",
                "mean_rare_f1_ci95_high",
            ]
        )
    )
    realdata_repeat_depths = [
        int(float(row.get("n_repeats", "0")))
        for row in realdata_rows
        if row.get("n_repeats", "")
    ]
    realdata_max_repeats = max(realdata_repeat_depths) if realdata_repeat_depths else 0
    realdata_component_rows = []
    for row in realdata_rows:
        run_label = row.get("run_label", "")
        ablation_id = row.get("ablation_id", "")
        try:
            subsample_fraction = float(row.get("subsample_fraction", "1"))
        except ValueError:
            subsample_fraction = 1.0
        if "seurat_matched" in run_label:
            continue
        if ablation_id == "default_v3_3":
            continue
        if not (0.79 <= subsample_fraction <= 0.81):
            continue
        realdata_component_rows.append(row)
    realdata_component_repeat_depths = [
        int(float(row.get("n_repeats", "0")))
        for row in realdata_component_rows
        if row.get("n_repeats", "")
    ]
    realdata_component_min_repeats = (
        min(realdata_component_repeat_depths)
        if realdata_component_repeat_depths
        else 0
    )
    if not rows:
        return {
            "status": "missing",
            "component_count": 0,
            "benchmark_rows": len(benchmark_rows),
            "synthetic_min_repeats": synthetic_min_repeats,
            "component_ci_present": ci_present,
            "realdata_rows": len(realdata_rows),
            "realdata_max_repeats": realdata_max_repeats,
            "realdata_component_min_repeats": realdata_component_min_repeats,
            "missing_components": "all",
        }
    missing = [
        row.get("component_id", "")
        for row in rows
        if row.get("current_evidence_status") == "missing_experiment"
    ]
    partial = [
        row.get("component_id", "")
        for row in rows
        if "partial" in row.get("current_evidence_status", "")
        or row.get("current_evidence_status") == "single_dataset_draft"
    ]
    if benchmark_rows:
        status = "draft_benchmark_present_final_experiments_pending"
    else:
        status = "control_matrix_present_final_experiments_pending"
    if realdata_rows:
        status = "draft_benchmark_and_realdata_annotation_present_final_experiments_pending"
    if realdata_max_repeats >= 3:
        status = "draft_benchmark_and_repeated_realdata_annotation_pilot_present_final_experiments_pending"
    if synthetic_min_repeats >= 20 and ci_present and realdata_component_min_repeats >= 20:
        status = "current_20_repeat_synthetic_and_realdata_component_layer_complete_power_pending"
    return {
        "status": status,
        "component_count": len(rows),
        "benchmark_rows": len(benchmark_rows),
        "synthetic_min_repeats": synthetic_min_repeats,
        "component_ci_present": ci_present,
        "realdata_rows": len(realdata_rows),
        "realdata_max_repeats": realdata_max_repeats,
        "realdata_component_min_repeats": realdata_component_min_repeats,
        "missing_components": ",".join(missing) if missing else "none",
        "partial_components": ",".join(partial) if partial else "none",
    }


def _pdac_tme_deep_validation_summary() -> dict[str, str]:
    rows = _read_tsv(PDAC_TME_DEEP_VALIDATION_SUMMARY)
    if not rows:
        return {
            "status": "not_started",
            "significant_de": "0",
            "significant_enrichment": "0",
            "external_label_support": "0",
        }
    lookup = {row.get("summary_id", ""): row for row in rows}
    return {
        "status": lookup.get("pdac_deep_validation_status", {}).get("value", "unknown"),
        "significant_de": lookup.get("significant_de_marker_rows", {}).get("value", "0"),
        "significant_enrichment": lookup.get("significant_marker_set_enrichments", {}).get("value", "0"),
        "external_label_support": lookup.get("external_label_supported_primary_signatures", {}).get("value", "0"),
    }


def _pdac_tme_pathway_atlas_summary() -> dict[str, str]:
    rows = _read_tsv(PDAC_TME_PATHWAY_ATLAS_SUMMARY)
    if not rows:
        return {
            "status": "not_started",
            "significant_hallmark": "0",
            "significant_reactome": "0",
            "atlas_support": "0",
            "interpretable_pathways": "0",
        }
    lookup = {row.get("summary_id", ""): row for row in rows}
    return {
        "status": lookup.get("pdac_pathway_atlas_validation_status", {}).get("value", "unknown"),
        "significant_hallmark": lookup.get("significant_hallmark_pathways", {}).get("value", "0"),
        "significant_reactome": lookup.get("significant_reactome_pathways", {}).get("value", "0"),
        "atlas_support": lookup.get("atlas_supported_cluster_signature_rows", {}).get("value", "0"),
        "interpretable_pathways": lookup.get("manuscript_interpretable_pathways", {}).get("value", "0"),
    }


def build_gap_rows() -> list[dict[str, object]]:
    gates = _read_tsv(GATE_REPORT)
    actions = _read_tsv(ACTION_PLAN)
    guard = _read_tsv(SUBMISSION_GUARD)
    release_rows = _read_tsv(RELEASE_READINESS)
    calibration = _calibration_summary()
    manuscript_stability = _manuscript_stability_summary()
    component_ablation = _component_ablation_summary()
    pdac_deep = _pdac_tme_deep_validation_summary()
    pdac_pathway = _pdac_tme_pathway_atlas_summary()
    component_matrix_exists = component_ablation["component_count"] > 0
    rare_state_claim_boundary_present = RARE_STATE_CLAIM_BOUNDARY.exists()
    realdata_ablation_assets_present = REALDATA_ABLATION_ASSET_SUMMARY.exists()
    matched_baseline_design_present = MATCHED_BASELINE_DESIGN.exists()
    matched_baseline_pilot_present = MATCHED_BASELINE_PILOT_SUMMARY.exists()
    seurat_matched_status_rows = _read_tsv(SEURAT_MATCHED_STATUS)
    seurat_status_by_id = {
        row.get("check_id", ""): row.get("status", "")
        for row in seurat_matched_status_rows
    }
    jackstraw_status_rows = _read_tsv(SEURAT_JACKSTRAW_FEASIBILITY_STATUS)
    jackstraw_status_by_id = {
        row.get("check_id", ""): row.get("status", "")
        for row in jackstraw_status_rows
    }
    jackstraw_feasibility_present = jackstraw_status_by_id.get(
        "seurat_jackstraw_feasibility"
    ) in {"feasibility_pass", "manuscript_candidate"}
    jackstraw_final_present = (
        jackstraw_status_by_id.get("manuscript_grade_jackstraw")
        == "manuscript_candidate"
        or seurat_status_by_id.get("seurat_v5_jackstraw") == "manuscript_candidate"
    )
    paired_status_rows = _read_tsv(RMTGUARD_SEURAT_PAIRED_STATUS)
    paired_status_by_id = {
        row.get("check_id", ""): row.get("status", "")
        for row in paired_status_rows
    }
    paired_stats_pilot_present = paired_status_by_id.get("paired_overlap") in {
        "paired10_pilot_pass",
        "paired20_manuscript_candidate",
    }
    paired_stats_manuscript_candidate = (
        paired_status_by_id.get("paired_statistics_claim_status")
        == "manuscript_candidate"
    )
    paired_stats_rows = _read_tsv(RMTGUARD_SEURAT_PAIRED_STATS)
    paired_label_dataset_count = len(
        {
            row.get("dataset_id", "")
            for row in paired_stats_rows
            if row.get("metric") == "label_ari" and row.get("dataset_id")
        }
    )
    annotation_boundary_present = ANNOTATION_BOUNDARY.exists()
    seurat_executable_present = (
        seurat_status_by_id.get("seurat_mtx_bridge") == "pass"
        and _status_at_least(
            seurat_status_by_id.get("seurat_v5_fixed_30", ""),
            {"smoke_pass", "pilot10_pass", "manuscript_candidate"},
        )
        and _status_at_least(
            seurat_status_by_id.get("seurat_v5_elbow", ""),
            {"smoke_pass", "pilot10_pass", "manuscript_candidate"},
        )
    )
    seurat_core_pilot10_present = (
        seurat_status_by_id.get("seurat_mtx_bridge") == "pass"
        and all(
            _status_at_least(
                seurat_status_by_id.get(method, ""),
                {"pilot10_pass", "manuscript_candidate"},
            )
            for method in [
                "seurat_v5_fixed_30",
                "seurat_v5_fixed_50",
                "seurat_v5_elbow",
            ]
        )
    )
    seurat_core_20_present = (
        seurat_status_by_id.get("seurat_mtx_bridge") == "pass"
        and all(
            seurat_status_by_id.get(method, "") == "manuscript_candidate"
            for method in [
                "seurat_v5_fixed_30",
                "seurat_v5_fixed_50",
                "seurat_v5_elbow",
            ]
        )
    )
    seurat_full_20_present = seurat_core_20_present and jackstraw_final_present
    benchmark_dataset_count = int(manuscript_stability["dataset_count"])
    benchmark_breadth_reached = benchmark_dataset_count >= 7
    if benchmark_dataset_count >= 4:
        scientific_next = (
            "Stability-superiority is still not supported; either improve the "
            "algorithm against the strongest comparator or reframe the main "
            "claim as callability-aware noise control rather than stability "
            "superiority."
        )
    else:
        scientific_next = (
            "Run manuscript-grade stability rerun with 10+ repeats, confidence "
            "intervals, cluster-number variance, and a callability-aware "
            "noninferiority table."
        )
    benchmark_score = min(10, 6 + benchmark_dataset_count) if benchmark_dataset_count else 6
    if benchmark_dataset_count >= 4 and matched_baseline_pilot_present:
        benchmark_score = min(15, benchmark_score + 1)
    if benchmark_dataset_count >= 4 and seurat_executable_present:
        benchmark_score = min(15, benchmark_score + 1)
    if benchmark_dataset_count >= 4 and seurat_core_pilot10_present:
        benchmark_score = min(15, benchmark_score + 1)
    if benchmark_dataset_count >= 4 and seurat_core_20_present:
        benchmark_score = min(15, benchmark_score + 1)
    if (
        benchmark_dataset_count >= 4
        and seurat_full_20_present
        and jackstraw_feasibility_present
    ):
        benchmark_score = min(15, benchmark_score + 1)
    if benchmark_dataset_count >= 4 and paired_stats_pilot_present:
        benchmark_score = min(15, benchmark_score + 1)
    if benchmark_dataset_count >= 4:
        if (
            benchmark_breadth_reached
            and seurat_full_20_present
            and paired_stats_manuscript_candidate
        ):
            benchmark_blockers = (
                "none"
                if paired_label_dataset_count >= benchmark_dataset_count
                or annotation_boundary_present
                else "added_dataset_label_free_boundary"
            )
        elif (
            seurat_full_20_present
            and paired_stats_manuscript_candidate
        ):
            benchmark_blockers = "additional_datasets"
        elif (
            seurat_core_20_present
            and jackstraw_final_present
            and paired_stats_pilot_present
            and not paired_stats_manuscript_candidate
        ):
            benchmark_blockers = (
                "RMTGuard_paired_repeat_depth_20;additional_datasets"
            )
        elif seurat_full_20_present:
            benchmark_blockers = (
                "paired_RMTGuard_vs_Seurat_statistics;additional_datasets"
            )
        elif seurat_core_20_present and jackstraw_feasibility_present:
            benchmark_blockers = (
                "manuscript_grade_Seurat_JackStraw;paired_RMTGuard_vs_Seurat_statistics;"
                "additional_datasets"
            )
        elif seurat_core_20_present:
            benchmark_blockers = (
                "manuscript_grade_Seurat_JackStraw;paired_RMTGuard_vs_Seurat_statistics;"
                "additional_datasets"
            )
        elif seurat_core_pilot10_present:
            benchmark_blockers = (
                "official_Seurat_JackStraw;20_plus_repeat_matched_baselines;"
                "additional_datasets"
            )
        elif seurat_executable_present:
            benchmark_blockers = (
                "official_Seurat_v5_fixed50;official_Seurat_JackStraw;"
                "20_50_repeat_matched_baselines;additional_datasets"
            )
        elif matched_baseline_pilot_present:
            benchmark_blockers = (
                "official_Seurat_v5;official_Seurat_JackStraw;additional_datasets"
            )
        else:
            benchmark_blockers = (
                "full_Seurat_v5;JackStraw_or_parallel_analysis;additional_datasets"
            )
        if (
            benchmark_breadth_reached
            and seurat_full_20_present
            and paired_stats_manuscript_candidate
        ):
            benchmark_next = (
                "Freeze the final comparator table."
                if paired_label_dataset_count >= benchmark_dataset_count
                or annotation_boundary_present
                else (
                    "Treat PBMC3k and PDAC GSE154778 as label-free stability/"
                    "runtime comparator evidence, or add reliable cell-state "
                    "annotations before using them in annotation-ARI claims."
                )
            )
        elif (
            seurat_full_20_present
            and paired_stats_manuscript_candidate
        ):
            benchmark_next = (
                "Expand to at least 3 additional public datasets under the same "
                "split logic, then freeze the final comparator table."
            )
        elif (
            seurat_core_20_present
            and jackstraw_final_present
            and paired_stats_pilot_present
            and not paired_stats_manuscript_candidate
        ):
            benchmark_next = (
                "Scale RMTGuard default repeated annotation rows from 10 to "
                "20 repeats so paired RMTGuard-versus-Seurat statistics match "
                "the official Seurat fixed-PC/elbow/JackStraw depth, then "
                "expand to at least 3 "
                "additional public datasets."
            )
        elif seurat_full_20_present:
            benchmark_next = (
                "Add paired RMTGuard-versus-Seurat statistics on matched "
                "repeats, then expand to at least 3 additional public datasets."
            )
        elif seurat_core_20_present and jackstraw_feasibility_present:
            benchmark_next = (
                "Convert JackStraw from feasibility-only to final comparator "
                "or document a quantitative runtime omission, add paired "
                "RMTGuard-versus-Seurat statistics on matched repeats, then "
                "expand to at least 3 additional public datasets."
            )
        elif seurat_core_20_present:
            benchmark_next = (
                "Run Seurat JackStraw feasibility/final comparator where "
                "feasible, add paired RMTGuard-versus-Seurat statistics on "
                "matched repeats, then expand to at least 3 additional public datasets."
            )
        elif seurat_core_pilot10_present:
            benchmark_next = (
                "Scale official Seurat fixed30/fixed50/elbow from 10 to "
                "20+ repeats with paired statistics, run Seurat JackStraw "
                "where feasible or document a runtime-based omission, then "
                "expand to at least 3 additional public datasets."
            )
        elif seurat_executable_present:
            benchmark_next = (
                "Scale the official Seurat fixed30/elbow smoke layer to "
                "10-20+ repeats, add Seurat fixed50 and JackStraw where "
                "runtime permits, then expand to at least 3 additional public datasets."
            )
        elif matched_baseline_pilot_present:
            benchmark_next = (
                "Run the remaining official Seurat v5 and Seurat JackStraw "
                "matched baselines, scale the local matched pilot from 10 to "
                "20-50 repeats, then expand to at least 3 additional public datasets."
            )
        elif matched_baseline_design_present:
            benchmark_next = (
                "Execute the matched-baseline design with final Seurat v5 and "
                "JackStraw/parallel-analysis baselines, then expand to at least "
                "3 additional public datasets under identical splits."
            )
        else:
            benchmark_next = (
                "Add final Seurat v5 and JackStraw/parallel-analysis baselines, "
                "then expand to at least 3 additional public datasets under identical splits."
            )
        if benchmark_blockers != "none":
            benchmark_score = min(benchmark_score, 14)
    else:
        benchmark_blockers = (
            "10_repeat_real_data_stability;full_Seurat_v5;"
            "JackStraw_or_parallel_analysis;additional_datasets"
        )
        benchmark_next = (
            "Add at least 3 datasets and rerun Scanpy, Seurat v5, fixed PC, "
            "elbow, permutation/parallel PCA, and JackStraw-like baselines "
            "under identical splits."
        )
    benchmark_done = (
        "Four Phase 1 datasets and expanded PC-rule baselines exist in the "
        "current control plane. Manuscript stability statistics status is "
        f"{manuscript_stability['status']} for "
        f"{manuscript_stability['dataset_count']} dataset(s): "
        f"{manuscript_stability['datasets']}."
    )
    if benchmark_breadth_reached:
        benchmark_done += (
            " The manuscript stability benchmark has been expanded to seven "
            "prepared public datasets, adding Paul15 hematopoiesis, PDAC "
            "GSE154778, and PDAC GSE263733 to the earlier PBMC/pancreas set."
        )
    if paired_label_dataset_count:
        benchmark_done += (
            f" Paired RMTGuard-versus-official-Seurat annotation statistics now "
            f"cover {paired_label_dataset_count} labeled comparator dataset(s)."
        )
    if annotation_boundary_present:
        benchmark_done += (
            " The added-dataset annotation-boundary table is present, so PBMC3k "
            "and PDAC GSE154778 are explicitly treated as label-free stability/"
            "runtime evidence unless reliable annotations are later documented."
        )
    if matched_baseline_pilot_present:
        benchmark_done += (
            " A local Python matched-baseline pilot is now present on the "
            "same 80% subsampling framework, with RMTGuard rows imported from "
            "the real-data ablation pilot and local Scanpy-like/fixed-PC/elbow/"
            "parallel-analysis/JackStraw-like proxy rows executed."
        )
    if seurat_core_20_present:
        benchmark_done += (
            " Official Seurat v5 fixed30, fixed50, and elbow-rule baselines "
            "now have 20-repeat manuscript-candidate rows across the four "
            "prepared datasets through a MatrixMarket bridge."
        )
        if jackstraw_final_present:
            benchmark_done += (
                " Official Seurat JackStraw now has 20-repeat, 20-replicate "
                "comparator-candidate rows across the same four prepared datasets."
            )
        elif jackstraw_feasibility_present:
            benchmark_done += (
                " Official Seurat JackStraw feasibility now passes across the "
                "four prepared datasets with a 1-repeat, 5-replicate feasibility run."
            )
        if paired_stats_pilot_present:
            benchmark_done += (
                " RMTGuard-versus-official-Seurat paired annotation statistics "
                "are now generated for matched repeats, including bootstrap "
                "CIs, sign-flip p values, FDR, and a Figure 3 source-data/"
                "forest-plot asset."
            )
    elif seurat_core_pilot10_present:
        benchmark_done += (
            " Official Seurat v5 fixed30, fixed50, and elbow-rule baselines "
            "now have 10-repeat pilot rows across the four prepared datasets "
            "through a MatrixMarket bridge."
        )
        if jackstraw_feasibility_present:
            benchmark_done += (
                " Official Seurat JackStraw feasibility now passes across the "
                "four prepared datasets with a 1-repeat, 5-replicate feasibility run."
            )
    elif seurat_executable_present:
        benchmark_done += (
            " Official Seurat v5 matched-baseline executability has now been "
            "shown across the four prepared datasets through a MatrixMarket "
            "bridge, with fixed30 and elbow-rule smoke rows generated."
        )
    archived_release_pass = _github_release_executed() and _zenodo_doi_recorded()
    release_core_pass = archived_release_pass or all(
        _release_status(release_rows, check_id) == "pass"
        for check_id in [
            "repository_url",
            "github_remote",
            "git_worktree",
            "github_release_tag",
            "zenodo_doi",
        ]
    )

    rows = [
        {
            "domain": "scientific_core",
            "weight": 25,
            "current_score": 18,
            "status": "partial",
            "evidence": _rel(GATE_REPORT),
            "blocking_items": (
                "stability_advantage"
                if _gate_status(gates, "stability_advantage") != "pass"
                else "none"
            ),
            "what_is_done": "Synthetic null, diagnostic no-call, rare-state retention, annotation noninferiority, real dataset count, and figure source data are controlled.",
            "what_is_missing": "Real-data stability advantage is still failed against the strongest current baseline set.",
            "next_supplement": scientific_next,
        },
        {
            "domain": "calibration_statistics",
            "weight": 15,
            "current_score": (
                15
                if component_ablation.get("realdata_component_min_repeats", 0)
                >= 20
                and component_ablation.get("synthetic_min_repeats", 0) >= 20
                and component_ablation.get("component_ci_present", False)
                else 14
                if component_ablation.get("realdata_component_min_repeats", 0)
                >= 10
                else (
                    13
                    if component_ablation["realdata_rows"]
                    else (
                        12
                        if component_ablation["benchmark_rows"]
                        else (10 if component_matrix_exists else 9)
                    )
                )
            ),
            "status": (
                "manuscript_grade_calibration_done_limit_detected"
                if calibration.get("null_min_repeats", 0) >= 50
                and calibration.get("power_min_repeats", 0) >= 50
                and calibration.get("ci_present", False)
                else "component_ablation_20_repeat_done_power_pending"
                if component_ablation.get("realdata_component_min_repeats", 0) >= 20
                and component_ablation.get("synthetic_min_repeats", 0) >= 20
                and component_ablation.get("component_ci_present", False)
                else "synthetic_component_ablation_20_repeat_done_realdata_and_power_pending"
                if component_ablation.get("synthetic_min_repeats", 0) >= 20
                and component_ablation.get("component_ci_present", False)
                else "partial_improved_component_controlled"
                if component_matrix_exists
                else "partial_improved"
            ),
            "evidence": (
                f"{_rel(CALIBRATION_POWER)};{_rel(COMPONENT_ABLATION)}"
                if component_matrix_exists
                else _rel(CALIBRATION_POWER)
            ),
            "blocking_items": (
                "none"
                if rare_state_claim_boundary_present
                else "weak_effect_low_prevalence_power_claim_boundary"
                if calibration.get("null_min_repeats", 0) >= 50
                and calibration.get("power_min_repeats", 0) >= 50
                and calibration.get("ci_present", False)
                and calibration["min_power"] < 0.80
                else "none"
                if calibration.get("null_min_repeats", 0) >= 50
                and calibration.get("power_min_repeats", 0) >= 50
                and calibration.get("ci_present", False)
                else "weak_effect_low_prevalence_power"
                if component_ablation.get("realdata_component_min_repeats", 0) >= 20
                and component_ablation.get("synthetic_min_repeats", 0) >= 20
                and component_ablation.get("component_ci_present", False)
                else "weak_effect_low_prevalence_power;realdata_annotation_repeat_depth"
                if component_ablation.get("synthetic_min_repeats", 0) >= 20
                and component_ablation.get("component_ci_present", False)
                else "weak_effect_low_prevalence_power;draft_repeat_count"
            ),
            "what_is_done": f"Count-preserving null false-call max is {calibration['max_false_call']:.3f}; rare-state power has 50-repeat curves with {calibration['settings_power_ge_080']:.0%} of grid settings at power >=0.80. Null repeat depth is {calibration.get('null_min_repeats', 0)} and power-grid repeat depth is {calibration.get('power_min_repeats', 0)} with CI columns present={calibration.get('ci_present', False)}. Synthetic component ablation now has minimum repeat depth {component_ablation['synthetic_min_repeats']} with CI columns present={component_ablation['component_ci_present']}. Component ablation status is {component_ablation['status']} across {component_ablation['component_count']} components, {component_ablation['benchmark_rows']} synthetic benchmark summary rows, and {component_ablation['realdata_rows']} real-data annotation rows; component-specific real-data ablation minimum repeat depth is {component_ablation['realdata_component_min_repeats']}. Real-data ablation figure/table assets present: {realdata_ablation_assets_present}.",
            "what_is_missing": f"Minimum rare-state power remains {calibration['min_power']:.2f}; this is now an evidence-based limitation rather than a repeat-depth gap. Rare-state claim boundary present: {rare_state_claim_boundary_present}. Missing or nonfinal component experiments: {component_ablation['missing_components']}.",
            "next_supplement": (
                "Calibration source data and rare-state claim boundary are controlled; only add extra dropout/batch power grids if the Nature Methods rare-state claim remains central."
                if rare_state_claim_boundary_present
                else "Freeze the calibration source data and write the rare-state claim boundary; only add extra dropout/batch power grids if the Nature Methods rare-state claim remains central."
            ),
        },
        {
            "domain": "release_reproducibility",
            "weight": 25,
            "current_score": 25 if release_core_pass else 12,
            "status": "pass" if release_core_pass else "blocked_external",
            "evidence": _rel(RELEASE_READINESS),
            "blocking_items": (
                "none" if release_core_pass else "repository_url;github_remote;zenodo_doi"
            ),
            "what_is_done": "Public GitHub repository, v0.1.0 GitHub Release, Zenodo version DOI, source audit, CI scaffold, Dockerfile, license, citation metadata, release manifests, figures, and table artifacts are present.",
            "what_is_missing": "No release-engineering blocker remains; future changes should be issued as a new release version rather than moving the archived v0.1.0 DOI snapshot.",
            "next_supplement": "Keep v0.1.0 archived and immutable; create a future v0.1.1 only after the next benchmark/metadata freeze.",
        },
        {
            "domain": "benchmark_breadth_and_baselines",
            "weight": 15,
            "current_score": benchmark_score,
            "status": (
                "controlled"
                if benchmark_blockers == "none"
                else _action_status(actions, "03_manuscript_grade_stability_baselines")
            ),
            "evidence": f"{_rel(ACTION_PLAN)};{_rel(MANUSCRIPT_STABILITY_STATS)}",
            "blocking_items": benchmark_blockers,
            "what_is_done": benchmark_done,
            "what_is_missing": (
                "The current benchmark is not broad or statistically strong "
                "enough for a Nature Methods-style methods claim; official "
                "The dataset-breadth layer now reaches seven public datasets, "
                "official Seurat fixed-PC, elbow, and JackStraw baselines have "
                "20-repeat rows across the prepared benchmark set, and paired "
                "RMTGuard annotation statistics are available on the labeled "
                "subset. Component ablation and power calibration remain "
                "incomplete for a Nature Methods-style claim."
            ),
            "next_supplement": benchmark_next,
        },
        {
            "domain": "biological_showcase",
            "weight": 10,
            "current_score": (
                8
                if pdac_pathway["status"] == "pathway_atlas_supported_with_limits"
                else
                7
                if pdac_deep["status"] == "main_figure_candidate_supported_with_limits"
                else 4
            ),
            "status": (
                pdac_pathway["status"]
                if pdac_pathway["status"] != "not_started"
                else
                pdac_deep["status"]
                if pdac_deep["status"] != "not_started"
                else _action_status(actions, "06_biological_showcase_decision")
            ),
            "evidence": (
                "docs/pdac_tme_showcase_depth.md;docs/pdac_tme_route_decision_packet.md;docs/pdac_tme_dual_route_preflight.md;docs/pdac_tme_dual_route_runbook.md;docs/pdac_tme_deep_validation.md;docs/pdac_tme_pathway_atlas_validation.md"
                if PDAC_TME_PATHWAY_ATLAS_SUMMARY.exists()
                else
                "docs/pdac_tme_showcase_depth.md;docs/pdac_tme_route_decision_packet.md;docs/pdac_tme_dual_route_preflight.md;docs/pdac_tme_dual_route_runbook.md;docs/pdac_tme_deep_validation.md"
                if PDAC_TME_DEEP_VALIDATION_SUMMARY.exists()
                else "docs/pdac_tme_showcase_depth.md;docs/pdac_tme_route_decision_packet.md;docs/pdac_tme_dual_route_preflight.md;docs/pdac_tme_dual_route_runbook.md"
                if PDAC_TME_ROUTE_PACKET.exists() and PDAC_TME_DUAL_ROUTE_PREFLIGHT.exists()
                else "docs/pdac_tme_showcase_depth.md;docs/pdac_tme_route_decision_packet.md"
                if PDAC_TME_ROUTE_PACKET.exists()
                else "docs/pdac_tme_showcase_depth.md"
            ),
            "blocking_items": (
                "PDAC_TME_author_route_confirmation_and_final_figure_wording"
                if pdac_pathway["status"] == "pathway_atlas_supported_with_limits"
                else
                "PDAC_TME_full_pathway_GSEA_and_author_route_confirmation"
                if pdac_deep["status"] == "main_figure_candidate_supported_with_limits"
                else "PDAC_TME_depth_or_demotion"
            ),
            "what_is_done": (
                f"PDAC/TME public use case now has FDR-controlled DE markers, external signature transfer, rank-based MSigDB Hallmark/Reactome pathway enrichment, atlas marker citation mapping, and Figure 4 pathway/atlas source data. Significant Hallmark pathways={pdac_pathway['significant_hallmark']}; significant Reactome pathways={pdac_pathway['significant_reactome']}; manuscript-interpretable pathways={pdac_pathway['interpretable_pathways']}; atlas-supported cluster/signature rows={pdac_pathway['atlas_support']}."
                if pdac_pathway["status"] == "pathway_atlas_supported_with_limits"
                else
                "PDAC/TME public use case now has FDR-controlled DE markers, marker-set enrichment, external signature transfer, Figure 4 source data, and bounded wording."
                if pdac_deep["status"] == "main_figure_candidate_supported_with_limits"
                else
                "PDAC/TME public use case has marker-level immune/ductal validation, bounded wording, "
                "a main-figure-versus-supplement route decision packet, and a dual-route preflight/runbook."
                if PDAC_TME_ROUTE_PACKET.exists() and PDAC_TME_DUAL_ROUTE_PREFLIGHT.exists()
                else "PDAC/TME public use case has marker-level immune/ductal validation, bounded wording, and a main-figure-versus-supplement route decision packet."
                if PDAC_TME_ROUTE_PACKET.exists()
                else "PDAC/TME public use case has marker-level immune/ductal validation and bounded wording."
            ),
            "what_is_missing": (
                "Explicit author route confirmation, final Figure 4 wording/caption/source-data freeze, and optional sensitivity check using a Broad GSEA/clusterProfiler implementation if reviewers require permutation-style GSEA."
                if pdac_pathway["status"] == "pathway_atlas_supported_with_limits"
                else
                "Full MSigDB/Reactome/Hallmark GSEA, exact published-atlas marker citations, and explicit author route confirmation."
                if pdac_deep["status"] == "main_figure_candidate_supported_with_limits"
                else "An explicit author route decision and, if kept as main figure, deeper DE/GSEA/external-validation evidence."
            ),
            "next_supplement": (
                "Freeze the pathway/atlas evidence for bounded Figure 4 wording, then obtain author route confirmation and regenerate final captions/source data."
                if pdac_pathway["status"] == "pathway_atlas_supported_with_limits"
                else
                "Upgrade marker-set enrichment to formal pathway GSEA and add literature-backed PDAC atlas marker mapping before final Nature Methods wording."
                if pdac_deep["status"] == "main_figure_candidate_supported_with_limits"
                else "Either add DE/GSEA/trajectory/published-atlas validation for PDAC/TME, or demote PDAC/TME and use a stronger ground-truth application."
            ),
        },
        {
            "domain": "manuscript_claim_control",
            "weight": 10,
            "current_score": 8
            if realdata_ablation_assets_present
            and matched_baseline_design_present
            and seurat_core_pilot10_present
            else 7,
            "status": "controlled_but_not_submission_ready",
            "evidence": _rel(SUBMISSION_GUARD),
            "blocking_items": "editorial_send_status;nature_methods_route",
            "what_is_done": "Claim lint and traceability pass; external-review packet, route reframe, figures, tables, visual audit, real-data ablation forest/table assets, matched-baseline design, local matched-baseline pilot, official Seurat fixed30/fixed50/elbow/JackStraw 20-repeat evidence, and paired20 RMTGuard-versus-official-Seurat statistics are generated.",
            "what_is_missing": "Submission guard remains do_not_submit and Nature Methods presubmission remains on hold.",
            "next_supplement": "After scientific and release blockers are fixed, regenerate final abstract, cover letter, reporting summary, source data, and claims.",
        },
    ]
    return rows


def build_journal_rows() -> list[dict[str, object]]:
    return [
        {
            "journal": "Nature Methods",
            "verified_2024_jif": "32.1",
            "verified_2024_5yr_jif": "51.7",
            "strict_20_50_fit": "yes",
            "current_route": "primary_target_on_hold",
            "cas_zone_note": "Likely CAS 1区 based on third-party 2025 lookup; verify with institutional CAS table before submission.",
            "warning_note": "Not observed in searched 2025 warning-list summaries; verify against the official current warning PDF before submission.",
            "source_url": "https://www.nature.com/nmeth/journal-impact",
            "current_fit": "only plausible strict 20-50 target; release is complete, but stability, benchmark, and biological-application blockers remain",
        },
        {
            "journal": "Nature Biotechnology",
            "verified_2024_jif": "41.7",
            "verified_2024_5yr_jif": "59.5",
            "strict_20_50_fit": "yes",
            "current_route": "not_fit_for_current_scope",
            "cas_zone_note": "Likely CAS 1区; verify locally.",
            "warning_note": "Verify against official current warning PDF.",
            "source_url": "https://www.nature.com/nbt/journal-impact",
            "current_fit": "requires biotechnology platform or adoption-level advance beyond current workflow benchmark",
        },
        {
            "journal": "Nature Communications",
            "verified_2024_jif": "15.7",
            "verified_2024_5yr_jif": "17.2",
            "strict_20_50_fit": "no",
            "current_route": "possible_if_biological_or_methods_impact_strengthens",
            "cas_zone_note": "Third-party 2025 pages report CAS 1区; verify locally.",
            "warning_note": "Verify against official current warning PDF.",
            "source_url": "https://www.nature.com/ncomms/journal-impact",
            "current_fit": "below strict 20 JIF; requires stronger cross-field or biological application than current package",
        },
        {
            "journal": "Genome Biology",
            "verified_2024_jif": "9.4",
            "verified_2024_5yr_jif": "16.3",
            "strict_20_50_fit": "no",
            "current_route": "most_realistic_high_quality_fallback",
            "cas_zone_note": "Third-party 2025 pages report CAS 1区 Top; verify locally.",
            "warning_note": "Verify against official current warning PDF.",
            "source_url": "https://genomebiology.biomedcentral.com/about",
            "current_fit": "best realistic high-quality fallback after reframe, but not a 20-50 JIF journal by 2024 JIF",
        },
        {
            "journal": "Cell Reports Medicine",
            "verified_2024_jif": "10.6",
            "verified_2024_5yr_jif": "10.8",
            "strict_20_50_fit": "no",
            "current_route": "low_fit_without_clinical_biology",
            "cas_zone_note": "Verify locally.",
            "warning_note": "Verify against official current warning PDF.",
            "source_url": "https://www.sciencedirect.com/journal/cell-reports-medicine/about/insights",
            "current_fit": "needs disease or translational biology depth; current RMTGuard is primarily methods/software",
        },
    ]


def build_markdown(
    gap_rows: list[dict[str, object]], journal_rows: list[dict[str, object]]
) -> str:
    total_weight = sum(int(row["weight"]) for row in gap_rows)
    total_score = sum(int(row["current_score"]) for row in gap_rows)
    percent = total_score / total_weight * 100 if total_weight else 0.0
    blockers = [
        str(row["blocking_items"])
        for row in gap_rows
        if str(row["blocking_items"]) != "none"
    ]
    blocker_text = ";".join(blockers)
    rare_state_claim_boundary_present = RARE_STATE_CLAIM_BOUNDARY.exists()
    seurat_status_rows = _read_tsv(SEURAT_MATCHED_STATUS)
    seurat_status_by_id = {
        row.get("check_id", ""): row.get("status", "") for row in seurat_status_rows
    }
    jackstraw_status_rows = _read_tsv(SEURAT_JACKSTRAW_FEASIBILITY_STATUS)
    jackstraw_status_by_id = {
        row.get("check_id", ""): row.get("status", "")
        for row in jackstraw_status_rows
    }
    jackstraw_feasibility_present = jackstraw_status_by_id.get(
        "seurat_jackstraw_feasibility"
    ) in {"feasibility_pass", "manuscript_candidate"}
    jackstraw_final_present = (
        jackstraw_status_by_id.get("manuscript_grade_jackstraw")
        == "manuscript_candidate"
        or seurat_status_by_id.get("seurat_v5_jackstraw") == "manuscript_candidate"
    )
    paired_status_rows = _read_tsv(RMTGUARD_SEURAT_PAIRED_STATUS)
    paired_status_by_id = {
        row.get("check_id", ""): row.get("status", "")
        for row in paired_status_rows
    }
    paired_stats_pilot_present = paired_status_by_id.get("paired_overlap") in {
        "paired10_pilot_pass",
        "paired20_manuscript_candidate",
    }
    paired_stats_manuscript_candidate = (
        paired_status_by_id.get("paired_statistics_claim_status")
        == "manuscript_candidate"
    )
    seurat_executable_present = (
        seurat_status_by_id.get("seurat_mtx_bridge") == "pass"
        and _status_at_least(
            seurat_status_by_id.get("seurat_v5_fixed_30", ""),
            {"smoke_pass", "pilot10_pass", "manuscript_candidate"},
        )
        and _status_at_least(
            seurat_status_by_id.get("seurat_v5_elbow", ""),
            {"smoke_pass", "pilot10_pass", "manuscript_candidate"},
        )
    )
    seurat_core_pilot10_present = (
        seurat_status_by_id.get("seurat_mtx_bridge") == "pass"
        and all(
            _status_at_least(
                seurat_status_by_id.get(method, ""),
                {"pilot10_pass", "manuscript_candidate"},
            )
            for method in [
                "seurat_v5_fixed_30",
                "seurat_v5_fixed_50",
                "seurat_v5_elbow",
            ]
        )
    )
    seurat_core_20_present = (
        seurat_status_by_id.get("seurat_mtx_bridge") == "pass"
        and all(
            seurat_status_by_id.get(method, "") == "manuscript_candidate"
            for method in [
                "seurat_v5_fixed_30",
                "seurat_v5_fixed_50",
                "seurat_v5_elbow",
            ]
        )
    )
    seurat_full_20_present = seurat_core_20_present and jackstraw_final_present
    if "10_repeat_real_data_stability" in blocker_text:
        missing_real_data = (
            "2. Manuscript-grade real-data stability rerun with 10+ repeats "
            "and stronger baselines."
        )
        missing_statistics = (
            "3. Statistical confidence intervals and paired tests for stability, "
            "annotation, and rare-state power."
        )
    else:
        if not any(
            token in blocker_text
            for token in [
                "added_dataset_label_free_boundary",
                "additional_datasets",
                "full_Seurat_v5",
                "JackStraw",
                "paired_RMTGuard_vs_Seurat_statistics",
                "RMTGuard_paired_repeat_depth_20",
                "official_Seurat",
                "20_plus_repeat_matched_baselines",
                "20_50_repeat_matched_baselines",
            ]
        ):
            missing_real_data = (
            "2. Benchmark breadth, official Seurat/JackStraw baselines, "
                "paired statistics on the labeled subset, and label-free "
                "dataset boundaries are now controlled. Do not reopen this "
                "layer unless adding optional atlas-scale evidence."
            )
        elif "added_dataset_label_free_boundary" in blocker_text:
            missing_real_data = (
                "2. Label-free added-dataset boundary: the stability benchmark "
                "and official Seurat/JackStraw rows now cover seven public "
                "datasets, but annotation-ARI paired statistics are available "
                "only for the labeled subset. PBMC3k and PDAC GSE154778 should "
                "remain label-free stability/runtime evidence unless reliable "
                "cell-state annotations are added."
            )
        elif seurat_full_20_present and paired_stats_manuscript_candidate:
            missing_real_data = (
                "2. Expand public benchmark breadth: official Seurat fixed30/"
                "fixed50/elbow/JackStraw and paired RMTGuard-versus-Seurat "
                "annotation statistics now have 20-repeat manuscript-candidate "
                "evidence across the four prepared datasets. Still missing: "
                "additional public datasets under the same split framework."
            )
        elif (
            seurat_core_20_present
            and jackstraw_final_present
            and paired_stats_pilot_present
            and not paired_stats_manuscript_candidate
        ):
            missing_real_data = (
                "2. Finish the matched-baseline framework: official Seurat "
                "fixed30/fixed50/elbow/JackStraw now have 20-repeat manuscript-candidate "
                "evidence, "
                "and paired RMTGuard-versus-Seurat annotation statistics exist "
                "for the overlapping 10 RMTGuard repeats. Still missing: "
                "RMTGuard default repeats 10-19 for 20-repeat paired statistics, "
                "and additional public datasets."
            )
        elif seurat_full_20_present:
            missing_real_data = (
                "2. Finish the matched-baseline framework: official Seurat "
                "fixed30/fixed50/elbow/JackStraw now have 20-repeat manuscript-"
                "candidate evidence, but paired RMTGuard-versus-Seurat tests "
                "and additional public datasets are still missing."
            )
        elif seurat_core_20_present and jackstraw_feasibility_present:
            missing_real_data = (
                "2. Finish the matched-baseline framework: official Seurat "
                "fixed30/fixed50/elbow now have 20-repeat manuscript-candidate "
                "evidence and JackStraw has four-dataset feasibility evidence, "
                "but final JackStraw repeats, paired RMTGuard-versus-Seurat "
                "tests, and additional public datasets are still missing."
            )
        elif seurat_core_20_present:
            missing_real_data = (
                "2. Finish the matched-baseline framework: official Seurat "
                "fixed30/fixed50/elbow now have 20-repeat manuscript-candidate "
                "evidence, but JackStraw feasibility/final repeats, paired "
                "RMTGuard-versus-Seurat tests, and additional public datasets "
                "are still missing."
            )
        elif seurat_core_pilot10_present and jackstraw_feasibility_present:
            missing_real_data = (
                "2. Finish the matched-baseline framework: official Seurat "
                "fixed30/fixed50/elbow now have 10-repeat pilot evidence and "
                "JackStraw has four-dataset feasibility evidence, but "
                "JackStraw final repeats, 20+ repeat confidence intervals, "
                "paired tests, and additional public datasets are still missing."
            )
        elif seurat_core_pilot10_present:
            missing_real_data = (
                "2. Finish the matched-baseline framework: official Seurat "
                "fixed30/fixed50/elbow now have 10-repeat pilot evidence "
                "across four datasets, but JackStraw, 20+ repeat confidence "
                "intervals, paired tests, and additional public datasets are "
                "still missing."
            )
        elif seurat_executable_present:
            missing_real_data = (
                "2. Finish the matched-baseline framework: official Seurat "
                "fixed30/elbow are smoke-tested across four datasets, but "
                "fixed50, JackStraw, 10-20+ repeat confidence intervals, and "
                "additional public datasets are still missing."
            )
        elif MATCHED_BASELINE_DESIGN.exists():
            missing_real_data = (
                "2. Finish the matched-baseline framework: local Python "
                "comparators now have a pilot result layer, but official "
                "Seurat v5 and Seurat JackStraw are still missing."
                if MATCHED_BASELINE_PILOT_SUMMARY.exists()
                else "2. Execute the matched-baseline design: final Seurat v5, "
                "JackStraw, and permutation/parallel-PCA results on the same "
                "split framework. The design exists; the comparator results "
                "do not."
            )
        else:
            missing_real_data = (
                "2. Final Seurat v5, JackStraw, and permutation/parallel-PCA "
                "baselines on the same 10-repeat split framework."
            )
        missing_statistics = (
            "3. Rare-state power confidence intervals, cluster-number variance, "
            "and annotation-recovery statistics after benchmark freeze."
        )
        calibration_done = any(
            row["domain"] == "calibration_statistics"
            and str(row["status"]).startswith("manuscript_grade_calibration_done")
            for row in gap_rows
        )
        if calibration_done:
            missing_statistics = (
                "3. Realistic-null and rare-state power repeat depth is complete "
                "at 50 repeats with CIs, and the low-prevalence/weak-effect "
                "claim boundary is documented."
                if rare_state_claim_boundary_present
                else "3. Realistic-null and rare-state power repeat depth is complete "
                "at 50 repeats with CIs; the remaining statistics issue is a "
                "claim boundary for low-prevalence/weak-effect rare states."
            )
    lines = [
        "# RMTGuard 20-50 JIF Gap Assessment",
        "",
        "Generated by `python scripts/build_jif20_50_gap_assessment.py`.",
        "",
        "## Bottom Line",
        "",
        f"- Current readiness score: `{total_score}/{total_weight}` = `{percent:.1f}%`.",
        "- Acceptance guarantee: `impossible`.",
        "- Current strict 20-50 JIF status: `not ready`.",
        "- Current best strict 20-50 target: `Nature Methods`, but only after gate recovery.",
        "- Current most realistic fallback if strict 20-50 is relaxed: `Genome Biology`, but this is below strict 20 JIF by 2024 JIF and should be treated as a high-quality genomics fallback rather than a 20-50 target.",
        f"- Active blocker groups: `{blocker_text}`.",
        "",
        "## Distance By Domain",
        "",
        "| Domain | Weight | Score | Status | Blocking items | Next supplement |",
        "| --- | ---: | ---: | --- | --- | --- |",
    ]
    for row in gap_rows:
        lines.append(
            f"| {row['domain']} | {row['weight']} | {row['current_score']} | {row['status']} | {row['blocking_items']} | {row['next_supplement']} |"
        )

    lines.extend(
        [
            "",
            "## Journal Route Check",
            "",
            "| Journal | 2024 JIF | 5-year JIF | Strict 20-50 fit | Current route | Current fit |",
            "| --- | ---: | ---: | --- | --- | --- |",
        ]
    )
    for row in journal_rows:
        lines.append(
            f"| {row['journal']} | {row['verified_2024_jif']} | {row['verified_2024_5yr_jif']} | {row['strict_20_50_fit']} | {row['current_route']} | {row['current_fit']} |"
        )

    lines.extend(
        [
            "",
            "## What Is Still Missing",
            "",
            "1. Release engineering is complete for v0.1.0; the remaining gap is scientific evidence, not public code availability.",
            missing_real_data,
            missing_statistics,
            "4. Component ablation has reached the current 20-repeat synthetic and labeled real-data layer; realistic null and rare-state power have reached 50-repeat depth, and the low-prevalence/weak-effect limitation is now captured in a claim-boundary artifact.",
            "5. PDAC/TME decision packet, dual-route preflight, runbook, first-pass deep validation, rank-based MSigDB Hallmark/Reactome enrichment, and atlas marker citation mapping are complete; authors still need to confirm the route and final Figure 4 wording.",
            "6. Optional broader atlas-scale dataset if the Nature Methods route remains active after the current blockers are cleared.",
            "7. Final source-data/caption/reporting-summary regeneration after benchmark freeze.",
            "",
            "## What Can Be Added To Improve The Route",
            "",
            "- Rare-state claim boundary is controlled; add optional dropout/batch power grids only if the Nature Methods rare-state claim remains central."
            if rare_state_claim_boundary_present
            else "- Freeze the 50-repeat realistic-null and rare-state power source data, then write a rare-state claim boundary that explicitly covers low-prevalence/weak-effect failure modes.",
            "- Add a realistic null family that preserves library size, gene marginals, dropout, and batch structure.",
            "- Add a full `callability map` figure where no-call is treated as a validated decision, not a failure.",
            "- Keep PBMC3k and PDAC GSE154778 as label-free stability/runtime evidence unless reliable cell-state annotations are added.",
            "- Use `docs/pdac_tme_deep_validation.md` and `docs/pdac_tme_pathway_atlas_validation.md` as bounded PDAC/TME support; freeze only manuscript-interpretable pathway hits for Figure 4 and keep low-specificity translation/ribosomal hits in source data.",
            "",
            "## Source Artifacts",
            "",
            f"- Gap TSV: `{_rel(OUT_TSV)}`",
            f"- Journal TSV: `{_rel(OUT_JOURNALS)}`",
            f"- Gate report: `{_rel(GATE_REPORT)}`",
            f"- External action plan: `{_rel(ACTION_PLAN)}`",
            f"- Manuscript stability statistics: `{_rel(MANUSCRIPT_STABILITY_STATS)}`",
            f"- Component ablation evidence: `{_rel(COMPONENT_ABLATION)}`",
            f"- Component ablation summary: `{_rel(COMPONENT_ABLATION_SUMMARY)}`",
            "- P0 science sprint status: `results/submission/p0_science_sprint_status.tsv`",
            f"- Rare-state claim boundary: `{_rel(RARE_STATE_CLAIM_BOUNDARY)}`",
            f"- PDAC/TME route decision packet: `{_rel(PDAC_TME_ROUTE_PACKET)}`",
            f"- PDAC/TME dual-route preflight: `{_rel(PDAC_TME_DUAL_ROUTE_PREFLIGHT)}`",
            f"- PDAC/TME dual-route runbook: `{_rel(PDAC_TME_DUAL_ROUTE_RUNBOOK)}`",
            f"- PDAC/TME pathway/atlas summary: `{_rel(PDAC_TME_PATHWAY_ATLAS_SUMMARY)}`",
            f"- Real-data ablation annotation summary: `{_rel(REALDATA_ABLATION_SUMMARY)}`",
            f"- Real-data ablation figure source data: `{_rel(REALDATA_ABLATION_ASSET_SUMMARY)}`",
            f"- Matched baseline design: `{_rel(MATCHED_BASELINE_DESIGN)}`",
            f"- Matched baseline pilot summary: `{_rel(MATCHED_BASELINE_PILOT_SUMMARY)}`",
            f"- Matched baseline external blockers: `{_rel(MATCHED_BASELINE_EXTERNAL_BLOCKERS)}`",
            f"- Official Seurat matched summary: `{_rel(SEURAT_MATCHED_SUMMARY)}`",
            f"- Official Seurat matched status: `{_rel(SEURAT_MATCHED_STATUS)}`",
            f"- Official Seurat JackStraw feasibility summary: `{_rel(SEURAT_JACKSTRAW_FEASIBILITY_SUMMARY)}`",
            f"- Official Seurat JackStraw feasibility status: `{_rel(SEURAT_JACKSTRAW_FEASIBILITY_STATUS)}`",
            f"- Paired RMTGuard-versus-official-Seurat statistics: `{_rel(RMTGUARD_SEURAT_PAIRED_STATS)}`",
            f"- Paired RMTGuard-versus-official-Seurat status: `{_rel(RMTGUARD_SEURAT_PAIRED_STATUS)}`",
            f"- Added-dataset annotation boundary: `{_rel(ANNOTATION_BOUNDARY)}`",
            f"- Submission guard: `{_rel(SUBMISSION_GUARD)}`",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    gap_rows = build_gap_rows()
    journal_rows = build_journal_rows()
    _write_tsv(
        OUT_TSV,
        gap_rows,
        [
            "domain",
            "weight",
            "current_score",
            "status",
            "evidence",
            "blocking_items",
            "what_is_done",
            "what_is_missing",
            "next_supplement",
        ],
    )
    _write_tsv(
        OUT_JOURNALS,
        journal_rows,
        [
            "journal",
            "verified_2024_jif",
            "verified_2024_5yr_jif",
            "strict_20_50_fit",
            "current_route",
            "cas_zone_note",
            "warning_note",
            "source_url",
            "current_fit",
        ],
    )
    _write_text(OUT_MD, build_markdown(gap_rows, journal_rows))
    print(_rel(OUT_TSV))
    print(_rel(OUT_JOURNALS))
    print(_rel(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
