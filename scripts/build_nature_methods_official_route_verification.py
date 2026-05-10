from __future__ import annotations

"""Build an official-source Nature Methods route verification checklist.

Author: RMTGuard development team
Date: 2026-05-10
Purpose: Record the official Nature Methods presubmission, article-type, data,
code, ethics, and AI-use route checks needed before editor-facing submission.
Data source: Official Nature Methods and Nature Portfolio web pages verified on
2026-05-10.
Method notes: This script records source URLs and project implications only. It
does not replace a final manual website check immediately before sending.
"""

import csv
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

OUT_TSV = ROOT / "results" / "submission" / "nature_methods_official_route_verification.tsv"
OUT_MD = ROOT / "docs" / "nature_methods_official_route_verification.md"

SOURCES = {
    "presubmission": "https://www.nature.com/nmeth/submission-guidelines/presubmission-enquiries",
    "submission_guidelines": "https://www.nature.com/nmeth/submission-guidelines",
    "contact": "https://www.nature.com/nmeth/contact",
    "content_types": "https://www.nature.com/nmeth/content",
    "aims": "https://www.nature.com/nmeth/aims",
    "preparing": "https://www.nature.com/nmeth/submission-guidelines/preparing-your-submission",
    "reporting": "https://www.nature.com/nmeth/editorial-policies/reporting-standards",
    "ethics": "https://www.nature.com/nmeth/editorial-policies/ethics-and-biosecurity",
    "ai": "https://www.nature.com/nmeth/editorial-policies/ai",
}


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "check_id",
        "evidence_level",
        "current_status",
        "official_source",
        "source_url",
        "official_requirement_summary",
        "rmtguard_implication",
        "required_action",
        "risk_if_unfixed",
        "verified_at",
    ]
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


def build_rows() -> list[dict[str, str]]:
    verified_at = date.today().isoformat()
    return [
        {
            "check_id": "presubmission_route",
            "evidence_level": "direct guideline",
            "current_status": "pass_with_hold",
            "official_source": "Nature Methods presubmission enquiries",
            "source_url": SOURCES["presubmission"],
            "official_requirement_summary": (
                "Nature Methods accepts presubmission enquiries for scope questions "
                "through the online Manuscript Tracking System with an abstract."
            ),
            "rmtguard_implication": (
                "Use the online system after author acknowledgement; do not send the "
                "HOLD EML as an email submission."
            ),
            "required_action": (
                "After both corresponding authors confirm Figure 4 wording, log in to "
                "the Nature Methods MTS and submit the concise inquiry abstract."
            ),
            "risk_if_unfixed": "technical-check delay or wrong-route desk handling",
            "verified_at": verified_at,
        },
        {
            "check_id": "no_full_manuscript_as_presubmission",
            "evidence_level": "direct guideline",
            "current_status": "pass_with_hold",
            "official_source": "Nature Methods presubmission enquiries and contact",
            "source_url": SOURCES["contact"],
            "official_requirement_summary": (
                "Presubmission enquiries should not be used to submit a full manuscript; "
                "Nature Methods directs manuscripts and presubmission enquiries to the "
                "online system and says complete manuscripts should not be emailed."
            ),
            "rmtguard_implication": (
                "The presubmission packet must remain an abstract-level scope inquiry, "
                "not a full manuscript package."
            ),
            "required_action": "Do not attach the full manuscript or full figure package to the presubmission inquiry.",
            "risk_if_unfixed": "editorial irritation or immediate route rejection",
            "verified_at": verified_at,
        },
        {
            "check_id": "article_type_fit",
            "evidence_level": "direct guideline",
            "current_status": "high_gate",
            "official_source": "Nature Methods content types",
            "source_url": SOURCES["content_types"],
            "official_requirement_summary": (
                "A Nature Methods Article is for a novel method or tool and should "
                "include technical description plus validation of performance, "
                "reproducibility, broad applicability, and biological discovery potential."
            ),
            "rmtguard_implication": (
                "RMTGuard can be pitched as an Article only if the claims stay bounded "
                "and the validation/benchmark evidence remains explicit."
            ),
            "required_action": "Keep the inquiry centered on method novelty, reproducibility, and validation; do not claim broad superiority.",
            "risk_if_unfixed": "scope-based desk rejection",
            "verified_at": verified_at,
        },
        {
            "check_id": "scope_fit",
            "evidence_level": "direct guideline",
            "current_status": "conditional_fit",
            "official_source": "Nature Methods aims and scope",
            "source_url": SOURCES["aims"],
            "official_requirement_summary": (
                "The journal includes single-cell, computational, statistical, and "
                "machine-learning methods for biological data, but requires practical "
                "relevance, strong validation, biological application, and comparisons "
                "with available approaches."
            ),
            "rmtguard_implication": (
                "The current strongest pitch is callability-aware random-matrix noise "
                "control, not automatic parameter tuning or universal stability gain."
            ),
            "required_action": "Keep Figure 4 as bounded biological application evidence and keep comparator limitations visible.",
            "risk_if_unfixed": "high editorial-fit risk",
            "verified_at": verified_at,
        },
        {
            "check_id": "initial_submission_materials_later",
            "evidence_level": "direct guideline",
            "current_status": "not_needed_for_presubmission_yet",
            "official_source": "Nature Methods preparing your material",
            "source_url": SOURCES["preparing"],
            "official_requirement_summary": (
                "A formal initial submission requires a manuscript file, cover letter, "
                "and optional supplementary information; the cover letter should explain "
                "importance and relevance to Nature Methods readers."
            ),
            "rmtguard_implication": (
                "Do not treat the presubmission packet as full submission readiness; "
                "build the formal cover letter only if the presubmission response is encouraging."
            ),
            "required_action": "Keep formal submission package under NO-GO until editor response and final evidence freeze.",
            "risk_if_unfixed": "premature full-submission technical delay",
            "verified_at": verified_at,
        },
        {
            "check_id": "data_availability",
            "evidence_level": "direct guideline",
            "current_status": "pass_pending_final_text",
            "official_source": "Nature Methods reporting standards",
            "source_url": SOURCES["reporting"],
            "official_requirement_summary": (
                "Nature Portfolio research articles need a data availability statement; "
                "public datasets should include accessions or identifiers and large "
                "datasets should use repositories rather than supplementary files."
            ),
            "rmtguard_implication": (
                "Use GEO/CELLxGENE/Zenodo links and source-data tables; do not commit "
                "large expression matrices to GitHub."
            ),
            "required_action": "Before full submission, freeze the Data Availability statement and dataset accession table.",
            "risk_if_unfixed": "technical-check delay or reproducibility objection",
            "verified_at": verified_at,
        },
        {
            "check_id": "code_availability",
            "evidence_level": "direct guideline",
            "current_status": "pass_pending_version_freeze",
            "official_source": "Nature Methods reporting standards",
            "source_url": SOURCES["reporting"],
            "official_requirement_summary": (
                "Custom central code should be available to editors and reviewers; "
                "published code is best deposited in a DOI-minting repository and "
                "described in a Code Availability section."
            ),
            "rmtguard_implication": (
                "Keep GitHub release and Zenodo DOI evidence stable; do not imply "
                "working-branch updates are inside the immutable release archive."
            ),
            "required_action": "Freeze a new DOI archive only after final benchmark and text freeze if post-release changes are material.",
            "risk_if_unfixed": "hard reproducibility concern",
            "verified_at": verified_at,
        },
        {
            "check_id": "ethics_public_human_data",
            "evidence_level": "direct guideline",
            "current_status": "author_statement_needed",
            "official_source": "Nature Methods research ethics",
            "source_url": SOURCES["ethics"],
            "official_requirement_summary": (
                "Human-participant research requires ethics/consent statements or "
                "exemption details; public-data-only analyses still need a clear "
                "ethics/public-data-use boundary."
            ),
            "rmtguard_implication": (
                "State that analyses use public de-identified datasets and that no "
                "new private clinical data or patient-level intervention is reported."
            ),
            "required_action": "Corresponding authors must approve the final ethics/public-data-use wording.",
            "risk_if_unfixed": "technical-check delay or ethics query",
            "verified_at": verified_at,
        },
        {
            "check_id": "ai_use_statement",
            "evidence_level": "direct guideline",
            "current_status": "author_statement_needed",
            "official_source": "Nature Methods AI policy",
            "source_url": SOURCES["ai"],
            "official_requirement_summary": (
                "LLMs are not authors; substantive AI-tool use should be documented, "
                "while AI-assisted copy editing alone does not need declaration."
            ),
            "rmtguard_implication": (
                "If Codex/Claude helped generate code, documentation, or manuscript "
                "drafts, authors should disclose this in an appropriate statement."
            ),
            "required_action": "Add an author-approved AI-use disclosure before full submission.",
            "risk_if_unfixed": "policy-compliance query",
            "verified_at": verified_at,
        },
    ]


