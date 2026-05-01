from __future__ import annotations

"""Build a blocker report for public GitHub/Zenodo release readiness.

Author: RMTGuard development team
Date: 2026-05-01
Purpose: Convert the external software-release boundary into an auditable
reviewer-facing table before journal submission.
Data source: Local Git metadata, release readiness artifacts, pyproject/CFF
metadata, and Zenodo metadata placeholders.
Method notes: This script is read-only with respect to GitHub and Zenodo. It
uses atomic writes for generated TSV/Markdown outputs.
"""

import csv
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "release"
REPORT_TSV = OUT_DIR / "public_release_blockers.tsv"
REPORT_MD = ROOT / "docs" / "public_release_blocker_report.md"
READINESS_TSV = OUT_DIR / "release_readiness.tsv"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


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


def _detect_remote_url() -> str:
    code, out = _git(["remote", "get-url", "origin"])
    if code == 0:
        return out.strip()
    return ""


def _detect_worktree_clean() -> bool:
    code, out = _git(["status", "--short"])
    return code == 0 and not out.strip()


def _detect_head_tags() -> list[str]:
    code, out = _git(["tag", "--points-at", "HEAD"])
    if code != 0 or not out.strip():
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def _detect_placeholder_repo_present() -> bool:
    paths = [
        ROOT / "pyproject.toml",
        ROOT / "CITATION.cff",
        ROOT / "docs" / "data_and_code_availability_template.md",
        ROOT / "docs" / "github_release_checklist.md",
    ]
    text = "\n".join(_read_text(path) for path in paths)
    return "your-lab/rmtguard" in text or "<owner>/rmtguard" in text


def _detect_zenodo_doi_present() -> bool:
    text = _read_text(ROOT / ".zenodo.json")
    return '"doi"' in text and "10." in text


def _release_status(rows: list[dict[str, str]], check_id: str) -> str:
    for row in rows:
        if row.get("check_id") == check_id:
            return row.get("status", "")
    return ""


def _row(
    blocker_id: str,
    status: str,
    owner: str,
    evidence_path: Path | str,
    required_action: str,
    next_command: str,
    notes: str,
) -> dict[str, str]:
    evidence = _rel(evidence_path) if isinstance(evidence_path, Path) else evidence_path
    return {
        "blocker_id": blocker_id,
        "status": status,
        "owner": owner,
        "evidence_path": evidence,
        "required_action": required_action,
        "next_command": next_command,
        "notes": notes,
    }


