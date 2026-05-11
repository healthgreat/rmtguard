from __future__ import annotations

"""Build the current Nature Methods go/no-go decision packet.

Author: RMTGuard development team
Date: 2026-05-10
Purpose: Convert the current release, evidence, claim-boundary, and Figure 4
state into a reviewer-safe submission-route decision.
Data source: Generated RMTGuard submission-control reports under docs/,
results/, and manuscript/.
Method notes: This is a decision-control artifact. It does not guarantee
acceptance and does not replace current journal guideline checks.
"""

import csv
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GAP_TSV = ROOT / "results" / "submission" / "jif20_50_gap_assessment.tsv"
EDITORIAL_TSV = ROOT / "results" / "submission" / "editorial_presubmission_packet.tsv"
FIGURE4_TSV = ROOT / "results" / "submission" / "figure4_pdac_tme_wording_freeze.tsv"
AUTHOR_SIGNOFF_TRACKER = ROOT / "metadata" / "corresponding_author_signoff_tracker.tsv"
CLAIM_LINT_MD = ROOT / "docs" / "claim_boundary_lint.md"
TRACEABILITY_MD = ROOT / "docs" / "claim_traceability.md"
PRESUBMISSION_MD = ROOT / "manuscript" / "nature_methods_presubmission_inquiry.md"

OUT_TSV = ROOT / "results" / "submission" / "nature_methods_go_no_go_final.tsv"
OUT_MD = ROOT / "docs" / "nature_methods_go_no_go_final.md"
ACK_MD = (
    ROOT
    / "manuscript"
    / "corresponding_author_figure4_acknowledgement_template.md"
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


def _doc_violation_count(path: Path) -> int | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"Violations:\s*`?(\d+)`?", text)
    if not match:
        return None
    return int(match.group(1))


def _gap_rows() -> list[dict[str, str]]:
    return _read_tsv(GAP_TSV)


def _score(gap_rows: list[dict[str, str]]) -> tuple[int, int]:
    score = sum(int(row.get("current_score", "0") or "0") for row in gap_rows)
    weight = sum(int(row.get("weight", "0") or "0") for row in gap_rows)
    return score, weight


def _blocking_items(gap_rows: list[dict[str, str]]) -> list[str]:
    blockers: list[str] = []
    for row in gap_rows:
        value = row.get("blocking_items", "")
        if value and value != "none":
            blockers.extend(item for item in value.split(";") if item)
    return blockers


def _editorial_status(item_id: str) -> str:
    for row in _read_tsv(EDITORIAL_TSV):
        if row.get("item_id") == item_id:
            return row.get("status", "missing")
    return "missing"


def _author_acknowledgement_status() -> tuple[str, int, int]:
    rows = _read_tsv(AUTHOR_SIGNOFF_TRACKER)
    if not rows:
        return "missing_tracker", 0, 0
    confirmed = sum(1 for row in rows if row.get("status") == "confirmed")
    required = len(rows)
    if required and confirmed == required:
        return "all_confirmed", confirmed, required
    return "pending_author_reply", confirmed, required


def _author_proxy_assumption_count() -> int:
    return sum(
        1
        for row in _read_tsv(AUTHOR_SIGNOFF_TRACKER)
        if row.get("status") == "proxy_authorized_working_assumption"
    )


