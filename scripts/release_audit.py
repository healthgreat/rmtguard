from __future__ import annotations

import argparse
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SOURCE_FILES = [
    "README.md",
    "LICENSE",
    "CITATION.cff",
    ".zenodo.json",
    "pyproject.toml",
    "metadata/datasets.tsv",
    "metadata/submission_gates.tsv",
    "metadata/gate_evidence_template.tsv",
    "metadata/benchmark_phases.tsv",
    "metadata/external_review_feedback_template.tsv",
    "metadata/external_review_feedback_active.tsv",
    "metadata/author_metadata.tsv",
    "metadata/credit_roles.tsv",
    "metadata/orcid_search_evidence.tsv",
    "docs/benchmark_plan.md",
    "docs/publication_strategy.md",
    "docs/data_and_code_availability_template.md",
    "docs/github_release_checklist.md",
    "docs/github_staging_plan.md",
    "docs/external_release_plan.md",
    "docs/public_release_blocker_report.md",
    "docs/top_paper_route_package.md",
    "docs/editorial_presubmission_packet.md",
    "docs/external_review_feedback_triage.md",
    "docs/external_review_action_plan.md",
    "docs/post_feedback_journal_route_gate.md",
    "docs/route_reframe_package.md",
    "docs/genome_biology_transfer_package.md",
    "docs/reviewer_defense_package.md",
    "docs/author_release_execution_packet.md",
    "docs/author_metadata_status.md",
    "docs/author_declarations_and_credit_roles.md",
    "docs/github_public_repo_action_required.md",
    "docs/manual_author_execution_steps.md",
    "docs/claim_boundary_lint.md",
    "docs/claim_traceability.md",
    "docs/submission_guard.md",
    "docs/stability_gate_diagnostics.md",
    "docs/stability_utility_tradeoff.md",
    "docs/algorithm_rescue_probe_report.md",
    "docs/no_call_benchmark.md",
    "docs/publication_20_50_rescue_plan.md",
    "docs/claim_scope_decision.md",
    "docs/pdac_tme_showcase_depth.md",
    "docs/realistic_null_power_calibration.md",
    "docs/manuscript_grade_stability_statistics.md",
    "docs/component_ablation_benchmark.md",
    "docs/realdata_ablation_annotation.md",
    "docs/realdata_ablation_figure_table.md",
    "docs/matched_baseline_design.md",
    "docs/matched_baseline_pilot.md",
    "docs/seurat_matched_baseline.md",
    "docs/seurat_jackstraw_feasibility.md",
    "docs/component_ablation_evidence.md",
    "docs/jif20_50_gap_assessment.md",
    "docs/publication_execution_board.md",
    "docs/nature_reporting_summary_draft.md",
    "docs/editorial_risk_audit.md",
    "docs/method_risk_log.md",
    "manuscript/title_page_author_metadata.md",
    "benchmarks/run_synthetic_benchmark.py",
    "benchmarks/run_phase1_benchmark.py",
    "benchmarks/run_stability_benchmark.py",
    "benchmarks/run_seurat_baseline.R",
    "benchmarks/run_seurat_matched_baseline.R",
    "src/rmtguard/__init__.py",
    "src/rmtguard/__main__.py",
    "src/rmtguard/core.py",
    "src/rmtguard/rmt.py",
    "src/rmtguard/preprocess.py",
    "src/rmtguard/cluster.py",
    "src/rmtguard/scanpy_api.py",
    "src/rmtguard/cli.py",
    "src/rmtguard/simulate.py",
    "scripts/evaluate_submission_gates.py",
    "scripts/prepare_phase1_datasets.py",
    "scripts/prepare_pdac_datasets.py",
    "scripts/build_figure_source_data.py",
    "scripts/render_main_figures.py",
    "scripts/build_stability_gate_report.py",
    "scripts/build_stability_utility_report.py",
    "scripts/build_algorithm_rescue_probe_report.py",
    "scripts/build_pdac_showcase_depth_report.py",
    "scripts/build_no_call_benchmark_report.py",
    "scripts/build_callability_decision_map.py",
    "scripts/build_publication_20_50_plan.py",
    "scripts/build_publication_tables.py",
    "scripts/audit_publication_visual_assets.py",
    "scripts/build_project_gantt.py",
    "scripts/run_realistic_null_power_calibration.py",
    "scripts/render_calibration_figures.py",
    "scripts/build_manuscript_stability_statistical_report.py",
    "scripts/run_component_ablation_benchmark.py",
    "scripts/run_realdata_ablation_annotation.py",
    "scripts/build_realdata_ablation_assets.py",
    "scripts/build_matched_baseline_design.py",
    "scripts/run_matched_baseline_pilot.py",
    "scripts/export_seurat_mtx_inputs.py",
    "scripts/build_seurat_matched_baseline_report.py",
    "scripts/build_seurat_jackstraw_feasibility_report.py",
    "scripts/build_component_ablation_evidence.py",
    "scripts/build_jif20_50_gap_assessment.py",
    "scripts/build_claim_scope_decision.py",
    "scripts/build_presubmission_package.py",
    "scripts/build_journal_compliance_audit.py",
    "scripts/build_publication_execution_board.py",
    "scripts/execute_github_release.py",
    "scripts/finalize_submission_release.py",
    "scripts/build_reporting_summary_draft.py",
    "scripts/build_editorial_risk_audit.py",
    "scripts/build_release_readiness.py",
    "scripts/record_external_release.py",
    "scripts/build_release_artifact_manifest.py",
    "scripts/build_release_asset_bundle.py",
    "scripts/build_external_release_plan.py",
    "scripts/build_public_release_blocker_report.py",
    "scripts/build_top_paper_route_package.py",
    "scripts/build_editorial_presubmission_packet.py",
    "scripts/lint_claim_boundaries.py",
    "scripts/validate_claim_traceability.py",
    "scripts/build_submission_guard.py",
    "scripts/export_current_article_review_packet.py",
    "scripts/triage_external_review_feedback.py",
    "scripts/build_external_review_action_plan.py",
    "scripts/build_post_feedback_journal_route_gate.py",
    "scripts/build_route_reframe_package.py",
    "scripts/build_genome_biology_transfer_package.py",
    "scripts/build_reviewer_defense_package.py",
    "scripts/build_author_release_execution_packet.py",
    "scripts/build_manuscript_evidence_package.py",
    "scripts/build_manuscript_draft_package.py",
    "scripts/build_github_staging_plan.py",
    "scripts/build_github_release_handoff.py",
    "scripts/stage_github_release_files.py",
    "scripts/update_repository_metadata.py",
    "scripts/update_gate_evidence_from_results.py",
    "benchmarks/run_pdac_showcase.py",
    "manuscript/figure_plan.md",
    "manuscript/submission_readiness.md",
    "manuscript/nature_methods_presubmission_draft.md",
    "manuscript/abstract_draft.md",
    "manuscript/cover_letter_draft.md",
    "manuscript/nature_methods_outline.md",
    "manuscript/genome_biology_fallback_outline.md",
    "manuscript/genome_biology_conversion_draft.md",
    "manuscript/genome_biology_cover_letter_draft.md",
    "manuscript/genome_biology_reframed_abstract.md",
    "manuscript/nature_methods_hold_statement.md",
    "manuscript/reviewer_defense_response_draft.md",
    "manuscript/code_availability_finalization_draft.md",
    "manuscript/top_paper_claim_ladder.md",
    "manuscript/nature_methods_presubmission_inquiry.md",
    "manuscript/reviewer_response_playbook.md",
    "manuscript/figure_claim_checklist.md",
    ".github/workflows/ci.yml",
]

