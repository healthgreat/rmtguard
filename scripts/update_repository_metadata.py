from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "release"
PLAN_TSV = OUT_DIR / "repository_metadata_update_plan.tsv"
PLACEHOLDER_REPO = "https://github.com/your-lab/rmtguard"
PLACEHOLDER_GIT = "https://github.com/your-lab/rmtguard.git"


TARGET_FILES = [
    ROOT / "pyproject.toml",
    ROOT / "CITATION.cff",
    ROOT / "docs" / "data_and_code_availability_template.md",
    ROOT / "docs" / "github_release_checklist.md",
]


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def normalize_repo_url(repo_url: str) -> str:
    repo_url = repo_url.strip().rstrip("/")
    if repo_url.endswith(".git"):
        repo_url = repo_url[:-4]
    if not re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo_url):
        raise ValueError("Repository URL must look like https://github.com/<owner>/<repo>")
    return repo_url


def replacement_pairs(repo_url: str) -> list[tuple[str, str]]:
    repo_url = normalize_repo_url(repo_url)
    return [
        (PLACEHOLDER_GIT, repo_url + ".git"),
        (PLACEHOLDER_REPO, repo_url),
    ]


def planned_rows(repo_url: str | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    pairs = replacement_pairs(repo_url) if repo_url else []
    for path in TARGET_FILES:
        if not path.exists():
            rows.append(
                {
                    "path": _rel(path),
                    "status": "missing",
                    "placeholder_hits": "0",
                    "replacement_preview": "",
                    "notes": "Target metadata file is missing.",
                }
            )
            continue
        text = path.read_text(encoding="utf-8")
        hits = text.count(PLACEHOLDER_REPO) + text.count(PLACEHOLDER_GIT)
        if repo_url is None:
            status = "pending"
            preview = ""
            notes = "Provide --repo-url to preview or execute repository URL replacement."
        elif hits == 0:
            status = "unchanged"
            preview = ""
            notes = "No placeholder repository URL found."
        else:
            status = "would_update"
            preview = "; ".join(f"{old} -> {new}" for old, new in pairs if old in text)
            notes = "Use --execute to write this replacement."
        rows.append(
            {
                "path": _rel(path),
                "status": status,
                "placeholder_hits": str(hits),
                "replacement_preview": preview,
                "notes": notes,
            }
        )
    return rows


def write_plan(rows: list[dict[str, str]], out: Path = PLAN_TSV) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["path", "status", "placeholder_hits", "replacement_preview", "notes"],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(out)


def execute_replacements(repo_url: str) -> None:
    pairs = replacement_pairs(repo_url)
    for path in TARGET_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        updated = text
        for old, new in pairs:
            updated = updated.replace(old, new)
        if updated != text:
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(updated, encoding="utf-8")
            tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preview or update repository URLs in release metadata.")
    parser.add_argument("--repo-url", default=None, help="Real GitHub URL, for example https://github.com/<owner>/rmtguard.")
    parser.add_argument("--execute", action="store_true", help="Write URL replacements. Default only writes a dry-run plan.")
    parser.add_argument("--out", type=Path, default=PLAN_TSV)
    args = parser.parse_args(argv)

    if args.execute and not args.repo_url:
        raise SystemExit("--execute requires --repo-url")
    rows = planned_rows(args.repo_url)
    write_plan(rows, args.out)
    if args.execute and args.repo_url:
        execute_replacements(args.repo_url)
        rows = planned_rows(args.repo_url)
        write_plan(rows, args.out)
    print(_rel(args.out))
    print(f"{'updated' if args.execute else 'dry_run'}\t{sum(row['status'] == 'would_update' for row in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
