from __future__ import annotations

"""Triage external model or collaborator feedback for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-01
Purpose: Convert external manuscript-review feedback into an auditable action
queue for claims, figures, analyses, software release, and journal routing.
Data source: `metadata/external_review_feedback_template.tsv` or a user-supplied
TSV with the same columns.
Method notes: The classifier is deliberately conservative. Fatal novelty,
validity, or release objections become P0/P1 blockers, but this script never
changes manuscript claims by itself.
"""

import argparse
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_INPUT = ROOT / "metadata" / "external_review_feedback_active.tsv"
TEMPLATE_INPUT = ROOT / "metadata" / "external_review_feedback_template.tsv"
DEFAULT_INPUT = ACTIVE_INPUT if ACTIVE_INPUT.exists() else TEMPLATE_INPUT
OUT_TSV = ROOT / "results" / "submission" / "external_review_feedback_triage.tsv"
OUT_MD = ROOT / "docs" / "external_review_feedback_triage.md"

FIELDNAMES = [
    "feedback_id",
    "reviewer_source",
    "reviewer_type",
    "section",
    "triage_category",
    "priority",
    "route_impact",
    "linked_artifact",
    "required_action",
    "stop_condition",
    "status",
    "comment",
    "suggested_action",
]

REQUIRED_COLUMNS = [
    "feedback_id",
    "reviewer_source",
    "reviewer_type",
    "section",
    "comment",
    "suggested_action",
    "evidence_path",
    "severity_hint",
    "journal_route_hint",
]

