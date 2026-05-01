from __future__ import annotations

"""Build a claim-scope decision register for the RMTGuard publication route.

Author: RMTGuard development team
Date: 2026-05-01
Purpose: Convert current gates into an explicit manuscript-claim boundary so
the 20-50 JIF route is governed by evidence rather than acceptance promises.
Data source: Generated gate evidence, publication route table, and manuscript
claim-evidence matrix.
Method notes: This artifact cannot guarantee journal acceptance. It records
which claims may be used, which claims are forbidden, and when to downgrade.
"""

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATES = ROOT / "results" / "gates" / "gate_evidence.tsv"
JOURNALS = ROOT / "results" / "gates" / "publication_20_50_decision.tsv"
CLAIMS = ROOT / "results" / "manuscript" / "claim_evidence_matrix.tsv"
OUT_DIR = ROOT / "results" / "submission"
OUT_TSV = OUT_DIR / "claim_scope_decision.tsv"
OUT_MD = ROOT / "docs" / "claim_scope_decision.md"


FIELDNAMES = [
    "decision_id",
    "category",
    "status",
    "evidence_path",
    "allowed_claim",
    "forbidden_claim",
    "required_action",
    "journal_route",
]


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
    return {row.get(key, ""): row.get("status", row.get("current_readiness", "")) for row in rows}


def _claim_map(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row.get("claim_id", ""): row for row in rows}


def _journal_map(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row.get("journal", ""): row for row in rows}


def _claim_status(claims: dict[str, dict[str, str]], claim_id: str) -> str:
    return claims.get(claim_id, {}).get("status", "missing")


def _claim_allowed(claims: dict[str, dict[str, str]], claim_id: str) -> str:
    return claims.get(claim_id, {}).get("allowed_wording", "")


def _claim_forbidden(claims: dict[str, dict[str, str]], claim_id: str) -> str:
    return claims.get(claim_id, {}).get("prohibited_wording", "")


