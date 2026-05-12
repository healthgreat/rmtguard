"""Build the author-confirmation delivery bundle for RMTGuard.

Author: RMTGuard contributors
Date: 2026-05-12
Purpose: Package only the files that should be sent to authors for manual
confirmation of title-page metadata, CRediT roles, funding, competing
interests, public-data ethics, Figure 4 bounded wording, and reporting-summary
items.
Data source: Generated author-confirmation packets, email/chat drafts, and
high-impact dashboard.
Method notes: This script creates a local ZIP and manifest only. It does not
send email, record replies, change metadata, or certify author approval.
"""

from __future__ import annotations

import csv
import hashlib
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output" / "delivery"
OUT_ZIP = OUT_DIR / "RMTGuard_author_confirmation_delivery_2026-05-12.zip"
OUT_MD = ROOT / "docs" / "author_confirmation_delivery_bundle.md"
OUT_TSV = ROOT / "results" / "submission" / "author_confirmation_delivery_manifest.tsv"


@dataclass(frozen=True)
class BundleItem:
    source: Path
    archive_name: str
    role: str
    send_to_author: str


ITEMS = [
    BundleItem(
        ROOT / "output" / "doc" / "RMTGuard_author_declaration_confirmation_packet.docx",
        "01_author_declaration_confirmation_packet.docx",
        "Main Word packet for author confirmation",
        "yes",
    ),
    BundleItem(
        ROOT / "manuscript" / "author_declaration_confirmation_wechat_draft.md",
        "02_wechat_copy_paste_draft.md",
        "Short WeChat message to send with the Word packet",
        "yes",
    ),
    BundleItem(
        ROOT / "manuscript" / "author_declaration_confirmation_email_draft.md",
        "03_email_draft.md",
        "Email text if confirmation is requested by email",
        "yes",
    ),
    BundleItem(
        ROOT / "output" / "email" / "RMTGuard_author_declaration_confirmation_email.eml",
        "04_email_draft.eml",
        "Local email draft with the Word packet attached",
        "optional",
    ),
    BundleItem(
        ROOT / "docs" / "author_declaration_reply_intake_runbook.md",
        "05_reply_intake_runbook.md",
        "Instructions for saving and recording author replies",
        "no_author_send_required",
    ),
    BundleItem(
        ROOT / "docs" / "high_impact_submission_dashboard.md",
        "06_current_high_impact_dashboard.md",
        "Current project status and submission boundary",
        "optional",
    ),
    BundleItem(
        ROOT / "output" / "doc" / "RMTGuard_corresponding_author_signoff_packet.docx",
        "07_figure4_signoff_packet.docx",
        "Narrow Figure 4 bounded-wording sign-off packet",
        "optional",
    ),
    BundleItem(
        ROOT / "manuscript" / "corresponding_author_figure4_acknowledgement_template.md",
        "08_figure4_acknowledgement_template.md",
        "Exact Figure 4 acknowledgement wording",
        "optional",
    ),
    BundleItem(
        ROOT / "docs" / "figure4_pdac_tme_wording_freeze.md",
        "09_figure4_wording_freeze.md",
        "Frozen bounded Figure 4 wording and stop rules",
        "optional",
    ),
]


