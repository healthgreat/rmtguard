from __future__ import annotations

"""Build the top-paper route package for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-01
Purpose: Convert current gates, claims, compliance rows, and release blockers
into a Nature Methods-first / Genome Biology-fallback manuscript routing
package without overclaiming.
Data source: Local generated gate, claim-evidence, compliance, editorial risk,
and release readiness tables.
Method notes: This is a manuscript-control artifact. It does not assert journal
acceptance, and it writes outputs atomically.
"""

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "submission"
MANUSCRIPT_DIR = ROOT / "manuscript"
DOCS_DIR = ROOT / "docs"

GATE_REPORT = ROOT / "results" / "gates" / "gate_report.tsv"
GATE_EVIDENCE = ROOT / "results" / "gates" / "gate_evidence.tsv"
CLAIM_MATRIX = ROOT / "results" / "manuscript" / "claim_evidence_matrix.tsv"
COMPLIANCE = OUT_DIR / "nature_methods_compliance_audit.tsv"
EDITORIAL_RISK = OUT_DIR / "editorial_risk_audit.tsv"
RELEASE_READINESS = ROOT / "results" / "release" / "release_readiness.tsv"
PUBLIC_RELEASE_BLOCKERS = ROOT / "results" / "release" / "public_release_blockers.tsv"

ROUTE_TSV = OUT_DIR / "top_paper_route_decision.tsv"
ROUTE_MD = DOCS_DIR / "top_paper_route_package.md"
GB_DRAFT = MANUSCRIPT_DIR / "genome_biology_conversion_draft.md"
CLAIM_LADDER_MD = MANUSCRIPT_DIR / "top_paper_claim_ladder.md"


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


def _status_map(
    rows: list[dict[str, str]], key_field: str, status_field: str = "status"
) -> dict[str, str]:
    return {row.get(key_field, ""): row.get(status_field, "") for row in rows}


def _claim_map(claims: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row.get("claim_id", ""): row for row in claims}


def _blocked_ids(
    statuses: dict[str, str], pass_values: set[str] | None = None
) -> list[str]:
    pass_values = pass_values or {"pass", "controlled"}
    return [
        key for key, status in statuses.items() if key and status not in pass_values
    ]


def _allowed_claim(claims: dict[str, dict[str, str]], claim_id: str) -> str:
    return claims.get(claim_id, {}).get("allowed_wording", "")


def _prohibited_claim(claims: dict[str, dict[str, str]], claim_id: str) -> str:
    return claims.get(claim_id, {}).get("prohibited_wording", "")


def _extract_ari(text: str) -> str:
    match = re.search(r"ARI(?:\s*(?:reached|=))?\s*([0-9]+(?:\.[0-9]+)?)", text)
    if match:
        return match.group(1)
    return "above the pre-specified threshold"


def _route_decision(
    gate_status: dict[str, str],
    compliance_status: dict[str, str],
    release_status: dict[str, str],
) -> tuple[str, str, str]:
    scientific_blockers = [
        gate_id
        for gate_id in ["stability_advantage", "software_release"]
        if gate_status.get(gate_id) != "pass"
    ]
    compliance_blockers = [
        check_id
        for check_id in [
            "nature_methods_scope_fit",
            "article_content_type_fit",
            "performance_comparison",
            "code_availability",
            "code_doi_repository",
            "nature_methods_submission_ready",
        ]
        if compliance_status.get(check_id) != "pass"
    ]
    release_blockers = [
        check_id
        for check_id in [
            "repository_url",
            "github_remote",
            "github_release_tag",
            "zenodo_doi",
        ]
        if release_status.get(check_id) != "pass"
    ]
    all_blockers = scientific_blockers + compliance_blockers + release_blockers
    if not all_blockers:
        return (
            "submission_candidate",
            "none",
            "Proceed to author-verified Nature Methods presubmission checks.",
        )
    return (
        "hold_pre_submission",
        ";".join(dict.fromkeys(all_blockers)),
        "Resolve software release and keep the benchmark claim callability-aware before any Nature Methods submission.",
    )


