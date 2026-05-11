from __future__ import annotations

"""Build a gated Nature Methods presubmission send packet.

Author: RMTGuard development team
Date: 2026-05-10
Purpose: Create a local presubmission send checklist, HOLD email draft, and
machine-readable status table for the Nature Methods presubmission gate.
Data source: Corresponding-author sign-off tracker, Nature Methods go/no-go
packet, and the controlled presubmission inquiry draft.
Method notes: This script does not send email and does not verify current
journal submission portal instructions. The route must be checked manually
immediately before sending.
"""

import csv
from datetime import date
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

AUTHOR_TRACKER = ROOT / "metadata" / "corresponding_author_signoff_tracker.tsv"
GO_NO_GO_TSV = ROOT / "results" / "submission" / "nature_methods_go_no_go_final.tsv"
GO_NO_GO_MD = ROOT / "docs" / "nature_methods_go_no_go_final.md"
PRESUBMISSION_MD = ROOT / "manuscript" / "nature_methods_presubmission_inquiry.md"

OUT_TSV = ROOT / "results" / "submission" / "nature_methods_presubmission_send_packet.tsv"
OUT_MD = ROOT / "manuscript" / "nature_methods_presubmission_send_packet.md"
OUT_RUNBOOK = ROOT / "docs" / "nature_methods_presubmission_send_runbook.md"
OUT_EMAIL_DIR = ROOT / "output" / "email"
OUT_EML = OUT_EMAIL_DIR / "RMTGuard_nature_methods_presubmission_inquiry_HOLD.eml"
OUT_EMAIL_README = OUT_EMAIL_DIR / "README.md"

STOP_RULE = (
    "Do not send if corresponding-author Figure 4 acknowledgement is incomplete, "
    "if Figure 4 is rewritten as a PDAC mechanism or clinical-validation claim, "
    "or if the final presubmission route has not been manually verified."
)


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
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


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _author_status() -> tuple[str, int, int, int]:
    rows = _read_tsv(AUTHOR_TRACKER)
    if not rows:
        return "missing_tracker", 0, 0, 0
    confirmed = sum(1 for row in rows if row.get("status") == "confirmed")
    proxy = sum(
        1
        for row in rows
        if row.get("status") == "proxy_authorized_working_assumption"
    )
    required = len(rows)
    if confirmed == required and required > 0:
        return "all_confirmed", confirmed, required, proxy
    return "pending_author_reply", confirmed, required, proxy


def _go_no_go_row() -> dict[str, str]:
    for row in _read_tsv(GO_NO_GO_TSV):
        if row.get("decision_id") == "nature_methods_presubmission_inquiry":
            return row
    return {}


def _send_status() -> tuple[str, str, str]:
    author_status, confirmed, required, proxy = _author_status()
    row = _go_no_go_row()
    decision = row.get("decision", "missing_go_no_go")
    if author_status != "all_confirmed":
        proxy_note = (
            f"; proxy working assumption is recorded ({proxy}/{required})"
            if proxy
            else ""
        )
        return (
            "hold_author_acknowledgement",
            f"Corresponding-author acknowledgement is incomplete ({confirmed}/{required}{proxy_note}).",
            "Send the sign-off email first and record both confirmations.",
        )
    if decision != "go_after_final_wording_review":
        return (
            "hold_final_go_no_go_refresh",
            f"Author acknowledgement is complete, but go/no-go decision is `{decision}`.",
            "Rerun the go/no-go packet and perform final wording review.",
        )
    return (
        "ready_for_final_human_review",
        "All author acknowledgements are complete and go/no-go allows final wording review.",
        "Manually verify the Nature Methods presubmission route, then send only after final human review.",
    )


