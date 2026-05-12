"""Build the high-impact submission dashboard for RMTGuard.

Author: RMTGuard contributors
Date: 2026-05-12
Purpose: Merge the current 20-50 JIF gap assessment, author confirmation
packet, v0.1.1 release preflight, Figure/source audit, reporting summary, and
Nature Methods go/no-go decision into one auditable dashboard.
Data source: Local generated TSV reports under results/submission/ and
results/gates/.
Method notes: This is a project-management and claim-control artifact. It does
not guarantee journal acceptance and does not replace final author or journal
policy checks.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

GAP = ROOT / "results" / "submission" / "jif20_50_gap_assessment.tsv"
PREFLIGHT = ROOT / "results" / "submission" / "v0_1_1_release_preflight.tsv"
AUTHOR_CONFIRM = ROOT / "results" / "submission" / "author_declaration_confirmation_checklist.tsv"
AUTHOR_EMAIL = ROOT / "manuscript" / "author_declaration_confirmation_email_draft.md"
AUTHOR_DELIVERY = ROOT / "output" / "delivery" / "RMTGuard_author_confirmation_delivery_2026-05-12.zip"
AUTHOR_REPLY_TRIAGE = ROOT / "docs" / "author_reply_triage.md"
FIGURE_AUDIT = ROOT / "results" / "submission" / "figure_caption_source_audit.tsv"
REPORTING = ROOT / "results" / "submission" / "reporting_summary_draft.tsv"
GO_NO_GO = ROOT / "results" / "submission" / "nature_methods_go_no_go_final.tsv"
SUBMISSION_GUARD = ROOT / "results" / "submission" / "submission_guard.tsv"
CLAIM_LINT = ROOT / "results" / "submission" / "claim_boundary_lint.tsv"
CLAIM_TRACE = ROOT / "results" / "submission" / "claim_traceability.tsv"
FREEZE = ROOT / "results" / "submission" / "current_evidence_freeze_manifest.tsv"

OUT_TSV = ROOT / "results" / "submission" / "high_impact_submission_dashboard.tsv"
OUT_MD = ROOT / "docs" / "high_impact_submission_dashboard.md"


@dataclass(frozen=True)
class DashboardRow:
    lane: str
    status: str
    severity: str
    evidence_path: str
    blocker: str
    next_action: str
    journal_implication: str
    owner: str


FIELDNAMES = [
    "lane",
    "status",
    "severity",
    "evidence_path",
    "blocker",
    "next_action",
    "journal_implication",
    "owner",
]


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


def write_tsv(path: Path, rows: list[DashboardRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)
    tmp.replace(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def row_by(rows: list[dict[str, str]], key: str, value: str) -> dict[str, str]:
    return next((row for row in rows if row.get(key) == value), {})


def score_summary(gap_rows: list[dict[str, str]]) -> tuple[int, int, str]:
    score = sum(int(row.get("current_score", "0") or "0") for row in gap_rows)
    weight = sum(int(row.get("weight", "0") or "0") for row in gap_rows)
    status = "not_ready"
    if score >= 95:
        status = "near_submission_ready_after_manual_checks"
    elif score >= 90:
        status = "strong_but_blocked"
    return score, weight, status


def count_status(rows: list[dict[str, str]], field: str, values: set[str]) -> int:
    return sum(1 for row in rows if row.get(field) in values)


def build_rows() -> list[DashboardRow]:
    gap_rows = read_tsv(GAP)
    preflight_rows = read_tsv(PREFLIGHT)
    author_rows = read_tsv(AUTHOR_CONFIRM)
    figure_rows = read_tsv(FIGURE_AUDIT)
    reporting_rows = read_tsv(REPORTING)
    go_rows = read_tsv(GO_NO_GO)
    guard_rows = read_tsv(SUBMISSION_GUARD)
    lint_rows = read_tsv(CLAIM_LINT)
    trace_rows = read_tsv(CLAIM_TRACE)
    freeze_rows = read_tsv(FREEZE)

    score, weight, score_status = score_summary(gap_rows)
    scientific = row_by(gap_rows, "domain", "scientific_core")
    benchmark = row_by(gap_rows, "domain", "benchmark_breadth_and_baselines")
    calibration = row_by(gap_rows, "domain", "calibration_statistics")
    bio = row_by(gap_rows, "domain", "biological_showcase")
    claim_control = row_by(gap_rows, "domain", "manuscript_claim_control")

    release_decision = row_by(preflight_rows, "gate_id", "git_worktree_clean")
    author_gate = row_by(preflight_rows, "gate_id", "author_declarations")
    figure_gate = row_by(preflight_rows, "gate_id", "figure_caption_source_audit")
    reporting_gate = row_by(preflight_rows, "gate_id", "reporting_summary")
    version_gate = row_by(preflight_rows, "gate_id", "version_coverage")
    claim_gate = row_by(preflight_rows, "gate_id", "claim_integrity")

    full_submission = row_by(go_rows, "decision_id", "nature_methods_full_submission")
    presubmission = row_by(go_rows, "decision_id", "nature_methods_presubmission_inquiry")
    fallback = row_by(go_rows, "decision_id", "genome_biology_fallback")

    author_pending = len(author_rows)
    figure_pending = count_status(figure_rows, "audit_status", {"ready_pending_author_ack"})
    reporting_pending = count_status(reporting_rows, "status", {"pending_manual", "needs_author_completion"})
    lint_bad = count_status(lint_rows, "status", {"violation"})
    trace_bad = count_status(trace_rows, "trace_status", {"violation"})
    missing_freeze = count_status(freeze_rows, "exists", {"False", "false", ""})

    guard_decision = row_by(guard_rows, "guard_id", "submission_decision")
    if not guard_decision:
        guard_decision = row_by(guard_rows, "check_id", "submission_decision")

    return [
        DashboardRow(
            "overall_20_50_readiness",
            score_status,
            "major_hold",
            _rel(GAP),
            f"readiness={score}/{weight}; strict 20-50 status remains not ready",
            "Treat Nature Methods as the only strict 20-50 target and keep Genome Biology as fallback.",
            "Strong package, but not a full 20-50 submission until manual and scientific blockers close.",
            "Codex + authors",
        ),
        DashboardRow(
            "nature_methods_full_submission",
            full_submission.get("decision", "no_go"),
            "hard_stop",
            _rel(GO_NO_GO),
            full_submission.get("reason", "Full submission remains blocked."),
            full_submission.get("required_next_action", "Do not submit full manuscript yet."),
            "Full Nature Methods submission remains no-go.",
            "Codex + corresponding authors",
        ),
        DashboardRow(
            "nature_methods_presubmission",
            presubmission.get("decision", "hold"),
            "manual_hold",
            _rel(GO_NO_GO),
            presubmission.get("reason", "Presubmission remains on hold."),
            "Obtain corresponding-author Figure 4 acknowledgement, then do one final route-policy check.",
            "Presubmission inquiry can be considered only after author acknowledgement.",
            "Corresponding authors",
        ),
        DashboardRow(
            "genome_biology_fallback",
            fallback.get("decision", "ready_if_nature_methods_not_encouraging"),
            "fallback_ready_with_reframe",
            _rel(GO_NO_GO),
            "Fallback is scientifically realistic but not strict 20-50 by current JIF.",
            "Keep a Genome Biology-style reproducible workflow framing ready.",
            "Best realistic fallback if Nature Methods does not encourage submission.",
            "Codex",
        ),
        DashboardRow(
            "author_declarations",
            author_gate.get("status", "blocked"),
            "manual_blocker",
            f"{_rel(AUTHOR_CONFIRM)};{_rel(ROOT / 'docs' / 'author_declaration_confirmation_packet.md')};{_rel(AUTHOR_EMAIL)};{_rel(AUTHOR_DELIVERY)};{_rel(AUTHOR_REPLY_TRIAGE)}",
            f"{author_pending} author-confirmation items remain.",
            "A preliminary mentor OK is recorded; obtain explicit final wording for funding, COI, postal code, CRediT, reporting summary, and named Figure 4 acknowledgement.",
            "Blocks v0.1.1 release metadata and any editor-facing package.",
            "All authors",
        ),
        DashboardRow(
            "figure4_author_acknowledgement",
            figure_gate.get("status", "blocked"),
            "manual_blocker",
            _rel(FIGURE_AUDIT),
            f"{figure_pending} display item needs author acknowledgement.",
            "Yi Miao and Han Yan must confirm bounded Figure 4 wording in writing.",
            "Blocks Nature Methods presubmission and Figure 4 use in external-facing materials.",
            "Yi Miao; Han Yan",
        ),
        DashboardRow(
            "reporting_summary",
            reporting_gate.get("status", "pending_author_verification"),
            "manual_blocker",
            _rel(REPORTING),
            f"{reporting_pending} reporting-summary rows need author/manual verification.",
            "Verify statistics, multiple testing, software, data availability, ethics, and AI-use rows.",
            "Blocks official Nature Portfolio form completion.",
            "Corresponding authors",
        ),
        DashboardRow(
            "v0_1_1_release_coverage",
            version_gate.get("status", "ready_after_manual_blockers"),
            "release_hold",
            _rel(PREFLIGHT),
            version_gate.get("notes", "v0.1.1 is needed only after manual blockers resolve."),
            "Do not tag or archive v0.1.1 until author declarations and final figure/source freeze are complete.",
            "Prevents a DOI that does not match submitted files.",
            "Codex",
        ),
        DashboardRow(
            "git_cleanliness",
            release_decision.get("status", "missing"),
            "controlled",
            _rel(PREFLIGHT),
            release_decision.get("notes", "Worktree status is tracked by preflight."),
            "Keep committing generated control artifacts after each change.",
            "Engineering state is controlled; this is not the limiting factor.",
            "Codex",
        ),
        DashboardRow(
            "scientific_core",
            scientific.get("status", "partial"),
            "science_gap",
            scientific.get("evidence", _rel(GAP)),
            scientific.get("blocking_items", "stability_advantage"),
            scientific.get("next_supplement", "Do not claim stability superiority without stronger evidence."),
            "The largest Nature Methods risk is still method-performance novelty, not packaging.",
            "Codex",
        ),
        DashboardRow(
            "benchmark_breadth_and_baselines",
            benchmark.get("status", "controlled"),
            "controlled_with_boundary",
            benchmark.get("evidence", _rel(GAP)),
            benchmark.get("blocking_items", "none"),
            benchmark.get("next_supplement", "Freeze comparator table."),
            "Good enough for a bounded workflow paper; still not universal superiority evidence.",
            "Codex",
        ),
        DashboardRow(
            "calibration_statistics",
            calibration.get("status", "controlled"),
            "controlled",
            calibration.get("evidence", _rel(GAP)),
            calibration.get("blocking_items", "none"),
            calibration.get("next_supplement", "Add optional dropout/batch grids only if central."),
            "Supports false-signal and rare-state claim boundaries.",
            "Codex",
        ),
        DashboardRow(
            "biological_showcase",
            bio.get("status", "pathway_atlas_supported_with_limits"),
            "manual_hold",
            bio.get("evidence", _rel(GAP)),
            bio.get("blocking_items", "PDAC_TME_corresponding_author_acknowledgement"),
            bio.get("next_supplement", "Obtain author acknowledgement."),
            "Figure 4 is usable only as a bounded public-data showcase.",
            "Corresponding authors",
        ),
        DashboardRow(
            "claim_integrity",
            claim_gate.get("status", "pass"),
            "controlled",
            f"{_rel(CLAIM_LINT)};{_rel(CLAIM_TRACE)}",
            f"lint_violations={lint_bad}; trace_violations={trace_bad}",
            "Keep claim lint and traceability at zero after every manuscript change.",
            "Protects against overclaim-driven rejection.",
            "Codex",
        ),
        DashboardRow(
            "evidence_freeze",
            "pass" if missing_freeze == 0 else "blocked",
            "controlled" if missing_freeze == 0 else "submission_blocker",
            _rel(FREEZE),
            f"missing_freeze_items={missing_freeze}",
            "Refresh after every figure, manuscript, or release-control change.",
            "Source-data traceability is currently controlled.",
            "Codex",
        ),
        DashboardRow(
            "submission_guard",
            guard_decision.get("decision", guard_decision.get("status", "do_not_submit")),
            "hard_stop",
            _rel(SUBMISSION_GUARD),
            "Submission guard remains the final local stop rule.",
            "Run the submission guard again only after author confirmations and final evidence freeze.",
            "Do not submit while guard is do_not_submit or missing.",
            "Codex",
        ),
    ]


def status_counts(rows: list[DashboardRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.severity] = counts.get(row.severity, 0) + 1
    return counts


def build_markdown(rows: list[DashboardRow]) -> str:
    counts = status_counts(rows)
    hard_or_manual = [
        row for row in rows if row.severity in {"hard_stop", "manual_blocker", "manual_hold", "science_gap"}
    ]
    lines = [
        "# RMTGuard high-impact submission dashboard",
        "",
        f"Generated: {date.today().isoformat()}",
        "Generated by `python scripts/build_high_impact_submission_dashboard.py`.",
        "",
        "## Mentor Decision",
        "",
        "- Current action: `continue_development_do_not_submit`.",
        "- Strict 20-50 JIF route: `Nature Methods only after gate recovery`.",
        "- Realistic fallback: `Genome Biology-style reproducible workflow`, if strict 20-50 is relaxed.",
        "- Acceptance guarantee: `impossible`.",
        "",
        "## Severity Counts",
        "",
    ]
    for key, value in sorted(counts.items()):
        lines.append(f"- `{key}`: `{value}`")

    lines.extend(
        [
            "",
            "## Dashboard",
            "",
            "| Lane | Status | Severity | Blocker | Next action | Owner |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        blocker = row.blocker.replace("|", "/")
        next_action = row.next_action.replace("|", "/")
        lines.append(
            f"| {row.lane} | {row.status} | {row.severity} | {blocker} | {next_action} | {row.owner} |"
        )

    lines.extend(
        [
            "",
            "## What This Means",
            "",
            "The package is no longer blocked by public-code release engineering. The remaining blockers are concentrated in author-controlled declarations, Figure 4 acknowledgement, reporting-summary verification, and the scientific claim that real-data stability advantage is not yet strong enough for unrestricted Nature Methods language.",
            "",
            "## What We Can Safely Say Now",
            "",
            "- RMTGuard is an open, DOI-archived, callability-aware random-matrix workflow for scRNA-seq noise-control diagnostics.",
            "- The current evidence supports transparent no-call/caveat reporting and bounded false-signal control under tested settings.",
            "- PDAC/TME can be shown only as a public-data application with pathway/atlas support, not as a mechanism, clinical, prognosis, treatment-response, spatial, or protein-validation discovery.",
            "",
            "## What We Must Not Say Yet",
            "",
            "- Do not claim broad real-data stability superiority.",
            "- Do not claim Nature Methods submission readiness.",
            "- Do not claim v0.1.1 DOI coverage until a new release is actually tagged and archived.",
            "- Do not send the presubmission inquiry while Figure 4 acknowledgement is missing.",
            "",
            "## Next Execution Order",
            "",
            "1. Close author declarations and Figure 4 acknowledgement.",
            "2. Refresh reporting summary and v0.1.1 preflight.",
            "3. Decide whether to add one more high-value science experiment or route directly to presubmission.",
            "4. If authors confirm, prepare v0.1.1 GitHub Release and Zenodo archive.",
            "5. Re-run claim lint, traceability, evidence freeze, Gantt, and shared export.",
            "",
            "## Immediate Blockers",
            "",
        ]
    )
    for row in hard_or_manual:
        lines.append(f"- `{row.lane}`: {row.blocker} Next: {row.next_action}")

    lines.extend(
        [
            "",
            "## Source Files",
            "",
        ]
    )
    seen = []
    for row in rows:
        for path in row.evidence_path.split(";"):
            if path and path not in seen:
                seen.append(path)
                lines.append(f"- `{path}`")
    return "\n".join(lines)


def main() -> int:
    rows = build_rows()
    write_tsv(OUT_TSV, rows)
    write_text(OUT_MD, build_markdown(rows))
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print("continue_development_do_not_submit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
