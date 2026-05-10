from __future__ import annotations

"""Record corresponding-author Figure 4 sign-off replies.

Author: RMTGuard development team
Date: 2026-05-10
Purpose: Update the corresponding-author sign-off tracker after a real email
reply or signed document is received.
Data source: metadata/corresponding_author_signoff_tracker.tsv and author
reply evidence supplied by the user.
Method notes: The script never fabricates confirmation. Confirmation-like
statuses require a real evidence file path.
"""

import argparse
import csv
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRACKER = ROOT / "metadata" / "corresponding_author_signoff_tracker.tsv"
VALID_STATUSES = {
    "pending_author_reply",
    "confirmed",
    "needs_revision",
    "rejected",
}
EVIDENCE_REQUIRED = {"confirmed", "needs_revision", "rejected"}


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Tracker not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_tsv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _resolve_evidence(raw: str) -> str:
    if not raw:
        return ""
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise FileNotFoundError(f"Evidence path does not exist: {path}")
    return _rel(path)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def update_rows(
    rows: list[dict[str, str]],
    author_email: str,
    status: str,
    evidence_path: str,
    notes: str,
    confirmed_at: str,
) -> tuple[list[dict[str, str]], dict[str, str]]:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    if status in EVIDENCE_REQUIRED and not evidence_path:
        raise ValueError(f"--evidence-path is required when status={status}")

    updated = False
    updated_row: dict[str, str] = {}
    for row in rows:
        if row.get("email", "").lower() != author_email.lower():
            continue
        row["status"] = status
        row["evidence_path"] = evidence_path
        row["notes"] = notes
        row["confirmed_at"] = confirmed_at if status == "confirmed" else ""
        updated = True
        updated_row = dict(row)
        break
    if not updated:
        raise ValueError(f"Author email not found in tracker: {author_email}")
    return rows, updated_row


def _run_refresh_commands() -> None:
    commands = [
        [sys.executable, "scripts/build_corresponding_author_email_packet.py"],
        [sys.executable, "scripts/build_nature_methods_go_no_go_final.py"],
        [sys.executable, "scripts/export_shared_project_info.py"],
    ]
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record a corresponding-author Figure 4 sign-off reply."
    )
    parser.add_argument("--author-email", required=True)
    parser.add_argument("--status", required=True, choices=sorted(VALID_STATUSES))
    parser.add_argument(
        "--evidence-path",
        default="",
        help="Path to the author reply, signed document, or saved email evidence.",
    )
    parser.add_argument("--notes", default="")
    parser.add_argument(
        "--confirmed-at",
        default="",
        help="ISO timestamp. Defaults to now for confirmed status.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the update without writing files.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    evidence_path = _resolve_evidence(args.evidence_path)
    confirmed_at = args.confirmed_at
    if args.status == "confirmed" and not confirmed_at:
        confirmed_at = _now()
    rows = _read_tsv(TRACKER)
    fieldnames = list(rows[0].keys()) if rows else []
    rows, updated_row = update_rows(
        rows,
        args.author_email,
        args.status,
        evidence_path,
        args.notes,
        confirmed_at,
    )
    if args.dry_run:
        print("dry_run\ttrue")
        for key in fieldnames:
            print(f"{key}\t{updated_row.get(key, '')}")
        return 0

    _write_tsv(TRACKER, rows, fieldnames)
    _run_refresh_commands()
    print(f"updated\t{args.author_email}\t{args.status}")
    print(f"tracker\t{_rel(TRACKER)}")
    print("refreshed\tdocs/corresponding_author_signoff_tracker.md")
    print("refreshed\tdocs/nature_methods_go_no_go_final.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