def build_rows() -> list[dict[str, str]]:
    author_status, confirmed, required, proxy = _author_status()
    go_no_go = _go_no_go_row()
    send_status, reason, next_action = _send_status()
    today = date.today().isoformat()
    return [
        {
            "item_id": "send_status",
            "status": send_status,
            "evidence_path": _rel(AUTHOR_TRACKER),
            "reason": reason,
            "required_next_action": next_action,
            "stop_rule": STOP_RULE,
            "date_checked": today,
        },
        {
            "item_id": "corresponding_author_acknowledgement",
            "status": author_status,
            "evidence_path": _rel(AUTHOR_TRACKER),
            "reason": (
                f"{confirmed}/{required} required corresponding-author confirmations "
                f"are recorded; proxy working assumption={proxy}/{required}."
            ),
            "required_next_action": (
                "Keep the packet locked until both Yi Miao and Han Yan are confirmed."
                if author_status != "all_confirmed"
                else "Proceed to final wording review."
            ),
            "stop_rule": "Do not infer confirmation from silence or informal discussion.",
            "date_checked": today,
        },
        {
            "item_id": "nature_methods_go_no_go",
            "status": go_no_go.get("decision", "missing_go_no_go"),
            "evidence_path": _rel(GO_NO_GO_TSV),
            "reason": go_no_go.get("reason", "No Nature Methods go/no-go row found."),
            "required_next_action": go_no_go.get(
                "required_next_action",
                "Regenerate the Nature Methods go/no-go control packet.",
            ),
            "stop_rule": go_no_go.get("stop_rule", STOP_RULE),
            "date_checked": today,
        },
        {
            "item_id": "manual_route_verification",
            "status": "required_before_send",
            "evidence_path": "external_manual_check",
            "reason": "Current Nature Methods presubmission route and recipient details may change.",
            "required_next_action": "Verify the official Nature Methods submission/presubmission instructions immediately before sending.",
            "stop_rule": "Do not rely on an old local draft for recipient, portal, or attachment rules.",
            "date_checked": today,
        },
        {
            "item_id": "acceptance_guarantee",
            "status": "impossible",
            "evidence_path": _rel(GO_NO_GO_MD),
            "reason": "A local send packet cannot guarantee editorial interest, peer review, or acceptance.",
            "required_next_action": "Use the packet only to reduce avoidable desk-reject risk.",
            "stop_rule": "Do not state or imply guaranteed acceptance in any author-facing or editor-facing text.",
            "date_checked": today,
        },
    ]


def _inquiry_text() -> str:
    if not PRESUBMISSION_MD.exists():
        return "[Missing presubmission inquiry draft]"
    return PRESUBMISSION_MD.read_text(encoding="utf-8", errors="replace").rstrip()


def build_markdown(rows: list[dict[str, str]]) -> str:
    send_status = rows[0]["status"]
    hold = send_status.startswith("hold_")
    lines = [
        "# Nature Methods Presubmission Send Packet",
        "",
        "Generated by `python scripts/build_nature_methods_presubmission_send_packet.py`.",
        "",
        "## Bottom Line",
        "",
        f"- Send status: `{send_status}`.",
        f"- Current action: `{'DO NOT SEND' if hold else 'final human review required before send'}`.",
        "- Full Nature Methods submission remains `NO-GO`.",
        "- Acceptance guarantee: `impossible`.",
        "- Manual route verification: required immediately before any send.",
        "",
        "## Gate Table",
        "",
        "| Item | Status | Evidence | Reason | Required next action |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['item_id']} | `{row['status']}` | `{row['evidence_path']}` | "
            f"{row['reason']} | {row['required_next_action']} |"
        )
    lines.extend(
        [
            "",
            "## Stop Rule",
            "",
            STOP_RULE,
            "",
            "## Editor-Facing Draft",
            "",
            "The inquiry text below is preserved as a controlled draft and must be reviewed before use.",
            "",
            "```text",
            _inquiry_text(),
            "```",
            "",
            "## Source Files",
            "",
            f"- Author tracker: `{_rel(AUTHOR_TRACKER)}`",
            f"- Nature Methods go/no-go: `{_rel(GO_NO_GO_MD)}`",
            f"- Presubmission inquiry draft: `{_rel(PRESUBMISSION_MD)}`",
            f"- HOLD email draft: `{_rel(OUT_EML)}`",
        ]
    )
    return "\n".join(lines)


