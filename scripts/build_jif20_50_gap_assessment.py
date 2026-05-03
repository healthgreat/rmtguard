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
        }
    powers = [_float(row.get("power", "")) for row in power_rows]
    return {
        "max_false_call": max(
            _float(row.get("false_call_rate", "")) for row in null_rows
        ),
        "min_power": min(powers),
        "median_power": sorted(powers)[len(powers) // 2],
        "settings_power_ge_080": sum(power >= 0.80 for power in powers) / len(powers),
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
    realdata_repeat_depths = [
        int(float(row.get("n_repeats", "0")))
        for row in realdata_rows
        if row.get("n_repeats", "")
    ]
    realdata_max_repeats = max(realdata_repeat_depths) if realdata_repeat_depths else 0
    if not rows:
        return {
            "status": "missing",
            "component_count": 0,
            "benchmark_rows": len(benchmark_rows),
            "realdata_rows": len(realdata_rows),
            "realdata_max_repeats": realdata_max_repeats,
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
    return {
        "status": status,
        "component_count": len(rows),
        "benchmark_rows": len(benchmark_rows),
        "realdata_rows": len(realdata_rows),
        "realdata_max_repeats": realdata_max_repeats,
        "missing_components": ",".join(missing) if missing else "none",
        "partial_components": ",".join(partial) if partial else "none",
    }


def build_gap_rows() -> list[dict[str, object]]:
    gates = _read_tsv(GATE_REPORT)
    actions = _read_tsv(ACTION_PLAN)
    guard = _read_tsv(SUBMISSION_GUARD)
    release_rows = _read_tsv(RELEASE_READINESS)
    calibration = _calibration_summary()
    manuscript_stability = _manuscript_stability_summary()
    component_ablation = _component_ablation_summary()
    component_matrix_exists = component_ablation["component_count"] > 0
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
                else "Treat PBMC3k and PDAC GSE154778 as label-free stability/"
                "runtime comparator evidence, or add reliable cell-state "
                "annotations before using them in annotation-ARI claims."
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
            "current_score": 14 if component_ablation.get("realdata_max_repeats", 0) >= 10 else (13 if component_ablation["realdata_rows"] else (12 if component_ablation["benchmark_rows"] else (10 if component_matrix_exists else 9))),
            "status": (
                "partial_improved_component_controlled"
                if component_matrix_exists
                else "partial_improved"
            ),
            "evidence": (
                f"{_rel(CALIBRATION_POWER)};{_rel(COMPONENT_ABLATION)}"
                if component_matrix_exists
                else _rel(CALIBRATION_POWER)
            ),
            "blocking_items": "weak_effect_low_prevalence_power;draft_repeat_count",
            "what_is_done": f"Count-preserving null false-call max is {calibration['max_false_call']:.3f}; rare-state power improved, with {calibration['settings_power_ge_080']:.0%} of grid settings at power >=0.80. Component ablation status is {component_ablation['status']} across {component_ablation['component_count']} components, {component_ablation['benchmark_rows']} draft synthetic benchmark summary rows, and {component_ablation['realdata_rows']} real-data annotation rows with maximum repeat depth {component_ablation['realdata_max_repeats']}. Real-data ablation figure/table assets present: {realdata_ablation_assets_present}.",
            "what_is_missing": f"Minimum rare-state power remains {calibration['min_power']:.2f}; current repeats are draft scale, not manuscript grade. Missing or nonfinal component experiments: {component_ablation['missing_components']}.",
            "next_supplement": "Scale the draft P0 component ablations and real-data annotation checks from the current 10-repeat pilot to 20-50 repeats, add final confidence intervals, and freeze the matched Seurat/JackStraw comparator table.",
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
            "status": _action_status(
                actions, "03_manuscript_grade_stability_baselines"
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
                "subset. Label-free dataset boundaries and component ablation "
                "remain incomplete for a Nature Methods-style claim."
            ),
            "next_supplement": benchmark_next,
        },
        {
            "domain": "biological_showcase",
            "weight": 10,
            "current_score": 4,
            "status": _action_status(actions, "06_biological_showcase_decision"),
            "evidence": "docs/pdac_tme_showcase_depth.md",
            "blocking_items": "PDAC_TME_depth_or_demotion",
            "what_is_done": "PDAC/TME public use case has marker-level immune/ductal validation and bounded wording.",
            "what_is_missing": "It is not yet a strong biological application figure for a high-tier method paper.",
            "next_supplement": "Either add DE/GSEA/trajectory/published-atlas validation for PDAC/TME, or demote PDAC/TME and use a stronger ground-truth application.",
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
        if "added_dataset_label_free_boundary" in blocker_text:
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
            "4. Manuscript-grade component ablation experiments for MP edge, TW proxy, permutation calibration, HVG plateau, adaptive embedding, rare-state guard, no-call contract, and batch residualization. A resumable draft benchmark now includes null, rare-state, synthetic batch-effect, real-data annotation screens, and a pilot forest/table asset layer, but P0 runs still need 20-50 repeats, confidence intervals, and executed matched baselines.",
            "5. A stronger biological application, or a deliberate demotion of PDAC/TME to supplementary use case.",
            "6. Optional broader atlas-scale dataset if the Nature Methods route remains active after the current blockers are cleared.",
            "7. Final source-data/caption/reporting-summary regeneration after benchmark freeze.",
            "",
            "## What Can Be Added To Improve The Route",
            "",
            "- Scale the `rare_state_guard` on/off ablation from draft screen to manuscript-grade repeats with confidence intervals.",
            "- Add a realistic null family that preserves library size, gene marginals, dropout, and batch structure.",
            "- Add a full `callability map` figure where no-call is treated as a validated decision, not a failure.",
            "- Keep PBMC3k and PDAC GSE154778 as label-free stability/runtime evidence unless reliable cell-state annotations are added.",
            "- Add a stronger application with known external ground truth if PDAC/TME remains shallow.",
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
