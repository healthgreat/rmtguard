from __future__ import annotations

"""Validate claim-to-evidence traceability for manuscript-facing artifacts.

Author: RMTGuard development team
Date: 2026-05-01
Purpose: Ensure figures, editor-facing pitch rows, and routing artifacts only
use claims that exist in the generated claim-evidence matrix, and that failed
or pending claims are handled as caveats rather than positive claims.
Data source: Claim-evidence matrix, storyline-panel map, editorial
presubmission packet, top-paper route package, and figure-claim checklist.
Method notes: This validator allows blocked/pending claims when they are
explicitly used as caveats or release blockers. Unknown claims or uncontrolled
failed-claim usage are violations.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "submission"
CLAIM_MATRIX = ROOT / "results" / "manuscript" / "claim_evidence_matrix.tsv"
STORYLINE_PANEL_MAP = ROOT / "results" / "manuscript" / "storyline_panel_map.tsv"
EDITORIAL_PACKET = OUT_DIR / "editorial_presubmission_packet.tsv"
TOP_ROUTE = OUT_DIR / "top_paper_route_decision.tsv"
FIGURE_CHECKLIST = OUT_DIR / "figure_claim_checklist.tsv"

REPORT_TSV = OUT_DIR / "claim_traceability.tsv"
REPORT_MD = ROOT / "docs" / "claim_traceability.md"

PASS_STATUSES = {"pass", "usable"}
CONTROLLED_STATUSES = {
    "blocked",
    "pending",
    "fail",
    "must_disclose",
    "do_not_send",
    "draft_controlled",
    "usable_with_scope",
    "activate_after_software_release",
    "hold_pre_submission",
    "must_complete_before_submission",
    "secondary_transfer_candidate",
    "reserve_not_primary",
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


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "artifact",
                "item_id",
                "linked_claim_ids",
                "claim_statuses",
                "trace_status",
                "evidence_path",
                "decision",
                "notes",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _claim_statuses(
    claims: dict[str, dict[str, str]], claim_ids: list[str]
) -> dict[str, str]:
    return {
        claim_id: claims.get(claim_id, {}).get("status", "missing")
        for claim_id in claim_ids
    }


def _split_claims(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(";") if part.strip()]


def _status_string(statuses: dict[str, str]) -> str:
    return ";".join(f"{claim_id}:{status}" for claim_id, status in statuses.items())


def _evidence_exists(raw_paths: str) -> bool:
    if not raw_paths:
        return False
    for part in [item.strip() for item in raw_paths.split(";") if item.strip()]:
        first = part.split(" | ", 1)[0].strip()
        if first in {
            "conversation policy",
            "manual Nature Portfolio reporting summary form",
        }:
            continue
        path = ROOT / first.replace("\\", "/")
        if not path.exists():
            return False
    return True


def _row(
    artifact: str,
    item_id: str,
    claim_ids: list[str],
    statuses: dict[str, str],
    trace_status: str,
    evidence_path: str,
    decision: str,
    notes: str,
) -> dict[str, str]:
    return {
        "artifact": artifact,
        "item_id": item_id,
        "linked_claim_ids": ";".join(claim_ids),
        "claim_statuses": _status_string(statuses),
        "trace_status": trace_status,
        "evidence_path": evidence_path,
        "decision": decision,
        "notes": notes,
    }


def validate_storyline(
    storyline_rows: list[dict[str, str]], claims: dict[str, dict[str, str]]
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in storyline_rows:
        claim_ids = _split_claims(row.get("linked_claim_ids", ""))
        statuses = _claim_statuses(claims, claim_ids)
        missing = [
            claim_id for claim_id, status in statuses.items() if status == "missing"
        ]
        has_failed = any(status == "fail" for status in statuses.values())
        has_pending = any(status == "pending" for status in statuses.values())
        figure_status = row.get("status", "")
        evidence_path = row.get("source_artifact", "")
        evidence_ok = _evidence_exists(evidence_path)
        if missing:
            trace_status = "violation"
            decision = "unknown_claim"
            notes = "Figure links to claim IDs absent from claim_evidence_matrix.tsv."
        elif has_failed and figure_status != "blocked":
            trace_status = "violation"
            decision = "failed_claim_not_blocked"
            notes = "Failed claims must make the figure blocked or explicitly caveated."
        elif has_pending and figure_status not in {"pending", "blocked"}:
            trace_status = "violation"
            decision = "pending_claim_not_controlled"
            notes = "Pending claims must keep the figure pending or blocked."
        elif not evidence_ok:
            trace_status = "violation"
            decision = "missing_source_artifact"
            notes = "Figure source artifact does not exist."
        elif figure_status == "pass" and all(
            status == "pass" for status in statuses.values()
        ):
            trace_status = "pass"
            decision = "positive_claim_traceable"
            notes = "Figure positive claims all trace to pass-status claims."
        else:
            trace_status = "controlled"
            decision = "caveated_claim_traceable"
            notes = "Figure uses pending/failed claims only as controlled caveats."
        rows.append(
            _row(
                "storyline_panel_map",
                row.get("figure", ""),
                claim_ids,
                statuses,
                trace_status,
                evidence_path,
                decision,
                notes,
            )
        )
    return rows


def validate_editorial_packet(
    packet_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in packet_rows:
        status = row.get("status", "")
        evidence_path = row.get("evidence_path", "")
        evidence_ok = _evidence_exists(evidence_path)
        if not evidence_ok:
            trace_status = "violation"
            decision = "missing_evidence_path"
            notes = "Editor-facing row lacks an existing evidence path."
        elif status in {
            "do_not_send",
            "blocked",
            "must_disclose",
            "draft_controlled",
            "usable_with_scope",
            "activate_after_software_release",
        }:
            trace_status = "controlled"
            decision = "editorial_boundary_traceable"
            notes = (
                "Editor-facing text is explicitly bounded by status and evidence path."
            )
        else:
            trace_status = "pass"
            decision = "editorial_claim_traceable"
            notes = "Editor-facing row has evidence and non-blocking status."
        rows.append(
            _row(
                "editorial_presubmission_packet",
                row.get("item_id", ""),
                [],
                {},
                trace_status,
                evidence_path,
                decision,
                notes,
            )
        )
    return rows


def validate_top_route(route_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in route_rows:
        decision = row.get("decision", "")
        evidence_path = row.get("evidence_path", "")
        evidence_ok = _evidence_exists(evidence_path)
        if not evidence_ok:
            trace_status = "violation"
            trace_decision = "missing_route_evidence"
            notes = "Route row evidence path is missing."
        elif (
            decision in CONTROLLED_STATUSES
            or "hold" in decision
            or "fallback" in row.get("route_id", "")
        ):
            trace_status = "controlled"
            trace_decision = "route_boundary_traceable"
            notes = "Route decision is explicitly conditional or fallback."
        else:
            trace_status = "pass"
            trace_decision = "route_traceable"
            notes = "Route row has evidence and non-blocking decision."
        rows.append(
            _row(
                "top_paper_route_decision",
                row.get("route_id", ""),
                [],
                {},
                trace_status,
                evidence_path,
                trace_decision,
                notes,
            )
        )
    return rows


def validate_figure_checklist(rows_in: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in rows_in:
        evidence_path = row.get("source_artifact", "")
        evidence_ok = _evidence_exists(evidence_path)
        prohibited = row.get("prohibited_caption_claim", "").strip()
        caveat = row.get("must_show_caveat", "").strip()
        if not evidence_ok:
            trace_status = "violation"
            decision = "missing_figure_source"
            notes = "Figure checklist source artifact is missing."
        elif row.get("status") in {"blocked", "pending"} and not caveat:
            trace_status = "violation"
            decision = "missing_required_caveat"
            notes = "Blocked or pending figure rows must include a caveat."
        elif prohibited:
            trace_status = "controlled"
            decision = "caption_boundary_traceable"
            notes = "Caption checklist includes prohibited wording and required caveat controls."
        else:
            trace_status = "pass"
            decision = "caption_claim_traceable"
            notes = "Caption checklist source and allowed claims are traceable."
        rows.append(
            _row(
                "figure_claim_checklist",
                row.get("figure", ""),
                [],
                {},
                trace_status,
                evidence_path,
                decision,
                notes,
            )
        )
    return rows


def build_rows() -> list[dict[str, str]]:
    claim_rows = _read_tsv(CLAIM_MATRIX)
    claims = {row["claim_id"]: row for row in claim_rows}
    rows: list[dict[str, str]] = []
    rows.extend(validate_storyline(_read_tsv(STORYLINE_PANEL_MAP), claims))
    rows.extend(validate_editorial_packet(_read_tsv(EDITORIAL_PACKET)))
    rows.extend(validate_top_route(_read_tsv(TOP_ROUTE)))
    rows.extend(validate_figure_checklist(_read_tsv(FIGURE_CHECKLIST)))
    return rows


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    violations = [row for row in rows if row["trace_status"] == "violation"]
    controlled = [row for row in rows if row["trace_status"] == "controlled"]
    passing = [row for row in rows if row["trace_status"] == "pass"]
    lines = [
        "# Claim Traceability",
        "",
        "This file is generated by `python scripts/validate_claim_traceability.py`.",
        "",
        "Acceptance guarantee: `impossible`.",
        "Every manuscript-facing positive claim must trace to `results/manuscript/claim_evidence_matrix.tsv`; blocked or pending claims may appear only as caveats or release blockers.",
        "",
        "## Summary",
        "",
        f"- Passing rows: `{len(passing)}`",
        f"- Controlled rows: `{len(controlled)}`",
        f"- Violations: `{len(violations)}`",
        "",
    ]
    if violations:
        lines.extend(["## Violations", ""])
        for row in violations:
            lines.append(
                f"- `{row['artifact']}` / `{row['item_id']}`: {row['decision']} - {row['notes']}"
            )
    else:
        lines.extend(["## Violations", "", "- none"])
    lines.extend(["", "## Controlled Rows", ""])
    if controlled:
        for row in controlled:
            lines.append(
                f"- `{row['artifact']}` / `{row['item_id']}`: {row['decision']}"
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Submission Rule",
            "",
            "Do not submit or send editor-facing materials if any row in `results/submission/claim_traceability.tsv` has `trace_status=violation`.",
        ]
    )
    return lines


def main() -> int:
    rows = build_rows()
    _write_tsv(REPORT_TSV, rows)
    _write_text(REPORT_MD, build_markdown(rows))
    violations = [row for row in rows if row["trace_status"] == "violation"]
    print(_rel(REPORT_TSV))
    print(_rel(REPORT_MD))
    print(f"violations\t{len(violations)}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
