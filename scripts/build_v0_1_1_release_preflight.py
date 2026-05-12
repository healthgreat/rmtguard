"""Build a preflight gate for the future v0.1.1 submission release.

Author: RMTGuard contributors
Date: 2026-05-12
Purpose: Convert the conditions for a future v0.1.1 GitHub Release/Zenodo
archive into explicit machine-readable gates. This prevents creating a DOI
before author-controlled and manuscript-freeze blockers are resolved.
Data source: author metadata, corresponding-author sign-off tracker,
figure-caption-source audit, reporting-summary worksheet, claim-boundary lint,
claim traceability, post-release coverage audit, and Git status.
Method notes: This script does not create tags, push commits, make GitHub
Releases, or mint Zenodo DOIs.
"""

from __future__ import annotations

import csv
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_TSV = ROOT / "results" / "submission" / "v0_1_1_release_preflight.tsv"
OUT_MD = ROOT / "docs" / "v0_1_1_release_preflight.md"

AUTHOR_META = ROOT / "metadata" / "author_metadata.tsv"
SIGNOFF = ROOT / "metadata" / "corresponding_author_signoff_tracker.tsv"
FIGURE_AUDIT = ROOT / "results" / "submission" / "figure_caption_source_audit.tsv"
REPORTING = ROOT / "results" / "submission" / "reporting_summary_draft.tsv"
CLAIM_LINT = ROOT / "results" / "submission" / "claim_boundary_lint.tsv"
CLAIM_TRACE = ROOT / "results" / "submission" / "claim_traceability.tsv"
VERSION_AUDIT = ROOT / "results" / "submission" / "post_release_version_coverage_audit.tsv"
FREEZE_MANIFEST = ROOT / "results" / "submission" / "current_evidence_freeze_manifest.tsv"

SELF_OUTPUTS = {
    OUT_TSV.relative_to(ROOT).as_posix(),
    OUT_MD.relative_to(ROOT).as_posix(),
}


