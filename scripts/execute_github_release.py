from __future__ import annotations

"""Execute or dry-run the GitHub side of the RMTGuard external release.

Author: RMTGuard development team
Date: 2026-04-30
Purpose: Automate the GitHub repository push and release creation once a real
repository URL and GitHub token are available.
Data source: Local Git tag plus generated release manifests.
Method notes: The default mode is dry-run. `--execute` requires
GITHUB_TOKEN or GH_TOKEN and never records the token in project files.
"""

import argparse
import base64
import csv
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "release"
EXECUTION_TSV = OUT_DIR / "github_release_execution_plan.tsv"
EXECUTION_MD = ROOT / "docs" / "github_release_execution.md"
ASSET_MANIFEST = OUT_DIR / "release_asset_manifest.tsv"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def normalize_repo_url(repo_url: str) -> str:
    repo_url = repo_url.strip().rstrip("/")
    if repo_url.endswith(".git"):
        repo_url = repo_url[:-4]
    if not re.fullmatch(
        r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo_url
    ):
        raise ValueError(
            "Repository URL must look like https://github.com/<owner>/<repo>"
        )
    return repo_url


def parse_repo(repo_url: str) -> tuple[str, str]:
    repo_url = normalize_repo_url(repo_url)
    parsed = urllib.parse.urlparse(repo_url)
    parts = parsed.path.strip("/").split("/")
    if len(parts) != 2:
        raise ValueError(
            "Repository URL must look like https://github.com/<owner>/<repo>"
        )
    return parts[0], parts[1]


def _token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def _git(
    args: list[str], *, token: str | None = None, check: bool = False
) -> tuple[int, str]:
    cmd = ["git"]
    redactions: list[str] = []
    if token:
        basic = base64.b64encode(f"x-access-token:{token}".encode("ascii")).decode(
            "ascii"
        )
        redactions.extend([token, basic])
        cmd.extend(
            [
                "-c",
                "credential.helper=",
                "-c",
                "credential.interactive=never",
                "-c",
                "core.askPass=",
                "-c",
                f"http.extraheader=AUTHORIZATION: Basic {basic}",
            ]
        )
    cmd.extend(args)
    env = os.environ.copy()
    env.update(
        {
            "GIT_TERMINAL_PROMPT": "0",
            "GCM_INTERACTIVE": "Never",
            "GIT_ASKPASS": "",
            "SSH_ASKPASS": "",
        }
    )
    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            env=env,
            timeout=120,
        )
        output = result.stdout.strip()
        code = result.returncode
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        output = (output + "\ngit command timed out after 120 seconds").strip()
        code = 124
    for secret in redactions:
        output = output.replace(secret, "[REDACTED]")
    if check and code != 0:
        raise RuntimeError(output)
    return code, output


def _github_api(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
    content_type: str = "application/vnd.github+json",
    data: bytes | None = None,
) -> tuple[int, dict[str, Any] | str]:
    body = data
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            text = raw.decode("utf-8", errors="replace")
            if "application/json" in response.headers.get("Content-Type", ""):
                return response.status, json.loads(text) if text else {}
            return response.status, text
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(text)
        except json.JSONDecodeError:
            return exc.code, text


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "step_id",
                "status",
                "command_or_endpoint",
                "evidence_path",
                "notes",
            ],
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


def _selected_assets(max_assets: int) -> list[Path]:
    if not ASSET_MANIFEST.exists():
        return []
    with ASSET_MANIFEST.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    out: list[Path] = []
    for row in rows:
        if row.get("asset_status") != "selected":
            continue
        path = ROOT / row.get("path", "")
        if path.exists() and path.is_file():
            out.append(path)
        if len(out) >= max_assets:
            break
    return out


