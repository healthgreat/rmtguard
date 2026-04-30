from __future__ import annotations

"""Build an editorial desk-reject and transfer-risk audit for RMTGuard.

Author: RMTGuard development team
Date: 2026-04-30
Purpose: Convert reviewer risks, compliance blockers, and journal-route
decisions into a pre-submission editorial risk register.
Data source: Reviewer objection matrix, Nature Methods compliance audit,
publication route table, and execution board.
Method notes: This is a risk-control artifact. It cannot predict or guarantee
journal acceptance.
"""

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_TSV = ROOT / "results" / "submission" / "editorial_risk_audit.tsv"
OUT_MD = ROOT / "docs" / "editorial_risk_audit.md"

OBJECTIONS = ROOT / "results" / "manuscript" / "reviewer_objection_matrix.tsv"
COMPLIANCE = ROOT / "results" / "submission" / "nature_methods_compliance_audit.tsv"
JOURNAL_ROUTE = ROOT / "results" / "gates" / "publication_20_50_decision.tsv"
EXECUTION_BOARD = ROOT / "results" / "submission" / "publication_execution_board.tsv"
PDAC_DEPTH_AUDIT = ROOT / "results" / "pdac_tme" / "pdac_showcase_depth_audit.tsv"
PHASE1_RUNNER = ROOT / "benchmarks" / "run_phase1_benchmark.py"
STABILITY_RUNNER = ROOT / "benchmarks" / "run_stability_benchmark.py"
SEURAT_RUNNER = ROOT / "benchmarks" / "run_seurat_baseline.R"
PHASE1_SUMMARY = ROOT / "results" / "phase1_benchmarks" / "phase1_benchmark_summary.tsv"
STABILITY_SUMMARY = ROOT / "results" / "stability_benchmarks" / "stability_summary.tsv"
SEURAT_BASELINE_RESULT = ROOT / "results" / "phase1_benchmarks" / "pbmc3k_10x_seurat_baseline.tsv"
STABILITY_UTILITY = ROOT / "results" / "stability_benchmarks" / "stability_utility_tradeoff.tsv"
PC_RULE_BASELINES = {"elbow_rule", "parallel_analysis", "jackstraw_like"}


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


def _write_tsv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _status_map(rows: list[dict[str, str]], key: str) -> dict[str, str]:
    return {row.get(key, ""): row.get("status", "pending") for row in rows if row.get(key)}


def _row(
    risk_id: str,
    risk_level: str,
    status: str,
    editorial_risk: str,
    evidence_path: Path | str,
    mitigation: str,
    go_no_go_rule: str,
    fallback_route: str,
) -> dict[str, str]:
    evidence = _rel(evidence_path) if isinstance(evidence_path, Path) else evidence_path
    return {
        "risk_id": risk_id,
        "risk_level": risk_level,
        "status": status,
        "editorial_risk": editorial_risk,
        "evidence_path": evidence,
        "mitigation": mitigation,
        "go_no_go_rule": go_no_go_rule,
        "fallback_route": fallback_route,
    }


def _objection(rows: list[dict[str, str]], objection_id: str) -> dict[str, str]:
    return next((row for row in rows if row.get("objection_id") == objection_id), {})


def _journal(rows: list[dict[str, str]], journal: str) -> dict[str, str]:
    return next((row for row in rows if row.get("journal") == journal), {})


def _text_contains_all(path: Path, needles: set[str]) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return all(needle in text for needle in needles)


def _summary_methods(path: Path) -> set[str]:
    return {row.get("method", "") for row in _read_tsv(path) if row.get("method")}


