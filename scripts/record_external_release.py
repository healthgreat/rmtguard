from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "release"
PLAN_TSV = OUT_DIR / "external_release_metadata_plan.tsv"
REPO_PLACEHOLDERS = [
    "https://github.com/your-lab/rmtguard.git",
    "https://github.com/your-lab/rmtguard",
]

TARGET_TEXT_FILES = [
    ROOT / "pyproject.toml",
    ROOT / "CITATION.cff",
    ROOT / "docs" / "data_and_code_availability_template.md",
    ROOT / "docs" / "github_release_checklist.md",
    ROOT / "results" / "release" / "github_release_handoff.md",
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


def normalize_doi(doi: str) -> str:
    doi = doi.strip()
    doi = doi.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    if not re.fullmatch(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", doi):
        raise ValueError("DOI must look like 10.xxxx/xxxxx")
    return doi


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _write_text(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _write_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["path", "status", "planned_change", "notes"],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _repo_replacements(repo_url: str) -> list[tuple[str, str]]:
    repo_url = normalize_repo_url(repo_url)
    return [
        ("https://github.com/your-lab/rmtguard.git", repo_url + ".git"),
        ("https://github.com/your-lab/rmtguard", repo_url),
        ("https://github.com/<owner>/rmtguard.git", repo_url + ".git"),
        ("https://github.com/<owner>/rmtguard", repo_url),
    ]


def _update_citation_doi(text: str, doi: str) -> str:
    doi = normalize_doi(doi)
    if re.search(r"^doi:\s*", text, flags=re.MULTILINE):
        return re.sub(r"^doi:\s*.*$", f'doi: "{doi}"', text, flags=re.MULTILINE)
    lines = text.splitlines()
    insert_at = 0
    for idx, line in enumerate(lines):
        if line.startswith("repository-code:"):
            insert_at = idx + 1
            break
    lines.insert(insert_at, f'doi: "{doi}"')
    return "\n".join(lines) + "\n"


def _update_code_availability(text: str, repo_url: str, doi: str) -> str:
    doi = normalize_doi(doi)
    repo_url = normalize_repo_url(repo_url)
    text = text.replace("https://github.com/your-lab/rmtguard", repo_url)
    doi_url = f"https://doi.org/{doi}"
    if "Zenodo DOI:" in text:
        text = re.sub(r"Zenodo DOI:\s*.*", f"Zenodo DOI: {doi_url}", text)
    else:
        text = text.rstrip() + f"\n\nZenodo DOI: {doi_url}\n"
    return text


def _update_text_file(path: Path, repo_url: str, doi: str) -> tuple[str, str]:
    text = _read_text(path)
    if not text:
        return "missing", "Target text file is missing."
    updated = text
    for old, new in _repo_replacements(repo_url):
        updated = updated.replace(old, new)
    if path.name == "CITATION.cff":
        updated = _update_citation_doi(updated, doi)
    if path.name == "data_and_code_availability_template.md":
        updated = _update_code_availability(updated, repo_url, doi)
    if updated == text:
        return "unchanged", "No placeholder or DOI field needed updating."
    return "would_update", "Repository URL and/or DOI metadata would be updated."


def planned_rows(repo_url: str | None, doi: str | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not repo_url or not doi:
        for path in [*TARGET_TEXT_FILES, ROOT / ".zenodo.json"]:
            rows.append(
                {
                    "path": _rel(path),
                    "status": "pending",
                    "planned_change": "",
                    "notes": "Provide --repo-url and --doi to preview or execute external release metadata recording.",
                }
            )
        return rows

    repo_url = normalize_repo_url(repo_url)
    doi = normalize_doi(doi)
    for path in TARGET_TEXT_FILES:
        status, notes = _update_text_file(path, repo_url, doi)
        rows.append(
            {
                "path": _rel(path),
                "status": status,
                "planned_change": f"repo={repo_url}; doi={doi}",
                "notes": notes,
            }
        )

    zenodo_path = ROOT / ".zenodo.json"
    if zenodo_path.exists():
        payload = json.loads(zenodo_path.read_text(encoding="utf-8"))
        status = "unchanged" if payload.get("doi") == doi else "would_update"
        notes = "Zenodo DOI already recorded." if status == "unchanged" else "Zenodo DOI would be recorded."
    else:
        status = "missing"
        notes = ".zenodo.json is missing."
    rows.append(
        {
            "path": _rel(zenodo_path),
            "status": status,
            "planned_change": f"doi={doi}",
            "notes": notes,
        }
    )
    return rows


def execute(repo_url: str, doi: str, set_remote: bool = False) -> None:
    repo_url = normalize_repo_url(repo_url)
    doi = normalize_doi(doi)
    for path in TARGET_TEXT_FILES:
        if not path.exists():
            continue
        text = _read_text(path)
        updated = text
        for old, new in _repo_replacements(repo_url):
            updated = updated.replace(old, new)
        if path.name == "CITATION.cff":
            updated = _update_citation_doi(updated, doi)
        if path.name == "data_and_code_availability_template.md":
            updated = _update_code_availability(updated, repo_url, doi)
        if updated != text:
            _write_text(path, updated)

    zenodo_path = ROOT / ".zenodo.json"
    payload = json.loads(zenodo_path.read_text(encoding="utf-8")) if zenodo_path.exists() else {}
    payload["doi"] = doi
    payload["related_identifiers"] = [{"identifier": repo_url, "relation": "isSupplementTo", "resource_type": "software"}]
    _write_json(zenodo_path, payload)

    if set_remote:
        remote_url = repo_url + ".git"
        code = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
        if code == 0:
            subprocess.run(["git", "remote", "set-url", "origin", remote_url], cwd=ROOT, check=True)
        else:
            subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=ROOT, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record real GitHub and Zenodo release metadata after external release exists.")
    parser.add_argument("--repo-url", default=None)
    parser.add_argument("--doi", default=None)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--set-remote", action="store_true")
    parser.add_argument("--out", type=Path, default=PLAN_TSV)
    args = parser.parse_args(argv)

    if args.execute and (not args.repo_url or not args.doi):
        raise SystemExit("--execute requires --repo-url and --doi")
    rows = planned_rows(args.repo_url, args.doi)
    _write_tsv(args.out, rows)
    if args.execute:
        execute(args.repo_url, args.doi, set_remote=args.set_remote)
        rows = planned_rows(args.repo_url, args.doi)
        _write_tsv(args.out, rows)
    print(_rel(args.out))
    print(f"{'updated' if args.execute else 'dry_run'}\t{sum(row['status'] == 'would_update' for row in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
