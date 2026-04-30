from __future__ import annotations

"""Build the journal-compliance audit for the RMTGuard submission route.

Author: RMTGuard development team
Date: 2026-04-30
Purpose: Convert Nature Methods/Nature Portfolio author requirements into
local pass/block gates for a reproducible methods submission package.
Data source: Local gate, release, dataset, and manuscript evidence tables.
Method notes: This is a compliance audit, not a prediction or guarantee of
journal acceptance.
"""

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "submission"
AUDIT_TSV = OUT_DIR / "nature_methods_compliance_audit.tsv"
AUDIT_MD = OUT_DIR / "nature_methods_compliance_audit.md"

GATE_EVIDENCE = ROOT / "results" / "gates" / "gate_evidence.tsv"
RELEASE_READINESS = ROOT / "results" / "release" / "release_readiness.tsv"
PRESUBMISSION_GATEKEEPER = OUT_DIR / "presubmission_gatekeeper.tsv"
DATASET_MANIFEST = ROOT / "metadata" / "datasets.tsv"
CLAIM_MATRIX = ROOT / "results" / "manuscript" / "claim_evidence_matrix.tsv"

SOURCE_CHECK_DATE = "2026-04-30"
SOURCE_URLS = {
    "aims_scope": "https://www.nature.com/nmeth/aims",
    "content_types": "https://www.nature.com/nmeth/content",
    "submission_guidelines": "https://www.nature.com/nmeth/submission-guidelines",
    "reporting_standards": "https://www.nature.com/nature-portfolio/editorial-policies/reporting-standards",
}


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


def _evidence_path(path: Path) -> str:
    if path.exists():
        return _rel(path)
    return f"{_rel(path)} (missing)"


def _row(
    check_id: str,
    status: str,
    requirement: str,
    local_evidence: Path | str,
    source_url: str,
    source_basis: str,
    blocking_item: str,
    next_action: str,
) -> dict[str, str]:
    evidence = _evidence_path(local_evidence) if isinstance(local_evidence, Path) else local_evidence
    return {
        "check_id": check_id,
        "status": status,
        "requirement": requirement,
        "local_evidence": evidence,
        "source_url": source_url,
        "source_checked_date": SOURCE_CHECK_DATE,
        "source_basis": source_basis,
        "blocking_item": blocking_item,
        "next_action": next_action,
    }


def _all_present(paths: list[Path]) -> bool:
    return all(path.exists() and path.stat().st_size > 0 for path in paths)


def _scientific_gates_pass(gate_status: dict[str, str]) -> bool:
    scientific = [gate for gate in gate_status if gate != "software_release"]
    return bool(scientific) and all(gate_status.get(gate) == "pass" for gate in scientific)


def _release_checks_pass(release_status: dict[str, str], checks: list[str]) -> bool:
    return all(release_status.get(check) == "pass" for check in checks)