def build_rows() -> list[dict[str, str]]:
    gap_rows = _gap_rows()
    score, weight = _score(gap_rows)
    blockers = _blocking_items(gap_rows)
    release_status = next(
        (
            row.get("status", "")
            for row in gap_rows
            if row.get("domain") == "release_reproducibility"
        ),
        "missing",
    )
    figure4_rows = _read_tsv(FIGURE4_TSV)
    figure4_freeze_present = any(
        row.get("element_id") == "figure4_decision" for row in figure4_rows
    )
    claim_lint_violations = _doc_violation_count(CLAIM_LINT_MD)
    trace_violations = _doc_violation_count(TRACEABILITY_MD)
    send_status = _editorial_status("send_status")
    software_status = _editorial_status("software_release_disclosure")
    presubmission_exists = PRESUBMISSION_MD.exists()
    author_ack_status, author_confirmed, author_required = (
        _author_acknowledgement_status()
    )
    proxy_assumption = _author_proxy_assumption_count()

    presubmission_condition = (
        score >= 90
        and release_status == "pass"
        and software_status == "pass"
        and figure4_freeze_present
        and claim_lint_violations == 0
        and trace_violations == 0
        and presubmission_exists
    )
    presubmission_unlocked = (
        presubmission_condition and author_ack_status == "all_confirmed"
    )

    return [
        {
            "decision_id": "nature_methods_full_submission",
            "decision": "no_go",
            "status": "not_submission_ready",
            "evidence": _rel(GAP_TSV),
            "reason": (
                "Full submission remains blocked because active blockers include "
                + ";".join(blockers)
                + "."
            ),
            "required_next_action": (
                "Do not submit a full manuscript until stability-superiority "
                "claims are removed or new evidence supports them, and final "
                "source-data/reporting-summary checks are frozen."
            ),
            "stop_rule": "Stop if any draft claims broad stability superiority.",
        },
        {
            "decision_id": "nature_methods_presubmission_inquiry",
            "decision": (
                "go_after_final_wording_review"
                if presubmission_unlocked
                else "conditional_go_after_author_ack"
                if presubmission_condition
                else "hold"
            ),
            "status": (
                "author_acknowledgement_complete"
                if presubmission_unlocked
                else "author_acknowledgement_needed"
                if presubmission_condition
                else "gate_incomplete"
            ),
            "evidence": _rel(PRESUBMISSION_MD),
            "reason": (
                f"Readiness score is {score}/{weight}; release status is "
                f"{release_status}; claim lint violations={claim_lint_violations}; "
                f"traceability violations={trace_violations}; Figure 4 wording "
                f"freeze present={figure4_freeze_present}; send_status={send_status}; "
                f"author_acknowledgement={author_ack_status} "
                f"({author_confirmed}/{author_required}); "
                f"proxy_working_assumption={proxy_assumption}/{author_required}."
            ),
            "required_next_action": (
                "Run one final wording review, then the presubmission inquiry can be sent."
                if presubmission_unlocked
                else
                "Corresponding authors must acknowledge the bounded Figure 4 "
                "route, then the presubmission inquiry can be reviewed one final "
                "time before sending."
            ),
            "stop_rule": (
                "Do not send if Figure 4 is rewritten as a PDAC mechanism or "
                "clinical-validation claim."
            ),
        },
        {
            "decision_id": "genome_biology_fallback",
            "decision": "ready_if_nature_methods_not_encouraging",
            "status": "fallback_controlled",
            "evidence": _rel(EDITORIAL_TSV),
            "reason": (
                "Genome Biology remains the realistic high-quality fallback if "
                "Nature Methods editors view the contribution as an incremental "
                "methods/software workflow."
            ),
            "required_next_action": (
                "Reframe as an open genomics workflow for callability-aware "
                "scRNA-seq noise control; do not present it as a strict 20-50 "
                "JIF route."
            ),
            "stop_rule": "Do not oversell Genome Biology as satisfying strict 20-50 JIF.",
        },
        {
            "decision_id": "nature_biotechnology",
            "decision": "no_go_current_scope",
            "status": "scope_mismatch",
            "evidence": _rel(GAP_TSV),
            "reason": (
                "Current RMTGuard is a statistical genomics workflow, not a "
                "biotechnology platform or adoption-level engineering advance."
            ),
            "required_next_action": "Do not target Nature Biotechnology in this round.",
            "stop_rule": "Reconsider only if a platform/adoption story emerges.",
        },
        {
            "decision_id": "acceptance_guarantee",
            "decision": "impossible",
            "status": "controlled_boundary",
            "evidence": _rel(CLAIM_LINT_MD),
            "reason": "No journal acceptance can be guaranteed by local evidence.",
            "required_next_action": (
                "Maximize probability through gate discipline, claim boundaries, "
                "and appropriate fallback routing."
            ),
            "stop_rule": "Do not state or imply guaranteed acceptance.",
        },
    ]