REQUIRED_GENERATED_ARTIFACTS = [
    "results/manuscript/reviewer_objection_matrix.tsv",
    "results/manuscript/storyline_panel_map.tsv",
    "results/manuscript/manuscript_draft_package_manifest.tsv",
    "results/stability_benchmarks/stability_gate_diagnostics.tsv",
    "results/stability_benchmarks/stability_utility_tradeoff.tsv",
    "results/rescue/algorithm_rescue_probe_summary.tsv",
    "results/pdac_tme/pdac_showcase_depth_audit.tsv",
    "results/no_call_benchmarks/no_call_summary.tsv",
    "results/callability/no_call_decision_map.tsv",
    "results/figures/source_data/figure3_callability_decision_map.tsv",
    "results/gates/publication_20_50_decision.tsv",
    "results/submission/claim_scope_decision.tsv",
    "results/release/public_release_blockers.tsv",
    "results/submission/top_paper_route_decision.tsv",
    "results/submission/editorial_presubmission_packet.tsv",
    "results/submission/figure_claim_checklist.tsv",
    "results/submission/claim_boundary_lint.tsv",
    "results/submission/claim_traceability.tsv",
    "results/submission/submission_guard.tsv",
    "results/submission/external_review_feedback_triage.tsv",
    "results/submission/external_review_action_plan.tsv",
    "results/submission/post_feedback_journal_route_gate.tsv",
    "results/submission/route_reframe_decision.tsv",
    "results/submission/genome_biology_transfer_checklist.tsv",
    "results/submission/reviewer_defense_matrix.tsv",
    "results/submission/publication_visual_asset_audit.tsv",
    "results/project_management/rmtguard_project_gantt.tsv",
    "results/project_management/rmtguard_project_gantt.md",
    "figures/project_management/rmtguard_project_gantt.png",
    "figures/project_management/rmtguard_project_gantt.pdf",
    "results/calibration/realistic_null_detail.tsv",
    "results/calibration/realistic_null_summary.tsv",
    "results/calibration/rare_state_power_detail.tsv",
    "results/calibration/rare_state_power_summary.tsv",
    "figures/calibration/calibration_figure_manifest.tsv",
    "figures/calibration/realistic_null_power_calibration.png",
    "figures/calibration/realistic_null_power_calibration.pdf",
    "figures/calibration/realistic_null_power_calibration.tiff",
    "results/manuscript_stability_benchmarks/manuscript_stability_statistics.tsv",
    "results/manuscript_stability_benchmarks/manuscript_stability_paired_deltas.tsv",
    "results/ablation/component_ablation_detail.tsv",
    "results/ablation/component_ablation_summary.tsv",
    "results/ablation/realdata_ablation_annotation_detail.tsv",
    "results/ablation/realdata_ablation_annotation_summary.tsv",
    "results/figures/source_data/figure5_realdata_ablation_delta_summary.tsv",
    "figures/manuscript/figure5_realdata_ablation_forest.png",
    "figures/manuscript/figure5_realdata_ablation_forest.pdf",
    "figures/manuscript/figure5_realdata_ablation_forest.tiff",
    "figures/manuscript/realdata_ablation_figure_manifest.tsv",
    "results/tables/manuscript/supplemental_realdata_ablation_table.tsv",
    "results/tables/manuscript/supplemental_realdata_ablation_table.docx",
    "results/tables/manuscript/realdata_ablation_table_manifest.tsv",
    "results/ablation/component_ablation_evidence.tsv",
    "results/ablation/component_ablation_gap_matrix.tsv",
    "results/submission/matched_baseline_design.tsv",
    "results/submission/matched_baseline_pilot_detail.tsv",
    "results/submission/matched_baseline_pilot_summary.tsv",
    "results/submission/matched_baseline_external_blockers.tsv",
    "results/submission/seurat_matched_baseline_summary.tsv",
    "results/submission/seurat_matched_baseline_status.tsv",
    "results/submission/seurat_jackstraw_feasibility_summary.tsv",
    "results/submission/seurat_jackstraw_feasibility_status.tsv",
    "data/processed/seurat_mtx/seurat_mtx_manifest.tsv",
    "results/submission/jif20_50_gap_assessment.tsv",
    "results/submission/jif20_50_journal_route.tsv",
    "results/release/author_release_execution_checklist.tsv",
    "results/tables/manuscript/table1_submission_gate_summary.tsv",
    "results/tables/manuscript/table2_public_benchmark_summary.tsv",
    "results/tables/manuscript/table3_external_review_action_plan.tsv",
    "results/tables/manuscript/publication_table_manifest.tsv",
    "results/tables/manuscript/rmtguard_publication_tables.docx",
]

