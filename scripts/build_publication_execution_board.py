from __future__ import annotations

"""Build the publication execution board for RMTGuard.

Author: RMTGuard development team
Date: 2026-04-30
Purpose: Convert the 20-50 JIF publication route into an auditable ownership
board with explicit external blockers.
Data source: Generated gate, compliance, release, and journal-route tables.
Method notes: This file records execution responsibility. It is not a journal
acceptance guarantee.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_TSV = ROOT / "results" / "submission" / "publication_execution_board.tsv"
OUT_MD = ROOT / "docs" / "publication_execution_board.md"

COMPLIANCE = ROOT / "results" / "submission" / "nature_methods_compliance_audit.tsv"
RELEASE_READINESS = ROOT / "results" / "release" / "release_readiness.tsv"
PRESUBMISSION = ROOT / "results" / "submission" / "presubmission_gatekeeper.tsv"
JOURNAL_ROUTE = ROOT / "results" / "gates" / "publication_20_50_decision.tsv"


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
    return {
        row.get(key, ""): row.get("status", "pending") for row in rows if row.get(key)
    }


def _journal_row(rows: list[dict[str, str]], journal: str) -> dict[str, str]:
    return next((row for row in rows if row.get("journal") == journal), {})


def _board_row(
    step_id: str,
    execution_phase: str,
    status: str,
    owner: str,
    codex_can_execute: str,
    external_input_required: str,
    evidence_path: Path | str,
    next_action: str,
    stop_condition: str,
    notes: str,
) -> dict[str, str]:
    evidence = _rel(evidence_path) if isinstance(evidence_path, Path) else evidence_path
    return {
        "step_id": step_id,
        "execution_phase": execution_phase,
        "status": status,
        "owner": owner,
        "codex_can_execute": codex_can_execute,
        "external_input_required": external_input_required,
        "evidence_path": evidence,
        "next_action": next_action,
        "stop_condition": stop_condition,
        "notes": notes,
    }


def build_board_rows(
    compliance_rows: list[dict[str, str]],
    release_rows: list[dict[str, str]],
    presubmission_rows: list[dict[str, str]],
    journal_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    compliance = _status_map(compliance_rows, "check_id")
    release = _status_map(release_rows, "check_id")
    presubmission = _status_map(presubmission_rows, "check_id")
    nature = _journal_row(journal_rows, "Nature Methods")
    nat_biotech = _journal_row(journal_rows, "Nature Biotechnology")
    genome_biology = _journal_row(journal_rows, "Genome Biology")

    repo_ready = (
        release.get("repository_url") == "pass"
        and release.get("github_remote") == "pass"
    )
    doi_ready = release.get("zenodo_doi") == "pass"
    compliance_blocked = any(row.get("status") == "blocked" for row in compliance_rows)
    manual_pending = any(
        row.get("status", "").startswith("pending") for row in compliance_rows
    )
    presubmission_ready = presubmission.get("nature_methods_submission_ready") == "pass"

    return [
        _board_row(
            "01_lock_claim_boundary",
            "local_manuscript",
            "pass" if compliance.get("claim_boundary") == "pass" else "blocked",
            "Codex",
            "yes",
            "none",
            COMPLIANCE,
            "Keep PBMC68k as diagnostic no-call and prohibit broad fixed-PC superiority claims.",
            "Stop if manuscript text claims universal superiority or biological discovery from no-call outputs.",
            "This is the main guard against overclaiming the 20-50 JIF route.",
        ),
        _board_row(
            "02_create_public_github_repository",
            "external_release",
            "pass" if repo_ready else "blocked_external",
            "GitHub account owner",
            "no_without_authenticated_account",
            "real public GitHub repository URL",
            RELEASE_READINESS,
            "Create an empty public repository, preferably `https://github.com/<owner>/rmtguard`.",
            "Stop if repository URL is missing or still contains `your-lab/rmtguard`.",
            "This is required before code availability can pass.",
        ),
        _board_row(
            "03_update_repository_metadata",
            "local_release",
            (
                "pass"
                if release.get("repository_url") == "pass"
                else "waiting_external_input"
            ),
            "Codex",
            "yes_after_repo_url",
            "real repository URL",
            RELEASE_READINESS,
            "Run `python scripts/update_repository_metadata.py --repo-url <URL> --execute`, then regenerate release manifests.",
            "Stop if metadata still has placeholder repository URLs.",
            "This step is local and can be completed immediately after a real repository exists.",
        ),
        _board_row(
            "04_push_source_and_tag",
            "external_release",
            (
                "pass"
                if release.get("github_remote") == "pass"
                and release.get("github_release_tag") == "pass"
                else "blocked_external"
            ),
            "GitHub account owner + Codex",
            "yes_after_git_auth",
            "GitHub authentication and remote",
            RELEASE_READINESS,
            "Push the current commit and tag `v0.1.0-rc5`; verify the GitHub file list excludes raw and processed data.",
            "Stop if GitHub auth is absent or raw data would be pushed.",
            "The local tag exists, but the remote release object does not.",
        ),
        _board_row(
            "05_create_github_release_and_zenodo_doi",
            "external_release",
            "pass" if doi_ready else "blocked_external",
            "GitHub/Zenodo account owner",
            "no_without_authenticated_accounts",
            "GitHub Release plus Zenodo DOI",
            RELEASE_READINESS,
            "Create the GitHub Release, archive it with Zenodo, and record the DOI locally.",
            "Stop if Zenodo DOI is missing.",
            "This is the hard blocker for Nature Portfolio code availability best practice.",
        ),
        _board_row(
            "06_refresh_gates_after_external_release",
            "local_validation",
            "pass" if presubmission_ready else "waiting_external_input",
            "Codex",
            "yes_after_repo_and_doi",
            "real repository URL and DOI",
            PRESUBMISSION,
            "Run release manifests, gate updater, compliance audit, tests, and presubmission package rebuild.",
            "Stop if `nature_methods_submission_ready` remains blocked.",
            "This converts external release evidence into the formal submission gate.",
        ),
        _board_row(
            "07_complete_reporting_summary",
            "manual_submission",
            "pending_manual" if manual_pending else "pass",
            "Corresponding author",
            "assist_only",
            "official Nature Portfolio submission form",
            COMPLIANCE,
            "Complete the official reporting summary during final submission assembly.",
            "Stop if required reporting-summary fields cannot be supported by source data.",
            "Codex can draft answers but cannot truthfully submit the official form without author verification.",
        ),
        _board_row(
            "08_nature_methods_submission_decision",
            "journal_submission",
            "pass" if presubmission_ready and not compliance_blocked else "blocked",
            "Corresponding author + Codex",
            "assist_only",
            "all gates pass plus manual author approval",
            PRESUBMISSION,
            "Submit to Nature Methods only after code availability, DOI, reporting summary, and claim boundary are all resolved.",
            "Stop if any compliance row is blocked.",
            f"Current route: {nature.get('fit_for_current_project', 'unknown')}; readiness={nature.get('current_readiness', 'unknown')}.",
        ),
        _board_row(
            "09_20_50_fallback_decision",
            "journal_strategy",
            "ready_for_decision_after_release",
            "Codex",
            "yes",
            "Nature Methods editorial outcome or explicit pre-submission downgrade",
            JOURNAL_ROUTE,
            "If Nature Methods is too broad/strict after release, consider Nature Biotechnology only as stretch; otherwise relax strict IF20 and move to Genome Biology/Cell Genomics style route.",
            "Stop if fallback text hides the fact that Genome Biology is outside strict 20-50 JIF in the current table.",
            f"Nature Biotechnology: {nat_biotech.get('fit_for_current_project', 'unknown')}; Genome Biology: {genome_biology.get('fit_for_current_project', 'unknown')}.",
        ),
    ]


def _overall_status(rows: list[dict[str, str]]) -> str:
    if any(row["status"] in {"blocked", "blocked_external"} for row in rows):
        return "blocked_before_submission"
    if any(
        row["status"].startswith("waiting") or row["status"].startswith("pending")
        for row in rows
    ):
        return "pending_before_submission"
    return "ready_for_author_submission_review_not_acceptance_guaranteed"


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    blocked = [row for row in rows if row["status"] in {"blocked", "blocked_external"}]
    waiting = [
        row
        for row in rows
        if row["status"].startswith("waiting") or row["status"].startswith("pending")
    ]
    lines = [
        "# Publication Execution Board",
        "",
        "This file is generated by `python scripts/build_publication_execution_board.py`.",
        "",
        "## Current Decision",
        "",
        f"- Overall status: `{_overall_status(rows)}`.",
        "- Acceptance guarantee: `impossible`; the enforceable target is a complete, auditable 20-50 JIF submission package.",
        "- Active 20-50 target: `Nature Methods`.",
        "- Hard rule: do not submit while any `blocked` or `blocked_external` row remains.",
        "",
        "## Blocking Rows",
        "",
    ]
    if blocked:
        lines.extend(
            f"- `{row['step_id']}` ({row['owner']}): {row['next_action']}"
            for row in blocked
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Waiting Or Manual Rows", ""])
    if waiting:
        lines.extend(
            f"- `{row['step_id']}` ({row['status']}): {row['external_input_required']}"
            for row in waiting
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Execution Rows", ""])
    for row in rows:
        lines.extend(
            [
                f"### {row['step_id']}",
                "",
                f"- Status: `{row['status']}`",
                f"- Owner: {row['owner']}",
                f"- Codex can execute: `{row['codex_can_execute']}`",
                f"- External input required: {row['external_input_required']}",
                f"- Evidence: `{row['evidence_path']}`",
                f"- Next action: {row['next_action']}",
                f"- Stop condition: {row['stop_condition']}",
                f"- Notes: {row['notes']}",
                "",
            ]
        )
    return lines


def build_outputs() -> list[dict[str, str]]:
    rows = build_board_rows(
        _read_tsv(COMPLIANCE),
        _read_tsv(RELEASE_READINESS),
        _read_tsv(PRESUBMISSION),
        _read_tsv(JOURNAL_ROUTE),
    )
    _write_tsv(
        OUT_TSV,
        rows,
        [
            "step_id",
            "execution_phase",
            "status",
            "owner",
            "codex_can_execute",
            "external_input_required",
            "evidence_path",
            "next_action",
            "stop_condition",
            "notes",
        ],
    )
    _write_text(OUT_MD, build_markdown(rows))
    return rows


def main() -> int:
    rows = build_outputs()
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print(f"overall_status\t{_overall_status(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