README_TEXT = """# RMTGuard Author Confirmation Delivery Bundle

Generated: {today}

## Purpose

This ZIP contains only the files needed to ask the corresponding authors to
confirm author-controlled manuscript items before any v0.1.1 release, Zenodo
archive refresh, or editor-facing presubmission inquiry.

## What To Send First

1. Send `01_author_declaration_confirmation_packet.docx`.
2. Copy the text from `02_wechat_copy_paste_draft.md` into WeChat, or use
   `03_email_draft.md` / `04_email_draft.eml` if email is preferred.
3. Ask authors to reply in writing. A verbal approval is not enough for the
   local release gate.

## Items Needing Confirmation

- Postal code: author-provided 350000 versus public-source candidate 210019.
- CRediT author roles.
- Funding statement.
- Competing interests statement.
- Ethics / public-data-use statement.
- Figure 4 bounded wording.
- Nature reporting-summary items.
- Title-page author order, affiliation, emails, and ORCID records.

## Stop Rules

- Do not submit to a journal yet.
- Do not create a v0.1.1 GitHub Release or Zenodo archive yet.
- Do not send the Nature Methods presubmission inquiry yet.
- Stop and update the manuscript package if any author changes funding,
  competing interests, authorship, affiliation, ORCID, or Figure 4 wording.

## After Replies Arrive

1. Save replies under `metadata/author_reply_evidence/`.
2. Follow `05_reply_intake_runbook.md`.
3. Re-run the author declaration packet, v0.1.1 preflight, dashboard, evidence
   freeze, Gantt, and shared export.
"""


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _write_manifest(rows: list[dict[str, str]]) -> None:
    OUT_TSV.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_TSV.with_suffix(OUT_TSV.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "archive_name",
                "role",
                "send_to_author",
                "source_path",
                "status",
                "size_bytes",
                "sha256",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(OUT_TSV)


def build_zip() -> list[dict[str, str]]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for loose_name in ["README_TO_AUTHORS.md", *(item.archive_name for item in ITEMS)]:
        loose_path = OUT_DIR / loose_name
        if loose_path.exists() and loose_path.is_file():
            loose_path.unlink()
    rows: list[dict[str, str]] = []
    tmp_zip = OUT_ZIP.with_suffix(OUT_ZIP.suffix + ".tmp")
    if tmp_zip.exists():
        tmp_zip.unlink()
    with zipfile.ZipFile(tmp_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        readme_bytes = README_TEXT.format(today=date.today().isoformat()).encode("utf-8")
        archive.writestr("README_TO_AUTHORS.md", readme_bytes)
        rows.append(
            {
                "archive_name": "README_TO_AUTHORS.md",
                "role": "Bundle instructions",
                "send_to_author": "yes",
                "source_path": "generated",
                "status": "written",
                "size_bytes": str(len(readme_bytes)),
                "sha256": hashlib.sha256(readme_bytes).hexdigest(),
            }
        )
        for item in ITEMS:
            if item.source.exists():
                archive.write(item.source, arcname=item.archive_name)
                rows.append(
                    {
                        "archive_name": item.archive_name,
                        "role": item.role,
                        "send_to_author": item.send_to_author,
                        "source_path": _rel(item.source),
                        "status": "included",
                        "size_bytes": str(item.source.stat().st_size),
                        "sha256": _sha256(item.source),
                    }
                )
            else:
                rows.append(
                    {
                        "archive_name": item.archive_name,
                        "role": item.role,
                        "send_to_author": item.send_to_author,
                        "source_path": _rel(item.source),
                        "status": "missing",
                        "size_bytes": "",
                        "sha256": "",
                    }
                )
    tmp_zip.replace(OUT_ZIP)
    return rows


def build_markdown(rows: list[dict[str, str]]) -> str:
    missing = [row for row in rows if row["status"] == "missing"]
    included = [row for row in rows if row["status"] in {"included", "written"}]
    lines = [
        "# RMTGuard author confirmation delivery bundle",
        "",
        f"Generated: {date.today().isoformat()}",
        "Generated by `python scripts/build_author_confirmation_delivery_bundle.py`.",
        "",
        "## Decision",
        "",
        "- Bundle status: `" + ("blocked_missing_files" if missing else "ready_for_manual_send") + "`.",
        "- This bundle does not send email and does not certify author approval.",
        f"- ZIP: `{_rel(OUT_ZIP)}`",
        f"- Manifest: `{_rel(OUT_TSV)}`",
        "",
        "## Files In Bundle",
        "",
        "| Archive file | Status | Send to author | Role | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['archive_name']} | `{row['status']}` | {row['send_to_author']} | {row['role']} | `{row['source_path']}` |"
        )
    lines.extend(
        [
            "",
            "## Send Order",
            "",
            "1. Send `01_author_declaration_confirmation_packet.docx`.",
            "2. Use `02_wechat_copy_paste_draft.md` or `03_email_draft.md` as the message body.",
            "3. Save all written replies under `metadata/author_reply_evidence/`.",
            "4. Follow `05_reply_intake_runbook.md` before changing metadata.",
            "",
            "## Current Boundary",
            "",
            "- Full Nature Methods submission remains no-go.",
            "- Presubmission remains conditional on author acknowledgement.",
            "- v0.1.1 release remains blocked until author declarations and final figure/source freeze are complete.",
            "",
            f"Included/written files: `{len(included)}`",
            f"Missing files: `{len(missing)}`",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    rows = build_zip()
    _write_manifest(rows)
    _write_text_atomic(OUT_MD, build_markdown(rows))
    print(_rel(OUT_ZIP))
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print("ready_for_manual_send" if all(row["status"] != "missing" for row in rows) else "blocked_missing_files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
