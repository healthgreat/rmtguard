from __future__ import annotations

"""Finalize local submission gates after external GitHub/Zenodo release.

Author: RMTGuard development team
Date: 2026-04-30
Purpose: Safely record real repository and DOI metadata, then rebuild release,
gate, compliance, and presubmission artifacts for journal submission.
Data source: GitHub repository URL, Zenodo DOI, and generated local gate tables.
Method notes: Default mode is dry-run. `--execute` updates metadata but does
not commit, push, or force-update a public release tag.
"""

import argparse
import csv
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "release"
PLAN_TSV = OUT_DIR / "submission_release_finalization.tsv"
PLAN_MD = OUT_DIR / "submission_release_finalization.md"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["step_id", "status", "command", "evidence_path", "notes"],
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


def _git(args: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout.strip()


def _run_python_script(script: str, args: list[str] | None = None) -> tuple[int, str]:
    cmd = [sys.executable, str(ROOT / script), *(args or [])]
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout.strip()


def _load_record_external_release() -> object:
    script = ROOT / "scripts" / "record_external_release.py"
    spec = importlib.util.spec_from_file_location("record_external_release", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load record_external_release.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validate_repo_and_doi(repo_url: str, doi: str) -> tuple[str, str]:
    module = _load_record_external_release()
    return module.normalize_repo_url(repo_url), module.normalize_doi(doi)


def build_plan(
    repo_url: str | None, doi: str | None, tag: str, execute: bool = False
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    code, status = _git(["status", "--short"])
    clean = code == 0 and not status.strip()
    code, tag_target = _git(["rev-list", "-n", "1", tag])
    tag_exists = code == 0 and bool(tag_target)
    code, head = _git(["rev-parse", "HEAD"])
    tag_at_head = tag_exists and code == 0 and tag_target == head

    if repo_url and doi:
        try:
            repo_url, doi = _validate_repo_and_doi(repo_url, doi)
            metadata_status = "ready" if not execute else "would_update"
            metadata_notes = "Repository URL and DOI parse correctly."
        except ValueError as exc:
            metadata_status = "blocked"
            metadata_notes = str(exc)
    else:
        metadata_status = "blocked"
        metadata_notes = "Provide --repo-url and --doi."

    rows.extend(
        [
            {
                "step_id": "01_validate_inputs",
                "status": metadata_status,
                "command": "validate --repo-url and --doi",
                "evidence_path": "arguments",
                "notes": metadata_notes,
            },
            {
                "step_id": "02_validate_clean_worktree",
                "status": "ready" if clean else "blocked",
                "command": "git status --short",
                "evidence_path": ".git",
                "notes": "Clean work tree is required before final release metadata is recorded.",
            },
            {
                "step_id": "03_validate_tag_state",
                "status": "ready" if tag_at_head else "manual_review",
                "command": f"git rev-list -n 1 {tag}; git rev-parse HEAD",
                "evidence_path": ".git",
                "notes": (
                    f"Tag {tag} points at HEAD."
                    if tag_at_head
                    else f"Tag {tag} is missing or does not point at HEAD. Do not force-update a public tag; create a new final tag if needed."
                ),
            },
            {
                "step_id": "04_record_external_metadata",
                "status": "would_run" if metadata_status != "blocked" else "blocked",
                "command": "python scripts/record_external_release.py --repo-url <URL> --doi <DOI> --set-remote --execute",
                "evidence_path": "results/release/external_release_metadata_plan.tsv",
                "notes": "Records repository URL, DOI, and optionally origin remote. Does not commit or push.",
            },
            {
                "step_id": "05_rebuild_submission_artifacts",
                "status": "would_run" if metadata_status != "blocked" else "blocked",
                "command": "rebuild release readiness, gates, compliance audit, execution board, presubmission package",
                "evidence_path": "results/submission/presubmission_gatekeeper.tsv",
                "notes": "Refreshes all generated evidence after DOI metadata is present.",
            },
            {
                "step_id": "06_manual_commit_and_final_tag_decision",
                "status": "manual_review",
                "command": "git diff; git commit; create final tag if required",
                "evidence_path": ".git",
                "notes": "If DOI metadata changes tracked files, commit them. For public releases, prefer a new final tag over force-updating an existing public tag.",
            },
        ]
    )
    return rows


def _require_no_blockers(rows: list[dict[str, str]]) -> None:
    blockers = [row["step_id"] for row in rows if row["status"] == "blocked"]
    if blockers:
        raise RuntimeError("Finalization blocked by: " + ", ".join(blockers))


def _refresh_all() -> list[tuple[str, int, str]]:
    commands = [
        ("scripts/build_github_release_handoff.py", []),
        ("scripts/build_release_readiness.py", []),
        ("scripts/update_gate_evidence_from_results.py", []),
        (
            "scripts/evaluate_submission_gates.py",
            [
                "--evidence",
                "results/gates/gate_evidence.tsv",
                "--out",
                "results/gates/gate_report.tsv",
            ],
        ),
        ("scripts/build_publication_20_50_plan.py", []),
        ("scripts/build_manuscript_evidence_package.py", []),
        ("scripts/build_manuscript_draft_package.py", []),
        ("scripts/build_journal_compliance_audit.py", []),
        ("scripts/build_publication_execution_board.py", []),
        ("scripts/build_reporting_summary_draft.py", []),
        ("scripts/build_editorial_risk_audit.py", []),
        ("scripts/build_top_paper_route_package.py", []),
        ("scripts/build_editorial_presubmission_packet.py", []),
        ("scripts/lint_claim_boundaries.py", []),
        ("scripts/validate_claim_traceability.py", []),
        ("scripts/build_submission_guard.py", []),
        ("scripts/build_presubmission_package.py", []),
        ("scripts/build_release_artifact_manifest.py", []),
        ("scripts/build_release_asset_bundle.py", []),
        ("scripts/build_public_release_blocker_report.py", []),
        ("scripts/build_release_readiness.py", []),
        ("scripts/build_journal_compliance_audit.py", []),
        ("scripts/build_publication_execution_board.py", []),
        ("scripts/build_reporting_summary_draft.py", []),
        ("scripts/build_editorial_risk_audit.py", []),
        ("scripts/build_presubmission_package.py", []),
    ]
    results: list[tuple[str, int, str]] = []
    for script, args in commands:
        code, out = _run_python_script(script, args)
        results.append((script, code, out))
        if code != 0:
            break
    return results


def execute(
    repo_url: str, doi: str, tag: str, set_remote: bool
) -> list[dict[str, str]]:
    repo_url, doi = _validate_repo_and_doi(repo_url, doi)
    plan = build_plan(repo_url, doi, tag, execute=True)
    _require_no_blockers(plan)
    record = _load_record_external_release()
    record.execute(repo_url, doi, set_remote=set_remote)
    refresh_results = _refresh_all()
    failed = [script for script, code, _out in refresh_results if code != 0]
    rows = build_plan(repo_url, doi, tag, execute=False)
    for row in rows:
        if (
            row["step_id"]
            in {"04_record_external_metadata", "05_rebuild_submission_artifacts"}
            and not failed
        ):
            row["status"] = "executed"
    rows.append(
        {
            "step_id": "07_refresh_command_log",
            "status": "pass" if not failed else "blocked",
            "command": "; ".join(
                f"{script}:{code}" for script, code, _out in refresh_results
            ),
            "evidence_path": _rel(PLAN_TSV),
            "notes": (
                "All refresh commands completed."
                if not failed
                else "Refresh failed at: " + ", ".join(failed)
            ),
        }
    )
    return rows


def build_markdown(
    rows: list[dict[str, str]],
    repo_url: str | None,
    doi: str | None,
    tag: str,
    execute_mode: bool,
) -> list[str]:
    blocked = [row for row in rows if row["status"] == "blocked"]
    manual = [row for row in rows if row["status"] == "manual_review"]
    lines = [
        "# Submission Release Finalization",
        "",
        "This file is generated by `python scripts/finalize_submission_release.py`.",
        "",
        f"- Repository: `{repo_url or 'pending'}`",
        f"- DOI: `{doi or 'pending'}`",
        f"- Tag checked: `{tag}`",
        f"- Execute mode: `{execute_mode}`",
        "- Acceptance guarantee: `impossible`; this only finalizes release evidence for submission gates.",
        "",
        "## Blocking Items",
        "",
    ]
    if blocked:
        lines.extend(f"- `{row['step_id']}`: {row['notes']}" for row in blocked)
    else:
        lines.append("- none")
    lines.extend(["", "## Manual Review Items", ""])
    if manual:
        lines.extend(f"- `{row['step_id']}`: {row['notes']}" for row in manual)
    else:
        lines.append("- none")
    lines.extend(["", "## Steps", ""])
    for row in rows:
        lines.extend(
            [
                f"### {row['step_id']}",
                "",
                f"- Status: `{row['status']}`",
                f"- Command: `{row['command']}`",
                f"- Evidence: `{row['evidence_path']}`",
                f"- Notes: {row['notes']}",
                "",
            ]
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Finalize local gates after real GitHub/Zenodo release metadata exists."
    )
    parser.add_argument("--repo-url", default=None)
    parser.add_argument("--doi", default=None)
    parser.add_argument("--tag", default="v0.1.0-rc6")
    parser.add_argument("--set-remote", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--out", type=Path, default=PLAN_TSV)
    args = parser.parse_args(argv)

    if args.execute:
        if not args.repo_url or not args.doi:
            raise SystemExit("--execute requires --repo-url and --doi")
        rows = execute(args.repo_url, args.doi, args.tag, args.set_remote)
    else:
        rows = build_plan(args.repo_url, args.doi, args.tag, execute=False)
    _write_tsv(args.out, rows)
    _write_text(
        PLAN_MD, build_markdown(rows, args.repo_url, args.doi, args.tag, args.execute)
    )
    print(_rel(args.out))
    print(_rel(PLAN_MD))
    print(
        f"{'executed' if args.execute else 'dry_run'}\t{sum(row['status'] == 'blocked' for row in rows)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
