from __future__ import annotations

"""Export the current RMTGuard manuscript package for external review.

Author: RMTGuard development team
Date: 2026-05-01
Purpose: Combine the current manuscript drafts, claim-evidence tables,
submission gates, release status, and editorial risk controls into one
Markdown packet that can be sent to another model or collaborator for critique.
Data source: Existing manuscript, docs, and generated submission/release tables.
Method notes: Binary release assets are listed with hashes only. This exporter
does not change scientific claims or submission gates.
"""

import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "manuscript" / "current_article_external_review_packet.md"
PACKAGE_MANIFEST = (
    ROOT
    / "results"
    / "submission"
    / "nature_methods_presubmission_package_manifest.tsv"
)

TEXT_SUFFIXES = {
    ".cff",
    ".csv",
    ".json",
    ".md",
    ".txt",
    ".toml",
    ".tsv",
    ".yaml",
    ".yml",
}

CORE_ARTICLE_FILES = [
    "manuscript/README.md",
    "manuscript/title_page_author_metadata.md",
    "manuscript/nature_methods_outline.md",
    "manuscript/figure_plan.md",
    "manuscript/nature_methods_presubmission_draft.md",
    "manuscript/abstract_draft.md",
    "manuscript/cover_letter_draft.md",
    "manuscript/submission_readiness.md",
    "manuscript/top_paper_claim_ladder.md",
    "manuscript/nature_methods_presubmission_inquiry.md",
    "manuscript/reviewer_response_playbook.md",
    "manuscript/figure_claim_checklist.md",
    "manuscript/genome_biology_fallback_outline.md",
    "manuscript/genome_biology_conversion_draft.md",
    "manuscript/genome_biology_cover_letter_draft.md",
    "manuscript/genome_biology_reframed_abstract.md",
    "manuscript/nature_methods_hold_statement.md",
    "manuscript/reviewer_defense_response_draft.md",
    "manuscript/code_availability_finalization_draft.md",
]

ADDITIONAL_REVIEW_FILES = [
    "PROJECT_STATUS.md",
    "docs/benchmark_plan.md",
    "docs/statistical_analysis_plan.md",
    "docs/data_and_code_availability_template.md",
    "docs/publication_strategy.md",
    "docs/publication_20_50_rescue_plan.md",
    "docs/top_paper_route_package.md",
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
    "docs/submission_guard.md",
    "docs/claim_traceability.md",
    "docs/claim_boundary_lint.md",
    "docs/editorial_risk_audit.md",
    "docs/method_risk_log.md",
    "docs/pdac_tme_showcase_depth.md",
    "docs/stability_gate_diagnostics.md",
    "docs/no_call_benchmark.md",
    "docs/no_call_decision_map.md",
    "docs/publication_visual_asset_audit.md",
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
    "docs/public_release_blocker_report.md",
    "docs/publication_execution_board.md",
    "docs/nature_reporting_summary_draft.md",
    "docs/external_release_plan.md",
    "docs/github_release_checklist.md",
    "src/rmtguard/__init__.py",
    "src/rmtguard/__main__.py",
    "src/rmtguard/core.py",
    "src/rmtguard/rmt.py",
    "src/rmtguard/preprocess.py",
    "src/rmtguard/cluster.py",
    "src/rmtguard/scanpy_api.py",
    "src/rmtguard/cli.py",
    "src/rmtguard/simulate.py",
    "benchmarks/run_seurat_matched_baseline.R",
    "metadata/author_metadata.tsv",
    "metadata/credit_roles.tsv",
    "metadata/orcid_search_evidence.tsv",
    "scripts/export_seurat_mtx_inputs.py",
    "scripts/build_seurat_matched_baseline_report.py",
    "scripts/build_seurat_jackstraw_feasibility_report.py",
    "results/gates/gate_report.tsv",
    "results/gates/gate_evidence.tsv",
    "results/manuscript/claim_evidence_matrix.tsv",
    "results/manuscript/storyline_panel_map.tsv",
    "results/manuscript/reviewer_objection_matrix.tsv",
    "results/submission/top_paper_route_decision.tsv",
    "results/submission/editorial_presubmission_packet.tsv",
    "results/submission/submission_guard.tsv",
    "results/submission/external_review_feedback_triage.tsv",
    "results/submission/external_review_action_plan.tsv",
    "results/submission/post_feedback_journal_route_gate.tsv",
    "results/submission/route_reframe_decision.tsv",
    "results/submission/genome_biology_transfer_checklist.tsv",
    "results/submission/reviewer_defense_matrix.tsv",
    "results/release/author_release_execution_checklist.tsv",
    "results/callability/no_call_decision_map.tsv",
    "results/figures/source_data/figure3_callability_decision_map.tsv",
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
    "results/submission/presubmission_gatekeeper.tsv",
    "results/release/release_readiness.tsv",
    "results/release/public_release_blockers.tsv",
    "figures/manuscript/rendered_figure_manifest.tsv",
    "results/tables/manuscript/table1_submission_gate_summary.tsv",
    "results/tables/manuscript/table2_public_benchmark_summary.tsv",
    "results/tables/manuscript/table3_external_review_action_plan.tsv",
    "results/tables/manuscript/publication_table_manifest.tsv",
    "results/tables/manuscript/rmtguard_publication_tables.docx",
]


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _read_manifest_paths() -> tuple[list[str], list[dict[str, str]]]:
    if not PACKAGE_MANIFEST.exists():
        return [], []
    with PACKAGE_MANIFEST.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    return [
        row["path"] for row in rows if row.get("package_status") == "included"
    ], rows