REQUIRED_FILES = REQUIRED_SOURCE_FILES + REQUIRED_GENERATED_ARTIFACTS


def _is_git_ignored(path: Path) -> bool:
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        rel = path
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", str(rel)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit RMTGuard release readiness files."
    )
    parser.add_argument(
        "--source-only",
        action="store_true",
        help="Check repository source files only. Use this mode in clean CI checkouts where generated results are intentionally not committed.",
    )
    args = parser.parse_args(argv)

    failures: list[str] = []
    required_files = REQUIRED_SOURCE_FILES if args.source_only else REQUIRED_FILES
    for rel in required_files:
        path = ROOT / rel
        if not path.exists():
            failures.append(f"missing required file: {rel}")

    forbidden_dirs = ["__pycache__", ".pytest_cache"]
    for forbidden in forbidden_dirs:
        hits = [path for path in ROOT.rglob(forbidden) if not _is_git_ignored(path)]
        if hits:
            failures.append(f"remove generated directory: {hits[0]}")

    for area in ["data/raw", "data/processed", "data/external"]:
        path = ROOT / area
        for file in path.glob("*"):
            if (
                file.name != ".gitkeep"
                and file.is_file()
                and file.stat().st_size > 50 * 1024 * 1024
                and not _is_git_ignored(file)
            ):
                failures.append(
                    f"large data file should not be committed directly: {file}"
                )

    data_suffixes = {".h5ad", ".h5", ".rds", ".rda", ".mtx", ".gz", ".tar", ".zip"}
    data_root = ROOT / "data"
    if data_root.exists():
        for file in data_root.rglob("*"):
            if (
                file.is_file()
                and file.name not in {".gitkeep", "README.md"}
                and file.suffix.lower() in data_suffixes
                and not _is_git_ignored(file)
            ):
                failures.append(f"data artifact is not git-ignored: {file}")

    if failures:
        print("Release audit failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    if args.source_only:
        print("Release audit passed (source-only mode).")
    else:
        print("Release audit passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