def build_markdown(rows: list[dict[str, str]]) -> str:
    gap_rows = _gap_rows()
    score, weight = _score(gap_rows)
    blockers = _blocking_items(gap_rows)
    author_ack_status, author_confirmed, author_required = (
        _author_acknowledgement_status()
    )
    proxy_assumption = _author_proxy_assumption_count()
    presubmission_line = (
        "go after final wording review"
        if author_ack_status == "all_confirmed"
        else "conditional go after corresponding-author Figure 4 acknowledgement"
    )
    lines = [
        "# Nature Methods Final Go/No-Go Control Packet",
        "",
        "Generated by `python scripts/build_nature_methods_go_no_go_final.py`.",
        "",
        "## Bottom Line",
        "",
        "- Full Nature Methods submission: `NO-GO`.",
        f"- Nature Methods presubmission inquiry: `{presubmission_line}`.",
        "- Genome Biology fallback: `ready if Nature Methods presubmission is not encouraging`.",
        "- Acceptance guarantee: `impossible`.",
        f"- Current readiness score: `{score}/{weight}`.",
        f"- Corresponding-author acknowledgement: `{author_ack_status}` ({author_confirmed}/{author_required}).",
        f"- Internal proxy working assumption: `{proxy_assumption}/{author_required}`; this does not unlock editor-facing submission.",
        "- Active blockers: `" + (";".join(blockers) if blockers else "none") + "`.",
        "",
        "## Decision Table",
        "",
        "| Decision | Status | Reason | Required next action | Stop rule |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            + row["decision_id"]
            + " | `"
            + row["decision"]
            + "` / `"
            + row["status"]
            + "` | "
            + row["reason"]
            + " | "
            + row["required_next_action"]
            + " | "
            + row["stop_rule"]
            + " |"
        )
    lines.extend(
        [
            "",
            "## Mentor Decision",
            "",
            (
                "Send only a presubmission inquiry after corresponding-author "
                "acknowledgement. Do not submit the full manuscript yet. The "
                "main claim remains callability-aware random-matrix noise "
                "control, not broad benchmark superiority."
            ),
            "",
            "## Source Files",
            "",
            f"- Gap assessment: `{_rel(GAP_TSV)}`",
            f"- Editorial presubmission packet: `{_rel(EDITORIAL_TSV)}`",
            f"- Figure 4 wording freeze: `{_rel(FIGURE4_TSV)}`",
            f"- Author sign-off tracker: `{_rel(AUTHOR_SIGNOFF_TRACKER)}`",
            f"- Claim lint: `{_rel(CLAIM_LINT_MD)}`",
            f"- Traceability: `{_rel(TRACEABILITY_MD)}`",
            f"- Presubmission inquiry draft: `{_rel(PRESUBMISSION_MD)}`",
        ]
    )
    return "\n".join(lines)


def build_acknowledgement_template() -> str:
    today = date.today().isoformat()
    return f"""# Corresponding Author Figure 4 Acknowledgement Template

Generated by `python scripts/build_nature_methods_go_no_go_final.py` on {today}.

## Required Acknowledgement Before Nature Methods Presubmission Inquiry

I acknowledge that Figure 4 will be presented only as a bounded public-data
PDAC/TME showcase of RMTGuard callability. I understand that Figure 4 must not
be described as demonstrating a new PDAC mechanism, CAF discovery, prognosis,
therapy response, clinical validation, patient-level reproducibility, or
treatment stratification.

The allowed Figure 4 language is the wording frozen in:

```text
docs/figure4_pdac_tme_wording_freeze.md
```

The Nature Methods presubmission inquiry should not be sent until this
acknowledgement is confirmed by the corresponding authors.

## Signature / Confirmation

- Yi Miao, MD, PhD: ____________________  Date: __________
- Han Yan, MD, PhD: ____________________  Date: __________

## Optional Notes

```text

```
"""


def main() -> int:
    rows = build_rows()
    fieldnames = [
        "decision_id",
        "decision",
        "status",
        "evidence",
        "reason",
        "required_next_action",
        "stop_rule",
    ]
    _write_tsv(OUT_TSV, rows, fieldnames)
    _write_text(OUT_MD, build_markdown(rows))
    _write_text(ACK_MD, build_acknowledgement_template())
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print(_rel(ACK_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