def build_plan(
    repo_url: str, tag: str, upload_assets: bool = False, max_assets: int = 0
) -> list[dict[str, str]]:
    repo_url = normalize_repo_url(repo_url)
    owner, repo = parse_repo(repo_url)
    token_available = _token() is not None
    code, status = _git(["status", "--short"])
    clean = code == 0 and not status.strip()
    code, tag_target = _git(["rev-list", "-n", "1", tag])
    tag_exists = code == 0 and bool(tag_target)
    code, head = _git(["rev-parse", "HEAD"])
    tag_points_to_head = tag_exists and code == 0 and tag_target == head
    assets = _selected_assets(max_assets) if upload_assets else []

    return [
        {
            "step_id": "01_validate_local_git",
            "status": "ready" if clean and tag_points_to_head else "blocked",
            "command_or_endpoint": f"git status --short; git rev-list -n 1 {tag}",
            "evidence_path": ".git",
            "notes": "Clean work tree and tag at HEAD are required.",
        },
        {
            "step_id": "02_validate_github_token",
            "status": "ready" if token_available else "blocked_external",
            "command_or_endpoint": "GITHUB_TOKEN or GH_TOKEN",
            "evidence_path": "environment",
            "notes": "A GitHub token with repository write/release permission is required for --execute.",
        },
        {
            "step_id": "03_configure_remote",
            "status": "would_run",
            "command_or_endpoint": f"git remote set-url/add origin {repo_url}.git",
            "evidence_path": ".git/config",
            "notes": "The token is not written to the remote URL.",
        },
        {
            "step_id": "04_push_main_and_tag",
            "status": "would_run",
            "command_or_endpoint": f"git push origin HEAD:main; git push origin {tag}",
            "evidence_path": ".git",
            "notes": "Pushes the current committed source tree and release tag.",
        },
        {
            "step_id": "05_create_github_release",
            "status": "would_run",
            "command_or_endpoint": f"https://api.github.com/repos/{owner}/{repo}/releases",
            "evidence_path": EXECUTION_TSV.as_posix(),
            "notes": "Creates or reuses the GitHub Release for the tag.",
        },
        {
            "step_id": "06_upload_release_assets",
            "status": "would_run" if upload_assets else "skipped",
            "command_or_endpoint": f"uploads.github.com/repos/{owner}/{repo}/releases/<id>/assets",
            "evidence_path": _rel(ASSET_MANIFEST),
            "notes": f"Selected assets requested: {len(assets)}. Use --upload-assets --max-assets N intentionally.",
        },
    ]


def _set_remote(repo_url: str) -> None:
    remote_url = normalize_repo_url(repo_url) + ".git"
    code, _ = _git(["remote", "get-url", "origin"])
    if code == 0:
        _git(["remote", "set-url", "origin", remote_url], check=True)
    else:
        _git(["remote", "add", "origin", remote_url], check=True)


def _create_or_get_release(
    repo_url: str, tag: str, token: str, prerelease: bool
) -> dict[str, Any]:
    owner, repo = parse_repo(repo_url)
    get_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{urllib.parse.quote(tag)}"
    status, payload = _github_api("GET", get_url, token)
    if status == 200 and isinstance(payload, dict):
        return payload
    create_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    body = {
        "tag_name": tag,
        "target_commitish": "main",
        "name": tag,
        "body": "RMTGuard manuscript release candidate. Public data are downloaded from accessions; generated source-data assets are archived separately as needed.",
        "draft": False,
        "prerelease": prerelease,
    }
    status, payload = _github_api("POST", create_url, token, payload=body)
    if status not in {200, 201} or not isinstance(payload, dict):
        raise RuntimeError(f"GitHub release creation failed ({status}): {payload}")
    return payload


def _upload_asset(upload_url_template: str, path: Path, token: str) -> str:
    upload_url = upload_url_template.split("{", 1)[0]
    url = upload_url + "?" + urllib.parse.urlencode({"name": path.name})
    status, payload = _github_api(
        "POST",
        url,
        token,
        data=path.read_bytes(),
        content_type="application/octet-stream",
    )
    if status not in {200, 201}:
        raise RuntimeError(f"Asset upload failed for {path.name} ({status}): {payload}")
    if isinstance(payload, dict):
        return str(payload.get("browser_download_url", ""))
    return ""


