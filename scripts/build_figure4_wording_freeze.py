from __future__ import annotations

"""Build bounded Figure 4 wording for the PDAC/TME public-data showcase.

Author: RMTGuard development team
Date: 2026-05-10
Purpose: Freeze editor-facing and manuscript-facing Figure 4 wording after the
PDAC/TME pathway/atlas validation layer.
Data source: Public PDAC/TME scRNA-seq benchmark outputs derived from GSE154778
and GSE263733. Method references are recorded in the upstream validation
artifacts; this script only assembles claim-boundary wording.
Method notes: The output is a claim-control artifact. It does not assert a new
PDAC mechanism, clinical validation, prognosis, treatment response, or patient
level reproducibility.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SUMMARY = (
    ROOT
    / "results"
    / "pdac_tme"
    / "pathway_atlas_validation"
    / "pdac_pathway_atlas_validation_summary.tsv"
)
PATHWAYS = (
    ROOT
    / "results"
    / "pdac_tme"
    / "pathway_atlas_validation"
    / "pdac_pathway_rank_enrichment.tsv"
)
ATLAS = (
    ROOT
    / "results"
    / "pdac_tme"
    / "pathway_atlas_validation"
    / "pdac_atlas_marker_citation_mapping.tsv"
)

OUT_TSV = ROOT / "results" / "submission" / "figure4_pdac_tme_wording_freeze.tsv"
OUT_MD = ROOT / "docs" / "figure4_pdac_tme_wording_freeze.md"
CAPTION_MD = ROOT / "manuscript" / "figure4_caption_bounded_draft.md"


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


def _summary_lookup() -> dict[str, dict[str, str]]:
    return {row.get("summary_id", ""): row for row in _read_tsv(SUMMARY)}


def _top_interpretable_pathways(limit: int = 8) -> list[dict[str, str]]:
    rows = [
        row
        for row in _read_tsv(PATHWAYS)
        if row.get("significant_fdr_0_05") == "True"
        and row.get("pathway_priority_label") == "manuscript_interpretable_candidate"
    ]
    rows.sort(key=lambda row: float(row.get("p_adj_bh", "1") or "1"))
    return rows[:limit]


def _supported_atlas_rows() -> list[dict[str, str]]:
    return [
        row
        for row in _read_tsv(ATLAS)
        if row.get("support_status") == "supported"
    ]


def build_rows() -> list[dict[str, str]]:
    summary = _summary_lookup()
    top_pathways = _top_interpretable_pathways()
    atlas_rows = _supported_atlas_rows()
    hallmark_n = summary.get("significant_hallmark_pathways", {}).get("value", "0")
    reactome_n = summary.get("significant_reactome_pathways", {}).get("value", "0")
    interpretable_n = summary.get("manuscript_interpretable_pathways", {}).get(
        "value", "0"
    )
    atlas_n = summary.get("atlas_supported_cluster_signature_rows", {}).get(
        "value", "0"
    )
    key_pathways = "; ".join(
        f"{row.get('dataset_id')} cluster {row.get('cluster')}: "
        f"{row.get('pathway_name')} (BH-FDR={float(row.get('p_adj_bh', '1')):.2e})"
        for row in top_pathways[:5]
    )
    atlas_labels = "; ".join(
        f"{row.get('dataset_id')} cluster {row.get('cluster')}: "
        f"{row.get('expected_cluster_label')} ({row.get('reference')}, "
        f"overlap={row.get('overlap_n')})"
        for row in atlas_rows[:6]
    )

    return [
        {
            "element_id": "figure4_decision",
            "status": "mentor_freeze_with_author_ack_needed",
            "figure_panel": "overall",
            "recommended_text": (
                "Keep PDAC/TME as a bounded main-figure showcase for the "
                "Nature Methods presubmission route, not as an independent "
                "PDAC biology discovery."
            ),
            "evidence_path": (
                f"{_rel(SUMMARY)};{_rel(PATHWAYS)};{_rel(ATLAS)}"
            ),
            "claim_boundary": (
                "Requires final author acknowledgement before external "
                "submission."
            ),
        },
        {
            "element_id": "figure4_title",
            "status": "allowed",
            "figure_panel": "overall",
            "recommended_text": (
                "Bounded PDAC/TME public-data showcase of RMTGuard callability"
            ),
            "evidence_path": _rel(SUMMARY),
            "claim_boundary": "Use showcase/callability wording, not discovery wording.",
        },
        {
            "element_id": "caption_opening",
            "status": "allowed",
            "figure_panel": "overall",
            "recommended_text": (
                "Public PDAC/TME scRNA-seq datasets were used as a bounded "
                "application to illustrate how RMTGuard reports callable "
                "cell-state structure together with pathway and atlas-marker "
                "support."
            ),
            "evidence_path": _rel(SUMMARY),
            "claim_boundary": "Do not imply clinical validation or patient-level findings.",
        },
        {
            "element_id": "pathway_panel",
            "status": "allowed",
            "figure_panel": "pathway/atlas panel",
            "recommended_text": (
                f"Rank-based pathway testing identified {hallmark_n} "
                f"Hallmark and {reactome_n} Reactome significant rows, with "
                f"{interpretable_n} retained as manuscript-interpretable "
                f"pathway hits after excluding low-specificity labels. "
                f"Representative hits include {key_pathways}."
            ),
            "evidence_path": _rel(PATHWAYS),
            "claim_boundary": (
                "State rank-based Wilcoxon/Mann-Whitney pathway testing; do "
                "not call this Broad desktop permutation GSEA."
            ),
        },
        {
            "element_id": "atlas_panel",
            "status": "allowed",
            "figure_panel": "atlas-marker panel",
            "recommended_text": (
                f"Atlas-marker comparison supported {atlas_n} "
                f"cluster/signature rows with at least two overlapping "
                f"published markers. Representative supported labels include "
                f"{atlas_labels}."
            ),
            "evidence_path": _rel(ATLAS),
            "claim_boundary": (
                "Use marker support language; do not claim de novo cell-state "
                "discovery."
            ),
        },
        {
            "element_id": "forbidden_claims",
            "status": "forbidden",
            "figure_panel": "overall",
            "recommended_text": (
                "Do not claim new PDAC mechanism, CAF discovery, prognosis, "
                "therapy response, clinical validation, patient-level "
                "reproducibility, or treatment stratification from Figure 4."
            ),
            "evidence_path": _rel(SUMMARY),
            "claim_boundary": "Hard stop for Nature Methods and Genome Biology drafts.",
        },
    ]


def build_markdown(rows: list[dict[str, str]]) -> str:
    allowed = [row for row in rows if row["status"] == "allowed"]
    forbidden = [row for row in rows if row["status"] == "forbidden"]
    lines = [
        "# Figure 4 PDAC/TME Wording Freeze",
        "",
        "Generated by `python scripts/build_figure4_wording_freeze.py`.",
        "",
        "## Mentor Decision",
        "",
        (
            "Keep PDAC/TME as a bounded main-figure showcase for the Nature "
            "Methods presubmission route. This is not a disease-mechanism or "
            "clinical-validation figure."
        ),
        "",
        "## Allowed Wording",
        "",
        "| Element | Recommended text | Evidence | Boundary |",
        "| --- | --- | --- | --- |",
    ]
    for row in allowed:
        lines.append(
            "| "
            + row["element_id"]
            + " | "
            + row["recommended_text"]
            + " | `"
            + row["evidence_path"]
            + "` | "
            + row["claim_boundary"]
            + " |"
        )
    lines.extend(
        [
            "",
            "## Forbidden Wording",
            "",
            "| Element | Text | Boundary |",
            "| --- | --- | --- |",
        ]
    )
    for row in forbidden:
        lines.append(
            "| "
            + row["element_id"]
            + " | "
            + row["recommended_text"]
            + " | "
            + row["claim_boundary"]
            + " |"
        )
    lines.extend(
        [
            "",
            "## Exact Caption Draft",
            "",
            build_caption_text(rows),
            "",
            "## Remaining Author Step",
            "",
            (
                "The scientific mentor decision is frozen here, but the "
                "corresponding authors still need to acknowledge that Figure 4 "
                "is a bounded public-data showcase before external submission."
            ),
        ]
    )
    return "\n".join(lines)


def build_caption_text(rows: list[dict[str, str]]) -> str:
    lookup = {row["element_id"]: row for row in rows}
    return (
        "**Figure 4 | Bounded PDAC/TME public-data showcase of RMTGuard "
        "callability.** "
        + lookup["caption_opening"]["recommended_text"]
        + " "
        + lookup["pathway_panel"]["recommended_text"]
        + " "
        + lookup["atlas_panel"]["recommended_text"]
        + " "
        + "All PDAC/TME interpretations are public-data, non-clinical, and "
        + "hypothesis-generating."
    )


def main() -> int:
    rows = build_rows()
    fieldnames = [
        "element_id",
        "status",
        "figure_panel",
        "recommended_text",
        "evidence_path",
        "claim_boundary",
    ]
    _write_tsv(OUT_TSV, rows, fieldnames)
    _write_text(OUT_MD, build_markdown(rows))
    _write_text(CAPTION_MD, build_caption_text(rows))
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print(_rel(CAPTION_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
