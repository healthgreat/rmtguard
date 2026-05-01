from __future__ import annotations

"""Build the final submission guard for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-01
Purpose: Aggregate scientific gates, software-release evidence, claim lint,
claim traceability, and editor-facing send status into one go/no-go table.
Data source: Generated gate, release, claim-boundary, traceability, route, and
editorial presubmission artifacts.
Method notes: `do_not_submit` is the expected current controlled state. The
script returns success when it can build the guard, even if the guard says not
to submit.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "submission"
REPORT_TSV = OUT_DIR / "submission_guard.tsv"
REPORT_MD = ROOT / "docs" / "submission_guard.md"

GATE_REPORT = ROOT / "results" / "gates" / "gate_report.tsv"
PRESUBMISSION_GATEKEEPER = OUT_DIR / "presubmission_gatekeeper.tsv"
RELEASE_READINESS = ROOT / "results" / "release" / "release_readiness.tsv"
CLAIM_LINT = OUT_DIR / "claim_boundary_lint.tsv"
CLAIM_TRACEABILITY = OUT_DIR / "claim_traceability.tsv"
TOP_ROUTE = OUT_DIR / "top_paper_route_decision.tsv"
EDITORIAL_PACKET = OUT_DIR / "editorial_presubmission_packet.tsv"


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
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "guard_id",
                "status",
                "severity",
                "evidence_path",
                "blocking_items",
                "required_action",
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


def _status_by(
    rows: list[dict[str, str]], key: str, status_key: str = "status"
) -> dict[str, str]:
    return {row.get(key, ""): row.get(status_key, "") for row in rows}


def _blocked(
    statuses: dict[str, str], pass_values: set[str] | None = None
) -> list[str]:
    pass_values = pass_values or {"pass"}
    return [
        key for key, status in statuses.items() if key and status not in pass_values
    ]


def _row(
    guard_id: str,
    status: str,
    severity: str,
    evidence_path: Path,
    blocking_items: list[str],
    required_action: str,
    notes: str,
) -> dict[str, str]:
    return {
        "guard_id": guard_id,
        "status": status,
        "severity": severity,
        "evidence_path": _rel(evidence_path),
        "blocking_items": ";".join(blocking_items) if blocking_items else "none",
        "required_action": required_action,
        "notes": notes,
    }


def build_guard_rows(
    gate_rows: list[dict[str, str]],
    presubmission_rows: list[dict[str, str]],
    release_rows: list[dict[str, str]],
    lint_rows: list[dict[str, str]],
    trace_rows: list[dict[str, str]],
    route_rows: list[dict[str, str]],
    editorial_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    gate_status = _status_by(gate_rows, "gate_id")
    presub_status = _status_by(presubmission_rows, "check_id")
    release_status = _status_by(release_rows, "check_id")
    route_status = _status_by(route_rows, "route_id", "decision")
    editorial_status = _status_by(editorial_rows, "item_id")

    lint_violations = [row for row in lint_rows if row.get("status") == "violation"]
    trace_violations = [
        row for row in trace_rows if row.get("trace_status") == "violation"
    ]
    scientific_blockers = _blocked(gate_status)
    presub_blockers = _blocked(presub_status)
    release_blockers = _blocked(
        {
            key: release_status.get(key, "")
            for key in [
                "repository_url",
                "github_remote",
                "github_release_tag",
                "zenodo_doi",
            ]
        }
    )
    nature_route_blocked = (
        route_status.get("nature_methods_first") != "submission_candidate"
    )
    editor_send_blocked = editorial_status.get("send_status") != "send_ready"

    rows = [
        _row(
            "scientific_gates",
            "pass" if not scientific_blockers else "blocked",
            "blocking" if scientific_blockers else "controlled",
            GATE_REPORT,
            scientific_blockers,
            "Resolve failed/pending scientific gates or keep the manuscript in a fallback/no-send route.",
            (
                "Nature Methods scientific gates are not all pass."
                if scientific_blockers
                else "All scientific gates pass."
            ),
        ),
        _row(
            "presubmission_gatekeeper",
            "pass" if not presub_blockers else "blocked",
            "blocking" if presub_blockers else "controlled",
            PRESUBMISSION_GATEKEEPER,
            presub_blockers,
            "Do not submit until the presubmission gatekeeper has no blocked checks.",
            (
                "Presubmission gatekeeper has blocked rows."
                if presub_blockers
                else "Presubmission gatekeeper passes."
            ),
        ),
        _row(
            "external_release",
            "pass" if not release_blockers else "blocked",
            "blocking" if release_blockers else "controlled",
            RELEASE_READINESS,
            release_blockers,
            "Create public GitHub repository, tag release, create GitHub Release, archive with Zenodo, and rerun finalizer.",
            (
                "External repository/release/DOI objects are incomplete."
                if release_blockers
                else "External release objects pass."
            ),
        ),
        _row(
            "claim_boundary_lint",
            "pass" if not lint_violations else "integrity_violation",
            "blocking" if lint_violations else "controlled",
            CLAIM_LINT,
            [
                f"{row.get('rule_id')}:{row.get('path')}:{row.get('line')}"
                for row in lint_violations
            ],
            "Remove or downgrade unqualified overclaims before any editor-facing use.",
            (
                "Claim-boundary lint has violations."
                if lint_violations
                else "Claim-boundary lint has zero violations."
            ),
        ),
        _row(
            "claim_traceability",
            "pass" if not trace_violations else "integrity_violation",
            "blocking" if trace_violations else "controlled",
            CLAIM_TRACEABILITY,
            [f"{row.get('artifact')}:{row.get('item_id')}" for row in trace_violations],
            "Map every manuscript-facing claim to allowed evidence or recast it as a caveat.",
            (
                "Claim traceability has violations."
                if trace_violations
                else "Claim traceability has zero violations."
            ),
        ),
        _row(
            "nature_methods_route",
            "pass" if not nature_route_blocked else "blocked",
            "blocking" if nature_route_blocked else "controlled",
            TOP_ROUTE,
            ["nature_methods_first"] if nature_route_blocked else [],
            "Keep Nature Methods on hold until route decision becomes submission_candidate.",
            f"Nature Methods route decision is {route_status.get('nature_methods_first', 'missing')}.",
        ),
        _row(
            "editorial_send_status",
            "pass" if not editor_send_blocked else "blocked",
            "blocking" if editor_send_blocked else "controlled",
            EDITORIAL_PACKET,
            ["send_status"] if editor_send_blocked else [],
            "Do not send the presubmission inquiry while send_status is do_not_send.",
            f"Editorial send_status is {editorial_status.get('send_status', 'missing')}.",
        ),
    ]

    hard_blockers = [row["guard_id"] for row in rows if row["status"] != "pass"]
    rows.append(
        _row(
            "overall_submission_guard",
            "do_not_submit" if hard_blockers else "submission_candidate",
            "blocking" if hard_blockers else "controlled",
            REPORT_TSV,
            hard_blockers,
            "Submit only when this row is submission_candidate and all source artifacts have been regenerated.",
            "Acceptance guarantee remains impossible; this guard only controls submission readiness.",
        )
    )
    return rows


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    overall = next(
        (row for row in rows if row["guard_id"] == "overall_submission_guard"), {}
    )
    blocked = [
        row
        for row in rows
        if row["guard_id"] != "overall_submission_guard" and row["status"] != "pass"
    ]
    lines = [
        "# Submission Guard",
        "",
        "This file is generated by `python scripts/build_submission_guard.py`.",
        "",
        "Acceptance guarantee: `impossible`.",
        "This guard aggregates scientific, software-release, claim-boundary, traceability, route, and editor-send gates.",
        "",
        "## Overall Decision",
        "",
        f"- Status: `{overall.get('status', 'missing')}`",
        f"- Blocking items: `{overall.get('blocking_items', 'missing')}`",
        "",
        "## Blocking Rows",
        "",
    ]
    if blocked:
        for row in blocked:
            lines.extend(
                [
                    f"### {row['guard_id']}",
                    "",
                    f"- Status: `{row['status']}`",
                    f"- Severity: `{row['severity']}`",
                    f"- Evidence: `{row['evidence_path']}`",
                    f"- Blocking items: `{row['blocking_items']}`",
                    f"- Required action: {row['required_action']}",
                    f"- Notes: {row['notes']}",
                    "",
                ]
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "## Submission Rule",
            "",
            "Do not submit to Nature Methods, send presubmission inquiries, or describe the package as submission-ready while `overall_submission_guard` is `do_not_submit`.",
        ]
    )
    return lines


def main() -> int:
    rows = build_guard_rows(
        _read_tsv_from_header(GATE_REPORT, "gate_id"),
        _read_tsv(PRESUBMISSION_GATEKEEPER),
        _read_tsv(RELEASE_READINESS),
        _read_tsv(CLAIM_LINT),
        _read_tsv(CLAIM_TRACEABILITY),
        _read_tsv(TOP_ROUTE),
        _read_tsv(EDITORIAL_PACKET),
    )
    _write_tsv(REPORT_TSV, rows)
    _write_text(REPORT_MD, build_markdown(rows))
    overall = next(row for row in rows if row["guard_id"] == "overall_submission_guard")
    print(_rel(REPORT_TSV))
    print(_rel(REPORT_MD))
    print(f"overall\t{overall['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
