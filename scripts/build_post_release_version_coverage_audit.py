"""Audit whether post-release manuscript evidence is covered by the DOI release.

Author: RMTGuard contributors
Date: 2026-05-12
Purpose: Compare the current working branch with the archived software release
tag and decide whether a new GitHub Release/Zenodo archive is required before
submission.
Data source: local Git history, v0.1.0 tag, current HEAD, and file path classes.
Method notes: This is a release-version coverage audit. It does not create
tags, push commits, upload assets, or modify Zenodo records.
"""

from __future__ import annotations

import csv
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_TAG = "v0.1.0"
NEXT_RELEASE = "v0.1.1"

OUT_TSV = ROOT / "results" / "submission" / "post_release_version_coverage_audit.tsv"
OUT_CHANGED = ROOT / "results" / "submission" / "post_release_changed_files.tsv"
OUT_MD = ROOT / "docs" / "post_release_version_coverage_audit.md"
SELF_GENERATED_PATHS = {
    OUT_TSV.relative_to(ROOT).as_posix(),
    OUT_CHANGED.relative_to(ROOT).as_posix(),
    OUT_MD.relative_to(ROOT).as_posix(),
}


@dataclass(frozen=True)
class PathClass:
    prefix: str
    class_name: str
    manuscript_facing: bool
    notes: str


PATH_CLASSES = [
    PathClass("figures/manuscript/", "journal_figure", True, "rendered figure assets"),
    PathClass("figures/calibration/", "calibration_figure", True, "calibration figure assets"),
    PathClass("manuscript/", "manuscript_text", True, "manuscript drafts, captions, title page and sign-off text"),
    PathClass("docs/", "submission_doc", True, "submission, route, audit and validation reports"),
    PathClass("results/submission/", "submission_table", True, "submission-facing machine-readable tables"),
    PathClass("results/figures/", "figure_source_data", True, "figure source data and reproducibility manifests"),
    PathClass("results/calibration/", "calibration_result", True, "50-repeat calibration outputs"),
    PathClass("results/ablation/", "ablation_result", True, "component ablation outputs"),
    PathClass("results/pdac_tme/", "pdac_result", True, "PDAC/TME application outputs"),
    PathClass("results/realdata_topology/", "topology_result", True, "real-data topology benchmark outputs"),
    PathClass("results/sclens", "competitor_result", True, "scLENSpy comparator outputs"),
    PathClass("results/topology_stress", "topology_result", True, "synthetic topology benchmark outputs"),
    PathClass("results/shared_info/", "shared_export", False, "cross-project export manifest"),
    PathClass("output/doc/", "handoff_document", True, "Word handoff and author sign-off packets"),
    PathClass("output/email/", "handoff_email", True, "email drafts for manual author actions"),
    PathClass("benchmarks/", "benchmark_code", True, "benchmark execution code"),
    PathClass("scripts/", "pipeline_code", True, "analysis, figure, release and submission-control scripts"),
    PathClass("metadata/", "metadata", True, "author, dataset and sign-off metadata"),
    PathClass("README.md", "repository_doc", True, "repository landing documentation"),
    PathClass("Makefile", "reproducibility_entrypoint", True, "workflow entry points"),
    PathClass(".zenodo.json", "release_metadata", True, "Zenodo metadata"),
    PathClass("CITATION.cff", "release_metadata", True, "software citation metadata"),
]


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


def classify_path(path: str) -> PathClass:
    normalized = path.replace("\\", "/")
    for path_class in PATH_CLASSES:
        if normalized == path_class.prefix or normalized.startswith(path_class.prefix):
            return path_class
    return PathClass("other", "other", False, "not manuscript-facing by default")


def parse_changed_files() -> list[dict[str, str]]:
    raw = run_git(["diff", "--name-status", f"{RELEASE_TAG}..HEAD"])
    rows: list[dict[str, str]] = []
    if not raw:
        return rows
    for line in raw.splitlines():
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        path_class = classify_path(path)
        rows.append(
            {
                "change_status": status,
                "path": path.replace("\\", "/"),
                "class": path_class.class_name,
                "manuscript_facing": str(path_class.manuscript_facing),
                "notes": path_class.notes,
            }
        )
    return rows


def status_counts(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key, "")
        counts[value] = counts.get(value, 0) + 1
    return counts


def filtered_worktree_status() -> str:
    raw = run_git(["status", "--short"])
    if not raw:
        return ""
    kept: list[str] = []
    for line in raw.splitlines():
        path = line[3:].strip().replace("\\", "/")
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path in SELF_GENERATED_PATHS:
            continue
        kept.append(line)
    return "\n".join(kept)