FATAL_RE = re.compile(
    r"\b(fatal|invalid|not novel|no novelty|insufficient novelty|not enough for nature methods|"
    r"fundamental flaw|statistical(?:ly)? invalid|unsupported method|desk reject)\b",
    re.IGNORECASE,
)
RELEASE_RE = re.compile(
    r"\b(github|zenodo|doi|code availability|data availability|reproducib|release|repository)\b",
    re.IGNORECASE,
)
ANALYSIS_RE = re.compile(
    r"\b(benchmark|analysis|ablation|validation|dataset|baseline|compare|comparison|"
    r"sensitivity|simulation|ari|nmi|runtime|memory|pbmc|kang|baron|pdac|tabula)\b",
    re.IGNORECASE,
)
WORDING_RE = re.compile(
    r"\b(wording|overclaim|claim too strong|too strong|soften|rewrite|language|title|"
    r"abstract|cover letter|framing|tone)\b",
    re.IGNORECASE,
)
JOURNAL_RE = re.compile(
    r"\b(genome biology|nature methods|cell genomics|nature communications|bioinformatics|"
    r"journal route|fallback|transfer|scope fit|article type)\b",
    re.IGNORECASE,
)
FIGURE_RE = re.compile(
    r"\b(figure|panel|plot|legend|caption|visual|schematic)\b", re.IGNORECASE
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
        reader = csv.DictReader(handle, delimiter="\t")
        missing = [
            column
            for column in REQUIRED_COLUMNS
            if column not in (reader.fieldnames or [])
        ]
        if missing:
            raise ValueError(f"Missing required feedback columns: {', '.join(missing)}")
        return list(reader)


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _combined_text(row: dict[str, str]) -> str:
    return " ".join(
        [
            row.get("section", ""),
            row.get("comment", ""),
            row.get("suggested_action", ""),
            row.get("severity_hint", ""),
            row.get("journal_route_hint", ""),
        ]
    ).strip()


def _classification_text(row: dict[str, str]) -> str:
    """Use reviewer content for category detection, not route hints.

    `journal_route_hint` often names Nature Methods or Genome Biology for every
    row. Including it in category detection makes benchmark and ablation items
    look like journal-routing items, which hides the real action type.
    """
    return " ".join(
        [
            row.get("section", ""),
            row.get("comment", ""),
            row.get("suggested_action", ""),
            row.get("severity_hint", ""),
        ]
    ).strip()


def _is_template_row(row: dict[str, str]) -> bool:
    feedback_id = row.get("feedback_id", "").strip().lower()
    comment = row.get("comment", "").strip().lower()
    return feedback_id.startswith("template") or "replace this row" in comment


def _category(text: str) -> str:
    lowered = text.lower()
    if FATAL_RE.search(text):
        return "fatal_blocker"
    if "journal route" in lowered or "fallback" in lowered or "transfer" in lowered:
        return "journal_route_decision"
    if RELEASE_RE.search(text):
        return "release_or_reproducibility"
    if ANALYSIS_RE.search(text):
        return "analysis_request"
    if FIGURE_RE.search(text):
        return "figure_revision"
    if WORDING_RE.search(text):
        return "wording_or_claim_revision"
    if JOURNAL_RE.search(text):
        return "journal_route_decision"
    return "general_feedback"


def _priority(category: str, text: str) -> str:
    lowered = text.lower()
    if "p0" in lowered or "fatal" in lowered:
        return "P0"
    if "p1" in lowered or "major" in lowered:
        return "P1"
    if category == "fatal_blocker":
        return "P0"
    if category == "release_or_reproducibility":
        return (
            "P0"
            if any(token in lowered for token in ["doi", "zenodo", "release"])
            else "P1"
        )
    if category in {"analysis_request", "journal_route_decision"}:
        return "P1"
    if category in {"figure_revision", "wording_or_claim_revision"}:
        return "P2"
    return "P3"


def _route_impact(category: str, text: str) -> str:
    lowered = text.lower()
    if category == "fatal_blocker" and "nature methods" in lowered:
        return "nature_methods_go_no_go"
    if category == "journal_route_decision":
        return "journal_route"
    if category == "release_or_reproducibility":
        return "software_release_gate"
    if category == "analysis_request":
        return "scientific_gate_or_benchmark"
    if category == "wording_or_claim_revision":
        return "claim_boundary"
    if category == "figure_revision":
        return "figure_evidence"
    return "editorial_polish"


def _required_action(category: str, row: dict[str, str]) -> str:
    explicit = row.get("suggested_action", "").strip()
    if explicit and explicit.lower() not in {"na", "n/a", "none"}:
        return explicit
    return {
        "fatal_blocker": "Hold submission; decide whether new evidence, narrower claims, or fallback journal route resolves the objection.",
        "release_or_reproducibility": "Resolve GitHub/Zenodo/code/data availability evidence before editor-facing submission.",
        "journal_route_decision": "Update top-paper route package and decide Nature Methods versus Genome Biology after gate review.",
        "analysis_request": "Convert into a benchmark, ablation, figure-source-data, or no-go analysis ticket before revising claims.",
        "figure_revision": "Update figure plan, source-data table, caption boundary, or panel-level evidence map.",
        "wording_or_claim_revision": "Revise manuscript wording and rerun claim-boundary lint plus traceability checks.",
        "general_feedback": "Review manually and either close as not actionable or convert into a specific ticket.",
    }[category]


def _stop_condition(category: str) -> str:
    return {
        "fatal_blocker": "Do not submit until this objection is resolved or route is downgraded.",
        "release_or_reproducibility": "Do not claim public release, DOI, or code availability until external evidence exists.",
        "journal_route_decision": "Do not send Nature Methods inquiry until route decision remains justified after feedback.",
        "analysis_request": "Do not upgrade claims until the requested analysis is run or explicitly rejected with rationale.",
        "figure_revision": "Do not finalize figure captions until panel evidence and caveats match the claim matrix.",
        "wording_or_claim_revision": "Do not send editor-facing text until claim lint and traceability remain violation-free.",
        "general_feedback": "Do not act on vague feedback without converting it into a concrete revision ticket.",
    }[category]


def triage_rows(feedback_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    real_rows = [row for row in feedback_rows if not _is_template_row(row)]
    if not real_rows:
        return [
            {
                "feedback_id": "NO_EXTERNAL_FEEDBACK",
                "reviewer_source": "none",
                "reviewer_type": "none",
                "section": "overall",
                "triage_category": "awaiting_external_feedback",
                "priority": "P2",
                "route_impact": "review_loop",
                "linked_artifact": _rel(TEMPLATE_INPUT),
                "required_action": "Collect external model or collaborator comments in the feedback template, then rerun this script.",
                "stop_condition": "Do not treat the external-review loop as complete until at least one real feedback row is triaged.",
                "status": "awaiting_feedback",
                "comment": "No real feedback rows were found.",
                "suggested_action": "Use manuscript/current_article_external_review_packet.md as the review input.",
            }
        ]

    rows: list[dict[str, str]] = []
    for row in real_rows:
        text = _combined_text(row)
        classification_text = _classification_text(row)
        category = _category(classification_text)
        rows.append(
            {
                "feedback_id": row.get("feedback_id", "").strip()
                or f"feedback_{len(rows) + 1}",
                "reviewer_source": row.get("reviewer_source", "").strip(),
                "reviewer_type": row.get("reviewer_type", "").strip(),
                "section": row.get("section", "").strip(),
                "triage_category": category,
                "priority": _priority(category, text),
                "route_impact": _route_impact(category, text),
                "linked_artifact": row.get("evidence_path", "").strip()
                or "manuscript/current_article_external_review_packet.md",
                "required_action": _required_action(category, row),
                "stop_condition": _stop_condition(category),
                "status": "open",
                "comment": row.get("comment", "").strip(),
                "suggested_action": row.get("suggested_action", "").strip(),
            }
        )
    return rows


def build_markdown(rows: list[dict[str, str]], feedback_path: Path) -> list[str]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["triage_category"]] = counts.get(row["triage_category"], 0) + 1
    blockers = [row for row in rows if row["priority"] in {"P0", "P1"}]
    lines = [
        "# External Review Feedback Triage",
        "",
        "This file is generated by `python scripts/triage_external_review_feedback.py`.",
        "",
        "Acceptance guarantee: `impossible`.",
        "This report converts external model or collaborator comments into a controlled revision queue.",
        "",
        "## Input",
        "",
        f"- Feedback table: `{_rel(feedback_path)}`",
        f"- Rows triaged: `{len(rows)}`",
        "",
        "## Category Counts",
        "",
    ]
    for category in sorted(counts):
        lines.append(f"- `{category}`: `{counts[category]}`")
    lines.extend(["", "## P0/P1 Items", ""])
    if blockers:
        for row in blockers:
            lines.extend(
                [
                    f"### {row['feedback_id']}",
                    "",
                    f"- Priority: `{row['priority']}`",
                    f"- Category: `{row['triage_category']}`",
                    f"- Route impact: `{row['route_impact']}`",
                    f"- Section: `{row['section']}`",
                    f"- Linked artifact: `{row['linked_artifact']}`",
                    f"- Required action: {row['required_action']}",
                    f"- Stop condition: {row['stop_condition']}",
                    f"- Comment: {row['comment']}",
                    "",
                ]
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Review Loop Rule",
            "",
            "Do not upgrade Nature Methods readiness or strengthen claims based on external feedback unless the resulting action is implemented, regenerated, and still passes claim-boundary and traceability checks.",
        ]
    )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Triage external review feedback for RMTGuard."
    )
    parser.add_argument("--feedback", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out", type=Path, default=OUT_TSV)
    args = parser.parse_args(argv)

    feedback_path = args.feedback.resolve()
    rows = triage_rows(_read_tsv(feedback_path))
    _write_tsv(args.out, rows)
    _write_text(OUT_MD, build_markdown(rows, feedback_path))
    p0_p1 = sum(row["priority"] in {"P0", "P1"} for row in rows)
    print(_rel(args.out))
    print(_rel(OUT_MD))
    print(f"p0_p1\t{p0_p1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
