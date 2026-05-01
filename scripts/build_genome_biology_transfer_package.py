from __future__ import annotations

"""Build the Genome Biology transfer package for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-01
Purpose: Convert the current post-feedback route gate, claim matrix, figure
claim checklist, and release readiness table into a bounded Genome Biology
fallback execution package.
Data source: Generated submission, manuscript, figure, and release TSV files.
Method notes: This package is a fallback conversion control surface. It does
not claim that Genome Biology will accept the paper, and it does not reframe
failed stability evidence as a positive superiority result.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

POST_FEEDBACK_GATE = (
    ROOT / "results" / "submission" / "post_feedback_journal_route_gate.tsv"
)
CLAIM_MATRIX = ROOT / "results" / "manuscript" / "claim_evidence_matrix.tsv"
FIGURE_CLAIMS = ROOT / "results" / "submission" / "figure_claim_checklist.tsv"
RELEASE_READINESS = ROOT / "results" / "release" / "release_readiness.tsv"
TRANSFER_TSV = ROOT / "results" / "submission" / "genome_biology_transfer_checklist.tsv"
TRANSFER_MD = ROOT / "docs" / "genome_biology_transfer_package.md"
COVER_LETTER = ROOT / "manuscript" / "genome_biology_cover_letter_draft.md"

FIELDNAMES = [
    "item_id",
    "status",
    "owner",
    "evidence_path",
    "required_action",
    "allowed_wording",
    "forbidden_wording",
    "notes",
]

RELEASE_CHECKS = [
    "repository_url",
    "github_remote",
    "github_release_tag",
    "zenodo_doi",
]


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


def _by(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    return {row.get(key, ""): row for row in rows}


def _status_by(rows: list[dict[str, str]], key: str) -> dict[str, str]:
    return {row.get(key, ""): row.get("status", "") for row in rows}


def _blocked_release_checks(release_rows: list[dict[str, str]]) -> list[str]:
    status = _status_by(release_rows, "check_id")
    return [
        check_id
        for check_id in RELEASE_CHECKS
        if status.get(check_id, "missing") != "pass"
    ]


def _claim(claims_by_id: dict[str, dict[str, str]], claim_id: str, field: str) -> str:
    return claims_by_id.get(claim_id, {}).get(field, "")


def _row(
    item_id: str,
    status: str,
    owner: str,
    evidence_path: Path,
    required_action: str,
    allowed_wording: str,
    forbidden_wording: str,
    notes: str,
) -> dict[str, str]:
    return {
        "item_id": item_id,
        "status": status,
        "owner": owner,
        "evidence_path": _rel(evidence_path),
        "required_action": required_action,
        "allowed_wording": allowed_wording,
        "forbidden_wording": forbidden_wording,
        "notes": notes,
    }


def build_transfer_rows(
    post_feedback_rows: list[dict[str, str]],
    claim_rows: list[dict[str, str]],
    figure_rows: list[dict[str, str]],
    release_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    post_by_id = _by(post_feedback_rows, "decision_id")
    claims_by_id = _by(claim_rows, "claim_id")
    figure_by_id = _by(figure_rows, "figure")
    release_blockers = _blocked_release_checks(release_rows)

    overall_route = post_by_id.get("overall_post_feedback_route", {}).get(
        "decision", "missing"
    )
    gb_route = post_by_id.get("genome_biology_gate", {}).get("decision", "missing")
    release_ready = not release_blockers
    gb_allowed = gb_route in {"activate_after_release", "conversion_candidate"}

    route_status = (
        "ready_after_release"
        if overall_route == "genome_biology_after_release" and gb_allowed
        else (
            "candidate"
            if overall_route == "genome_biology_conversion_candidate" and gb_allowed
            else "hold"
        )
    )
    release_status = "pass" if release_ready else "blocked_external"
    figure3 = figure_by_id.get("Figure 3", {})
    figure3_status = (
        "needs_reframe"
        if figure3.get("status") in {"blocked", "pending"}
        else "pass" if figure3 else "missing"
    )
    software_claim_status = claims_by_id.get("software_release", {}).get(
        "status", "missing"
    )
    cover_status = (
        "draft_ready_after_release" if release_ready else "blocked_until_release"
    )

    rows = [
        _row(
            "route_activation",
            route_status,
            "Codex + corresponding author",
            POST_FEEDBACK_GATE,
            "Use this fallback only when Nature Methods remains held or receives negative editorial feedback.",
            "Genome Biology fallback is a reproducible genomics-workflow route after public release completion.",
            "Do not present fallback activation as journal acceptance or as a strict 20-50 JIF guarantee.",
            f"overall_route={overall_route}; genome_biology_gate={gb_route}.",
        ),
        _row(
            "public_release_completion",
            release_status,
            "GitHub/Zenodo account owner + Codex",
            RELEASE_READINESS,
            "Complete public GitHub repository, remote, release page, and Zenodo DOI before using the cover letter.",
            "The local package can be described as prepared; public code availability can be claimed only after release checks pass.",
            _claim(claims_by_id, "software_release", "prohibited_wording"),
            ";".join(release_blockers) if release_blockers else "release checks pass",
        ),
        _row(
            "claim_frame",
            "controlled_limitations",
            "Codex",
            CLAIM_MATRIX,
            "Use the callability-aware workflow frame and keep failed stability evidence visible.",
            "RMTGuard is an open, callability-aware random-matrix workflow for reproducible scRNA-seq state discovery.",
            _claim(claims_by_id, "pbmc3k_stability", "prohibited_wording"),
            "The fallback manuscript must emphasize reproducibility, diagnostics, annotation noninferiority, and no-call boundaries rather than universal stability superiority.",
        ),
        _row(
            "figure3_reframe",
            figure3_status,
            "Codex",
            FIGURE_CLAIMS,
            "Rewrite Figure 3 legend as a callability/no-call benchmark and preserve all comparator caveats.",
            figure3.get("allowed_caption_claim", ""),
            figure3.get("prohibited_caption_claim", ""),
            figure3.get("must_show_caveat", ""),
        ),
        _row(
            "pdac_showcase_scope",
            (
                "pass"
                if claims_by_id.get("pdac_tme_showcase", {}).get("status") == "pass"
                else "hold"
            ),
            "Codex",
            CLAIM_MATRIX,
            "Keep PDAC/TME as a public biological use case, not as a clinical or disease-mechanism discovery.",
            _claim(claims_by_id, "pdac_tme_showcase", "allowed_wording"),
            _claim(claims_by_id, "pdac_tme_showcase", "prohibited_wording"),
            "This remains useful as application depth only if the CAF/fibroblast boundary is not overstated.",
        ),
        _row(
            "cover_letter_draft",
            cover_status,
            "Codex + corresponding author",
            COVER_LETTER,
            "Use the generated cover letter only after repository URL and DOI placeholders are replaced.",
            "A bounded genomics software/workflow cover letter can be prepared from the current evidence.",
            "Do not send a cover letter with placeholder URLs, missing DOI, or universal superiority wording.",
            f"software_release_claim_status={software_claim_status}.",
        ),
    ]

    blocking = [
        row["item_id"]
        for row in rows
        if row["status"]
        in {"blocked_external", "hold", "missing", "blocked_until_release"}
    ]
    if route_status == "ready_after_release" and release_blockers:
        overall_status = "prepare_after_release"
    elif route_status in {"ready_after_release", "candidate"} and not blocking:
        overall_status = "transfer_candidate"
    else:
        overall_status = "hold"
    rows.append(
        _row(
            "overall_genome_biology_transfer",
            overall_status,
            "Codex + corresponding author",
            TRANSFER_TSV,
            "Proceed only when this row is transfer_candidate or prepare_after_release with a concrete external release action in progress.",
            "Use evidence-bounded reproducible-workflow language.",
            "Do not claim acceptance, strict IF20-50 eligibility, or broad clustering superiority.",
            ";".join(blocking) if blocking else "none",
        )
    )
    return rows


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    overall = next(
        (row for row in rows if row["item_id"] == "overall_genome_biology_transfer"),
        {},
    )
    lines = [
        "# Genome Biology Transfer Package",
        "",
        "This file is generated by `python scripts/build_genome_biology_transfer_package.py`.",
        "",
        "Acceptance guarantee: `impossible`.",
        "This is a controlled fallback package for a reproducible genomics workflow, not a stronger Nature Methods claim.",
        "",
        "## Overall Decision",
        "",
        f"- Status: `{overall.get('status', 'missing')}`",
        f"- Blocking items: `{overall.get('notes', 'missing')}`",
        f"- Required action: {overall.get('required_action', 'missing')}",
        "",
        "## Transfer Checklist",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"### {row['item_id']}",
                "",
                f"- Status: `{row['status']}`",
                f"- Owner: `{row['owner']}`",
                f"- Evidence: `{row['evidence_path']}`",
                f"- Required action: {row['required_action']}",
                f"- Allowed wording: {row['allowed_wording']}",
                f"- Forbidden wording: {row['forbidden_wording']}",
                f"- Notes: {row['notes']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Hard Language Boundary",
            "",
            "The transfer version may say `callability-aware`, `reproducible workflow`, `diagnostic no-call`, `public benchmark`, and `bounded PDAC/TME use case`.",
            "The transfer version must not make an `acceptance promise`, claim `universal clustering superiority`, claim a `positive PBMC68k discovery`, or say `DOI-archived release` until those exact gates pass.",
            "",
            "## Before Sending",
            "",
            "1. Replace the public repository and archive placeholders in the cover letter.",
            "2. Regenerate release readiness, claim lint, claim traceability, this transfer package, and the external review packet.",
            "3. Verify the current Genome Biology author instructions manually before final formatting.",
        ]
    )
    return lines


def build_cover_letter(rows: list[dict[str, str]]) -> list[str]:
    by_id = _by(rows, "item_id")
    release_status = by_id.get("public_release_completion", {}).get("status", "missing")
    overall_status = by_id.get("overall_genome_biology_transfer", {}).get(
        "status", "missing"
    )
    lines = [
        "# Genome Biology Cover Letter Draft",
        "",
        f"Status: `{overall_status}`; public release status: `{release_status}`.",
        "Do not send this draft until all placeholders are replaced and the current journal instructions are verified.",
        "",
        "Dear Editors,",
        "",
        "We submit RMTGuard, a callability-aware random-matrix workflow for reproducible single-cell RNA-seq state discovery, for consideration as a genomics software and benchmark manuscript.",
        "",
        "Single-cell RNA-seq analyses often depend on subjective choices of highly variable genes, principal components, graph neighborhoods and clustering resolution. RMTGuard addresses this reproducibility problem by exposing the spectral noise boundary as an explicit analysis decision, reporting diagnostic no-call states when low-signal data should not be forced into biological clusters, and exporting AnnData-compatible embeddings, diagnostics and benchmark metadata.",
        "",
        "The manuscript is intentionally evidence-bounded. Synthetic benchmarks support false-signal control under pure-null simulations and rare-state retention, while public real-data benchmarks show annotation noninferiority and transparent callability limits rather than universal superiority over fixed-PC baselines. PBMC68k/Zheng 2017 is reported as a diagnostic no-call stress case, not as a positive cell-state discovery. A public PDAC/TME showcase provides a bounded immune and ductal-context application with external validation, without claiming a standalone clinical or disease-mechanism discovery.",
        "",
        "The accompanying reproducibility package includes source code, tests, public data-accession workflow scripts, figure source data and release manifests. Public repository and archive information should be inserted here before submission: [TO CONFIRM: public GitHub URL]; [TO CONFIRM: Zenodo DOI].",
        "",
        "We believe this evidence-bounded framing is appropriate for readers who need reproducible single-cell workflows that distinguish robust signal, low-confidence no-calls and overstated clustering claims.",
        "",
        "Sincerely,",
        "",
        "[TO CONFIRM: corresponding author name and affiliation]",
    ]
    return lines


def main() -> int:
    rows = build_transfer_rows(
        _read_tsv(POST_FEEDBACK_GATE),
        _read_tsv(CLAIM_MATRIX),
        _read_tsv(FIGURE_CLAIMS),
        _read_tsv(RELEASE_READINESS),
    )
    _write_tsv(TRANSFER_TSV, rows)
    _write_text(TRANSFER_MD, build_markdown(rows))
    _write_text(COVER_LETTER, build_cover_letter(rows))
    overall = next(
        row for row in rows if row["item_id"] == "overall_genome_biology_transfer"
    )
    print(_rel(TRANSFER_TSV))
    print(_rel(TRANSFER_MD))
    print(_rel(COVER_LETTER))
    print(f"overall\t{overall['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