def build_rows(
    release_readiness_rows: list[dict[str, str]] | None = None,
    gh_path: str | None = None,
    remote_url: str | None = None,
    worktree_clean: bool | None = None,
    head_tags: list[str] | None = None,
    placeholder_repo_present: bool | None = None,
    zenodo_doi_present: bool | None = None,
) -> list[dict[str, str]]:
    if release_readiness_rows is None:
        release_readiness_rows = _read_tsv(READINESS_TSV)
    if gh_path is None:
        gh_path = shutil.which("gh") or ""
    if remote_url is None:
        remote_url = _detect_remote_url()
    if worktree_clean is None:
        worktree_clean = _detect_worktree_clean()
    if head_tags is None:
        head_tags = _detect_head_tags()
    if placeholder_repo_present is None:
        placeholder_repo_present = _detect_placeholder_repo_present()
    if zenodo_doi_present is None:
        zenodo_doi_present = _detect_zenodo_doi_present()

    github_remote_ok = bool(remote_url) and "github.com" in remote_url.lower()
    metadata_ok = not placeholder_repo_present
    tag_ok = bool(head_tags)
    release_gate_ok = all(
        _release_status(release_readiness_rows, check_id) == "pass"
        for check_id in [
            "repository_url",
            "github_remote",
            "github_release_tag",
            "zenodo_doi",
        ]
    )

    rows = [
        _row(
            "acceptance_boundary",
            "controlled",
            "codex",
            ROOT / "docs" / "claim_scope_decision.md",
            "Keep acceptance language bounded to evidence and review outcome.",
            "none",
            "Acceptance guarantee is impossible; this report controls publication-engineering blockers only.",
        ),
        _row(
            "github_cli_or_web_access",
            "pass" if gh_path else "blocked_external",
            "author",
            gh_path or "PATH",
            "Provide either GitHub CLI authentication or use the GitHub web UI for repository/release creation.",
            "gh auth status",
            (
                "GitHub CLI is available."
                if gh_path
                else "gh is not available in this checkout; web UI is acceptable but remains external."
            ),
        ),
        _row(
            "github_remote",
            "pass" if github_remote_ok else "blocked_external",
            "author",
            ".git/config",
            "Create a real public GitHub repository and connect this checkout to it.",
            "git remote add origin https://github.com/<owner>/rmtguard.git",
            (
                f"origin={remote_url}"
                if remote_url
                else "No GitHub origin remote is configured."
            ),
        ),
        _row(
            "repository_url_metadata",
            "pass" if metadata_ok else "blocked_external",
            "author",
            ROOT / "pyproject.toml",
            "Replace placeholder repository URLs after the real GitHub repository exists.",
            "python scripts/update_repository_metadata.py --repo-url https://github.com/<owner>/rmtguard --execute",
            (
                "Repository metadata points to a real URL."
                if metadata_ok
                else "Repository metadata still contains placeholder owner/repository values."
            ),
        ),
        _row(
            "clean_worktree_before_release",
            "pass" if worktree_clean else "blocked_local",
            "codex",
            ".git",
            "Commit or intentionally exclude local changes before creating a public release tag.",
            "git status --short",
            (
                "Git work tree is clean."
                if worktree_clean
                else "Git work tree has local changes; do not tag a moving target."
            ),
        ),
        _row(
            "release_tag_at_head",
            "pass" if tag_ok else "blocked_local",
            "codex",
            ".git",
            "Create an annotated release tag only after source, docs, tests, and metadata are final.",
            'git tag -a v0.1.0-rc4 -m "RMTGuard manuscript analysis release candidate 4"',
            (
                "HEAD tag(s): " + ", ".join(head_tags)
                if tag_ok
                else "Current HEAD has no release tag."
            ),
        ),
        _row(
            "github_release_page",
            "pass" if github_remote_ok and tag_ok else "blocked_external",
            "author",
            "GitHub Releases",
            "Create a GitHub Release from the approved release tag.",
            "python scripts/execute_github_release.py --repo-url https://github.com/<owner>/rmtguard --tag v0.1.0-rc4 --execute",
            "Requires a GitHub remote and release tag; this script cannot create an account-owned repository without author authentication.",
        ),
        _row(
            "zenodo_doi",
            "pass" if zenodo_doi_present else "blocked_external",
            "author",
            ROOT / ".zenodo.json",
            "Archive the GitHub Release with Zenodo and record the DOI.",
            "python scripts/finalize_submission_release.py --repo-url https://github.com/<owner>/rmtguard --doi 10.5281/zenodo.<id> --execute",
            (
                "Zenodo DOI is recorded."
                if zenodo_doi_present
                else "Zenodo DOI is still absent; software_release must remain pending."
            ),
        ),
        _row(
            "software_release_gate",
            "pass" if release_gate_ok else "blocked",
            "codex_author_joint",
            READINESS_TSV,
            "Rebuild release readiness after GitHub and Zenodo evidence are real.",
            "make release-manifests",
            (
                "All software-release evidence rows pass."
                if release_gate_ok
                else "One or more repository URL, remote, tag, or DOI checks remain pending."
            ),
        ),
    ]
    return rows


def write_tsv(rows: list[dict[str, str]], out: Path = REPORT_TSV) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "blocker_id",
                "status",
                "owner",
                "evidence_path",
                "required_action",
                "next_command",
                "notes",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(out)


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    blocked = [row for row in rows if row["status"].startswith("blocked")]
    pass_rows = [row for row in rows if row["status"] == "pass"]
    lines = [
        "# Public Release Blocker Report",
        "",
        "This file is generated by `python scripts/build_public_release_blocker_report.py`.",
        "",
        "Acceptance guarantee: `impossible`.",
        "This report is a release-engineering control surface, not a promise of journal acceptance.",
        "",
        "## Summary",
        "",
        f"- Passing release checks: `{len(pass_rows)}`",
        f"- Blocking checks: `{len(blocked)}`",
        "- Strict Nature Methods / 20-50 JIF route remains gated by real evidence, public release completion, and editorial review.",
        "",
        "## Immediate Blockers",
        "",
    ]
    if blocked:
        lines.extend(
            f"- `{row['blocker_id']}` ({row['status']}): {row['required_action']}"
            for row in blocked
        )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Execution Rows",
            "",
        ]
    )
    for row in rows:
        lines.extend(
            [
                f"### {row['blocker_id']}",
                "",
                f"- Status: `{row['status']}`",
                f"- Owner: `{row['owner']}`",
                f"- Evidence: `{row['evidence_path']}`",
                f"- Required action: {row['required_action']}",
                f"- Notes: {row['notes']}",
                "",
                "```bash",
                row["next_command"],
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "Do not mark the manuscript as submission-ready until the `software_release_gate` row is `pass` and the scientific gates still support the selected claim scope.",
        ]
    )
    return lines


def write_markdown(rows: list[dict[str, str]], out: Path = REPORT_MD) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text("\n".join(build_markdown(rows)).rstrip() + "\n", encoding="utf-8")
    tmp.replace(out)


def main() -> int:
    rows = build_rows()
    write_tsv(rows)
    write_markdown(rows)
    print(_rel(REPORT_TSV))
    print(_rel(REPORT_MD))
    blocked = [row["blocker_id"] for row in rows if row["status"].startswith("blocked")]
    print("blocked\t" + (",".join(blocked) if blocked else "none"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
