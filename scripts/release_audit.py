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
    "docs/benchmark_plan.md",
    "docs/publication_strategy.md",
    "docs/data_and_code_availability_template.md",
    "docs/github_release_checklist.md",
    "docs/github_staging_plan.md",
    "docs/external_release_plan.md",
    "docs/public_release_blocker_report.md",
    "docs/top_paper_route_package.md",
    "docs/editorial_presubmission_packet.md",
    "docs/claim_boundary_lint.md",
    "docs/claim_traceability.md",
    "docs/stability_gate_diagnostics.md",
    "docs/stability_utility_tradeoff.md",
    "docs/algorithm_rescue_probe_report.md",
    "docs/no_call_benchmark.md",
    "docs/publication_20_50_rescue_plan.md",
    "docs/claim_scope_decision.md",
    "docs/pdac_tme_showcase_depth.md",
    "docs/publication_execution_board.md",
    "docs/nature_reporting_summary_draft.md",
    "docs/editorial_risk_audit.md",
    "docs/method_risk_log.md",
    "benchmarks/run_synthetic_benchmark.py",
    "benchmarks/run_phase1_benchmark.py",
    "benchmarks/run_stability_benchmark.py",
    "benchmarks/run_seurat_baseline.R",
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
    "scripts/build_publication_20_50_plan.py",
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
    "results/gates/publication_20_50_decision.tsv",
    "results/submission/claim_scope_decision.tsv",
    "results/release/public_release_blockers.tsv",
    "results/submission/top_paper_route_decision.tsv",
    "results/submission/editorial_presubmission_packet.tsv",
    "results/submission/figure_claim_checklist.tsv",
    "results/submission/claim_boundary_lint.tsv",
    "results/submission/claim_traceability.tsv",
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