def build_runbook(rows: list[dict[str, str]]) -> str:
    send_status = rows[0]["status"]
    return f"""# Nature Methods Presubmission Send Runbook

Generated by `python scripts/build_nature_methods_presubmission_send_packet.py`.

## Current Status

- Send status: `{send_status}`.
- Full Nature Methods submission: `NO-GO`.
- Presubmission inquiry: locked until the send packet is not in a `hold_*` state.
- Acceptance guarantee: `impossible`.

## Safe Sequence

1. Send the corresponding-author Figure 4 sign-off email draft, not the Nature
   Methods inquiry.
2. Save each author reply as evidence.
3. Record each confirmation with
   `python scripts/record_corresponding_author_signoff.py`.
4. Rerun:

```bash
python scripts/build_nature_methods_go_no_go_final.py
python scripts/build_nature_methods_presubmission_send_packet.py
python scripts/export_shared_project_info.py
python scripts/lint_claim_boundaries.py
python scripts/validate_claim_traceability.py
```

5. Verify the official Nature Methods presubmission/submission route manually
   immediately before sending.
6. Only after final human review, copy the editor-facing text into the verified
   route.

## Stop Rules

- {STOP_RULE}
- Do not send the HOLD `.eml` file.
- Do not add stronger PDAC/TME, clinical, prognosis, therapy-response, or
  patient-level claims.
- Do not describe acceptance as guaranteed.

## Files

- Send packet: `{_rel(OUT_MD)}`
- Send status table: `{_rel(OUT_TSV)}`
- HOLD email draft: `{_rel(OUT_EML)}`
"""


def build_eml(rows: list[dict[str, str]]) -> None:
    send_status = rows[0]["status"]
    hold = send_status.startswith("hold_")
    subject_prefix = "HOLD - DO NOT SEND - " if hold else "FINAL REVIEW REQUIRED - "
    body = f"""Nature Methods presubmission inquiry draft for RMTGuard

Current send status: {send_status}
Current action: {'DO NOT SEND' if hold else 'final human review required before send'}

This local draft deliberately has no recipient. Verify the official Nature
Methods presubmission/submission route immediately before use.

Stop rule:
{STOP_RULE}

Editor-facing draft follows.

---

{_inquiry_text()}
"""

    OUT_EMAIL_DIR.mkdir(parents=True, exist_ok=True)
    message = EmailMessage()
    message["Subject"] = subject_prefix + "RMTGuard Nature Methods presubmission inquiry"
    message["Date"] = formatdate(localtime=True)
    message["X-RMTGuard-Send-Status"] = send_status
    message.set_content(body)
    tmp = OUT_EML.with_suffix(".eml.tmp")
    tmp.write_bytes(bytes(message))
    tmp.replace(OUT_EML)


def build_email_readme() -> str:
    return """# RMTGuard Email Draft Outputs

This folder contains local `.eml` drafts. These files are not sent by scripts.

## Files

- `RMTGuard_corresponding_author_signoff_email.eml`: send this first to request
  Figure 4 bounded-wording acknowledgement from Yi Miao and Han Yan.
- `RMTGuard_nature_methods_presubmission_inquiry_HOLD.eml`: locked Nature
  Methods presubmission draft. Do not send while the send packet reports a
  `hold_*` status.

## Boundary

The corresponding-author sign-off email can be used only to request author
acknowledgement. The Nature Methods HOLD draft intentionally has no recipient
because the official submission/presubmission route must be verified manually
immediately before sending.

## Regenerate

```bash
python scripts/build_corresponding_author_email_packet.py
python scripts/build_nature_methods_presubmission_send_packet.py
```
"""


def main() -> int:
    rows = build_rows()
    _write_tsv(
        OUT_TSV,
        rows,
        [
            "item_id",
            "status",
            "evidence_path",
            "reason",
            "required_next_action",
            "stop_rule",
            "date_checked",
        ],
    )
    _write_text(OUT_MD, build_markdown(rows))
    _write_text(OUT_RUNBOOK, build_runbook(rows))
    build_eml(rows)
    _write_text(OUT_EMAIL_README, build_email_readme())
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print(_rel(OUT_RUNBOOK))
    print(_rel(OUT_EML))
    print(_rel(OUT_EMAIL_README))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