def build_route_rows(
    gates: list[dict[str, str]],
    claims: list[dict[str, str]],
    compliance: list[dict[str, str]],
    release: list[dict[str, str]],
    public_release_blockers: list[dict[str, str]],
) -> list[dict[str, str]]:
    gate_status = _status_map(gates, "gate_id")
    compliance_status = _status_map(compliance, "check_id")
    release_status = _status_map(release, "check_id")
    blocker_status = _status_map(public_release_blockers, "blocker_id")
    claims_by_id = _claim_map(claims)

    nm_decision, nm_blockers, nm_next = _route_decision(
        gate_status, compliance_status, release_status
    )
    software_release_done = (
        gate_status.get("software_release") == "pass"
        and release_status.get("zenodo_doi") == "pass"
    )
    scoped_claim_usable = (
        gate_status.get("diagnostic_no_call_validation") == "pass"
        and gate_status.get("annotation_noninferiority") == "pass"
    )
    gb_decision = (
        "activate_after_software_release"
        if scoped_claim_usable and not software_release_done
        else "not_ready"
    )
    if software_release_done and scoped_claim_usable:
        gb_decision = "submission_candidate_if_nature_methods_not_pursued"

    rows = [
        {
            "route_id": "nature_methods_first",
            "journal": "Nature Methods",
            "decision": nm_decision,
            "claim_frame": "Methods Article: random-matrix noise-control contract with diagnostic no-call boundaries.",
            "allowed_claims": "; ".join(
                [
                    _allowed_claim(claims_by_id, "noise_control_null"),
                    _allowed_claim(claims_by_id, "diagnostic_no_call_validation"),
                    _allowed_claim(claims_by_id, "rare_state_retention"),
                    _allowed_claim(claims_by_id, "pdac_tme_showcase"),
                ]
            ),
            "forbidden_claims": "; ".join(
                [
                    _prohibited_claim(claims_by_id, "pbmc3k_stability"),
                    _prohibited_claim(claims_by_id, "software_release"),
                ]
            ),
            "blocking_items": nm_blockers,
            "next_action": nm_next,
            "risk_level": (
                "blocking" if nm_decision != "submission_candidate" else "controlled"
            ),
            "evidence_path": ";".join(
                [_rel(GATE_REPORT), _rel(COMPLIANCE), _rel(RELEASE_READINESS)]
            ),
        },
        {
            "route_id": "genome_biology_fallback",
            "journal": "Genome Biology",
            "decision": gb_decision,
            "claim_frame": "Open genomics software and benchmark workflow for callability-aware scRNA-seq noise control.",
            "allowed_claims": "; ".join(
                [
                    _allowed_claim(claims_by_id, "public_benchmark_breadth"),
                    _allowed_claim(claims_by_id, "diagnostic_no_call_validation"),
                    _allowed_claim(claims_by_id, "annotation_noninferiority"),
                    _allowed_claim(claims_by_id, "figure_source_data"),
                ]
            ),
            "forbidden_claims": "; ".join(
                [
                    "Do not call Genome Biology a 20-50 JIF route under the current verified metrics.",
                    _prohibited_claim(claims_by_id, "pbmc3k_stability"),
                    _prohibited_claim(claims_by_id, "pdac_tme_showcase"),
                ]
            ),
            "blocking_items": (
                "software_release" if not software_release_done else "none"
            ),
            "next_action": "Complete public GitHub/Zenodo release, then submit as reproducible genomics workflow if Nature Methods remains blocked.",
            "risk_level": "major" if not software_release_done else "controlled",
            "evidence_path": ";".join(
                [_rel(CLAIM_MATRIX), _rel(PUBLIC_RELEASE_BLOCKERS)]
            ),
        },
        {
            "route_id": "cell_genomics_or_nature_communications_transfer",
            "journal": "Cell Genomics / Nature Communications",
            "decision": "secondary_transfer_candidate",
            "claim_frame": "Transfer route only if editors value the diagnostic no-call benchmark and public PDAC/TME use case.",
            "allowed_claims": "Use the same claim matrix; no stronger performance or disease-mechanism claim is allowed.",
            "forbidden_claims": "Do not inflate PDAC/TME into a clinical or mechanistic cancer-discovery story without new evidence.",
            "blocking_items": "software_release; editorial_fit",
            "next_action": "Keep as transfer option after Nature Methods editorial feedback; do not prepare as the primary route now.",
            "risk_level": "high",
            "evidence_path": _rel(EDITORIAL_RISK),
        },
        {
            "route_id": "bioinformatics_safety",
            "journal": "Bioinformatics / NAR Genomics and Bioinformatics",
            "decision": "reserve_not_primary",
            "claim_frame": "Software/tool paper with reproducible benchmarks and conservative limitations.",
            "allowed_claims": "All pass-status claims in the claim-evidence matrix, with the stability failure disclosed.",
            "forbidden_claims": "Do not describe this as the target route while top-paper gates are still being worked.",
            "blocking_items": "software_release",
            "next_action": "Use only if stronger journal routes reject the evidence-bounded version.",
            "risk_level": "fallback",
            "evidence_path": _rel(CLAIM_MATRIX),
        },
        {
            "route_id": "public_release_action",
            "journal": "All journals",
            "decision": "must_complete_before_submission",
            "claim_frame": "Code/data reproducibility gate.",
            "allowed_claims": "Local release package can be described as prepared, not publicly DOI-archived.",
            "forbidden_claims": _prohibited_claim(claims_by_id, "software_release"),
            "blocking_items": ";".join(
                _blocked_ids(blocker_status, pass_values={"pass", "controlled"})
            ),
            "next_action": "Create public GitHub repository, replace metadata URLs, create release tag and GitHub Release, archive with Zenodo, then rerun finalizer.",
            "risk_level": "blocking",
            "evidence_path": _rel(PUBLIC_RELEASE_BLOCKERS),
        },
    ]
    return rows


