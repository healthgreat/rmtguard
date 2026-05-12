"""Build a triage report for author replies.

Author: RMTGuard contributors
Date: 2026-05-12
Purpose: Convert saved author/mentor replies into a conservative gate triage so
the project does not overinterpret brief approvals such as "可以" as full
journal-facing author confirmation.
Data source: metadata/author_reply_evidence/author_reply_log.tsv,
metadata/author_metadata.tsv, metadata/corresponding_author_signoff_tracker.tsv,
and results/submission/author_declaration_confirmation_checklist.tsv.
Method notes: This script never marks a gate as passed. It reports whether the
available reply evidence is sufficient for author declarations, Figure 4
acknowledgement, reporting summary, and v0.1.1 release preflight.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPLY_LOG = ROOT / "metadata" / "author_reply_evidence" / "author_reply_log.tsv"
AUTHOR_META = ROOT / "metadata" / "author_metadata.tsv"
SIGNOFF = ROOT / "metadata" / "corresponding_author_signoff_tracker.tsv"
CHECKLIST = ROOT / "results" / "submission" / "author_declaration_confirmation_checklist.tsv"
PREFLIGHT = ROOT / "results" / "submission" / "v0_1_1_release_preflight.tsv"

OUT_TSV = ROOT / "results" / "submission" / "author_reply_triage.tsv"
OUT_MD = ROOT / "docs" / "author_reply_triage.md"


@dataclass(frozen=True)
class TriageRow:
    triage_id: str
    status: str
    evidence: str
    interpretation: str
    gate_effect: str
    required_next_text: str


FIELDNAMES = [
    "triage_id",
    "status",
    "evidence",
    "interpretation",
    "gate_effect",
    "required_next_text",
]


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: list[TriageRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)
    tmp.replace(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def pending_author_fields() -> list[str]:
    rows = read_tsv(AUTHOR_META)
    watched = {
        "postal_code_author_provided",
        "postal_code_public_source_candidate",
        "credit_roles_draft",
        "funding_statement",
        "competing_interests_statement",
    }
    allowed = {
        "author_confirmed",
        "author_confirmed_removed",
        "author_confirmed_from_logged_in_orcid_screenshot",
        "published_release_doi",
        "author_created_public_repo",
        "drafted_from_project_scope",
    }
    return [
        f"{row.get('field')}:{row.get('status')}"
        for row in rows
        if row.get("field") in watched and row.get("status") not in allowed
    ]


def signoff_status() -> str:
    rows = read_tsv(SIGNOFF)
    if not rows:
        return "missing_tracker"
    confirmed = sum(1 for row in rows if row.get("status") == "confirmed")
    return f"{confirmed}/{len(rows)} confirmed"


def preflight_blockers() -> str:
    rows = read_tsv(PREFLIGHT)
    if not rows:
        return "missing_preflight"
    return rows[0].get("blocking_or_holding_gates", "")


def build_rows() -> list[TriageRow]:
    replies = read_tsv(REPLY_LOG)
    latest = replies[-1] if replies else {}
    raw_reply = latest.get("raw_reply", "")
    gate_use = latest.get("gate_use", "missing")
    checklist_count = len(read_tsv(CHECKLIST))
    pending_fields = pending_author_fields()
    signoff = signoff_status()
    blockers = preflight_blockers()

    return [
        TriageRow(
            "latest_reply_received",
            "received" if latest else "missing",
            _rel(REPLY_LOG),
            f"latest_raw_reply={raw_reply}; gate_use={gate_use}",
            "records_preliminary_progress_only",
            "Save any direct email, WeChat screenshot, or signed document if available.",
        ),
        TriageRow(
            "author_declarations",
            "still_blocked" if pending_fields else "ready_for_metadata_update",
            f"{_rel(AUTHOR_META)};{_rel(CHECKLIST)}",
            f"pending_fields={';'.join(pending_fields) if pending_fields else 'none'}; checklist_items={checklist_count}",
            "does_not_unlock_v0.1.1_release",
            "Need explicit final wording for postal code, funding/no funding, competing interests, CRediT roles, ethics/public-data statement, reporting summary, and title-page metadata.",
        ),
        TriageRow(
            "figure4_corresponding_author_ack",
            "still_blocked" if signoff != "2/2 confirmed" else "ready",
            _rel(SIGNOFF),
            f"corresponding_author_signoff={signoff}",
            "does_not_unlock_presubmission",
            "Need named approval from Yi Miao and Han Yan, or a saved message that clearly authorizes both corresponding authors.",
        ),
        TriageRow(
            "v0_1_1_preflight",
            "still_do_not_release" if blockers and blockers != "none" else "ready_to_recheck",
            _rel(PREFLIGHT),
            f"blocking_or_holding_gates={blockers}",
            "release_remains_blocked",
            "After exact author confirmations are recorded, rerun author packet, preflight, dashboard, evidence freeze, and shared export.",
        ),
    ]


def build_markdown(rows: list[TriageRow]) -> str:
    lines = [
        "# RMTGuard author reply triage",
        "",
        f"Generated: {date.today().isoformat()}",
        "Generated by `python scripts/build_author_reply_triage.py`.",
        "",
        "## Decision",
        "",
        "- Latest reply recorded: `导师：可以`.",
        "- Conservative status: `preliminary_mentor_ok_only`.",
        "- Current release/submission effect: `do_not_release`; `do_not_submit`.",
        "",
        "## Why This Is Not Yet Enough",
        "",
        "A brief approval is useful, but high-impact journal metadata still needs explicit author-controlled statements. In particular, funding, competing interests, postal code, CRediT roles, reporting-summary verification, and both corresponding-author Figure 4 acknowledgements should not be inferred silently.",
        "",
        "## Triage Table",
        "",
        "| Triage item | Status | Interpretation | Gate effect | Required next text |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row.triage_id} | `{row.status}` | {row.interpretation.replace('|', '/')} | {row.gate_effect} | {row.required_next_text.replace('|', '/')} |"
        )
    lines.extend(
        [
            "",
            "## Minimal Follow-up Text To Ask The Mentor",
            "",
            "```text",
            "老师您好，为了投稿和 Zenodo v0.1.1 归档留证据，请您帮我把“可以”再明确成下面一句：",
            "",
            "确认 RMTGuard 当前作者信息、CRediT roles、伦理/公共数据说明、Figure 4 bounded wording、reporting summary 按当前版本使用；邮编使用 [350000 或 210019]；funding statement 使用 [具体基金/无专项资助]；competing interests 使用 [The authors declare no competing interests 或具体披露]。",
            "",
            "如果 Han Yan 老师也同意 Figure 4 bounded wording，也请一并写明：Yi Miao 和 Han Yan 均确认 Figure 4 仅作为公共数据 PDAC/TME use case，不作为机制、临床验证、预后、治疗反应或患者层面结论。",
            "```",
            "",
            "## Source Evidence",
            "",
            f"- Reply log: `{_rel(REPLY_LOG)}`",
            "- Evidence note: `metadata/author_reply_evidence/2026-05-12_mentor_preliminary_ok_user_relay.txt`",
            f"- Preflight: `{_rel(PREFLIGHT)}`",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    rows = build_rows()
    write_tsv(OUT_TSV, rows)
    write_text(OUT_MD, build_markdown(rows))
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print("preliminary_mentor_ok_only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
