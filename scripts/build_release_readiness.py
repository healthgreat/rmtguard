from __future__ import annotations

import csv
import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "release"
READINESS_TSV = OUT_DIR / "release_readiness.tsv"
SUMMARY_TXT = OUT_DIR / "release_audit_summary.txt"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _row(
    check_id: str, status: str, evidence_path: Path | str, notes: str
) -> dict[str, str]:
    evidence = _rel(evidence_path) if isinstance(evidence_path, Path) else evidence_path
    return {
        "check_id": check_id,
        "status": status,
        "evidence_path": evidence,
        "notes": notes,
    }


def _text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


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


def _load_release_audit() -> object:
    script = ROOT / "scripts" / "release_audit.py"
    spec = importlib.util.spec_from_file_location("release_audit", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load release_audit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _release_audit_status() -> tuple[str, str]:
    module = _load_release_audit()
    code = module.main()
    if code == 0:
        return "pass", "Local release audit passed."
    return (
        "fail",
        "Local release audit failed; run python scripts/clean_artifacts.py then python scripts/release_audit.py.",
    )


def _placeholder_url_status() -> tuple[str, str]:
    paths = [
        ROOT / "pyproject.toml",
        ROOT / "CITATION.cff",
        ROOT / "docs" / "data_and_code_availability_template.md",
    ]
    text = "\n".join(_text(path) for path in paths)
    if "your-lab/rmtguard" in text:
        return (
            "pending",
            "Repository URLs still contain the placeholder your-lab/rmtguard.",
        )
    if "github.com" in text and "rmtguard" in text.lower():
        return "pass", "Repository URLs no longer use the placeholder."
    return "pending", "Repository URL is not yet recorded in release metadata."


def _zenodo_status() -> tuple[str, str]:
    text = _text(ROOT / ".zenodo.json").lower()
    if "doi" in text and "10." in text:
        return "pass", "Zenodo DOI appears in .zenodo.json."
    return "pending", "Zenodo DOI is not available until a GitHub release is archived."


def _git_release_status() -> tuple[str, str]:
    code, inside = _git(["rev-parse", "--is-inside-work-tree"])
    if code != 0 or inside.lower() != "true":
        return "pending", "This folder is not a Git work tree."
    code, head = _git(["rev-parse", "--verify", "HEAD"])
    if code != 0:
        return "pending", "No Git commit exists yet for a manuscript release tag."
    code, tags = _git(["tag", "--points-at", "HEAD"])
    if code == 0 and tags:
        return "pass", f"Current HEAD has release tag(s): {tags}."
    return (
        "pending",
        "Git repository exists, but the current HEAD is not tagged for release.",
    )


def _git_remote_status() -> tuple[str, str]:
    code, remotes = _git(["remote", "-v"])
    if code == 0 and "github.com" in remotes:
        return "pass", "GitHub remote is configured."
    return "pending", "GitHub remote is not configured in this local checkout."


def _git_worktree_status() -> tuple[str, str]:
    code, status = _git(["status", "--short"])
    if code != 0:
        return "pending", "Git status could not be read."
    if not status.strip():
        return "pass", "Git work tree is clean."
    lines = status.splitlines()
    return "pending", f"Git work tree has {len(lines)} uncommitted/untracked entries."


def _exists_status(
    check_id: str, path: Path, pass_notes: str, missing_notes: str
) -> dict[str, str]:
    if path.exists() and path.stat().st_size > 0:
        return _row(check_id, "pass", path, pass_notes)
    return _row(check_id, "pending", path, missing_notes)


def build_readiness_rows() -> list[dict[str, str]]:
    audit_status, audit_notes = _release_audit_status()
    url_status, url_notes = _placeholder_url_status()
    zenodo_status, zenodo_notes = _zenodo_status()
    tag_status, tag_notes = _git_release_status()
    remote_status, remote_notes = _git_remote_status()
    worktree_status, worktree_notes = _git_worktree_status()

    rows = [
        _row(
            "local_release_audit",
            audit_status,
            ROOT / "scripts" / "release_audit.py",
            audit_notes,
        ),
        _exists_status(
            "license",
            ROOT / "LICENSE",
            "MIT license file is present.",
            "LICENSE file is missing.",
        ),
        _exists_status(
            "citation_metadata",
            ROOT / "CITATION.cff",
            "Citation metadata is present.",
            "CITATION.cff is missing.",
        ),
        _exists_status(
            "zenodo_metadata",
            ROOT / ".zenodo.json",
            "Zenodo metadata file is present.",
            ".zenodo.json is missing.",
        ),
        _exists_status(
            "ci_workflow",
            ROOT / ".github" / "workflows" / "ci.yml",
            "GitHub Actions CI workflow is present.",
            "CI workflow is missing.",
        ),
        _exists_status(
            "dockerfile",
            ROOT / "Dockerfile",
            "Dockerfile is present.",
            "Dockerfile is missing.",
        ),
        _exists_status(
            "dataset_manifest",
            ROOT / "metadata" / "datasets.tsv",
            "Public dataset manifest is present.",
            "Dataset manifest is missing.",
        ),
        _exists_status(
            "figure_source_data_manifest",
            ROOT / "results" / "figures" / "figure_reproducibility.tsv",
            "Figure source-data manifest is present.",
            "Run python scripts/build_figure_source_data.py.",
        ),
        _exists_status(
            "rendered_figure_manifest",
            ROOT / "figures" / "manuscript" / "rendered_figure_manifest.tsv",
            "Rendered figure manifest is present.",
            "Run python scripts/render_main_figures.py.",
        ),
        _exists_status(
            "release_artifact_manifest",
            ROOT / "results" / "release" / "release_artifact_manifest.tsv",
            "Release artifact destination manifest is present.",
            "Run python scripts/build_release_artifact_manifest.py.",
        ),
        _exists_status(
            "github_staging_plan",
            ROOT / "results" / "release" / "github_staging_manifest.tsv",
            "GitHub staging manifest is present.",
            "Run python scripts/build_github_staging_plan.py.",
        ),
        _exists_status(
            "github_stage_dry_run",
            ROOT / "results" / "release" / "github_stage_dry_run.tsv",
            "GitHub staging dry-run output is present.",
            "Run python scripts/stage_github_release_files.py.",
        ),
        _exists_status(
            "github_release_handoff",
            ROOT / "results" / "release" / "github_release_handoff_manifest.tsv",
            "GitHub release handoff bundle manifest is present.",
            "Run python scripts/build_github_release_handoff.py.",
        ),
        _exists_status(
            "repository_metadata_update_plan",
            ROOT / "results" / "release" / "repository_metadata_update_plan.tsv",
            "Repository metadata update plan is present.",
            "Run python scripts/update_repository_metadata.py.",
        ),
        _exists_status(
            "external_release_metadata_plan",
            ROOT / "results" / "release" / "external_release_metadata_plan.tsv",
            "External release metadata recording plan is present.",
            "Run python scripts/record_external_release.py.",
        ),
        _exists_status(
            "external_release_plan",
            ROOT / "results" / "release" / "external_release_plan.tsv",
            "External GitHub/Zenodo release plan is present.",
            "Run python scripts/build_external_release_plan.py.",
        ),
        _exists_status(
            "public_release_blocker_report",
            ROOT / "results" / "release" / "public_release_blockers.tsv",
            "Public release blocker report is present.",
            "Run python scripts/build_public_release_blocker_report.py.",
        ),
        _exists_status(
            "release_asset_manifest",
            ROOT / "results" / "release" / "release_asset_manifest.tsv",
            "Release/Zenodo asset checksum manifest is present.",
            "Run python scripts/build_release_asset_bundle.py.",
        ),
        _exists_status(
            "manuscript_evidence_package",
            ROOT / "results" / "manuscript" / "claim_evidence_matrix.tsv",
            "Manuscript claim-evidence matrix is present.",
            "Run python scripts/build_manuscript_evidence_package.py.",
        ),
        _exists_status(
            "manuscript_draft_package",
            ROOT / "results" / "manuscript" / "reviewer_objection_matrix.tsv",
            "Guarded manuscript draft package and reviewer objection matrix are present.",
            "Run python scripts/build_manuscript_draft_package.py.",
        ),
        _exists_status(
            "stability_gate_report",
            ROOT
            / "results"
            / "stability_benchmarks"
            / "stability_gate_diagnostics.tsv",
            "Multi-dataset stability gate diagnostics are present.",
            "Run python scripts/build_stability_gate_report.py.",
        ),
        _exists_status(
            "no_call_benchmark_report",
            ROOT / "results" / "no_call_benchmarks" / "no_call_summary.tsv",
            "Diagnostic no-call benchmark report is present.",
            "Run python scripts/build_no_call_benchmark_report.py.",
        ),
        _exists_status(
            "publication_20_50_plan",
            ROOT / "results" / "gates" / "publication_20_50_decision.tsv",
            "20-50 JIF publication decision plan is present.",
            "Run python scripts/build_publication_20_50_plan.py.",
        ),
        _exists_status(
            "claim_scope_decision",
            ROOT / "results" / "submission" / "claim_scope_decision.tsv",
            "Claim-scope decision register is present.",
            "Run python scripts/build_claim_scope_decision.py.",
        ),
        _exists_status(
            "journal_compliance_audit",
            ROOT / "results" / "submission" / "nature_methods_compliance_audit.tsv",
            "Nature Methods compliance audit is present.",
            "Run python scripts/build_journal_compliance_audit.py.",
        ),
        _exists_status(
            "publication_execution_board",
            ROOT / "results" / "submission" / "publication_execution_board.tsv",
            "Publication execution board is present.",
            "Run python scripts/build_publication_execution_board.py.",
        ),
        _exists_status(
            "reporting_summary_draft",
            ROOT / "results" / "submission" / "reporting_summary_draft.tsv",
            "Nature reporting-summary draft worksheet is present.",
            "Run python scripts/build_reporting_summary_draft.py.",
        ),
        _exists_status(
            "editorial_risk_audit",
            ROOT / "results" / "submission" / "editorial_risk_audit.tsv",
            "Editorial desk-reject risk audit is present.",
            "Run python scripts/build_editorial_risk_audit.py.",
        ),
        _row("repository_url", url_status, ROOT / "pyproject.toml", url_notes),
        _row("github_remote", remote_status, ".git/config", remote_notes),
        _row("git_worktree", worktree_status, ".git", worktree_notes),
        _row("github_release_tag", tag_status, ".git", tag_notes),
        _row("zenodo_doi", zenodo_status, ROOT / ".zenodo.json", zenodo_notes),
    ]
    return rows


def write_rows(rows: list[dict[str, str]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = READINESS_TSV.with_suffix(READINESS_TSV.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["check_id", "status", "evidence_path", "notes"],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(READINESS_TSV)


def write_summary(rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    blocking = [row for row in rows if row["status"] != "pass"]
    lines = [
        "RMTGuard release readiness summary",
        f"pass\t{counts.get('pass', 0)}",
        f"pending\t{counts.get('pending', 0)}",
        f"fail\t{counts.get('fail', 0)}",
        "",
        "Blocking or pending items:",
    ]
    if blocking:
        lines.extend(
            f"- {row['check_id']}: {row['status']} - {row['notes']}" for row in blocking
        )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "Interpretation:",
            "The software_release submission gate should remain pending until a real GitHub Release and Zenodo DOI exist.",
        ]
    )
    tmp = SUMMARY_TXT.with_suffix(SUMMARY_TXT.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(SUMMARY_TXT)


def main() -> int:
    rows = build_readiness_rows()
    write_rows(rows)
    write_summary(rows)
    print(_rel(READINESS_TSV))
    print(_rel(SUMMARY_TXT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