def build_route_markdown(
    rows: list[dict[str, str]],
    claims: list[dict[str, str]],
    risks: list[dict[str, str]],
) -> list[str]:
    by_route = {row["route_id"]: row for row in rows}
    active_risks = [
        row
        for row in risks
        if row.get("status")
        in {"blocked", "active_risk", "pending_manual", "not_ready"}
    ]
    lines = [
        "# Top Paper Route Package",
        "",
        "This file is generated by `python scripts/build_top_paper_route_package.py`.",
        "",
        "Acceptance guarantee: `impossible`.",
        "Controllable goal: maximize submission quality by enforcing evidence gates, claim boundaries, public release readiness, and fallback routing.",
        "",
        "## Current Routing Decision",
        "",
        f"- Nature Methods first: `{by_route['nature_methods_first']['decision']}`.",
        f"- Genome Biology fallback: `{by_route['genome_biology_fallback']['decision']}`.",
        "- Most likely eventual acceptance route under the current evidence remains Genome Biology-style reproducible genomics workflow, after public software release.",
        "- Strict Nature Methods submission must wait until the scientific and software gates no longer have blocked rows.",
        "",
        "## Route Table",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"### {row['route_id']}",
                "",
                f"- Journal: `{row['journal']}`",
                f"- Decision: `{row['decision']}`",
                f"- Risk level: `{row['risk_level']}`",
                f"- Claim frame: {row['claim_frame']}",
                f"- Blocking items: `{row['blocking_items']}`",
                f"- Next action: {row['next_action']}",
                f"- Evidence: `{row['evidence_path']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Active Editorial Risks",
            "",
        ]
    )
    if active_risks:
        for row in active_risks:
            lines.append(
                f"- `{row.get('risk_id', 'risk')}` ({row.get('status', '')}): {row.get('editorial_risk', '')}"
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Claim Sources",
            "",
            "Every manuscript sentence should trace to `results/manuscript/claim_evidence_matrix.tsv` or be marked as author-confirmed.",
            "",
        ]
    )
    for claim in claims:
        lines.extend(
            [
                f"### {claim.get('claim_id', '')}",
                "",
                f"- Status: `{claim.get('status', '')}`",
                f"- Allowed wording: {claim.get('allowed_wording', '')}",
                f"- Prohibited wording: {claim.get('prohibited_wording', '')}",
                "",
            ]
        )
    return lines


def build_claim_ladder(claims: list[dict[str, str]]) -> list[str]:
    claim_groups = {
        "Main Positive Claims": [
            "noise_control_null",
            "diagnostic_no_call_validation",
            "rare_state_retention",
            "public_benchmark_breadth",
            "annotation_noninferiority",
            "pdac_tme_showcase",
        ],
        "Guarded Or Negative Claims": ["pbmc3k_stability", "software_release"],
        "Reproducibility Claims": ["figure_source_data"],
    }
    claims_by_id = _claim_map(claims)
    lines = [
        "# Top Paper Claim Ladder",
        "",
        "This file is generated by `python scripts/build_top_paper_route_package.py`.",
        "",
        "Use this ladder when drafting abstracts, cover letters, figure legends, and reviewer responses.",
        "",
    ]
    for group, claim_ids in claim_groups.items():
        lines.extend([f"## {group}", ""])
        for claim_id in claim_ids:
            row = claims_by_id.get(claim_id)
            if not row:
                continue
            lines.extend(
                [
                    f"### {claim_id}",
                    "",
                    f"- Status: `{row.get('status', '')}`",
                    f"- Manuscript claim: {row.get('manuscript_claim', '')}",
                    f"- Allowed wording: {row.get('allowed_wording', '')}",
                    f"- Prohibited wording: {row.get('prohibited_wording', '')}",
                    f"- Evidence: `{row.get('evidence', '')}`",
                    "",
                ]
            )
    lines.extend(
        [
            "## Non-Negotiable Language Boundary",
            "",
            "Do not write `guaranteed acceptance`, `submission-ready`, `broad superiority`, or `positive PBMC68k discovery` unless the corresponding generated gates change to pass and the claim-evidence matrix is regenerated.",
        ]
    )
    return lines