def build_rows(
    gate_rows: list[dict[str, str]] | None = None,
    journal_rows: list[dict[str, str]] | None = None,
    claim_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    gates = _status_map(gate_rows if gate_rows is not None else _read_tsv(GATES), "gate_id")
    journals = _journal_map(journal_rows if journal_rows is not None else _read_tsv(JOURNALS))
    claims = _claim_map(claim_rows if claim_rows is not None else _read_tsv(CLAIMS))

    stability = gates.get("stability_advantage", "pending")
    software = gates.get("software_release", "pending")
    nature = journals.get("Nature Methods", {})

    strict_nm_status = "blocked"
    if nature.get("current_readiness") == "ready" and stability == "pass" and software == "pass":
        strict_nm_status = "ready_for_author_review_not_acceptance_guaranteed"
    elif stability == "fail":
        strict_nm_status = "blocked_by_stability_advantage"
    elif software != "pass":
        strict_nm_status = "blocked_by_software_release"

    callability_status = "usable_as_narrowed_claim"
    if software != "pass":
        callability_status = "scientific_claim_scoped_but_release_blocked"
    if stability not in {"pass", "borderline", "fail"}:
        callability_status = "incomplete_evidence"

    rows = [
        {
            "decision_id": "strict_20_50_methods_article",
            "category": "journal_route",
            "status": strict_nm_status,
            "evidence_path": _rel(GATES) + ";" + _rel(JOURNALS),
            "allowed_claim": "Nature Methods remains the first 20-50 JIF target only after all scientific and software gates pass.",
            "forbidden_claim": "Do not state that the manuscript is guaranteed, accepted, or ready for 20-50 JIF submission while stability_advantage or software_release is not pass.",
            "required_action": "Either improve the stability gate or formally narrow the claim and complete GitHub/Zenodo release before any submission.",
            "journal_route": "Nature Methods",
        },
        {
            "decision_id": "callability_aware_noise_control_claim",
            "category": "claim_scope",
            "status": callability_status,
            "evidence_path": _rel(CLAIMS),
            "allowed_claim": _claim_allowed(claims, "pbmc3k_stability"),
            "forbidden_claim": _claim_forbidden(claims, "pbmc3k_stability"),
            "required_action": "Use this only as a scoped no-call/noise-control claim; disclose PBMC3k, Baron, and PBMC68k limitations in the abstract, Figure 3, and cover letter.",
            "journal_route": "Nature Methods presubmission only if release and wording gates pass; otherwise Genome Biology or lower.",
        },
        {
            "decision_id": "positive_core_method_claims",
            "category": "claim_scope",
            "status": "usable" if all(
                _claim_status(claims, claim_id) == "pass"
                for claim_id in ["noise_control_null", "diagnostic_no_call_validation", "rare_state_retention", "public_benchmark_breadth"]
            ) else "incomplete",
            "evidence_path": _rel(CLAIMS),
            "allowed_claim": "Use random-matrix noise control, diagnostic no-call validation, rare-state retention, and four-public-dataset benchmark breadth as the core positive claims.",
            "forbidden_claim": "Do not transform these into broad fixed-PC superiority or universal scRNA-seq clustering guarantees.",
            "required_action": "Keep all positive claims tied to the generated claim-evidence matrix.",
            "journal_route": "Nature Methods if novelty is accepted; Genome Biology/Cell Genomics/Bioinformatics if editors require a lower-bar workflow framing.",
        },
        {
            "decision_id": "pbmc68k_boundary",
            "category": "forbidden_claim",
            "status": "locked_no_call_boundary",
            "evidence_path": "results/stability_benchmarks/stability_gate_diagnostics.tsv;results/rescue/algorithm_rescue_probe_summary.tsv",
            "allowed_claim": "PBMC68k/Zheng 2017 is a diagnostic no-call stress case with weak absolute annotation recovery in both RMTGuard and comparators.",
            "forbidden_claim": "Do not claim PBMC68k positive cell-state discovery or hide that fixed_pcs_30 and elbow have higher raw stability.",
            "required_action": "Preserve PBMC68k as a no-call boundary in all drafts and reviewer responses.",
            "journal_route": "All routes",
        },
        {
            "decision_id": "software_release_boundary",
            "category": "submission_blocker",
            "status": "blocked" if software != "pass" else "pass",
            "evidence_path": _rel(GATES),
            "allowed_claim": "Local release checks pass, but external GitHub/Zenodo evidence is required before journal submission.",
            "forbidden_claim": "Do not claim DOI-archived code or a complete software release before the real DOI and public repository exist.",
            "required_action": "Create public GitHub repository, tag a release, archive with Zenodo, then rerun release finalization.",
            "journal_route": "All routes",
        },
        {
            "decision_id": "guarantee_language",
            "category": "forbidden_claim",
            "status": "prohibited",
            "evidence_path": "conversation policy;docs/editorial_risk_audit.md",
            "allowed_claim": "The project is being engineered toward a 20-50 JIF-ready evidence package under explicit gates.",
            "forbidden_claim": "Never write or imply guaranteed acceptance in the manuscript, README, cover letter, response letter, or submission notes.",
            "required_action": "Replace guarantee language with gate-controlled readiness language.",
            "journal_route": "All routes",
        },
    ]
    return rows


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    blocked = [row for row in rows if row["status"].startswith("blocked")]
    forbidden = [row for row in rows if row["category"] == "forbidden_claim"]
    lines = [
        "# Claim Scope Decision",
        "",
        "This file is generated by `python scripts/build_claim_scope_decision.py`.",
        "",
        "## Current Decision",
        "",
        "- Acceptance guarantee: `impossible`.",
        "- Enforceable commitment: complete an auditable evidence package and stop or downgrade when gates fail.",
        "- Strict 20-50 JIF route: `blocked` until `stability_advantage` and `software_release` are resolved.",
        "- Current usable scientific story: callability-aware random-matrix noise control with diagnostic no-call boundaries.",
        "",
        "## Blockers",
        "",
    ]
    if blocked:
        lines.extend(f"- `{row['decision_id']}`: {row['required_action']}" for row in blocked)
    else:
        lines.append("- No blocked rows in this generated snapshot.")
    lines.extend(["", "## Forbidden Claims", ""])
    lines.extend(f"- `{row['decision_id']}`: {row['forbidden_claim']}" for row in forbidden)
    lines.extend(["", "## Decision Rows", ""])
    for row in rows:
        lines.extend(
            [
                f"### {row['decision_id']}",
                "",
                f"- Category: `{row['category']}`",
                f"- Status: `{row['status']}`",
                f"- Journal route: {row['journal_route']}",
                f"- Allowed claim: {row['allowed_claim']}",
                f"- Forbidden claim: {row['forbidden_claim']}",
                f"- Required action: {row['required_action']}",
                f"- Evidence: `{row['evidence_path']}`",
                "",
            ]
        )
    lines.extend(["## Output", "", f"- Decision TSV: `{_rel(OUT_TSV)}`"])
    return lines


def main() -> int:
    rows = build_rows()
    _write_tsv(OUT_TSV, rows, FIELDNAMES)
    _write_text(OUT_MD, build_markdown(rows))
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