def write_tsv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def build_audit_rows(changed_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    tag_commit = run_git(["rev-list", "-n", "1", RELEASE_TAG])
    head_commit = run_git(["rev-parse", "HEAD"])
    commits_since = run_git(["rev-list", "--count", f"{RELEASE_TAG}..HEAD"])
    worktree_status = filtered_worktree_status()
    manuscript_changed = [
        row for row in changed_rows if row.get("manuscript_facing") == "True"
    ]
    figure_changed = [
        row
        for row in changed_rows
        if row.get("class") in {"journal_figure", "calibration_figure", "figure_source_data"}
    ]
    script_changed = [
        row for row in changed_rows if row.get("class") in {"pipeline_code", "benchmark_code"}
    ]
    status = "needs_new_release_if_submitted" if manuscript_changed else "covered_by_current_release"
    return [
        {
            "audit_id": "release_tag",
            "status": "present",
            "evidence": RELEASE_TAG,
            "required_action": "Keep v0.1.0 immutable.",
            "notes": f"{RELEASE_TAG} commit {tag_commit}.",
        },
        {
            "audit_id": "current_head",
            "status": "tracked",
            "evidence": head_commit,
            "required_action": "Use this commit or a later clean commit as the basis for any v0.1.1 release.",
            "notes": f"{commits_since} commits after {RELEASE_TAG}.",
        },
        {
            "audit_id": "worktree_cleanliness",
            "status": "clean" if not worktree_status else "dirty",
            "evidence": worktree_status or "none",
            "required_action": "Commit or intentionally ignore all changes before release.",
            "notes": "A clean worktree is required before tagging a new release.",
        },
        {
            "audit_id": "manuscript_facing_delta",
            "status": status,
            "evidence": str(len(manuscript_changed)),
            "required_action": f"Create {NEXT_RELEASE} only after Figure 4 acknowledgement and final figure/source-data freeze if these post-release files are cited.",
            "notes": "Manuscript-facing files changed after the archived v0.1.0 DOI.",
        },
        {
            "audit_id": "figure_source_delta",
            "status": "changed" if figure_changed else "unchanged",
            "evidence": str(len(figure_changed)),
            "required_action": "Ensure final figures and source data are included in the next release if used in submission.",
            "notes": "Figure/source-data changes after v0.1.0 affect reproducibility coverage.",
        },
        {
            "audit_id": "pipeline_code_delta",
            "status": "changed" if script_changed else "unchanged",
            "evidence": str(len(script_changed)),
            "required_action": "Archive updated scripts/benchmarks in the same release as the submitted source data.",
            "notes": "Code changes after v0.1.0 affect rerun parity.",
        },
        {
            "audit_id": "release_recommendation",
            "status": "prepare_v0.1.1_after_author_ack" if manuscript_changed else "no_refresh_needed",
            "evidence": NEXT_RELEASE,
            "required_action": "Do not tag the new release until manual Figure 4 and author-declaration blockers are resolved.",
            "notes": "The release refresh is a submission-readiness action, not a current scientific pass.",
        },
    ]


def write_markdown(audit_rows: list[dict[str, str]], changed_rows: list[dict[str, str]]) -> None:
    class_counts = status_counts(changed_rows, "class")
    change_counts = status_counts(changed_rows, "change_status")
    manuscript_count = sum(row["manuscript_facing"] == "True" for row in changed_rows)
    sample_rows = [row for row in changed_rows if row["manuscript_facing"] == "True"][:40]
    lines = [
        "# Post-release version coverage audit",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## Boundary",
        "",
        "This audit compares the archived `v0.1.0` release with the current branch. It does not create a tag, push a release, or mint a new DOI.",
        "",
        "## Bottom Line",
        "",
        f"- Commits after `{RELEASE_TAG}`: `{next(row['notes'].split()[0] for row in audit_rows if row['audit_id'] == 'current_head')}`.",
        f"- Changed files after `{RELEASE_TAG}`: `{len(changed_rows)}`.",
        f"- Manuscript-facing changed files: `{manuscript_count}`.",
        f"- Recommendation: `{next(row['status'] for row in audit_rows if row['audit_id'] == 'release_recommendation')}`.",
        f"- Candidate next release: `{NEXT_RELEASE}`.",
        "",
        "## Audit Rows",
        "",
        "| Audit ID | Status | Evidence | Required action | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in audit_rows:
        evidence = row["evidence"].replace("\n", "<br>")
        lines.append(
            f"| {row['audit_id']} | {row['status']} | {evidence} | {row['required_action']} | {row['notes']} |"
        )
    lines.extend(
        [
            "",
            "## Changed File Classes",
            "",
            "| Class | Count |",
            "| --- | ---: |",
        ]
    )
    for class_name, count in sorted(class_counts.items()):
        lines.append(f"| {class_name} | {count} |")
    lines.extend(["", "## Change Status Counts", "", "| Git status | Count |", "| --- | ---: |"])
    for change_status, count in sorted(change_counts.items()):
        lines.append(f"| {change_status} | {count} |")
    lines.extend(
        [
            "",
            "## Example Manuscript-facing Changed Files",
            "",
            "| Status | Class | Path |",
            "| --- | --- | --- |",
        ]
    )
    for row in sample_rows:
        lines.append(f"| {row['change_status']} | {row['class']} | `{row['path']}` |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- The existing DOI covers `v{RELEASE_TAG.lstrip('v')}`. It should not be described as covering later manuscript-facing changes unless a new release is made.",
            f"- If the submitted manuscript cites current figures, source data, reporting-summary worksheets or post-release scripts, prepare `{NEXT_RELEASE}` after all author-controlled blockers are resolved.",
            "- Do not create the new release before Figure 4 bounded wording and author declarations are confirmed, because a release should archive the exact submission state.",
        ]
    )
    tmp = OUT_MD.with_suffix(OUT_MD.suffix + ".tmp")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    tmp.replace(OUT_MD)


def main() -> int:
    changed_rows = parse_changed_files()
    audit_rows = build_audit_rows(changed_rows)
    write_tsv(
        OUT_CHANGED,
        changed_rows,
        ["change_status", "path", "class", "manuscript_facing", "notes"],
    )
    write_tsv(
        OUT_TSV,
        audit_rows,
        ["audit_id", "status", "evidence", "required_action", "notes"],
    )
    write_markdown(audit_rows, changed_rows)
    print(OUT_TSV.relative_to(ROOT).as_posix())
    print(OUT_CHANGED.relative_to(ROOT).as_posix())
    print(OUT_MD.relative_to(ROOT).as_posix())
    print(next(row["status"] for row in audit_rows if row["audit_id"] == "release_recommendation"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
