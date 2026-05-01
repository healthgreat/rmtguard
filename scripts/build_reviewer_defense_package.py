from __future__ import annotations

"""Build the reviewer defense package for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-01
Purpose: Convert reviewer-objection, editorial-risk, claim, and route-control
tables into evidence-bounded response language for Nature Methods and Genome
Biology routes.
Data source: Generated manuscript, editorial-risk, claim-evidence, post-feedback
route, and Genome Biology transfer TSV files.
Method notes: This script prepares response language only from existing local
evidence. It never promises acceptance, new analyses, or stronger results.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

OBJECTION_MATRIX = ROOT / "results" / "manuscript" / "reviewer_objection_matrix.tsv"
EDITORIAL_RISK = ROOT / "results" / "submission" / "editorial_risk_audit.tsv"
CLAIM_MATRIX = ROOT / "results" / "manuscript" / "claim_evidence_matrix.tsv"
POST_FEEDBACK_GATE = (
    ROOT / "results" / "submission" / "post_feedback_journal_route_gate.tsv"
)
GB_TRANSFER = ROOT / "results" / "submission" / "genome_biology_transfer_checklist.tsv"

OUT_TSV = ROOT / "results" / "submission" / "reviewer_defense_matrix.tsv"
OUT_MD = ROOT / "docs" / "reviewer_defense_package.md"
RESPONSE_DRAFT = ROOT / "manuscript" / "reviewer_defense_response_draft.md"

FIELDNAMES = [
    "defense_id",
    "status",
    "route_impact",
    "risk_level",
    "evidence_path",
    "safe_response",
    "nature_methods_position",
    "genome_biology_position",
    "required_action",
    "forbidden_response",
]

RISK_ORDER = {"blocking": 0, "high": 1, "major": 2, "medium": 3, "strategic": 4}


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


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _by(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    return {row.get(key, ""): row for row in rows}


def _claim(claims_by_id: dict[str, dict[str, str]], claim_id: str, field: str) -> str:
    return claims_by_id.get(claim_id, {}).get(field, "")


def _post_feedback_decision(rows: list[dict[str, str]], decision_id: str) -> str:
    return _by(rows, "decision_id").get(decision_id, {}).get("decision", "missing")


def _gb_transfer_status(rows: list[dict[str, str]], item_id: str) -> str:
    return _by(rows, "item_id").get(item_id, {}).get("status", "missing")


def _status_for_objection(
    objection: dict[str, str],
    post_feedback_rows: list[dict[str, str]],
    gb_rows: list[dict[str, str]],
) -> str:
    objection_id = objection.get("objection_id", "")
    current_status = objection.get("current_status", "")
    if objection_id == "software_release" or current_status == "pending":
        return "blocked_until_public_release"
    if objection_id == "stability_advantage" or current_status == "fail":
        return "major_reframe_required"
    if objection_id in {"method_novelty", "null_calibration_scope"}:
        return "argument_ready_with_caveats"
    if objection_id in {"rare_state_loss", "benchmark_baselines"}:
        return "controlled_with_existing_evidence"
    if objection_id in {"pbmc68k_label_quality", "pdac_biology_depth"}:
        return "controlled_by_boundary_wording"
    if (
        _post_feedback_decision(post_feedback_rows, "overall_post_feedback_route")
        == "genome_biology_after_release"
        and _gb_transfer_status(gb_rows, "overall_genome_biology_transfer")
        == "prepare_after_release"
    ):
        return "fallback_ready_after_release"
    return "manual_review"


def _nature_methods_position(objection_id: str) -> str:
    return {
        "stability_advantage": "Use only a callability-aware stability/no-call claim; this remains a Nature Methods risk until Figure 3 and the abstract visibly disclose comparator tradeoffs.",
        "software_release": "Do not submit to Nature Methods before public GitHub Release and archive evidence are real.",
        "method_novelty": "Lead with the random-matrix noise-control contract, diagnostic no-call behavior, and false-signal suppression rather than automatic parameter tuning.",
        "null_calibration_scope": "State RMT null assumptions and report tested-scenario calibration only; avoid exact universal type-I wording.",
        "rare_state_loss": "Use the rare-state synthetic ARI as support, while acknowledging that real rare states still require dataset-specific interpretation.",
        "benchmark_baselines": "Keep expanded baselines visible in the final tables and avoid hiding fixed-PC or elbow advantages.",
        "pbmc68k_label_quality": "Treat PBMC68k as label-granularity stress evidence and diagnostic no-call context, not as a positive annotation success.",
        "pdac_biology_depth": "Use PDAC/TME as a bounded public application, not as the central novelty claim.",
    }.get(objection_id, "Use evidence-bounded wording and avoid route escalation.")


def _genome_biology_position(objection_id: str) -> str:
    return {
        "stability_advantage": "Turn the limitation into a transparent workflow feature: the package reports when the evidence supports no-call rather than forced discovery.",
        "software_release": "Still blocked until public release; Genome Biology-style software framing requires the same repository and archive evidence.",
        "method_novelty": "Frame novelty as an open genomics workflow that operationalizes random-matrix diagnostics and no-call boundaries.",
        "null_calibration_scope": "Present calibration as benchmarked diagnostic behavior rather than universal theory.",
        "rare_state_loss": "Keep rare-state retention as synthetic support and avoid biological guarantees.",
        "benchmark_baselines": "Use expanded baseline tables as evidence of a serious benchmark workflow.",
        "pbmc68k_label_quality": "Use PBMC68k to motivate transparent stress testing and label-quality caveats.",
        "pdac_biology_depth": "Keep PDAC/TME as an example of public reproducible use, not a disease-mechanism article.",
    }.get(objection_id, "Use reproducible workflow framing.")


def _forbidden_response(
    objection_id: str, claims_by_id: dict[str, dict[str, str]]
) -> str:
    if objection_id == "stability_advantage":
        return _claim(claims_by_id, "pbmc3k_stability", "prohibited_wording")
    if objection_id == "software_release":
        return _claim(claims_by_id, "software_release", "prohibited_wording")
    if objection_id == "pbmc68k_label_quality":
        return _claim(claims_by_id, "annotation_noninferiority", "prohibited_wording")
    if objection_id == "pdac_biology_depth":
        return _claim(claims_by_id, "pdac_tme_showcase", "prohibited_wording")
    if objection_id == "rare_state_loss":
        return _claim(claims_by_id, "rare_state_retention", "prohibited_wording")
    if objection_id == "null_calibration_scope":
        return _claim(claims_by_id, "noise_control_null", "prohibited_wording")
    return (
        "Do not invent new analyses, journal outcomes, or stronger benchmark results."
    )


def _safe_strategy_text(text: str) -> str:
    replacements = {
        "broad fixed-PC superiority": "an overbroad fixed-PC performance claim",
        "broad superiority": "an overbroad performance claim",
        "guaranteed acceptance": "an acceptance promise",
        "guaranteed publication": "a publication promise",
    }
    cleaned = text
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    return cleaned


def build_defense_rows(
    objection_rows: list[dict[str, str]],
    editorial_rows: list[dict[str, str]],
    claim_rows: list[dict[str, str]],
    post_feedback_rows: list[dict[str, str]],
    gb_transfer_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    claims_by_id = _by(claim_rows, "claim_id")
    editorial_by_claim = {
        row.get("risk_id", ""): row for row in editorial_rows if row.get("risk_id")
    }
    rows: list[dict[str, str]] = []
    for objection in objection_rows:
        objection_id = objection.get("objection_id", "")
        risk_level = objection.get("risk_level", "")
        linked = objection.get("linked_gate_or_claim", "")
        editorial_risk = editorial_by_claim.get(objection_id, {})
        status = _status_for_objection(objection, post_feedback_rows, gb_transfer_rows)
        response_strategy = _safe_strategy_text(
            objection.get("response_strategy", "").rstrip(".")
        )
        safe_response = (
            f"We address this by keeping the claim limited to {linked or 'the linked evidence'}: "
            f"{response_strategy}. "
            f"Current evidence: {objection.get('evidence', '')}."
        )
        if objection_id == "software_release":
            route_impact = "blocks_all_submission_routes"
        elif objection_id == "stability_advantage":
            route_impact = "blocks_broad_superiority_claim"
        elif objection_id == "method_novelty":
            route_impact = "nature_methods_editorial_fit"
        else:
            route_impact = "controlled_reviewer_risk"
        if editorial_risk:
            route_impact = (
                f"{route_impact};editorial_status={editorial_risk.get('status', '')}"
            )
        rows.append(
            {
                "defense_id": objection_id,
                "status": status,
                "route_impact": route_impact,
                "risk_level": risk_level,
                "evidence_path": objection.get("evidence", ""),
                "safe_response": safe_response,
                "nature_methods_position": _nature_methods_position(objection_id),
                "genome_biology_position": _genome_biology_position(objection_id),
                "required_action": objection.get("required_before_submission", ""),
                "forbidden_response": _forbidden_response(objection_id, claims_by_id),
            }
        )

    rows.sort(key=lambda row: (RISK_ORDER.get(row["risk_level"], 9), row["defense_id"]))
    blocking_items = [
        row["defense_id"]
        for row in rows
        if row["status"] in {"blocked_until_public_release", "major_reframe_required"}
    ]
    overall_status = (
        "not_sendable_before_release"
        if "software_release" in blocking_items
        else "requires_major_reframe" if blocking_items else "defense_ready"
    )
    rows.append(
        {
            "defense_id": "overall_reviewer_defense",
            "status": overall_status,
            "route_impact": "controls_presubmission_and_transfer_language",
            "risk_level": "summary",
            "evidence_path": _rel(OUT_TSV),
            "safe_response": "Use this matrix to answer criticism without inflating claims or promising new evidence.",
            "nature_methods_position": "Nature Methods remains on hold until release and stability-claim boundaries are resolved.",
            "genome_biology_position": "Genome Biology fallback is usable only after public release and with workflow framing.",
            "required_action": ";".join(blocking_items) if blocking_items else "none",
            "forbidden_response": "Do not claim acceptance, broad superiority, DOI-backed release, or positive PBMC68k discovery unless the source gates change.",
        }
    )
    return rows


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    overall = next(
        (row for row in rows if row["defense_id"] == "overall_reviewer_defense"), {}
    )
    active = [
        row
        for row in rows
        if row["defense_id"] != "overall_reviewer_defense"
        and row["status"] in {"blocked_until_public_release", "major_reframe_required"}
    ]
    lines = [
        "# Reviewer Defense Package",
        "",
        "This file is generated by `python scripts/build_reviewer_defense_package.py`.",
        "",
        "Acceptance guarantee: `impossible`.",
        "This package prepares evidence-bounded reviewer responses for Nature Methods and Genome Biology routes.",
        "",
        "## Overall Defense Status",
        "",
        f"- Status: `{overall.get('status', 'missing')}`",
        f"- Required action: `{overall.get('required_action', 'missing')}`",
        f"- Nature Methods position: {overall.get('nature_methods_position', 'missing')}",
        f"- Genome Biology position: {overall.get('genome_biology_position', 'missing')}",
        "",
        "## Active Blockers",
        "",
    ]
    if active:
        for row in active:
            lines.append(
                f"- `{row['defense_id']}`: `{row['status']}`; action={row['required_action']}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Defense Rows", ""])
    for row in rows:
        lines.extend(
            [
                f"### {row['defense_id']}",
                "",
                f"- Status: `{row['status']}`",
                f"- Risk level: `{row['risk_level']}`",
                f"- Route impact: `{row['route_impact']}`",
                f"- Evidence: `{row['evidence_path']}`",
                f"- Safe response: {row['safe_response']}",
                f"- Nature Methods position: {row['nature_methods_position']}",
                f"- Genome Biology position: {row['genome_biology_position']}",
                f"- Required action: {row['required_action']}",
                f"- Forbidden response: {row['forbidden_response']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Response Boundary",
            "",
            "Do not promise new analyses, public release, editor interest, or stronger benchmark outcomes unless the corresponding files and generated gates have been updated.",
        ]
    )
    return lines


def build_response_draft(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Reviewer Defense Response Draft",
        "",
        "Status: generated from current evidence. Do not send as a response letter until real reviewer comments exist.",
        "",
    ]
    for row in rows:
        if row["defense_id"] == "overall_reviewer_defense":
            continue
        lines.extend(
            [
                f"## {row['defense_id']}",
                "",
                f"Potential concern: `{row['route_impact']}`.",
                "",
                "Draft response:",
                "",
                row["safe_response"],
                "",
                "For a Nature Methods route, we would keep the response aligned with: "
                + row["nature_methods_position"],
                "",
                "For a Genome Biology route, we would keep the response aligned with: "
                + row["genome_biology_position"],
                "",
                "Boundary: " + row["forbidden_response"],
                "",
            ]
        )
    lines.extend(
        [
            "## Non-Negotiable Boundary",
            "",
            "These draft responses are pre-review scaffolds. They must be edited against actual reviewer wording and regenerated after any new analysis, public release, or route change.",
        ]
    )
    return lines


def main() -> int:
    rows = build_defense_rows(
        _read_tsv(OBJECTION_MATRIX),
        _read_tsv(EDITORIAL_RISK),
        _read_tsv(CLAIM_MATRIX),
        _read_tsv(POST_FEEDBACK_GATE),
        _read_tsv(GB_TRANSFER),
    )
    _write_tsv(OUT_TSV, rows)
    _write_text(OUT_MD, build_markdown(rows))
    _write_text(RESPONSE_DRAFT, build_response_draft(rows))
    overall = next(
        row for row in rows if row["defense_id"] == "overall_reviewer_defense"
    )
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print(_rel(RESPONSE_DRAFT))
    print(f"overall\t{overall['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
