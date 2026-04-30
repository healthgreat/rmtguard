from __future__ import annotations

import sys
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
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
    "docs/stability_gate_diagnostics.md",
    "docs/no_call_benchmark.md",
    "docs/publication_20_50_rescue_plan.md",
    "docs/publication_execution_board.md",
    "docs/method_risk_log.md",
    "benchmarks/run_synthetic_benchmark.py",
    "benchmarks/run_phase1_benchmark.py",
    "benchmarks/run_stability_benchmark.py",
    "scripts/evaluate_submission_gates.py",
    "scripts/prepare_phase1_datasets.py",
    "scripts/prepare_pdac_datasets.py",
    "scripts/build_figure_source_data.py",
    "scripts/render_main_figures.py",
    "scripts/build_stability_gate_report.py",
    "scripts/build_no_call_benchmark_report.py",
    "scripts/build_publication_20_50_plan.py",
    "scripts/build_presubmission_package.py",
    "scripts/build_journal_compliance_audit.py",
    "scripts/build_publication_execution_board.py",
    "scripts/build_release_readiness.py",
    "scripts/record_external_release.py",
    "scripts/build_release_artifact_manifest.py",
    "scripts/build_release_asset_bundle.py",
    "scripts/build_external_release_plan.py",
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
    "results/manuscript/reviewer_objection_matrix.tsv",
    "results/manuscript/storyline_panel_map.tsv",
    "results/manuscript/manuscript_draft_package_manifest.tsv",
    "results/stability_benchmarks/stability_gate_diagnostics.tsv",
    "results/no_call_benchmarks/no_call_summary.tsv",
    "results/gates/publication_20_50_decision.tsv",
    ".github/workflows/ci.yml",
]


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


def main() -> int:
    failures: list[str] = []
    for rel in REQUIRED_FILES:
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
                failures.append(f"large data file should not be committed directly: {file}")

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

    print("Release audit passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