def _dedupe(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for path in paths:
        normalized = path.replace("\\", "/")
        if normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


def _fence_language(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".md":
        return "markdown"
    if suffix == ".tsv":
        return "tsv"
    if suffix == ".csv":
        return "csv"
    if suffix == ".toml":
        return "toml"
    if suffix in {".yml", ".yaml"}:
        return "yaml"
    if suffix == ".json":
        return "json"
    return "text"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").rstrip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_packet() -> list[str]:
    manifest_paths, manifest_rows = _read_manifest_paths()
    paths = _dedupe(CORE_ARTICLE_FILES + ADDITIONAL_REVIEW_FILES + manifest_paths)

    lines = [
        "# RMTGuard Current Article External Review Packet",
        "",
        "Generated by `python scripts/export_current_article_review_packet.py`.",
        "",
        "## How To Review This Packet",
        "",
        "Please critique this as a current, evidence-bounded manuscript package, not as an accepted paper.",
        "Current target route: Nature Methods first, Genome Biology fallback.",
        "Current submission guard: `do_not_submit` until scientific wording and public GitHub/Zenodo release gates are resolved.",
        "Acceptance guarantee: `impossible`.",
        "",
        "Please focus on:",
        "",
        "1. Whether the method framing is novel enough for Nature Methods.",
        "2. Which claims are too strong or insufficiently supported.",
        "3. What additional analyses would most improve acceptance probability.",
        "4. Whether Genome Biology is a better current route than Nature Methods.",
        "5. Whether Figures 1-5 and the PDAC/TME showcase are convincing.",
        "6. Whether code/data/release wording satisfies reproducibility expectations.",
        "",
        "## Included Text Files",
        "",
    ]
    text_paths: list[str] = []
    binary_rows: list[dict[str, str]] = []
    missing_paths: list[str] = []
    for path_text in paths:
        path = ROOT / path_text
        if not path.exists():
            missing_paths.append(path_text)
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            text_paths.append(path_text)
        else:
            row = next(
                (item for item in manifest_rows if item.get("path") == path_text), {}
            )
            binary_rows.append(
                {
                    "path": path_text,
                    "size_bytes": row.get("size_bytes", str(path.stat().st_size)),
                    "sha256": row.get("sha256") or _sha256(path),
                }
            )

    for path_text in text_paths:
        path = ROOT / path_text
        lines.extend(
            [
                f"- `{path_text}` ({path.stat().st_size} bytes)",
            ]
        )

    if binary_rows:
        lines.extend(["", "## Binary Or Non-Text Assets Listed Only", ""])
        lines.append("| path | size_bytes | sha256 |")
        lines.append("|---|---:|---|")
        for row in binary_rows:
            lines.append(
                f"| `{row['path']}` | {row['size_bytes']} | `{row['sha256']}` |"
            )

    if missing_paths:
        lines.extend(["", "## Missing Paths", ""])
        lines.extend(f"- `{path}`" for path in missing_paths)

    lines.extend(["", "## Full Text Contents", ""])
    for path_text in text_paths:
        path = ROOT / path_text
        language = _fence_language(path_text)
        lines.extend(
            [
                f"### {path_text}",
                "",
                f"```{language}",
                _read_text(path),
                "```",
                "",
            ]
        )
    return lines


def main() -> int:
    lines = build_packet()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_PATH.with_suffix(OUT_PATH.suffix + ".tmp")
    tmp.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    tmp.replace(OUT_PATH)
    print(_rel(OUT_PATH))
    print(f"bytes\t{OUT_PATH.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
