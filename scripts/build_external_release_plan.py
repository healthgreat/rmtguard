from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "release"
PLAN_TSV = OUT_DIR / "external_release_plan.tsv"
PLAN_MD = ROOT / "docs" / "external_release_plan.md"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def build_steps(repo_url: str = "https://github.com/<owner>/rmtguard", version: str = "v0.1.0") -> list[dict[str, str]]:
    repo_url = repo_url.rstrip("/")
    repo_git_url = repo_url + ".git" if not repo_url.endswith(".git") else repo_url
    repo_clean = repo_url[:-4] if repo_url.endswith(".git") else repo_url
    steps = [
        {
            "step_id": "01_create_github_repo",
            "phase": "external",
            "command": "Create an empty public GitHub repository at " + repo_clean,
            "blocking_input": "real GitHub owner/repository",
            "expected_output": "Repository exists and accepts pushes.",
            "status": "pending_external",
            "notes": "Do this in GitHub UI or gh; do not upload data files.",
        },
        {
            "step_id": "02_update_repository_metadata",
            "phase": "local",
            "command": f"python scripts/update_repository_metadata.py --repo-url {repo_clean} --execute",
            "blocking_input": "real GitHub repository URL",
            "expected_output": "pyproject.toml, CITATION.cff, and release docs point to the real repository.",
            "status": "ready_after_repo_exists",
            "notes": "Run without --execute first to preview replacements.",
        },
        {
            "step_id": "03_regenerate_release_manifests",
            "phase": "local",
            "command": "make release-manifests",
            "blocking_input": "updated repository metadata",
            "expected_output": "Release artifact, staging, dry-run, figure, and readiness manifests are current.",
            "status": "ready",
            "notes": "This target is dry-run safe and does not stage files.",
        },
        {
            "step_id": "04_run_tests_and_audit",
            "phase": "local",
            "command": "python -m unittest discover -s tests && python scripts/clean_artifacts.py && python scripts/release_audit.py",
            "blocking_input": "current local checkout",
            "expected_output": "All tests pass and release audit passes.",
            "status": "ready",
            "notes": "Warnings from optional GPU/CPU detection do not imply test failure.",
        },
        {
            "step_id": "05_stage_approved_files",
            "phase": "local_git",
            "command": "python scripts/stage_github_release_files.py --execute",
            "blocking_input": "reviewed docs/github_staging_plan.md",
            "expected_output": "Only approved source/metadata files are staged.",
            "status": "ready_after_review",
            "notes": "Never use git add . for this first public release.",
        },
        {
            "step_id": "06_commit_release_source",
            "phase": "local_git",
            "command": 'git commit -m "Initial RMTGuard research software release"',
            "blocking_input": "approved staged files",
            "expected_output": "Initial release commit exists.",
            "status": "pending_git",
            "notes": "Do not commit raw data, processed h5ad files, result tables, or draft figures.",
        },
        {
            "step_id": "07_configure_remote",
            "phase": "local_git",
            "command": f"git remote add origin {repo_git_url}",
            "blocking_input": "real GitHub repository URL",
            "expected_output": "origin remote points to GitHub.",
            "status": "pending_external",
            "notes": "If origin already exists, update it intentionally instead of adding a duplicate.",
        },
        {
            "step_id": "08_push_main",
            "phase": "external",
            "command": "git branch -M main && git push -u origin main",
            "blocking_input": "GitHub authentication",
            "expected_output": "GitHub repository contains the source release.",
            "status": "pending_external",
            "notes": "Confirm GitHub file list matches docs/github_staging_plan.md.",
        },
        {
            "step_id": "09_create_release_tag",
            "phase": "local_git",
            "command": f'git tag -a {version} -m "RMTGuard manuscript analysis release" && git push origin {version}',
            "blocking_input": "clean committed source release",
            "expected_output": f"Annotated tag {version} exists locally and on GitHub.",
            "status": "pending_git",
            "notes": "The software_release gate cannot pass before a release tag exists.",
        },
        {
            "step_id": "10_create_github_release",
            "phase": "external",
            "command": f"Create GitHub Release for {version} and attach DOI-archive candidate assets.",
            "blocking_input": "pushed release tag",
            "expected_output": "GitHub Release page exists.",
            "status": "pending_external",
            "notes": "Use release_artifact_manifest.tsv to decide which generated outputs belong as assets.",
        },
        {
            "step_id": "11_archive_with_zenodo",
            "phase": "external",
            "command": "Archive the GitHub Release with Zenodo and record the DOI.",
            "blocking_input": "GitHub Release",
            "expected_output": "Zenodo DOI is assigned.",
            "status": "pending_external",
            "notes": "Do not upload private or controlled-access clinical data.",
        },
        {
            "step_id": "12_update_doi_and_rerun_gates",
            "phase": "local",
            "command": "Update DOI/code availability text, then run make release-manifests && python scripts/update_gate_evidence_from_results.py",
            "blocking_input": "Zenodo DOI",
            "expected_output": "software_release evidence can be re-evaluated.",
            "status": "pending_external",
            "notes": "Only after this step can software_release move toward pass.",
        },
    ]
    return steps


def write_tsv(rows: list[dict[str, str]], out: Path = PLAN_TSV) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    fieldnames = ["step_id", "phase", "command", "blocking_input", "expected_output", "status", "notes"]
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(out)


def write_md(rows: list[dict[str, str]], out: Path = PLAN_MD) -> None:
    lines = [
        "# External Release Plan",
        "",
        "This file is generated by `python scripts/build_external_release_plan.py`.",
        "It is an execution plan only; it does not create remotes, commits, tags, GitHub releases, or Zenodo records.",
        "",
        "## Release Boundary",
        "",
        "The source repository should contain code, tests, metadata, workflows, docs, and placeholders.",
        "Raw public data, processed matrices, generated result tables, source-data archives, and draft figures stay out of the GitHub source tree unless explicitly attached as release/Zenodo assets.",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['step_id']}",
                "",
                f"- Phase: `{row['phase']}`",
                f"- Status: `{row['status']}`",
                f"- Blocking input: {row['blocking_input']}",
                f"- Expected output: {row['expected_output']}",
                f"- Notes: {row['notes']}",
                "",
                "```bash",
                row["command"],
                "```",
                "",
            ]
        )
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text("\n".join(lines), encoding="utf-8")
    tmp.replace(out)


def main() -> int:
    rows = build_steps()
    write_tsv(rows)
    write_md(rows)
    print(_rel(PLAN_TSV))
    print(_rel(PLAN_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