def _baseline_support_status(
    phase1_runner: Path = PHASE1_RUNNER,
    stability_runner: Path = STABILITY_RUNNER,
    seurat_runner: Path = SEURAT_RUNNER,
    phase1_summary: Path = PHASE1_SUMMARY,
    stability_summary: Path = STABILITY_SUMMARY,
    seurat_result: Path = SEURAT_BASELINE_RESULT,
) -> dict[str, str]:
    pc_rule_scripts_ready = _text_contains_all(phase1_runner, PC_RULE_BASELINES) and _text_contains_all(stability_runner, PC_RULE_BASELINES)
    seurat_script_ready = seurat_runner.exists()
    phase1_methods = _summary_methods(phase1_summary)
    stability_methods = _summary_methods(stability_summary)
    seurat_methods = _summary_methods(seurat_result)
    pc_rule_results_ready = PC_RULE_BASELINES.issubset(phase1_methods) and PC_RULE_BASELINES.issubset(stability_methods)
    seurat_results_ready = any(method.startswith("seurat_v5_like") for method in seurat_methods)

    if pc_rule_scripts_ready and seurat_script_ready and pc_rule_results_ready and seurat_results_ready:
        return {
            "status": "controlled",
            "mitigation": "Maintain Seurat, elbow, permutation PCA, and JackStraw-like baselines in final benchmark tables.",
            "go_no_go": "Baseline sufficiency can be treated as controlled only while final result tables include the expanded baselines.",
        }
    if pc_rule_scripts_ready and seurat_script_ready:
        return {
            "status": "implementation_ready_not_benchmarked",
            "mitigation": "PC-rule and Seurat baseline runners exist; rerun Phase 1 and stability benchmarks so final tables include elbow, permutation PCA, JackStraw-like, and Seurat rows.",
            "go_no_go": "Do not call baseline sufficiency resolved until the generated benchmark TSVs include the expanded baselines.",
        }
    if pc_rule_scripts_ready:
        return {
            "status": "partial_implementation",
            "mitigation": "PC-rule baselines exist; add a Seurat baseline runner and rerun the final benchmark tables.",
            "go_no_go": "Do not submit until missing Seurat and expanded baseline result rows are either added or explicitly justified.",
        }
    return {
        "status": "active_risk",
        "mitigation": "Add Seurat, elbow, permutation PCA, and JackStraw-like baselines where feasible.",
        "go_no_go": "Before final submission, either add the missing baseline table or explicitly justify why fixed-PC/Scanpy-like baselines define the scoped claim.",
    }


def _pdac_depth_status(path: Path = PDAC_DEPTH_AUDIT) -> dict[str, str]:
    rows = _read_tsv(path)
    if not rows:
        return {
            "status": "active_risk",
            "mitigation": "Use PDAC/TME as public workflow validation, not disease-mechanism proof.",
            "go_no_go": "Do not describe CAF/fibroblast discovery unless stronger marker/pathway/external validation is added.",
        }
    blocking = {row.get("status") for row in rows} & {"fail", "needs_review"}
    if blocking:
        return {
            "status": "active_risk",
            "mitigation": "Resolve failed PDAC/TME depth-audit rows or keep the showcase as a narrow supplemental use case.",
            "go_no_go": "Do not submit a main-text PDAC/TME claim while the depth audit has fail or needs_review rows.",
        }
    return {
        "status": "controlled_with_public_use_case",
        "mitigation": "Keep PDAC/TME as a public immune/ductal-context workflow validation with explicit forbidden-claim boundaries.",
        "go_no_go": "PDAC/TME can remain in the manuscript only as a bounded public use case, not a disease-mechanism claim.",
    }