def execute(
    repo_url: str, tag: str, upload_assets: bool, max_assets: int, prerelease: bool
) -> list[dict[str, str]]:
    token = _token()
    if token is None:
        raise RuntimeError("--execute requires GITHUB_TOKEN or GH_TOKEN")
    plan = build_plan(repo_url, tag, upload_assets=upload_assets, max_assets=max_assets)
    blocked = [row for row in plan if row["status"].startswith("blocked")]
    if blocked:
        raise RuntimeError(
            "Blocked release execution: " + ", ".join(row["step_id"] for row in blocked)
        )

    _set_remote(repo_url)
    _git(["push", "-u", "origin", "HEAD:main"], token=token, check=True)
    _git(["push", "origin", tag], token=token, check=True)
    release = _create_or_get_release(repo_url, tag, token, prerelease=prerelease)
    uploaded: list[str] = []
    if upload_assets:
        upload_url = str(release.get("upload_url", ""))
        for asset in _selected_assets(max_assets):
            uploaded.append(_upload_asset(upload_url, asset, token))

    rows = build_plan(repo_url, tag, upload_assets=upload_assets, max_assets=max_assets)
    for row in rows:
        if row["status"] == "would_run":
            row["status"] = "executed"
        if row["step_id"] == "05_create_github_release":
            row["evidence_path"] = str(release.get("html_url", ""))
    if uploaded:
        rows.append(
            {
                "step_id": "07_uploaded_asset_urls",
                "status": "executed",
                "command_or_endpoint": ";".join(uploaded),
                "evidence_path": str(release.get("html_url", "")),
                "notes": "Uploaded release assets.",
            }
        )
    return rows


def build_markdown(
    rows: list[dict[str, str]], repo_url: str, tag: str, execute_mode: bool
) -> list[str]:
    blocked = [row for row in rows if row["status"].startswith("blocked")]
    lines = [
        "# GitHub Release Execution",
        "",
        "This file is generated by `python scripts/execute_github_release.py`.",
        "",
        f"- Repository: `{normalize_repo_url(repo_url)}`",
        f"- Tag: `{tag}`",
        f"- Execute mode: `{execute_mode}`",
        "- Acceptance guarantee: `impossible`; this only automates the GitHub release evidence required by the submission gate.",
        "",
        "## Blocking Items",
        "",
    ]
    if blocked:
        lines.extend(f"- `{row['step_id']}`: {row['notes']}" for row in blocked)
    else:
        lines.append("- none")
    lines.extend(["", "## Steps", ""])
    for row in rows:
        lines.extend(
            [
                f"### {row['step_id']}",
                "",
                f"- Status: `{row['status']}`",
                f"- Command or endpoint: `{row['command_or_endpoint']}`",
                f"- Evidence: `{row['evidence_path']}`",
                f"- Notes: {row['notes']}",
                "",
            ]
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run or execute GitHub push/release creation for RMTGuard."
    )
    parser.add_argument(
        "--repo-url",
        required=True,
        help="Real GitHub URL, e.g. https://github.com/<owner>/rmtguard",
    )
    parser.add_argument("--tag", default="v0.1.0-rc8")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--upload-assets", action="store_true")
    parser.add_argument("--max-assets", type=int, default=0)
    parser.add_argument(
        "--final-release",
        action="store_true",
        help="Mark release as non-prerelease. Default keeps rc tag as prerelease.",
    )
    parser.add_argument("--out", type=Path, default=EXECUTION_TSV)
    args = parser.parse_args(argv)

    if args.max_assets < 0:
        raise SystemExit("--max-assets must be >= 0")
    if args.execute:
        rows = execute(
            args.repo_url,
            args.tag,
            upload_assets=args.upload_assets,
            max_assets=args.max_assets,
            prerelease=not args.final_release,
        )
    else:
        rows = build_plan(
            args.repo_url,
            args.tag,
            upload_assets=args.upload_assets,
            max_assets=args.max_assets,
        )
    _write_tsv(args.out, rows)
    _write_text(
        EXECUTION_MD,
        build_markdown(rows, args.repo_url, args.tag, execute_mode=args.execute),
    )
    print(_rel(args.out))
    print(_rel(EXECUTION_MD))
    print(
        f"{'executed' if args.execute else 'dry_run'}\t{sum(row['status'].startswith('blocked') for row in rows)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
