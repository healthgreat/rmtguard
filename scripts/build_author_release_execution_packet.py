from __future__ import annotations

"""Build the author release execution packet for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-01
Purpose: Reduce the remaining GitHub/Zenodo publication blocker to a minimal,
auditable author-action packet plus the local follow-up commands Codex can run
after the real repository URL and DOI exist.
Data source: Generated release readiness, public-release blocker, GitHub
handoff, and route-gate TSV files.
Method notes: This script does not create a GitHub repository, push code,
create a GitHub Release, or mint a Zenodo DOI. It only writes the execution
contract for those external actions.
"""

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RELEASE_READINESS = ROOT / "results" / "release" / "release_readiness.tsv"
PUBLIC_RELEASE_BLOCKERS = ROOT / "results" / "release" / "public_release_blockers.tsv"
GITHUB_HANDOFF = ROOT / "results" / "release" / "github_release_handoff_manifest.tsv"
POST_FEEDBACK_GATE = (
    ROOT / "results" / "submission" / "post_feedback_journal_route_gate.tsv"
)
GB_TRANSFER = ROOT / "results" / "submission" / "genome_biology_transfer_checklist.tsv"
REVIEWER_DEFENSE = ROOT / "results" / "submission" / "reviewer_defense_matrix.tsv"

OUT_TSV = ROOT / "results" / "release" / "author_release_execution_checklist.tsv"
OUT_MD = ROOT / "docs" / "author_release_execution_packet.md"
CODE_AVAILABILITY_DRAFT = (
    ROOT / "manuscript" / "code_availability_finalization_draft.md"
)

