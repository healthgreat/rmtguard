from __future__ import annotations

import csv
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "release"
MANIFEST = OUT_DIR / "release_artifact_manifest.tsv"
SUMMARY = OUT_DIR / "release_artifact_summary.tsv"


SCAN_DIRS = [
    "src",
    "scripts",
    "benchmarks",
    "tests",
    "examples",
    "docs",
    "metadata",
    "manuscript",
    "data",
    "results",
    "figures",
    ".github",
]
ROOT_FILES = [
    ".gitignore",
    ".zenodo.json",
    "CITATION.cff",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "Dockerfile",
    "LICENSE",
    "Makefile",
    "PROJECT_STATUS.md",
    "README.md",
    "pyproject.toml",
    "requirements.txt",
]
IGNORED_TOP_LEVEL = {"SheafSignal", "BioSignal_Stress_Test", "StateBridge", ".git"}


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _git_check_ignore(path: Path) -> bool:
    rel = _rel(path)
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", rel],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for rel in ROOT_FILES:
        path = ROOT / rel
        if path.exists() and path.is_file():
            files.append(path)
    for rel in SCAN_DIRS:
        root = ROOT / rel
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            parts = path.relative_to(ROOT).parts
            if parts and parts[0] in IGNORED_TOP_LEVEL:
                continue
            if any(part in {"__pycache__", ".pytest_cache"} for part in parts):
                continue
            files.append(path)
    return sorted(set(files), key=_rel)


def _classify(path: Path, ignored: bool) -> tuple[str, str, str, str]:
    rel = _rel(path)
    size = path.stat().st_size

    if rel.endswith(".gitkeep"):
        return (
            "directory_placeholder",
            "github_repository",
            "yes",
            "Directory placeholder is safe to commit.",
        )
    if rel.startswith("data/raw/"):
        return (
            "public_raw_data",
            "do_not_commit_accession_script_only",
            "yes",
            "Raw public data should be downloaded from the accession or URL in metadata/datasets.tsv.",
        )
    if rel.startswith("data/processed/") or rel == "data/pbmc3k_raw.h5ad":
        return (
            "processed_public_data",
            "do_not_commit_rebuild_or_archive_large_outputs",
            "yes",
            "Processed AnnData matrices are reproducible from public scripts and should not be committed directly.",
        )
    if rel.startswith("results/"):
        result_dirs = rel.split("/")[1:-1]
        if any("probe" in directory or "diagnostic" in directory for directory in result_dirs):
            return (
                "development_probe_output",
                "local_archive_only",
                "no",
                "Probe output is useful for method history but should not be part of the main GitHub release.",
            )
        return (
            "manuscript_result_or_source_data",
            "zenodo_or_github_release_asset",
            "yes",
            "Current benchmark tables, gates, source data, and release summaries should be archived with a DOI.",
        )
    if rel.startswith("figures/manuscript/"):
        return (
            "draft_rendered_figure",
            "zenodo_or_github_release_asset",
            "yes",
            "Draft figure renders are reproducible artifacts for manuscript assembly, not final production artwork.",
        )
    if rel.startswith("figures/"):
        return (
            "figure_placeholder_or_generated",
            "do_not_commit_unless_small_fixture",
            "no",
            "Generated figures are ignored by default; keep source scripts as the authoritative record.",
        )
    if size > 50 * 1024 * 1024:
        return (
            "large_file",
            "do_not_commit_review_manually",
            "yes",
            "Large file exceeds 50 MB and needs explicit release handling.",
        )
    if ignored:
        return (
            "ignored_local_file",
            "do_not_commit_review_if_needed",
            "no",
            "File is ignored by .gitignore and should not be accidentally uploaded.",
        )
    return (
        "source_code_or_metadata",
        "github_repository",
        "yes",
        "Small source, documentation, metadata, or workflow file intended for GitHub.",
    )


def build_manifest() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in _iter_files():
        ignored = _git_check_ignore(path)
        artifact_type, release_destination, required, notes = _classify(path, ignored)
        rows.append(
            {
                "path": _rel(path),
                "artifact_type": artifact_type,
                "size_bytes": str(path.stat().st_size),
                "git_ignored": str(ignored),
                "release_destination": release_destination,
                "required_for_submission_package": required,
                "notes": notes,
            }
        )
    return rows


def _write_tsv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def write_outputs(rows: list[dict[str, str]]) -> None:
    _write_tsv(
        MANIFEST,
        rows,
        [
            "path",
            "artifact_type",
            "size_bytes",
            "git_ignored",
            "release_destination",
            "required_for_submission_package",
            "notes",
        ],
    )
    summary: dict[tuple[str, str], dict[str, int]] = {}
    for row in rows:
        key = (row["artifact_type"], row["release_destination"])
        bucket = summary.setdefault(key, {"file_count": 0, "size_bytes": 0})
        bucket["file_count"] += 1
        bucket["size_bytes"] += int(row["size_bytes"])
    summary_rows = [
        {
            "artifact_type": artifact_type,
            "release_destination": release_destination,
            "file_count": str(values["file_count"]),
            "size_bytes": str(values["size_bytes"]),
        }
        for (artifact_type, release_destination), values in sorted(summary.items())
    ]
    _write_tsv(SUMMARY, summary_rows, ["artifact_type", "release_destination", "file_count", "size_bytes"])


def main() -> int:
    rows = build_manifest()
    write_outputs(rows)
    print(_rel(MANIFEST))
    print(_rel(SUMMARY))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