def build_rows(
    objections: list[dict[str, str]],
    compliance_rows: list[dict[str, str]],
    journal_rows: list[dict[str, str]],
    execution_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    compliance = _status_map(compliance_rows, "check_id")
    execution = _status_map(execution_rows, "step_id")
    nature = _journal(journal_rows, "Nature Methods")
    nbt = _journal(journal_rows, "Nature Biotechnology")
    gb = _journal(journal_rows, "Genome Biology")

    software_blocked = compliance.get("code_availability") == "blocked" or compliance.get("code_doi_repository") == "blocked"
    submission_blocked = compliance.get("nature_methods_submission_ready") == "blocked"
    manual_reporting = compliance.get("reporting_summary", "").startswith("pending")
    public_release_blocked = any(
        execution.get(step) == "blocked_external"
        for step in ["02_create_public_github_repository", "04_push_source_and_tag", "05_create_github_release_and_zenodo_doi"]
    )

    stability = _objection(objections, "stability_advantage")
    novelty = _objection(objections, "method_novelty")
    baselines = _objection(objections, "benchmark_baselines")
    pdac = _objection(objections, "pdac_biology_depth")
    baseline_support = _baseline_support_status()
    pdac_depth = _pdac_depth_status()

    rows = [
        _row(
            "software_release_desk_reject",
            "blocking",
            "blocked" if software_blocked or public_release_blocked else "controlled",
            "A methods manuscript can be desk-rejected if central custom code is not publicly available and DOI-archived.",
            COMPLIANCE,
            "Complete public GitHub repository, push the release tag, create GitHub Release, archive with Zenodo, and rerun finalizer.",
            "Do not submit while code_availability or code_doi_repository is blocked.",
            "No fallback journal should receive the manuscript before this is resolved.",
        ),
        _row(
            "reporting_summary_manual_blocker",
            "major",
            "pending_manual" if manual_reporting else "controlled",
            "Nature Portfolio may require a completed reporting summary for life-science research sent for review.",
            COMPLIANCE,
            "Use the reporting-summary draft worksheet and have the corresponding author verify the official form.",
            "Do not submit until official reporting-summary answers are author-verified.",
            "Same requirement likely follows to other Nature Portfolio journals.",
        ),
        _row(
            "method_novelty_editorial_fit",
            "high",
            "active_risk",
            novelty.get("likely_reviewer_concern", "The method could be perceived as automatic parameter tuning rather than a new method."),
            OBJECTIONS,
            novelty.get("response_strategy", "Center random-matrix noise control, diagnostic contracts, and false-signal suppression."),
            "Submit to Nature Methods only if the abstract, cover letter, and Figure 1 foreground the RMT noise-control primitive.",
            f"If novelty is judged too narrow, downgrade to {gb.get('journal', 'Genome Biology')} style workflow/resource framing.",
        ),
        _row(
            "stability_claim_scope",
            "high",
            "controlled_with_narrow_wording" if stability.get("current_status") == "pass" else "active_risk",
            stability.get("likely_reviewer_concern", "Stability advantage could be overstated."),
            STABILITY_UTILITY if STABILITY_UTILITY.exists() else OBJECTIONS,
            stability.get("response_strategy", "Keep the benchmark claim callability-aware and preserve diagnostic no-call wording.")
            + " Use the stability-utility tradeoff audit to separate reproducibility gains from annotation loss.",
            "Do not claim broad fixed-PC superiority; Nature Methods submission must use callability-aware wording and disclose comparator tradeoffs.",
            "If editors reject the no-call framing, transfer to a genomics workflow journal rather than inflating the claim.",
        ),
        _row(
            "baseline_sufficiency",
            "medium",
            baseline_support["status"],
            baselines.get("likely_reviewer_concern", "Baselines may be viewed as insufficient for a top methods journal."),
            OBJECTIONS,
            baseline_support.get("mitigation") or baselines.get("response_strategy", "Add Seurat, elbow, permutation PCA, and JackStraw-like baselines where feasible."),
            baseline_support["go_no_go"],
            "If baseline expansion is infeasible, keep Nature Methods as a presubmission attempt only and prepare fallback.",
        ),
        _row(
            "biological_application_depth",
            "medium",
            pdac_depth["status"],
            pdac.get("likely_reviewer_concern", "PDAC/TME showcase may be too shallow for a top methods paper."),
            PDAC_DEPTH_AUDIT,
            pdac_depth["mitigation"],
            pdac_depth["go_no_go"],
            "If biological application is judged too light, recast as reproducible public-data software benchmark.",
        ),
        _row(
            "strict_20_50_route",
            "strategic",
            "not_ready" if nature.get("current_readiness") != "ready" else "ready_for_author_review",
            "The strict 20-50 JIF route is currently Nature Methods first; Nature Biotechnology is stretch-only and Genome Biology is outside the strict band.",
            JOURNAL_ROUTE,
            "Keep Nature Methods as first target only after software release and official reporting summary are complete.",
            "Do not call Genome Biology a 20-50 JIF fallback under the current verified table.",
            f"Nature Biotechnology: {nbt.get('fit_for_current_project', 'stretch_only')}; Genome Biology: {gb.get('fit_for_current_project', 'fallback_if_strict_if_relaxed')}.",
        ),
        _row(
            "acceptance_guarantee_boundary",
            "policy",
            "controlled",
            "No local workflow can guarantee acceptance by a 20-50 JIF journal.",
            "conversation policy; generated gate artifacts",
            "Use gate discipline, claim boundaries, release evidence, and fallback routing instead of acceptance promises.",
            "Never write 'guaranteed publication' in manuscript, cover letter, README, or response documents.",
            "If the target rejects, route by evidence strength rather than changing claims post hoc.",
        ),
    ]
    return rows


def overall_status(rows: list[dict[str, str]]) -> str:
    if any(row["status"] == "blocked" for row in rows):
        return "blocked_before_editorial_submission"
    not_ready_statuses = {"active_risk", "pending_manual", "partial_implementation", "implementation_ready_not_benchmarked"}
    if any(row["status"] in not_ready_statuses for row in rows):
        return "not_ready_risk_active"
    return "ready_for_author_editorial_review_not_acceptance_guaranteed"


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    blocked = [row for row in rows if row["status"] == "blocked"]
    active_statuses = {"active_risk", "pending_manual", "partial_implementation", "implementation_ready_not_benchmarked"}
    active = [row for row in rows if row["status"] in active_statuses]
    lines = [
        "# Editorial Risk Audit",
        "",
        "This file is generated by `python scripts/build_editorial_risk_audit.py`.",
        "",
        "## Current Decision",
        "",
        f"- Overall status: `{overall_status(rows)}`.",
        "- Acceptance guarantee: `impossible`; this audit only controls desk-reject and overclaim risk.",
        "- Active first target: `Nature Methods` after external release and author-verified reporting summary.",
        "",
        "## Blocking Risks",
        "",
    ]
    if blocked:
        lines.extend(f"- `{row['risk_id']}`: {row['go_no_go_rule']}" for row in blocked)
    else:
        lines.append("- none")
    lines.extend(["", "## Active Risks", ""])
    if active:
        lines.extend(f"- `{row['risk_id']}` ({row['risk_level']}): {row['mitigation']}" for row in active)
    else:
        lines.append("- none")
    lines.extend(["", "## Risk Rows", ""])
    for row in rows:
        lines.extend(
            [
                f"### {row['risk_id']}",
                "",
                f"- Risk level: `{row['risk_level']}`",
                f"- Status: `{row['status']}`",
                f"- Editorial risk: {row['editorial_risk']}",
                f"- Evidence: `{row['evidence_path']}`",
                f"- Mitigation: {row['mitigation']}",
                f"- Go/no-go rule: {row['go_no_go_rule']}",
                f"- Fallback route: {row['fallback_route']}",
                "",
            ]
        )
    return lines


def build_outputs() -> list[dict[str, str]]:
    rows = build_rows(_read_tsv(OBJECTIONS), _read_tsv(COMPLIANCE), _read_tsv(JOURNAL_ROUTE), _read_tsv(EXECUTION_BOARD))
    _write_tsv(
        OUT_TSV,
        rows,
        ["risk_id", "risk_level", "status", "editorial_risk", "evidence_path", "mitigation", "go_no_go_rule", "fallback_route"],
    )
    _write_text(OUT_MD, build_markdown(rows))
    return rows


def main() -> int:
    rows = build_outputs()
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print(f"overall_status\t{overall_status(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
