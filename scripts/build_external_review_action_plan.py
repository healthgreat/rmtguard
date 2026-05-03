from __future__ import annotations

"""Build an action plan from external RMTGuard pre-review feedback.

Author: RMTGuard development team
Date: 2026-05-01
Purpose: Convert P0/P1 external-review feedback into an ordered execution queue
for public release, route reframing, benchmarks, calibration, ablation,
biological showcase depth, and figure/reporting cleanup.
Data source: `results/submission/external_review_feedback_triage.tsv`.
Method notes: This script does not mark feedback as resolved. It only exposes
which work packages must be completed before any journal route can be upgraded.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIAGE = ROOT / "results" / "submission" / "external_review_feedback_triage.tsv"
ROUTE_REFRAME = ROOT / "results" / "submission" / "route_reframe_decision.tsv"
CALIBRATION_NULL = ROOT / "results" / "calibration" / "realistic_null_summary.tsv"
CALIBRATION_POWER = ROOT / "results" / "calibration" / "rare_state_power_summary.tsv"
OUT_TSV = ROOT / "results" / "submission" / "external_review_action_plan.tsv"
OUT_MD = ROOT / "docs" / "external_review_action_plan.md"

FIELDNAMES = [
    "action_id",
    "priority",
    "phase",
    "status",
    "owner",
    "source_feedback_ids",
    "required_action",
    "success_gate",
    "evidence_path",
    "route_effect",
]

ACTIVE_STATUSES = {"", "open", "active", "blocked", "needs_action", "pending", "todo"}
BLOCKING_STATUSES = {
    "blocked",
    "implemented_pending_feedback_close",
    "partial_null_pass_power_fail",
    "partial_null_pass_power_improved",
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


def _float(value: str, default: float = float("nan")) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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


def _active_feedback_ids(
    triage_rows: list[dict[str, str]], feedback_ids: set[str]
) -> list[str]:
    active: list[str] = []
    for row in triage_rows:
        feedback_id = row.get("feedback_id", "")
        status = row.get("status", "").strip().lower()
        if feedback_id in feedback_ids and status in ACTIVE_STATUSES:
            active.append(feedback_id)
    return active


def _status_for(
    triage_rows: list[dict[str, str]],
    feedback_ids: set[str],
    implemented: bool = False,
) -> str:
    if implemented:
        return "implemented_pending_feedback_close"
    active = _active_feedback_ids(triage_rows, feedback_ids)
    return "blocked" if active else "ready_to_verify"


def _row(
    action_id: str,
    priority: str,
    phase: str,
    status: str,
    owner: str,
    source_feedback_ids: list[str],
    required_action: str,
    success_gate: str,
    evidence_path: Path,
    route_effect: str,
) -> dict[str, str]:
    return {
        "action_id": action_id,
        "priority": priority,
        "phase": phase,
        "status": status,
        "owner": owner,
        "source_feedback_ids": ";".join(source_feedback_ids) or "none",
        "required_action": required_action,
        "success_gate": success_gate,
        "evidence_path": _rel(evidence_path),
        "route_effect": route_effect,
    }


def _route_reframe_complete(route_reframe_rows: list[dict[str, str]]) -> bool:
    return any(
        row.get("item_id") == "overall_route_reframe"
        and row.get("status") == "local_reframe_complete"
        for row in route_reframe_rows
    )


def _calibration_status() -> str:
    """Return current status for the realistic-null/power work package."""

    if not CALIBRATION_NULL.exists() or not CALIBRATION_POWER.exists():
        return "blocked"
    null_rows = _read_tsv(CALIBRATION_NULL)
    power_rows = _read_tsv(CALIBRATION_POWER)
    if not null_rows or not power_rows:
        return "blocked"
    max_false_signal = max(
        _float(row.get("false_signal_rate", "")) for row in null_rows
    )
    max_false_call = max(_float(row.get("false_call_rate", "")) for row in null_rows)
    powers = [_float(row.get("power", "")) for row in power_rows]
    max_power = max(powers)
    min_power = min(powers)
    null_controlled = max_false_signal <= 0.05 and max_false_call <= 0.05
    power_controlled = min_power >= 0.80
    if null_controlled and power_controlled:
        return "implemented_pending_feedback_close"
    if null_controlled and max_power >= 0.80:
        return "partial_null_pass_power_improved"
    if null_controlled and not power_controlled:
        return "partial_null_pass_power_fail"
    return "blocked"


def build_rows(
    triage_rows: list[dict[str, str]],
    route_reframe_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    route_reframe_rows = route_reframe_rows or []
    route_reframe_done = _route_reframe_complete(route_reframe_rows)
    packages = [
        (
            "01_public_release_doi",
            "P0",
            "release",
            {"SG-P0-001"},
            "Author + Codex",
            "Create public GitHub repository, push current release tag, create GitHub Release, archive with Zenodo, record DOI, and rerun release/submission gates.",
            "release_readiness rows repository_url, github_remote, github_release_tag, and zenodo_doi all pass.",
            ROOT / "results" / "release" / "release_readiness.tsv",
            "All routes remain blocked until this passes.",
        ),
        (
            "02_route_reframe_no_nature_methods",
            "P0",
            "journal_route",
            {"SG-P0-002", "SG-P0-003", "SG-P0-004", "SG-P1-010"},
            "Codex",
            "Freeze Nature Methods presubmission, reframe claims around callability/no-call diagnostics, and make Genome Biology conditional after public release.",
            "post_feedback_journal_route_gate remains pause_for_p0_feedback until P0 evidence is resolved or explicitly downgraded.",
            ROOT / "results" / "submission" / "post_feedback_journal_route_gate.tsv",
            "Nature Methods is no-go; Genome Biology is conditional after release and reframe.",
        ),
        (
            "03_manuscript_grade_stability_baselines",
            "P1",
            "benchmark",
            {"SG-P1-001", "SG-P1-002", "SG-P1-004"},
            "Codex",
            "Expand public datasets and rerun stability with at least 10 repeats, stronger Seurat/Scanpy/JackStraw/permutation baselines, confidence intervals, and cluster-number variance.",
            "updated stability benchmark shows transparent callability trade-offs and no unsupported superiority claims.",
            ROOT
            / "results"
            / "stability_benchmarks"
            / "stability_gate_diagnostics.tsv",
            "Required for any high-tier method route.",
        ),
        (
            "04_realistic_null_and_power_calibration",
            "P1",
            "statistics",
            {"SG-P1-003"},
            "Codex",
            "Add count-preserving nulls, dropout/library-size preserving permutations, paired tests, multiple-testing correction, and rare-state prevalence/effect-size power grids.",
            "count-preserving null false-positive rates remain controlled and rare-state power meets the pre-specified floor across the grid.",
            ROOT / "docs" / "realistic_null_power_calibration.md",
            "Current draft null control is useful and v3.3 improves rare-state power, but incomplete weak-effect/low-prevalence power still blocks stronger noise-control claims.",
        ),
        (
            "05_ablation_and_no_call_decision_map",
            "P1",
            "algorithm_diagnostics",
            {"SG-P1-006", "SG-P1-007"},
            "Codex",
            "Run component ablations and expose quantitative no-call reasons, thresholds, and a Figure 3 callability decision map.",
            "ablation table and no-call decision outputs are generated and referenced by figure/source-data manifests.",
            ROOT / "docs" / "no_call_benchmark.md",
            "Converts the useful part of RMTGuard into the main defensible claim.",
        ),
        (
            "06_biological_showcase_decision",
            "P1",
            "application",
            {"SG-P1-005"},
            "Codex",
            "Either deepen PDAC/TME with differential expression, pathway enrichment, trajectory or published-atlas validation, or demote it to supplement.",
            "PDAC/TME depth audit either passes for a bounded main use case or is explicitly demoted.",
            ROOT / "docs" / "pdac_tme_showcase_depth.md",
            "Determines whether Cell Genomics or Nature Communications remain plausible.",
        ),
        (
            "07_figures_reporting_and_claim_language",
            "P1",
            "manuscript_package",
            {"SG-P1-008", "SG-P1-009", "SG-CLAIM-001"},
            "Codex + corresponding author",
            "Regenerate final figures, source-data tables, ethics/privacy wording, reporting summary, and claim-downgraded abstract language.",
            "claim lint and traceability remain pass, and figure manifests exactly reproduce manuscript numbers.",
            ROOT / "results" / "submission" / "claim_boundary_lint.tsv",
            "Required before any editor-facing package.",
        ),
    ]

    rows: list[dict[str, str]] = []
    for (
        action_id,
        priority,
        phase,
        feedback_ids,
        owner,
        required_action,
        success_gate,
        evidence_path,
        route_effect,
    ) in packages:
        source_ids = sorted(feedback_ids)
        implemented = (
            action_id == "02_route_reframe_no_nature_methods" and route_reframe_done
        )
        status = _status_for(triage_rows, feedback_ids, implemented=implemented)
        if action_id == "04_realistic_null_and_power_calibration":
            status = _calibration_status()
        rows.append(
            _row(
                action_id,
                priority,
                phase,
                status,
                owner,
                source_ids,
                required_action,
                success_gate,
                evidence_path,
                route_effect,
            )
        )

    unresolved = [
        row["action_id"] for row in rows if row["status"] in BLOCKING_STATUSES
    ]
    rows.append(
        _row(
            "overall_external_review_action_plan",
            "P0",
            "summary",
            "blocked_before_submission" if unresolved else "ready_for_route_recheck",
            "Codex + corresponding author",
            unresolved,
            "Complete or explicitly downgrade all blocked action packages, then rerun triage, route, transfer, reviewer-defense, claim, and release gates.",
            "overall_post_feedback_route is no longer pause_for_p0_feedback and submission_guard remains internally consistent.",
            OUT_TSV,
            "No Nature Methods or Genome Biology submission while this row is blocked.",
        )
    )
    return rows


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    overall = next(
        (
            row
            for row in rows
            if row["action_id"] == "overall_external_review_action_plan"
        ),
        {},
    )
    lines = [
        "# External Review Action Plan",
        "",
        "This file is generated by `python scripts/build_external_review_action_plan.py`.",
        "",
        "Acceptance guarantee: `impossible`.",
        "This plan translates SuperGrok-style external pre-review feedback into ordered work packages.",
        "",
        "## Overall Decision",
        "",
        f"- Status: `{overall.get('status', 'missing')}`",
        f"- Blocking action packages: `{overall.get('source_feedback_ids', 'missing')}`",
        f"- Required action: {overall.get('required_action', 'missing')}",
        "",
        "## Ordered Actions",
        "",
    ]
    for row in rows:
        if row["action_id"] == "overall_external_review_action_plan":
            continue
        lines.extend(
            [
                f"### {row['action_id']}",
                "",
                f"- Priority: `{row['priority']}`",
                f"- Phase: `{row['phase']}`",
                f"- Status: `{row['status']}`",
                f"- Owner: `{row['owner']}`",
                f"- Source feedback IDs: `{row['source_feedback_ids']}`",
                f"- Required action: {row['required_action']}",
                f"- Success gate: {row['success_gate']}",
                f"- Evidence: `{row['evidence_path']}`",
                f"- Route effect: {row['route_effect']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Execution Rule",
            "",
            "Resolve actions in order. Do not spend major compute on expanded benchmarks before the public release/DOI blocker is cleared unless the author explicitly chooses to continue development without submission.",
            "Do not upgrade claims; the default next narrative is `callability-aware diagnostic workflow`, not `stability-superior clustering method`.",
        ]
    )
    return lines


def main() -> int:
    rows = build_rows(_read_tsv(TRIAGE), _read_tsv(ROUTE_REFRAME))
    _write_tsv(OUT_TSV, rows)
    _write_text(OUT_MD, build_markdown(rows))
    overall = next(
        row for row in rows if row["action_id"] == "overall_external_review_action_plan"
    )
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print(f"overall\t{overall['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
