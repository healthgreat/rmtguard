from __future__ import annotations

"""Lint manuscript and release text for overclaiming.

Author: RMTGuard development team
Date: 2026-05-01
Purpose: Detect journal-facing wording that violates the generated claim
boundary, especially acceptance guarantees, broad fixed-PC superiority,
PBMC68k positive-discovery claims, premature DOI/release claims, and premature
submission-ready language.
Data source: Local Markdown/TXT manuscript, docs, and submission artifacts.
Method notes: Boundary documents may quote prohibited wording. Lines with
explicit negation or boundary terms are reported as controlled_boundary rather
than violations.
"""

import csv
import re
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "submission"
REPORT_TSV = OUT_DIR / "claim_boundary_lint.tsv"
REPORT_MD = ROOT / "docs" / "claim_boundary_lint.md"


class Rule(NamedTuple):
    rule_id: str
    severity: str
    pattern: re.Pattern[str]
    remediation: str


RULES = [
    Rule(
        "acceptance_guarantee",
        "blocking",
        re.compile(
            r"\b(acceptance guarantee|guaranteed acceptance|guaranteed publication|guarantee(?:d)? journal acceptance|guarantee(?:d)? acceptance|guarantee(?:d)? publication)\b",
            re.IGNORECASE,
        ),
        "Replace acceptance guarantees with gate-controlled readiness language.",
    ),
    Rule(
        "broad_fixed_pc_superiority",
        "blocking",
        re.compile(
            r"\b(broad superiority|broad fixed-PC superiority|outperforms fixed-PC baselines on every dataset|beats? fixed-PC baselines on every dataset|universal clustering-superiority)\b",
            re.IGNORECASE,
        ),
        "Use callability-aware stability/no-call wording and disclose comparator limits.",
    ),
    Rule(
        "pbmc68k_positive_discovery",
        "blocking",
        re.compile(
            r"\bPBMC68k\b.*\b(positive (?:cell-state )?discovery|strong positive|annotation-recovery success|cell-state discovery success)\b",
            re.IGNORECASE,
        ),
        "Keep PBMC68k/Zheng 2017 as diagnostic no-call or weak label-granularity stress evidence.",
    ),
    Rule(
        "premature_doi_release",
        "blocking",
        re.compile(
            r"\b(DOI-archived|DOI archived|Zenodo DOI|code DOI|fully released|public GitHub Release)\b",
            re.IGNORECASE,
        ),
        "State that DOI/GitHub release is pending until the real public release exists.",
    ),
    Rule(
        "premature_submission_ready",
        "major",
        re.compile(
            r"\b(submission-ready|submission ready|Nature Methods ready|ready for Nature Methods submission|submission_ready_for_editorial_review)\b",
            re.IGNORECASE,
        ),
        "Use not-submission-ready or conditional readiness language until gates pass.",
    ),
]

NEGATION_TERMS = [
    "not",
    "not_",
    "do not",
    "does not",
    "must not",
    "cannot",
    "never",
    "no ",
    "without",
    "until",
    "pending",
    "blocked",
    "impossible",
    "not possible",
    "not ready",
    "not_ready",
    "forbidden",
    "prohibited",
    "boundary",
    "caveat",
    "warning",
    "before the real",
    "before submission",
    "expected output",
    "blocking input",
    "external input required",
    "stop condition",
    "required",
    "still-missing",
    "missing",
    "archive",
    "complete public",
    "complete the public",
    "complete github",
    "complete public github",
    "with zenodo and run",
    "prohibit",
    "unsupported",
    "while",
]

CONTROLLED_PATH_HINTS = [
    "claim_boundary",
    "claim_scope",
    "claim_ladder",
    "editorial_presubmission_packet",
    "public_release_blocker",
    "reviewer_response_playbook",
    "figure_claim_checklist",
    "top_paper_route_package",
    "presubmission_gatekeeper",
    "external_release_plan",
    "github_release_checklist",
    "method_risk_log",
    "nature_reporting_summary_draft",
    "publication_execution_board",
    "nature_methods_compliance_audit",
    "project_status.md",
    "nature_methods_outline",
]

EXCLUDED_PATH_HINTS = [
    "docs/claim_boundary_lint.md",
    "current_article_external_review_packet",
]


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "rule_id",
                "severity",
                "status",
                "path",
                "line",
                "matched_text",
                "context",
                "remediation",
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