@dataclass(frozen=True)
class Gate:
    gate_id: str
    status: str
    severity: str
    evidence_path: str
    required_action: str
    notes: str


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def run_git(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return completed.stdout.strip()


def filtered_git_status() -> str:
    raw = run_git(["status", "--short"])
    if not raw:
        return ""
    kept: list[str] = []
    for line in raw.splitlines():
        path = line[3:].strip().replace("\\", "/")
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path in SELF_OUTPUTS:
            continue
        kept.append(line)
    return "\n".join(kept)


def author_declaration_gate() -> Gate:
    rows = read_tsv(AUTHOR_META)
    pending_fields = []
    for row in rows:
        field = row.get("field", "")
        status = row.get("status", "")
        if field in {
            "funding_statement",
            "competing_interests_statement",
            "ethics_public_data_statement",
            "postal_code_author_provided",
            "postal_code_public_source_candidate",
            "credit_roles_draft",
        } and status not in {
            "author_confirmed",
            "author_confirmed_removed",
            "author_confirmed_from_logged_in_orcid_screenshot",
            "published_release_doi",
            "author_created_public_repo",
            "drafted_from_project_scope",
        }:
            pending_fields.append(f"{field}:{status}")
    if pending_fields:
        return Gate(
            "author_declarations",
            "blocked",
            "manual_blocker",
            _rel(AUTHOR_META),
            "Confirm funding, competing interests, public-data ethics, postal code, and CRediT roles before release.",
            ";".join(pending_fields),
        )
    return Gate(
        "author_declarations",
        "pass",
        "controlled",
        _rel(AUTHOR_META),
        "No action.",
        "Author metadata has no pending release-blocking declaration rows.",
    )


def corresponding_author_gate() -> Gate:
    rows = read_tsv(SIGNOFF)
    bad = [
        f"{row.get('author_name')}:{row.get('status')}"
        for row in rows
        if row.get("status") != "confirmed"
    ]
    if bad:
        return Gate(
            "corresponding_author_figure4_ack",
            "blocked",
            "manual_blocker",
            _rel(SIGNOFF),
            "Save written replies under metadata/author_reply_evidence/ and record them with scripts/record_corresponding_author_signoff.py.",
            ";".join(bad),
        )
    return Gate(
        "corresponding_author_figure4_ack",
        "pass",
        "controlled",
        _rel(SIGNOFF),
        "No action.",
        "Both corresponding authors confirmed bounded Figure 4 wording.",
    )


def figure_gate() -> Gate:
    rows = read_tsv(FIGURE_AUDIT)
    blocked = [row for row in rows if row.get("audit_status", "").startswith("blocked")]
    pending_ack = [
        row for row in rows if row.get("audit_status") == "ready_pending_author_ack"
    ]
    if blocked:
        return Gate(
            "figure_caption_source_audit",
            "blocked",
            "submission_blocker",
            _rel(FIGURE_AUDIT),
            "Fix missing figure assets, source data, or legends before release.",
            ";".join(row.get("display_id", "") for row in blocked),
        )
    if pending_ack:
        return Gate(
            "figure_caption_source_audit",
            "blocked",
            "manual_blocker",
            _rel(FIGURE_AUDIT),
            "Resolve Figure 4 corresponding-author acknowledgement before release.",
            ";".join(row.get("display_id", "") for row in pending_ack),
        )
    return Gate(
        "figure_caption_source_audit",
        "pass",
        "controlled",
        _rel(FIGURE_AUDIT),
        "No action.",
        "All display items are ready with bounded claims.",
    )


def reporting_gate() -> Gate:
    rows = read_tsv(REPORTING)
    blocked = [row for row in rows if row.get("status") == "blocked"]
    manual = [
        row
        for row in rows
        if row.get("status") in {"pending_manual", "needs_author_completion"}
    ]
    if blocked:
        return Gate(
            "reporting_summary",
            "blocked",
            "submission_blocker",
            _rel(REPORTING),
            "Resolve blocked reporting-summary rows before release.",
            ";".join(f"{row.get('section')}/{row.get('item')}" for row in blocked),
        )
    if manual:
        return Gate(
            "reporting_summary",
            "pending_author_verification",
            "manual_blocker",
            _rel(REPORTING),
            "Have the corresponding author verify the reporting-summary worksheet before official submission.",
            ";".join(f"{row.get('section')}/{row.get('item')}" for row in manual),
        )
    return Gate(
        "reporting_summary",
        "pass",
        "controlled",
        _rel(REPORTING),
        "No action.",
        "Reporting-summary worksheet has no blocked or manual rows.",
    )


def claim_integrity_gate() -> Gate:
    lint_rows = read_tsv(CLAIM_LINT)
    trace_rows = read_tsv(CLAIM_TRACE)
    lint_bad = [row for row in lint_rows if row.get("status") == "violation"]
    trace_bad = [row for row in trace_rows if row.get("trace_status") == "violation"]
    if lint_bad or trace_bad:
        return Gate(
            "claim_integrity",
            "blocked",
            "submission_blocker",
            f"{_rel(CLAIM_LINT)};{_rel(CLAIM_TRACE)}",
            "Remove overclaims or add direct evidence mappings before release.",
            f"lint={len(lint_bad)};trace={len(trace_bad)}",
        )
    return Gate(
        "claim_integrity",
        "pass",
        "controlled",
        f"{_rel(CLAIM_LINT)};{_rel(CLAIM_TRACE)}",
        "No action.",
        f"lint_violations=0;trace_violations=0;lint_rows={len(lint_rows)};trace_rows={len(trace_rows)}",
    )


def version_coverage_gate() -> Gate:
    rows = read_tsv(VERSION_AUDIT)
    statuses = {row.get("audit_id"): row.get("status") for row in rows}
    recommendation = statuses.get("release_recommendation", "missing")
    worktree = statuses.get("worktree_cleanliness", "missing")
    if recommendation == "prepare_v0.1.1_after_author_ack":
        return Gate(
            "version_coverage",
            "ready_after_manual_blockers",
            "release_blocker",
            _rel(VERSION_AUDIT),
            "After author blockers are resolved, tag and archive v0.1.1 so DOI covers the submitted files.",
            f"recommendation={recommendation};worktree={worktree}",
        )
    if recommendation == "no_refresh_needed":
        return Gate(
            "version_coverage",
            "pass",
            "controlled",
            _rel(VERSION_AUDIT),
            "No action.",
            "Current files are covered by the archived release.",
        )
    return Gate(
        "version_coverage",
        "blocked",
        "release_blocker",
        _rel(VERSION_AUDIT),
        "Regenerate post-release version coverage audit.",
        f"recommendation={recommendation};worktree={worktree}",
    )


def freeze_manifest_gate() -> Gate:
    rows = read_tsv(FREEZE_MANIFEST)
    missing = [row.get("item_id", "") for row in rows if row.get("exists") != "True"]
    if missing:
        return Gate(
            "evidence_freeze_manifest",
            "blocked",
            "submission_blocker",
            _rel(FREEZE_MANIFEST),
            "Regenerate or restore missing evidence-freeze files before release.",
            ";".join(missing),
        )
    return Gate(
        "evidence_freeze_manifest",
        "pass",
        "controlled",
        _rel(FREEZE_MANIFEST),
        "No action.",
        f"{len(rows)} frozen evidence items exist.",
    )


def worktree_gate() -> Gate:
    status = filtered_git_status()
    if status:
        return Gate(
            "git_worktree_clean",
            "blocked",
            "release_blocker",
            "git status --short",
            "Commit all release-facing changes before creating a tag.",
            status.replace("\n", ";"),
        )
    return Gate(
        "git_worktree_clean",
        "pass",
        "controlled",
        "git status --short",
        "No action.",
        "Worktree is clean except self-generated preflight outputs.",
    )


def build_gates() -> list[Gate]:
    return [
        author_declaration_gate(),
        corresponding_author_gate(),
        figure_gate(),
        reporting_gate(),
        claim_integrity_gate(),
        version_coverage_gate(),
        freeze_manifest_gate(),
        worktree_gate(),
    ]


def release_decision(gates: list[Gate]) -> tuple[str, str]:
    blocked = [gate for gate in gates if gate.status == "blocked"]
    manual = [
        gate
        for gate in gates
        if gate.status in {"pending_author_verification", "ready_after_manual_blockers"}
    ]
    if blocked:
        return "do_not_release", ";".join(gate.gate_id for gate in blocked)
    if manual:
        return "hold_for_manual_confirmation", ";".join(gate.gate_id for gate in manual)
    return "ready_to_tag_v0.1.1", "none"


def write_tsv(gates: list[Gate], decision: str, blocking: str) -> None:
    OUT_TSV.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_TSV.with_suffix(OUT_TSV.suffix + ".tmp")
    fieldnames = [
        "gate_id",
        "status",
        "severity",
        "evidence_path",
        "required_action",
        "notes",
        "release_decision",
        "blocking_or_holding_gates",
    ]
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for gate in gates:
            writer.writerow(
                {
                    "gate_id": gate.gate_id,
                    "status": gate.status,
                    "severity": gate.severity,
                    "evidence_path": gate.evidence_path,
                    "required_action": gate.required_action,
                    "notes": gate.notes,
                    "release_decision": decision,
                    "blocking_or_holding_gates": blocking,
                }
            )
    tmp.replace(OUT_TSV)


def write_markdown(gates: list[Gate], decision: str, blocking: str) -> None:
    status_counts: dict[str, int] = {}
    for gate in gates:
        status_counts[gate.status] = status_counts.get(gate.status, 0) + 1
    lines = [
        "# RMTGuard v0.1.1 release preflight",
        "",
        "Generated by `python scripts/build_v0_1_1_release_preflight.py`.",
        "",
        "## Boundary",
        "",
        "This is a no-action preflight. It does not create a Git tag, GitHub Release, or Zenodo DOI. Its purpose is to prevent a premature release before the manuscript-facing files and author-controlled statements are frozen.",
        "",
        "## Decision",
        "",
        f"- Release decision: `{decision}`.",
        f"- Blocking or holding gates: `{blocking}`.",
        "- Candidate release: `v0.1.1`.",
        "",
        "## Status Counts",
        "",
    ]
    lines.extend(f"- `{key}`: `{value}`" for key, value in sorted(status_counts.items()))
    lines.extend(
        [
            "",
            "## Gate Table",
            "",
            "| Gate | Status | Severity | Required action | Notes |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for gate in gates:
        notes = gate.notes.replace("|", "/")
        action = gate.required_action.replace("|", "/")
        lines.append(f"| {gate.gate_id} | {gate.status} | {gate.severity} | {action} | {notes} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `do_not_release` means at least one hard blocker remains; do not create a release.",
            "- `hold_for_manual_confirmation` means the technical package is close, but author-controlled confirmations or final version coverage still hold the release.",
            "- `ready_to_tag_v0.1.1` should occur only after all author confirmations, final figure/source-data freeze, clean worktree, and claim-integrity checks pass.",
        ]
    )
    tmp = OUT_MD.with_suffix(OUT_MD.suffix + ".tmp")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    tmp.replace(OUT_MD)


def main() -> int:
    gates = build_gates()
    decision, blocking = release_decision(gates)
    write_tsv(gates, decision, blocking)
    write_markdown(gates, decision, blocking)
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print(decision)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
