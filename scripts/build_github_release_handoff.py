from __future__ import annotations

import argparse
import csv
import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "release"
DOC_MD = OUT_DIR / "github_release_handoff.md"
MANIFEST_TSV = OUT_DIR / "github_release_handoff_manifest.tsv"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


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


def _require_git_ok(args: list[str], message: str) -> str:
    code, out = _git(args)
    if code != 0:
        raise RuntimeError(f"{message}: {out}")
    return out


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["artifact", "path", "size_bytes", "sha256", "status", "notes"],
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


def _bundle_path(tag: str) -> Path:
    safe_tag = tag.replace("/", "-")
    return OUT_DIR / f"rmtguard_{safe_tag}_source.bundle"


def build_handoff(tag: str, repo_url: str | None = None) -> list[dict[str, str]]:
    _require_git_ok(["rev-parse", "--is-inside-work-tree"], "Not a Git work tree")
    status = _require_git_ok(["status", "--short"], "Could not read git status")
    if status.strip():
        raise RuntimeError(
            "Git work tree must be clean before building the release handoff bundle."
        )
    _require_git_ok(
        ["rev-parse", "--verify", tag], f"Required tag does not exist: {tag}"
    )
    head = _require_git_ok(["rev-parse", "--short", "HEAD"], "Could not read HEAD")
    tag_target = _require_git_ok(
        ["rev-list", "-n", "1", tag], f"Could not resolve tag: {tag}"
    )
    head_full = _require_git_ok(["rev-parse", "HEAD"], "Could not resolve HEAD")
    if tag_target != head_full:
        raise RuntimeError(f"Tag {tag} does not point at HEAD {head}.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bundle = _bundle_path(tag)
    tmp_bundle = bundle.with_suffix(bundle.suffix + ".tmp")
    if tmp_bundle.exists():
        tmp_bundle.unlink()
    code, out = _git(["bundle", "create", str(tmp_bundle), tag])
    if code != 0:
        raise RuntimeError(f"git bundle create failed: {out}")
    tmp_bundle.replace(bundle)
    bundle_hash = _sha256(bundle)

    manifest_rows = [
        {
            "artifact": "source_git_bundle",
            "path": _rel(bundle),
            "size_bytes": str(bundle.stat().st_size),
            "sha256": bundle_hash,
            "status": "ready",
            "notes": f"Contains tag {tag} at commit {head}.",
        },
        {
            "artifact": "handoff_document",
            "path": _rel(DOC_MD),
            "size_bytes": "pending",
            "sha256": "pending",
            "status": "ready",
            "notes": "Human-readable upload and verification commands.",
        },
    ]
    _write_tsv(MANIFEST_TSV, manifest_rows)
    _write_text(DOC_MD, _handoff_markdown(tag, head, bundle, bundle_hash, repo_url))

    rows = [
        {
            "artifact": "source_git_bundle",
            "path": _rel(bundle),
            "size_bytes": str(bundle.stat().st_size),
            "sha256": bundle_hash,
            "status": "ready",
            "notes": f"Contains tag {tag} at commit {head}.",
        },
        {
            "artifact": "handoff_document",
            "path": _rel(DOC_MD),
            "size_bytes": str(DOC_MD.stat().st_size),
            "sha256": _sha256(DOC_MD),
            "status": "ready",
            "notes": "Human-readable upload and verification commands.",
        },
    ]
    _write_tsv(MANIFEST_TSV, rows)
    return rows


def _handoff_markdown(
    tag: str, head: str, bundle: Path, bundle_hash: str, repo_url: str | None
) -> list[str]:
    repo_placeholder = repo_url or "https://github.com/<owner>/rmtguard"
    git_url = repo_placeholder.rstrip("/") + ".git"
    return [
        "# GitHub Release Handoff",
        "",
        "This file is generated by `python scripts/build_github_release_handoff.py`.",
        "",
        "## Current Local Release Candidate",
        "",
        f"- Tag: `{tag}`",
        f"- Commit: `{head}`",
        f"- Source bundle: `{_rel(bundle)}`",
        f"- SHA256: `{bundle_hash}`",
        "",
        "## Boundary",
        "",
        "This handoff bundle is not a public GitHub Release and does not create a Zenodo DOI. It is a transfer artifact for pushing the exact local release candidate to a real GitHub repository.",
        "",
        "## Verify Bundle",
        "",
        "```bash",
        f"git bundle verify {_rel(bundle)}",
        "```",
        "",
        "## Push To GitHub After Repository Exists",
        "",
        "```bash",
        f"python scripts/update_repository_metadata.py --repo-url {repo_placeholder} --execute",
        "python scripts/build_release_readiness.py",
        f"git remote add origin {git_url}",
        "git branch -M main",
        "git push -u origin main",
        f"git push origin {tag}",
        "```",
        "",
        "## Create Public Release",
        "",
        "1. Create a GitHub Release from the pushed tag.",
        "2. Attach approved generated artifacts listed in `results/release/release_asset_manifest.tsv` if needed.",
        "3. Archive the GitHub Release with Zenodo.",
        "4. Record the Zenodo DOI in `.zenodo.json` and code-availability documents.",
        "5. Rerun `python scripts/build_release_readiness.py` and `python scripts/update_gate_evidence_from_results.py`.",
        "",
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a GitHub release handoff bundle and upload instructions."
    )
    parser.add_argument("--tag", default="v0.1.0-rc8")
    parser.add_argument("--repo-url", default=None)
    args = parser.parse_args(argv)
    rows = build_handoff(args.tag, args.repo_url)
    print(_rel(MANIFEST_TSV))
    print(_rel(DOC_MD))
    for row in rows:
        print(f"{row['artifact']}\t{row['status']}\t{row['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