def build_compliance_rows(
    gate_rows: list[dict[str, str]],
    release_rows: list[dict[str, str]],
    presubmission_rows: list[dict[str, str]],
    dataset_rows: list[dict[str, str]],
    claim_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    gate_status = _status_map(gate_rows, "gate_id")
    release_status = _status_map(release_rows, "check_id")
    presubmission_status = _status_map(presubmission_rows, "check_id")

    scientific_pass = _scientific_gates_pass(gate_status)
    method_comparison_pass = all(
        gate_status.get(gate) == "pass"
        for gate in ["real_dataset_count", "stability_advantage", "annotation_noninferiority"]
    )
    biological_application_pass = gate_status.get("pdac_tme_interpretability") == "pass"
    data_public = bool(dataset_rows) and all("private" not in row.get("github_policy", "").lower() for row in dataset_rows)
    local_reproducibility_pass = _release_checks_pass(
        release_status,
        [
            "local_release_audit",
            "ci_workflow",
            "dockerfile",
            "figure_source_data_manifest",
            "manuscript_evidence_package",
            "publication_20_50_plan",
        ],
    )
    repo_release_pass = _release_checks_pass(
        release_status,
        ["repository_url", "github_remote", "github_release_tag"],
    )
    doi_pass = release_status.get("zenodo_doi") == "pass"
    claim_boundary_pass = (
        gate_status.get("diagnostic_no_call_validation") == "pass"
        and bool(claim_rows)
        and any("diagnostic no-call" in row.get("allowed_wording", "").lower() for row in claim_rows)
    )
    nature_gate_pass = presubmission_status.get("nature_methods_submission_ready") == "pass"

    rows = [
        _row(
            "nature_methods_scope_fit",
            "pass" if scientific_pass else "blocked",
            "Nature Methods must fit novel life-science methods with immediate practical relevance and broad methodological interest.",
            GATE_EVIDENCE,
            SOURCE_URLS["aims_scope"],
            "Nature Methods lists novel methods, single-cell methods, and computational/statistical/ML methods for biological data as in scope.",
            "none" if scientific_pass else "scientific_gates_not_all_pass",
            "Keep RMTGuard framed as a random-matrix noise-control method, not a generic autotuning wrapper.",
        ),
        _row(
            "article_content_type_fit",
            "pass" if scientific_pass else "blocked",
            "A Nature Methods Article should describe a novel method or tool with technical description, validation, reproducibility, general applicability, and new-biology potential.",
            CLAIM_MATRIX,
            SOURCE_URLS["content_types"],
            "Nature Methods Article content type requires strong validation data demonstrating performance, reproducibility, general applicability, and potential for discovering new biology.",
            "none" if scientific_pass else "method_validation_incomplete",
            "Preserve full technical descriptions, diagnostics schema, ablations, benchmarks, and PDAC/TME use case in the manuscript.",
        ),
        _row(
            "performance_comparison",
            "pass" if method_comparison_pass else "blocked",
            "Methods papers need performance evidence against available approaches.",
            GATE_EVIDENCE,
            SOURCE_URLS["aims_scope"],
            "Nature Methods says method descriptions must include results illustrating performance compared with available approaches.",
            "none" if method_comparison_pass else "comparison_or_stability_gate_incomplete",
            "Do not claim broad fixed-PC superiority; keep the callability-aware stability/no-call wording.",
        ),
        _row(
            "biological_application",
            "pass" if biological_application_pass else "blocked",
            "The method must be accompanied by an application to an important biological question.",
            GATE_EVIDENCE,
            SOURCE_URLS["aims_scope"],
            "Nature Methods requires strong validation plus application to an important biological question.",
            "none" if biological_application_pass else "pdac_tme_showcase_incomplete",
            "Keep PDAC/TME as a public biological use case unless stronger disease mechanism evidence is added.",
        ),
        _row(
            "data_availability",
            "pass" if data_public else "blocked",
            "Nature Portfolio articles must include transparent data availability for the minimum dataset required to verify and extend claims.",
            DATASET_MANIFEST,
            SOURCE_URLS["reporting_standards"],
            "Nature Portfolio requires a Data Availability statement and access conditions for the minimum dataset.",
            "none" if data_public else "dataset_manifest_missing_or_private_policy",
            "Keep large matrices out of Git; provide public accessions, download scripts, checksums, and source-data tables.",
        ),
        _row(
            "code_availability",
            "pass" if repo_release_pass else "blocked",
            "Central custom code or algorithms must be available to editors/reviewers and described in a Code Availability statement.",
            RELEASE_READINESS,
            SOURCE_URLS["reporting_standards"],
            "Nature Portfolio requires access details for central custom code or mathematical algorithms under Code availability.",
            "none" if repo_release_pass else "github_repository_or_release_missing",
            "Create the real GitHub repository, configure remote, push the tag, and replace placeholder repository URLs.",
        ),
        _row(
            "code_doi_repository",
            "pass" if doi_pass else "blocked",
            "Upon publication, custom code should be released in a repeatable form; DOI-minting repositories are preferred.",
            RELEASE_READINESS,
            SOURCE_URLS["reporting_standards"],
            "Nature Portfolio identifies DOI-minting repositories such as Zenodo or Code Ocean as best practice for code release.",
            "none" if doi_pass else "zenodo_doi_missing",
            "Archive the GitHub Release with Zenodo and record the DOI in `.zenodo.json`, `CITATION.cff`, and Code Availability text.",
        ),
        _row(
            "reproducibility_package",
            "pass" if local_reproducibility_pass else "blocked",
            "The submission package must let readers replicate and build upon the claims.",
            RELEASE_READINESS,
            SOURCE_URLS["reporting_standards"],
            "Nature Portfolio states that a core publication principle is enabling others to replicate and build upon published claims.",
            "none" if local_reproducibility_pass else "local_reproducibility_artifacts_missing",
            "Keep CI, Docker, tests, figure source data, release manifests, and source bundle synchronized.",
        ),
        _row(
            "reporting_summary",
            "pending_manual",
            "Life-sciences research sent for review may require a completed reporting summary.",
            "manual Nature Portfolio reporting summary form",
            SOURCE_URLS["reporting_standards"],
            "Nature Portfolio reporting standards require reporting-summary details where relevant for life-science research articles sent for review.",
            "reporting_summary_form_not_completed",
            "Complete the official Nature Portfolio reporting summary during final submission assembly.",
        ),
        _row(
            "claim_boundary",
            "pass" if claim_boundary_pass else "blocked",
            "Claims must not exceed the actual benchmark evidence and no-call boundaries.",
            CLAIM_MATRIX,
            SOURCE_URLS["submission_guidelines"],
            "Nature Methods submission guidance requires accurate, readable manuscripts and policy compliance before submission.",
            "none" if claim_boundary_pass else "claim_boundary_missing",
            "Keep PBMC68k as diagnostic no-call and avoid unsupported broad superiority claims.",
        ),
        _row(
            "nature_methods_submission_ready",
            "pass" if nature_gate_pass and repo_release_pass and doi_pass else "blocked",
            "Final Nature Methods submission readiness requires scientific gates plus external code/release objects.",
            PRESUBMISSION_GATEKEEPER,
            SOURCE_URLS["submission_guidelines"],
            "Nature Methods directs authors to verify journal fit, content type, policies, completeness, and initial formatting before submission.",
            "none" if nature_gate_pass and repo_release_pass and doi_pass else "external_release_or_presubmission_gate_blocked",
            "Do not submit until the compliance audit has no blocked rows and manual reporting-summary items are completed.",
        ),
    ]
    return rows


def _overall_decision(rows: list[dict[str, str]]) -> str:
    if any(row["status"] == "blocked" for row in rows):
        return "not_submission_ready"
    if any(row["status"].startswith("pending") for row in rows):
        return "submission_package_pending_manual_items"
    return "submission_ready_for_editorial_review_not_acceptance_guaranteed"


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    blocked = [row for row in rows if row["status"] == "blocked"]
    pending = [row for row in rows if row["status"].startswith("pending")]
    decision = _overall_decision(rows)
    lines = [
        "# Nature Methods Compliance Audit",
        "",
        "This file is generated by `python scripts/build_journal_compliance_audit.py`.",
        "",
        "## Decision",
        "",
        f"- Current decision: `{decision}`.",
        "- Acceptance guarantee: `not possible`; this audit enforces evidence, release, and policy gates only.",
        "- Target route: `Nature Methods first` only after blocked rows are resolved.",
        "- Fallback route: `Genome Biology or Cell Genomics` if method breadth is judged insufficient after release completion.",
        "",
        "## Blocking Items",
        "",
    ]
    if blocked:
        lines.extend(f"- `{row['check_id']}`: {row['blocking_item']} -> {row['next_action']}" for row in blocked)
    else:
        lines.append("- none")
    lines.extend(["", "## Pending Manual Items", ""])
    if pending:
        lines.extend(f"- `{row['check_id']}`: {row['next_action']}" for row in pending)
    else:
        lines.append("- none")
    lines.extend(["", "## Audit Rows", ""])
    for row in rows:
        lines.extend(
            [
                f"### {row['check_id']}",
                "",
                f"- Status: `{row['status']}`",
                f"- Requirement: {row['requirement']}",
                f"- Evidence: `{row['local_evidence']}`",
                f"- Source: {row['source_url']}",
                f"- Source checked date: `{row['source_checked_date']}`",
                f"- Next action: {row['next_action']}",
                "",
            ]
        )
    return lines


def build_outputs() -> list[dict[str, str]]:
    rows = build_compliance_rows(
        _read_tsv(GATE_EVIDENCE),
        _read_tsv(RELEASE_READINESS),
        _read_tsv(PRESUBMISSION_GATEKEEPER),
        _read_tsv(DATASET_MANIFEST),
        _read_tsv(CLAIM_MATRIX),
    )
    _write_tsv(
        AUDIT_TSV,
        rows,
        [
            "check_id",
            "status",
            "requirement",
            "local_evidence",
            "source_url",
            "source_checked_date",
            "source_basis",
            "blocking_item",
            "next_action",
        ],
    )
    _write_text(AUDIT_MD, build_markdown(rows))
    return rows


def main() -> int:
    rows = build_outputs()
    print(_rel(AUDIT_TSV))
    print(_rel(AUDIT_MD))
    print(f"decision\t{_overall_decision(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