def build_genome_biology_draft(
    claims: list[dict[str, str]], route_rows: list[dict[str, str]]
) -> list[str]:
    claims_by_id = _claim_map(claims)
    gb_route = next(
        row for row in route_rows if row["route_id"] == "genome_biology_fallback"
    )
    rare_ari = _extract_ari(_allowed_claim(claims_by_id, "rare_state_retention"))
    lines = [
        "# Genome Biology Conversion Draft",
        "",
        "Status: not submission-ready until the public GitHub/Zenodo release is complete.",
        "This is a fallback manuscript scaffold, not a downgrade of the scientific standards.",
        "",
        "## Working Title",
        "",
        "RMTGuard: a callability-aware random-matrix workflow for reproducible single-cell RNA-seq state discovery",
        "",
        "## Target Positioning",
        "",
        f"- Current route decision: `{gb_route['decision']}`",
        "- Article frame: genomics software, reproducible benchmark, public workflow, and transparent no-call boundaries.",
        "- Do not present Genome Biology as a strict 20-50 JIF target under the current verified metric table.",
        "",
        "## Evidence-Bounded Abstract Draft",
        "",
        "Single-cell RNA-seq workflows often require subjective choices of highly variable genes, principal components, graph neighborhoods and clustering resolution. "
        "RMTGuard addresses this reproducibility problem by treating embedding construction as a random-matrix noise-control decision rather than a purely manual tuning step. "
        "The workflow estimates spectral noise boundaries, calibrates signal-PC calls, records diagnostic no-call states when low-signal data should not be forced into clusters, and exports reproducible AnnData-compatible embeddings and diagnostics. "
        f"In synthetic stress tests, the pure-null benchmark retained one or fewer signal PCs and the rare-state benchmark reached ARI={rare_ari}. "
        "Across four public real datasets, the current benchmark supports breadth and annotation noninferiority, but it also preserves an explicit limitation: RMTGuard does not beat the strongest stability comparator on every dataset and PBMC68k/Zheng 2017 is reported as a diagnostic no-call rather than a positive discovery. "
        f"As a public biological use case, the PDAC/TME workflow recovered immune and ductal-context marker structure with external validation in GSE263733. "
        "RMTGuard is therefore best framed as a reproducible, evidence-bounded genomics workflow for noise-controlled cell-state analysis, not as a universal clustering-superiority claim.",
        "",
        "## Results Skeleton",
        "",
        "1. RMTGuard defines a random-matrix noise-control contract for scRNA-seq embeddings.",
        "2. Synthetic benchmarks support false-signal control and planted rare-state retention.",
        "3. Public benchmarks establish callability-aware behavior, annotation noninferiority, and transparent diagnostic no-calls.",
        "4. PDAC/TME public datasets provide a bounded immune/ductal-context application.",
        "5. The reproducibility package, release audit, source data, Docker, CI, and DOI archive define the software-resource contribution.",
        "",
        "## Figure Adaptation",
        "",
        "- Figure 1: workflow and diagnostic contract.",
        "- Figure 2: synthetic false-signal and rare-state tests.",
        "- Figure 3: public benchmark with callability/no-call labels and all comparator caveats.",
        "- Figure 4: PDAC/TME public use case.",
        "- Figure 5: release audit, runtime, memory, and reproducibility manifest.",
        "",
        "## Required Edits Before Use",
        "",
        "- Complete public GitHub Release and Zenodo DOI.",
        "- Replace any Nature Methods-only breakthrough language with reproducible genomics workflow language.",
        "- Keep PBMC68k as a diagnostic no-call stress case.",
        "- Keep PDAC/TME as a public use case, not a disease-mechanism discovery.",
        "- Regenerate claim-evidence and compliance artifacts after release metadata is real.",
    ]
    return lines


def main() -> int:
    gates = _read_tsv(GATE_EVIDENCE) or _read_tsv(GATE_REPORT)
    claims = _read_tsv(CLAIM_MATRIX)
    compliance = _read_tsv(COMPLIANCE)
    release = _read_tsv(RELEASE_READINESS)
    risks = _read_tsv(EDITORIAL_RISK)
    public_release_blockers = _read_tsv(PUBLIC_RELEASE_BLOCKERS)

    route_rows = build_route_rows(
        gates, claims, compliance, release, public_release_blockers
    )
    fieldnames = [
        "route_id",
        "journal",
        "decision",
        "claim_frame",
        "allowed_claims",
        "forbidden_claims",
        "blocking_items",
        "next_action",
        "risk_level",
        "evidence_path",
    ]
    _write_tsv(ROUTE_TSV, route_rows, fieldnames)
    _write_text(ROUTE_MD, build_route_markdown(route_rows, claims, risks))
    _write_text(CLAIM_LADDER_MD, build_claim_ladder(claims))
    _write_text(GB_DRAFT, build_genome_biology_draft(claims, route_rows))
    print(_rel(ROUTE_TSV))
    print(_rel(ROUTE_MD))
    print(_rel(CLAIM_LADDER_MD))
    print(_rel(GB_DRAFT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