def scan_paths() -> list[Path]:
    paths: list[Path] = []
    for folder in [
        ROOT,
        ROOT / "docs",
        ROOT / "manuscript",
        ROOT / "results" / "submission",
    ]:
        if not folder.exists():
            continue
        pattern = "*.md" if folder != ROOT else "*.md"
        paths.extend(
            path
            for path in folder.glob(pattern)
            if path.is_file() and not _is_excluded_path(path)
        )
        if folder == ROOT / "results" / "submission":
            paths.extend(
                path
                for path in folder.glob("*.txt")
                if path.is_file() and not _is_excluded_path(path)
            )
    return sorted(set(paths))


def _is_excluded_path(path: Path) -> bool:
    rel = _rel(path).lower()
    return any(hint in rel for hint in EXCLUDED_PATH_HINTS)


def _is_controlled_context(line: str, path: Path) -> bool:
    lowered = line.lower()
    rel = _rel(path).lower()
    if re.search(r"https?://doi\.org/10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", line):
        return True
    if any(term in lowered for term in NEGATION_TERMS):
        return True
    if any(hint in rel for hint in CONTROLLED_PATH_HINTS):
        return True
    return False


def scan_text(
    path: Path, text: str, rules: list[Rule] | None = None
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    rules = rules or RULES
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        for rule in rules:
            match = rule.pattern.search(stripped)
            if not match:
                continue
            status = (
                "controlled_boundary"
                if _is_controlled_context(stripped, path)
                else "violation"
            )
            rows.append(
                {
                    "rule_id": rule.rule_id,
                    "severity": rule.severity,
                    "status": status,
                    "path": _rel(path),
                    "line": str(line_no),
                    "matched_text": match.group(0),
                    "context": stripped[:500],
                    "remediation": rule.remediation,
                }
            )
    return rows


def build_rows(paths: list[Path] | None = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths or scan_paths():
        text = path.read_text(encoding="utf-8", errors="replace")
        rows.extend(scan_text(path, text))
    if rows:
        return rows
    return [
        {
            "rule_id": "all_rules",
            "severity": "info",
            "status": "pass",
            "path": ".",
            "line": "0",
            "matched_text": "",
            "context": "No claim-boundary terms detected.",
            "remediation": "No action required.",
        }
    ]


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    violations = [row for row in rows if row["status"] == "violation"]
    controlled = [row for row in rows if row["status"] == "controlled_boundary"]
    lines = [
        "# Claim Boundary Lint",
        "",
        "This file is generated by `python scripts/lint_claim_boundaries.py`.",
        "",
        "Acceptance guarantee: `impossible`.",
        "The linter blocks unsupported journal-facing claims while allowing explicit forbidden-claim or boundary statements.",
        "",
        "## Summary",
        "",
        f"- Violations: `{len(violations)}`",
        f"- Controlled boundary mentions: `{len(controlled)}`",
        "",
    ]
    if violations:
        lines.extend(["## Violations", ""])
        for row in violations:
            lines.extend(
                [
                    f"- `{row['rule_id']}` in `{row['path']}:{row['line']}`: {row['context']}",
                    f"  Remediation: {row['remediation']}",
                ]
            )
    else:
        lines.extend(["## Violations", "", "- none"])
    lines.extend(["", "## Controlled Boundary Mentions", ""])
    if controlled:
        for row in controlled[:100]:
            lines.append(f"- `{row['rule_id']}` in `{row['path']}:{row['line']}`")
        if len(controlled) > 100:
            lines.append(
                f"- ... {len(controlled) - 100} additional controlled mentions omitted from Markdown summary."
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Submission Rule",
            "",
            "Do not submit or send editor-facing materials if any row in `results/submission/claim_boundary_lint.tsv` has `status=violation`.",
        ]
    )
    return lines


def main() -> int:
    rows = build_rows()
    _write_tsv(REPORT_TSV, rows)
    _write_text(REPORT_MD, build_markdown(rows))
    violations = [row for row in rows if row["status"] == "violation"]
    print(_rel(REPORT_TSV))
    print(_rel(REPORT_MD))
    print(f"violations\t{len(violations)}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
