from __future__ import annotations

"""Build the post-feedback journal route gate for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-01
Purpose: Convert submission guard, external-review triage, journal-route, release
readiness, and scientific gate evidence into one deterministic post-feedback
Nature Methods versus Genome Biology routing decision.
Data source: Generated submission, release, external-review, and gate TSV files.
Method notes: This is a routing control artifact. It cannot guarantee
acceptance and returns success even when the correct route decision is to hold
or downgrade the manuscript.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "submission"

TRIAGE = OUT_DIR / "external_review_feedback_triage.tsv"
SUBMISSION_GUARD = OUT_DIR / "submission_guard.tsv"
TOP_ROUTE = OUT_DIR / "top_paper_route_decision.tsv"
RELEASE_READINESS = ROOT / "results" / "release" / "release_readiness.tsv"
GATE_REPORT = ROOT / "results" / "gates" / "gate_report.tsv"

OUT_TSV = OUT_DIR / "post_feedback_journal_route_gate.tsv"
OUT_MD = ROOT / "docs" / "post_feedback_journal_route_gate.md"

FIELDNAMES = [
    "decision_id",
    "decision",
    "status",
    "blocking_items",
    "evidence_path",
    "required_action",
    "notes",
]

RELEASE_CHECKS = [
    "repository_url",
    "github_remote",
    "github_release_tag",
    "zenodo_doi",
]

ACTIVE_FEEDBACK_STATUSES = {
    "",
    "open",
    "active",
    "blocked",
    "needs_action",
    "pending",
    "todo",
}

CLOSED_FEEDBACK_STATUSES = {
    "closed",
    "resolved",
    "done",
    "complete",
    "completed",
    "accepted",
    "deferred",
    "rejected",
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


def _read_tsv_from_header(path: Path, required_field: str) -> list[dict[str, str]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines):
        header = line.split("\t")
        if required_field in header:
            return list(csv.DictReader(lines[idx:], delimiter="\t"))
    return []


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


def _status_by(
    rows: list[dict[str, str]], key: str, status_key: str = "status"
) -> dict[str, str]:
    return {row.get(key, ""): row.get(status_key, "") for row in rows}


def _decision_by(rows: list[dict[str, str]], key: str) -> dict[str, str]:
    return {row.get(key, ""): row.get("decision", "") for row in rows}


def _active_external_blockers(rows: list[dict[str, str]]) -> list[str]:
    blockers: list[str] = []
    for row in rows:
        priority = row.get("priority", "").strip().upper()
        status = row.get("status", "").strip().lower()
        feedback_id = row.get("feedback_id", "").strip() or "feedback"
        if priority not in {"P0", "P1"}:
            continue
        if status == "awaiting_feedback" or status in CLOSED_FEEDBACK_STATUSES:
            continue
        if status in ACTIVE_FEEDBACK_STATUSES or status:
            blockers.append(feedback_id)
    return blockers


def _has_awaiting_feedback(rows: list[dict[str, str]]) -> bool:
    return any(
        row.get("status", "").strip().lower() == "awaiting_feedback" for row in rows
    )


def _blocked_status_ids(
    statuses: dict[str, str],
    pass_values: set[str] | None = None,
) -> list[str]:
    pass_values = pass_values or {"pass"}
    return [
        key for key, status in statuses.items() if key and status not in pass_values
    ]


def _row(
    decision_id: str,
    decision: str,
    status: str,
    blocking_items: list[str],
    evidence_path: Path,
    required_action: str,
    notes: str,
) -> dict[str, str]:
    return {
        "decision_id": decision_id,
        "decision": decision,
        "status": status,
        "blocking_items": ";".join(blocking_items) if blocking_items else "none",
        "evidence_path": _rel(evidence_path),
        "required_action": required_action,
        "notes": notes,
    }


def build_route_gate_rows(
    triage_rows: list[dict[str, str]],
    submission_guard_rows: list[dict[str, str]],
    route_rows: list[dict[str, str]],
    release_rows: list[dict[str, str]],
    gate_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    guard_status = _status_by(submission_guard_rows, "guard_id")
    route_decision = _decision_by(route_rows, "route_id")
    release_status = _status_by(release_rows, "check_id")
    gate_status = _status_by(gate_rows, "gate_id")

    external_blockers = _active_external_blockers(triage_rows)
    awaiting_external_feedback = _has_awaiting_feedback(triage_rows)
    release_blockers = _blocked_status_ids(
        {key: release_status.get(key, "") for key in RELEASE_CHECKS}
    )
    scientific_blockers = _blocked_status_ids(gate_status)

    overall_guard = guard_status.get("overall_submission_guard", "missing")
    nature_route = route_decision.get("nature_methods_first", "missing")
    genome_route = route_decision.get("genome_biology_fallback", "missing")
    release_ready = not release_blockers

    if external_blockers:
        external_decision = "blocked_by_external_feedback"
        external_status = "blocked"
        external_required_action = "Resolve P0/P1 external review feedback and rerun triage before any route upgrade."
        external_notes = "P0/P1 external feedback is active."
    elif awaiting_external_feedback:
        external_decision = "awaiting_external_feedback"
        external_status = "pending_review"
        external_required_action = "Collect external model or collaborator feedback in the template and rerun triage."
        external_notes = "External feedback loop has not produced real review rows yet."
    else:
        external_decision = "controlled"
        external_status = "pass"
        external_required_action = (
            "Keep the external feedback table archived with the submission package."
        )
        external_notes = "No active P0/P1 external feedback blockers were detected."

    nature_can_submit = (
        overall_guard == "submission_candidate"
        and nature_route == "submission_candidate"
        and not external_blockers
        and release_ready
    )
    if nature_can_submit:
        nature_decision = "submit_candidate"
        nature_status = "candidate"
        nature_blockers: list[str] = []
        nature_required_action = "Run final author checks, verify public release URLs/DOI, then prepare the Nature Methods presubmission step."
        nature_notes = "Nature Methods route is candidate by generated gates; this still does not predict acceptance."
    else:
        nature_decision = "hold_nature_methods"
        nature_status = "hold"
        nature_blockers = []
        if overall_guard != "submission_candidate":
            nature_blockers.append("overall_submission_guard")
        if nature_route != "submission_candidate":
            nature_blockers.append("nature_methods_first")
        nature_blockers.extend(external_blockers)
        if release_blockers:
            nature_blockers.append("external_release")
        if scientific_blockers:
            nature_blockers.append("scientific_gates")
        nature_required_action = "Do not submit or strengthen Nature Methods claims until all listed blockers are regenerated as pass/candidate."
        nature_notes = (
            f"overall_submission_guard={overall_guard}; nature_route={nature_route}; "
            f"scientific_blockers={';'.join(scientific_blockers) or 'none'}."
        )

    if genome_route == "activate_after_software_release" and not release_ready:
        genome_decision = "activate_after_release"
        genome_status = "ready_after_external_release"
        genome_blockers = release_blockers
        genome_required_action = "Complete GitHub remote/release and Zenodo DOI, then convert the manuscript to the Genome Biology reproducible-workflow frame if Nature Methods remains held."
        genome_notes = "Genome Biology fallback is the most realistic current route after public release completion."
    elif (
        genome_route
        in {
            "submission_candidate_if_nature_methods_not_pursued",
            "conversion_candidate",
        }
        and release_ready
    ):
        genome_decision = "conversion_candidate"
        genome_status = "candidate"
        genome_blockers = []
        genome_required_action = "Use the Genome Biology conversion draft only if Nature Methods is not pursued or receives negative editorial feedback."
        genome_notes = "Release gates pass and Genome Biology route can be prepared without stronger Nature Methods claims."
    elif nature_can_submit:
        genome_decision = "standby"
        genome_status = "standby"
        genome_blockers = []
        genome_required_action = "Keep as transfer/fallback route; do not dilute the Nature Methods package before editorial feedback."
        genome_notes = "Nature Methods is currently the candidate route."
    else:
        genome_decision = "standby"
        genome_status = "not_ready"
        genome_blockers = ["genome_biology_fallback"]
        genome_required_action = "Do not activate fallback until the route table supports Genome Biology and release blockers are explicit."
        genome_notes = f"Genome Biology route decision is {genome_route}."

    software_status = "pass" if release_ready else "blocked_external"
    software_decision = "pass" if release_ready else "complete_external_release"
    software_required_action = (
        "Keep release metadata archived with the submission."
        if release_ready
        else "Create public GitHub repository/remote, GitHub Release, Zenodo DOI, then rerun release readiness and route gates."
    )
    software_notes = (
        "External release checks pass."
        if release_ready
        else "External public-release objects remain incomplete."
    )

    if external_blockers:
        overall_decision = "pause_for_p0_feedback"
        overall_status = "blocked"
        overall_blockers = external_blockers
        overall_required_action = "Stop route escalation, resolve P0/P1 feedback, and regenerate all manuscript-control artifacts."
        overall_notes = "P0/P1 feedback overrides journal-route optimism."
    elif nature_can_submit:
        overall_decision = "nature_methods_submit_candidate"
        overall_status = "candidate"
        overall_blockers = []
        overall_required_action = "Proceed only after final author verification of release URLs, DOI, and editor-facing wording."
        overall_notes = (
            "Submission candidate is a readiness label, not an acceptance prediction."
        )
    elif genome_decision == "activate_after_release":
        overall_decision = "genome_biology_after_release"
        overall_status = "fallback_after_release"
        overall_blockers = release_blockers + scientific_blockers
        overall_required_action = "Finish public software release first; keep Nature Methods on hold unless stability and route gates change."
        overall_notes = (
            "Current controlled route is Genome Biology-style reproducible workflow after release; "
            "Nature Methods remains first target only if blockers are resolved."
        )
    elif genome_decision == "conversion_candidate":
        overall_decision = "genome_biology_conversion_candidate"
        overall_status = "fallback_candidate"
        overall_blockers = []
        overall_required_action = "Prepare Genome Biology submission package if Nature Methods is not pursued."
        overall_notes = "Use bounded genomics-workflow claims."
    else:
        overall_decision = "continue_controlled_revision"
        overall_status = "revise"
        overall_blockers = nature_blockers + genome_blockers + release_blockers
        overall_required_action = "Continue controlled manuscript revision and rerun gates after each material change."
        overall_notes = "No submit or fallback candidate state is currently available."

    return [
        _row(
            "external_feedback_gate",
            external_decision,
            external_status,
            external_blockers,
            TRIAGE,
            external_required_action,
            external_notes,
        ),
        _row(
            "nature_methods_gate",
            nature_decision,
            nature_status,
            list(dict.fromkeys(nature_blockers)),
            TOP_ROUTE,
            nature_required_action,
            nature_notes,
        ),
        _row(
            "genome_biology_gate",
            genome_decision,
            genome_status,
            list(dict.fromkeys(genome_blockers)),
            TOP_ROUTE,
            genome_required_action,
            genome_notes,
        ),
        _row(
            "software_release_gate",
            software_decision,
            software_status,
            release_blockers,
            RELEASE_READINESS,
            software_required_action,
            software_notes,
        ),
        _row(
            "overall_post_feedback_route",
            overall_decision,
            overall_status,
            list(dict.fromkeys(overall_blockers)),
            OUT_TSV,
            overall_required_action,
            overall_notes,
        ),
    ]


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    by_id = {row["decision_id"]: row for row in rows}
    overall = by_id.get("overall_post_feedback_route", {})
    blocking_rows = [
        row
        for row in rows
        if row["decision_id"] != "overall_post_feedback_route"
        and row["status"] not in {"pass", "candidate", "standby"}
    ]
    lines = [
        "# Post-Feedback Journal Route Gate",
        "",
        "This file is generated by `python scripts/build_post_feedback_journal_route_gate.py`.",
        "",
        "Acceptance guarantee: `impossible`.",
        "This gate decides whether the current package should keep Nature Methods on hold, activate the Genome Biology fallback after public release, or pause for P0/P1 external feedback.",
        "",
        "## Overall Decision",
        "",
        f"- Decision: `{overall.get('decision', 'missing')}`",
        f"- Status: `{overall.get('status', 'missing')}`",
        f"- Blocking items: `{overall.get('blocking_items', 'missing')}`",
        f"- Required action: {overall.get('required_action', 'missing')}",
        f"- Notes: {overall.get('notes', 'missing')}",
        "",
        "## Gate Rows",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"### {row['decision_id']}",
                "",
                f"- Decision: `{row['decision']}`",
                f"- Status: `{row['status']}`",
                f"- Blocking items: `{row['blocking_items']}`",
                f"- Evidence: `{row['evidence_path']}`",
                f"- Required action: {row['required_action']}",
                f"- Notes: {row['notes']}",
                "",
            ]
        )
    lines.extend(["## Blocking Rows", ""])
    if blocking_rows:
        for row in blocking_rows:
            lines.append(
                f"- `{row['decision_id']}`: `{row['decision']}`; blockers=`{row['blocking_items']}`"
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Submission Rule",
            "",
            "Do not submit to Nature Methods unless `nature_methods_gate` is `submit_candidate` and `overall_post_feedback_route` is `nature_methods_submit_candidate`.",
            "Do not switch to Genome Biology unless `genome_biology_gate` is `activate_after_release` or `conversion_candidate`, and keep the manuscript framed as a reproducible genomics workflow rather than a universal clustering-superiority claim.",
            "Do not treat external feedback as complete while the external feedback gate is `awaiting_external_feedback`.",
        ]
    )
    return lines


def main() -> int:
    rows = build_route_gate_rows(
        _read_tsv(TRIAGE),
        _read_tsv(SUBMISSION_GUARD),
        _read_tsv(TOP_ROUTE),
        _read_tsv(RELEASE_READINESS),
        _read_tsv_from_header(GATE_REPORT, "gate_id"),
    )
    _write_tsv(OUT_TSV, rows)
    _write_text(OUT_MD, build_markdown(rows))
    overall = next(
        row for row in rows if row["decision_id"] == "overall_post_feedback_route"
    )
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print(f"overall\t{overall['decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