FIELDNAMES = [
    "action_id",
    "phase",
    "owner",
    "status",
    "blocking_input",
    "exact_action",
    "verification",
    "evidence_path",
    "stop_condition",
    "notes",
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


def _status_by(rows: list[dict[str, str]], key: str) -> dict[str, str]:
    return {row.get(key, ""): row.get("status", "") for row in rows}


def _by(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    return {row.get(key, ""): row for row in rows}


def _current_tag(handoff_rows: list[dict[str, str]]) -> str:
    source = _by(handoff_rows, "artifact").get("source_git_bundle", {})
    text = " ".join([source.get("path", ""), source.get("notes", "")])
    match = re.search(r"v\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?", text)
    return match.group(0) if match else "v0.1.0-rc8"


def _source_bundle(handoff_rows: list[dict[str, str]]) -> str:
    return (
        _by(handoff_rows, "artifact")
        .get("source_git_bundle", {})
        .get("path", "results/release/rmtguard_<tag>_source.bundle")
    )


def _route_status(rows: list[dict[str, str]], key: str) -> str:
    return _by(rows, "decision_id").get(key, {}).get("decision", "missing")


def _gb_status(rows: list[dict[str, str]], key: str) -> str:
    return _by(rows, "item_id").get(key, {}).get("status", "missing")


def _defense_status(rows: list[dict[str, str]], key: str) -> str:
    return _by(rows, "defense_id").get(key, {}).get("status", "missing")


def _row(
    action_id: str,
    phase: str,
    owner: str,
    status: str,
    blocking_input: str,
    exact_action: str,
    verification: str,
    evidence_path: Path,
    stop_condition: str,
    notes: str,
) -> dict[str, str]:
    return {
        "action_id": action_id,
        "phase": phase,
        "owner": owner,
        "status": status,
        "blocking_input": blocking_input,
        "exact_action": exact_action,
        "verification": verification,
        "evidence_path": _rel(evidence_path),
        "stop_condition": stop_condition,
        "notes": notes,
    }


def build_author_release_rows(
    release_rows: list[dict[str, str]],
    blocker_rows: list[dict[str, str]],
    handoff_rows: list[dict[str, str]],
    post_feedback_rows: list[dict[str, str]],
    gb_transfer_rows: list[dict[str, str]],
    reviewer_defense_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    release_status = _status_by(release_rows, "check_id")
    blocker_status = _status_by(blocker_rows, "blocker_id")
    tag = _current_tag(handoff_rows)
    bundle = _source_bundle(handoff_rows)
    repo_ready = (
        release_status.get("repository_url") == "pass"
        and release_status.get("github_remote") == "pass"
    )
    doi_ready = release_status.get("zenodo_doi") == "pass"
    release_tag_ready = release_status.get("github_release_tag") == "pass"

    rows = [
        _row(
            "01_verify_local_release_candidate",
            "local",
            "Codex",
            "pass" if release_tag_ready else "blocked_local",
            "clean checkout and local tag",
            f"Verify `{bundle}` and keep `{tag}` as the current local release candidate.",
            f"git bundle verify {bundle}",
            GITHUB_HANDOFF,
            "Stop if the bundle does not verify or does not point to the current tag.",
            f"Current tag candidate: {tag}.",
        ),
        _row(
            "02_create_empty_public_github_repository",
            "external",
            "Author",
            (
                "blocked_external"
                if release_status.get("repository_url") != "pass"
                else "pass"
            ),
            "public GitHub account",
            "Create an empty public repository named `rmtguard`; do not upload data through the browser.",
            "Repository URL has the form `https://github.com/<owner>/rmtguard`.",
            PUBLIC_RELEASE_BLOCKERS,
            "Stop if the repository is private, contains raw/processed data, or is not owned by the intended account.",
            "This is the first action the author must complete.",
        ),
        _row(
            "03_provide_repository_url_to_codex",
            "author_input",
            "Author",
            "waiting_external_input" if not repo_ready else "pass",
            "real repository URL",
            "Send Codex the public repository URL exactly once it exists.",
            "URL should not contain `your-lab/rmtguard`.",
            RELEASE_READINESS,
            "Stop if the URL is still a placeholder or points outside GitHub.",
            "After this input, Codex can update local metadata and prepare push commands.",
        ),
        _row(
            "04_update_metadata_and_push_source",
            "local_after_repo_url",
            "Codex + Author authentication",
            "ready_after_repo_url" if not repo_ready else "pass",
            "repository URL plus GitHub authentication",
            f"python scripts/update_repository_metadata.py --repo-url <REPO_URL> --execute\n"
            "python scripts/build_release_readiness.py\n"
            "git remote add origin <REPO_URL>.git\n"
            "git branch -M main\n"
            "git push -u origin main\n"
            f"git push origin {tag}",
            "GitHub repository shows source files and the release tag.",
            RELEASE_READINESS,
            "Stop if `docs/github_staging_plan.md` would allow raw data, processed matrices, or generated large data into GitHub.",
            "Codex can run the local commands; authentication remains author-controlled.",
        ),
        _row(
            "05_create_github_release",
            "external",
            "Author or authenticated GitHub CLI",
            blocker_status.get("github_release_page", "blocked_external"),
            f"pushed tag {tag}",
            f"Create a GitHub Release from `{tag}` and attach only approved release/Zenodo assets if needed.",
            "GitHub Release page exists for the pushed tag.",
            PUBLIC_RELEASE_BLOCKERS,
            "Stop if unapproved raw data, processed matrices, private clinical data, or local-only probe outputs would be attached.",
            "Use release manifests to decide attachments.",
        ),
        _row(
            "06_archive_github_release_with_zenodo",
            "external",
            "Author",
            "blocked_external" if not doi_ready else "pass",
            "GitHub Release page",
            "Archive the GitHub Release with Zenodo and capture the assigned DOI.",
            "DOI has the form `10.5281/zenodo.<id>`.",
            PUBLIC_RELEASE_BLOCKERS,
            "Stop if the archive includes private data or if DOI metadata does not match the public repository.",
            "This is required before software_release can pass.",
        ),
        _row(
            "07_provide_zenodo_doi_to_codex",
            "author_input",
            "Author",
            "waiting_external_input" if not doi_ready else "pass",
            "Zenodo DOI",
            "Send Codex the Zenodo DOI after the archive is public.",
            "DOI validation passes in `scripts/finalize_submission_release.py`.",
            RELEASE_READINESS,
            "Stop if the DOI is missing, private, malformed, or points to the wrong release.",
            "No manuscript may claim DOI-backed release before this input exists.",
        ),
        _row(
            "08_record_doi_and_rerun_submission_gates",
            "local_after_doi",
            "Codex",
            "ready_after_doi" if not doi_ready else "pass",
            "repository URL and Zenodo DOI",
            "python scripts/finalize_submission_release.py --repo-url <REPO_URL> --doi <DOI> --execute\n"
            "make release-manifests\n"
            "python scripts/update_gate_evidence_from_results.py\n"
            "python scripts/evaluate_submission_gates.py --evidence results/gates/gate_evidence.tsv --out results/gates/gate_report.tsv\n"
            "python scripts/build_submission_guard.py\n"
            "python scripts/build_post_feedback_journal_route_gate.py",
            "`software_release` and route gates are regenerated from real public-release evidence.",
            POST_FEEDBACK_GATE,
            "Stop if release readiness still shows repository_url, github_remote, github_release_tag, or zenodo_doi as pending.",
            "This is the first point where submission readiness can be reconsidered.",
        ),
    ]
    blockers = [
        row["action_id"]
        for row in rows
        if row["status"]
        in {
            "blocked_external",
            "waiting_external_input",
            "blocked_local",
            "ready_after_repo_url",
            "ready_after_doi",
        }
    ]
    route = _route_status(post_feedback_rows, "overall_post_feedback_route")
    gb_status = _gb_status(gb_transfer_rows, "overall_genome_biology_transfer")
    defense = _defense_status(reviewer_defense_rows, "overall_reviewer_defense")
    if blockers:
        overall_status = "blocked_waiting_author_release"
    else:
        overall_status = "release_evidence_ready_for_gate_refresh"
    rows.append(
        _row(
            "overall_author_release_execution",
            "summary",
            "Author + Codex",
            overall_status,
            "repository URL, GitHub Release, Zenodo DOI",
            "Complete the external author-owned release actions, then rerun the local gates.",
            "All release readiness rows pass and route gates are regenerated.",
            OUT_TSV,
            "Do not mark Nature Methods, Genome Biology, or any route as sendable while this row is blocked.",
            f"blocked_actions={';'.join(blockers) if blockers else 'none'}; route={route}; gb_transfer={gb_status}; reviewer_defense={defense}.",
        )
    )
    return rows


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    overall = next(
        (row for row in rows if row["action_id"] == "overall_author_release_execution"),
        {},
    )
    author_rows = [
        row
        for row in rows
        if row["owner"].startswith("Author")
        or row["phase"] in {"external", "author_input"}
    ]
    lines = [
        "# Author Release Execution Packet",
        "",
        "This file is generated by `python scripts/build_author_release_execution_packet.py`.",
        "",
        "Acceptance guarantee: `impossible`.",
        "This packet reduces the remaining public-release blocker to author-owned external actions plus local Codex follow-up commands.",
        "",
        "## Overall Status",
        "",
        f"- Status: `{overall.get('status', 'missing')}`",
        f"- Blocking actions: `{overall.get('notes', 'missing')}`",
        f"- Stop condition: {overall.get('stop_condition', 'missing')}",
        "",
        "## Minimal Author Actions",
        "",
    ]
    for row in author_rows:
        lines.extend(
            [
                f"### {row['action_id']}",
                "",
                f"- Status: `{row['status']}`",
                f"- Blocking input: {row['blocking_input']}",
                f"- Exact action: {row['exact_action']}",
                f"- Verification: {row['verification']}",
                f"- Stop condition: {row['stop_condition']}",
                f"- Notes: {row['notes']}",
                "",
            ]
        )
    lines.extend(["## Full Execution Checklist", ""])
    for row in rows:
        lines.extend(
            [
                f"### {row['action_id']}",
                "",
                f"- Phase: `{row['phase']}`",
                f"- Owner: `{row['owner']}`",
                f"- Status: `{row['status']}`",
                f"- Evidence: `{row['evidence_path']}`",
                f"- Exact action:",
                "",
                "```bash",
                row["exact_action"],
                "```",
                "",
                f"- Verification: {row['verification']}",
                f"- Stop condition: {row['stop_condition']}",
                f"- Notes: {row['notes']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Non-Negotiable Boundary",
            "",
            "Do not claim public code release, DOI archive, submission readiness, or journal sendability until this packet and the generated submission gates are regenerated from real public repository and DOI evidence.",
        ]
    )
    return lines


def build_code_availability_draft(rows: list[dict[str, str]]) -> list[str]:
    overall = next(
        (row for row in rows if row["action_id"] == "overall_author_release_execution"),
        {},
    )
    lines = [
        "# Code Availability Finalization Draft",
        "",
        f"Status: `{overall.get('status', 'missing')}`.",
        "This draft is not final until the public repository URL and archive DOI are known.",
        "",
        "## Current Safe Wording",
        "",
        "The RMTGuard source package, tests, public-data download scripts, Docker/CI files, figure source-data manifests and release-audit scripts have been prepared locally. Public repository and archive identifiers remain pending and must be inserted only after the external release exists.",
        "",
        "## Final Wording Template",
        "",
        "Code for RMTGuard is available at [TO CONFIRM: public repository URL] under the MIT License. The release used for this manuscript is archived at [TO CONFIRM: public archive DOI]. Public datasets are accessed through the accession numbers and download scripts listed in the repository; raw and processed large matrices are not committed directly to GitHub.",
        "",
        "## Required Before Use",
        "",
        "1. Complete the public GitHub repository and pushed release tag.",
        "2. Create the GitHub Release and archive it with Zenodo.",
        "3. Record the repository URL and DOI locally.",
        "4. Regenerate release readiness, claim lint, claim traceability, submission guard, post-feedback route gate and external review packet.",
        "",
        "## Forbidden Wording",
        "",
        "Do not state that the code is publicly released, DOI archived, submission-ready, or editor-ready while repository_url, github_remote, GitHub Release, or Zenodo DOI evidence remains pending.",
    ]
    return lines


def main() -> int:
    rows = build_author_release_rows(
        _read_tsv(RELEASE_READINESS),
        _read_tsv(PUBLIC_RELEASE_BLOCKERS),
        _read_tsv(GITHUB_HANDOFF),
        _read_tsv(POST_FEEDBACK_GATE),
        _read_tsv(GB_TRANSFER),
        _read_tsv(REVIEWER_DEFENSE),
    )
    _write_tsv(OUT_TSV, rows)
    _write_text(OUT_MD, build_markdown(rows))
    _write_text(CODE_AVAILABILITY_DRAFT, build_code_availability_draft(rows))
    overall = next(
        row for row in rows if row["action_id"] == "overall_author_release_execution"
    )
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print(_rel(CODE_AVAILABILITY_DRAFT))
    print(f"overall\t{overall['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