def build_markdown(rows: list[dict[str, str]]) -> str:
    lines = [
        "# Nature Methods Official Route Verification",
        "",
        "Generated by `python scripts/build_nature_methods_official_route_verification.py`.",
        "",
        "## Bottom Line",
        "",
        "- Official route: Nature Methods presubmission enquiries should be submitted through the online Manuscript Tracking System.",
        "- Current RMTGuard action: `hold_author_acknowledgement`; do not send yet.",
        "- Full manuscript submission remains `NO-GO`.",
        "- The final route must be rechecked manually immediately before sending because journal pages and submission systems can change.",
        "",
        "## Checklist",
        "",
        "| Check | Evidence level | Status | Official source | RMTGuard implication | Required action |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['check_id']} | `{row['evidence_level']}` | `{row['current_status']}` | "
            f"[{row['official_source']}]({row['source_url']}) | {row['rmtguard_implication']} | "
            f"{row['required_action']} |"
        )
    lines.extend(
        [
            "",
            "## Sources",
            "",
        ]
    )
    for key, url in SOURCES.items():
        lines.append(f"- {key}: {url}")
    lines.extend(
        [
            "",
            "## Manual Stop Rules",
            "",
            "1. Do not send the Nature Methods HOLD email draft.",
            "2. Do not submit a full manuscript as a presubmission enquiry.",
            "3. Do not send before both corresponding authors confirm the bounded Figure 4 wording.",
            "4. Do not send before manually opening the official Nature Methods pages and MTS route.",
            "5. Do not add broad stability-superiority, clinical-validation, prognosis, therapy-response, or patient-level claims.",
            "",
            "## Machine-Readable Table",
            "",
            f"- `{_rel(OUT_TSV)}`",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    rows = build_rows()
    _write_tsv(OUT_TSV, rows)
    _write_text(OUT_MD, build_markdown(rows))
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
