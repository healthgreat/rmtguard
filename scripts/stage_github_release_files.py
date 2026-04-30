from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "results" / "release" / "github_staging_manifest.tsv"
DEFAULT_OUT = ROOT / "results" / "release" / "github_stage_dry_run.tsv"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "status", "notes"], delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _validate_relative_path(path_text: str) -> Path:
    if not path_text or Path(path_text).is_absolute():
        raise ValueError(f"Staging path must be a non-empty relative path: {path_text!r}")
    path = ROOT / path_text
    resolved = path.resolve()
    if ROOT.resolve() not in [resolved, *resolved.parents]:
        raise ValueError(f"Staging path escapes project root: {path_text}")
    return path


def stageable_paths(rows: list[dict[str, str]]) -> list[str]:
    out: list[str] = []
    for row in rows:
        if row.get("action") != "stage_for_initial_commit":
            continue
        if row.get("git_ignored") == "True":
            raise ValueError(f"Refusing to stage ignored path: {row.get('path')}")
        path = _validate_relative_path(row.get("path", ""))
        if not path.exists():
            raise FileNotFoundError(f"Staging path does not exist: {row.get('path')}")
        out.append(row["path"])
    return out


def build_dry_run_rows(paths: list[str]) -> list[dict[str, str]]:
    return [
        {
            "path": path,
            "status": "would_stage",
            "notes": "Use --execute to run git add for this path.",
        }
        for path in paths
    ]


def _git_add(paths: list[str]) -> None:
    if not paths:
        return
    batch_size = 40
    for start in range(0, len(paths), batch_size):
        batch = paths[start : start + batch_size]
        result = subprocess.run(
            ["git", "add", "--", *batch],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stdout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safely stage only files approved by the generated GitHub staging manifest.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--execute", action="store_true", help="Actually run git add for approved files. Default is dry-run.")
    args = parser.parse_args(argv)

    rows = _read_tsv(args.manifest)
    paths = stageable_paths(rows)
    dry_run_rows = build_dry_run_rows(paths)
    if args.execute:
        _git_add(paths)
        for row in dry_run_rows:
            row["status"] = "staged"
            row["notes"] = "Staged with git add."
    _write_tsv(args.out, dry_run_rows)
    print(_rel(args.out))
    print(f"{'staged' if args.execute else 'would_stage'}\t{len(paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
