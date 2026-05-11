from __future__ import annotations

"""Build Figure 4 strengthened caption, Results text, and claim audit.

Author: RMTGuard development team
Date: 2026-05-11
Purpose: Synchronize the strengthened PDAC/TME Figure 4 with bounded
manuscript prose and a machine-readable evidence audit.
Data source: Public-data PDAC/TME Figure 4 source data and validation tables
generated from GSE154778 and GSE263733.
Method notes: This script summarizes existing evidence only. It does not add
mechanistic, clinical, prognosis, therapy-response, spatial, protein, or
patient-level validation claims.
"""

import csv
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BOARD_TSV = ROOT / "results" / "submission" / "pdac_tme_figure4_strengthening_board.tsv"
FIGURE_MANIFEST = (
    ROOT / "figures" / "manuscript" / "figure4_pdac_tme_strengthened_manifest.tsv"
)
FIGURE_SOURCE = (
    ROOT
    / "results"
    / "figures"
    / "source_data"
    / "figure4_pdac_tme_strengthened_source.tsv"
)
DEEP_SUMMARY = (
    ROOT / "results" / "pdac_tme" / "deep_validation" / "pdac_deep_validation_summary.tsv"
)
EXTERNAL_SIGNATURE = (
    ROOT
    / "results"
    / "pdac_tme"
    / "deep_validation"
    / "pdac_external_signature_validation.tsv"
)
PATHWAY_SUMMARY = (
    ROOT
    / "results"
    / "pdac_tme"
    / "pathway_atlas_validation"
    / "pdac_pathway_atlas_validation_summary.tsv"
)
ATLAS_MAPPING = (
    ROOT
    / "results"
    / "pdac_tme"
    / "pathway_atlas_validation"
    / "pdac_atlas_marker_citation_mapping.tsv"
)
PDAC154_STABILITY = (
    ROOT
    / "results"
    / "manuscript_stability_benchmarks"
    / "pdac_gse154778_stability_summary.tsv"
)
PDAC263_STABILITY = (
    ROOT
    / "results"
    / "manuscript_stability_benchmarks"
    / "pdac_gse263733_stability_summary.tsv"
)

OUT_CAPTION = ROOT / "manuscript" / "figure4_caption_strengthened_draft.md"
OUT_RESULTS = ROOT / "manuscript" / "results_figure4_strengthened_draft.md"
OUT_AUDIT_MD = ROOT / "docs" / "figure4_strengthened_text_audit.md"
OUT_AUDIT_TSV = ROOT / "results" / "submission" / "figure4_strengthened_text_audit.tsv"

FAMILY_LABELS = {
    "ductal_malignant_context": "ductal/malignant-context",
    "immune_myeloid": "immune-myeloid",
    "t_nk": "T/NK",
    "b_plasma": "B/plasma",
    "caf_fibroblast": "CAF/fibroblast",
    "endothelial": "endothelial",
}


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


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "claim_id",
        "manuscript_file",
        "claim_text",
        "evidence_path",
        "evidence_level",
        "status",
        "boundary",
        "notes",
    ]
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _summary_value(path: Path, summary_id: str, default: str = "missing") -> str:
    for row in _read_tsv(path):
        if row.get("summary_id") == summary_id:
            return row.get("value", default)
    return default


def _board_row(layer: str) -> dict[str, str]:
    for row in _read_tsv(BOARD_TSV):
        if row.get("evidence_layer") == layer:
            return row
    return {}


def _method_ari(path: Path, method: str) -> float | None:
    for row in _read_tsv(path):
        if row.get("method") == method:
            try:
                return float(row.get("mean_pairwise_ari", "nan"))
            except ValueError:
                return None
    return None


def _best_baseline(path: Path) -> tuple[str, float | None]:
    best_method = "missing"
    best_value: float | None = None
    for row in _read_tsv(path):
        method = row.get("method", "")
        if method.startswith("rmtguard"):
            continue
        try:
            value = float(row.get("mean_pairwise_ari", "nan"))
        except ValueError:
            continue
        if best_value is None or value > best_value:
            best_method = method
            best_value = value
    return best_method, best_value


def _format_ari(value: float | None) -> str:
    if value is None:
        return "missing"
    return f"{value:.3f}"


def _external_signature_counts() -> tuple[str, str, str]:
    public_support = _summary_value(
        DEEP_SUMMARY, "external_label_supported_primary_signatures"
    )
    cluster_support = _summary_value(
        DEEP_SUMMARY, "external_cluster_signature_supported_primary_signatures"
    )
    shared = _format_families(_summary_value(DEEP_SUMMARY, "shared_top_signatures"))
    return public_support, cluster_support, shared


def _format_family(value: str) -> str:
    return FAMILY_LABELS.get(value, value.replace("_", " "))


def _format_families(value: str) -> str:
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if not parts:
        return value
    return ", ".join(_format_family(part) for part in parts)


def _clean_key_result(value: str) -> str:
    cleaned = value
    for raw, label in FAMILY_LABELS.items():
        cleaned = cleaned.replace(raw, label)
    cleaned = cleaned.replace(",immune", ", immune")
    return cleaned


def _top_pathway_examples(limit: int = 3) -> list[str]:
    rows = [
        row
        for row in _read_tsv(FIGURE_SOURCE)
        if row.get("panel") == "D_pathway_layer"
        and row.get("status") == "manuscript_interpretable_candidate"
    ]
    rows = sorted(rows, key=lambda row: float(row.get("value", "0") or 0), reverse=True)
    examples = []
    for row in rows[:limit]:
        pathway = row.get("item", "")
        group = _format_family(row.get("group", ""))
        value = float(row.get("value", "0") or 0)
        examples.append(f"{pathway} in {group} (-log10 BH-FDR={value:.2f})")
    return examples


def _atlas_overlap_examples(limit: int = 3) -> list[str]:
    rows = []
    for row in _read_tsv(ATLAS_MAPPING):
        try:
            overlap = int(float(row.get("overlap_n", "0") or 0))
        except ValueError:
            overlap = 0
        if overlap >= 2:
            rows.append((overlap, row))
    rows = sorted(rows, key=lambda item: item[0], reverse=True)
    examples = []
    for overlap, row in rows[:limit]:
        dataset = row.get("dataset_id", "").replace("pdac_", "").upper()
        cluster = row.get("cluster", "")
        signature = _format_family(
            row.get("cluster_top_signature", row.get("signature", ""))
        )
        reference = row.get("reference", "public PDAC atlas/reference")
        examples.append(
            f"{dataset} cluster {cluster} {signature} ({overlap} markers, {reference})"
        )
    return examples


def _stability_sentence() -> str:
    pdac154_rmt = _method_ari(PDAC154_STABILITY, "rmtguard")
    pdac154_best_method, pdac154_best = _best_baseline(PDAC154_STABILITY)
    pdac263_rmt = _method_ari(PDAC263_STABILITY, "rmtguard")
    pdac263_best_method, pdac263_best = _best_baseline(PDAC263_STABILITY)
    return (
        "Subsampling stability was reported as a boundary rather than a "
        "superiority claim: GSE154778 RMTGuard mean pairwise ARI="
        f"{_format_ari(pdac154_rmt)} versus the strongest baseline "
        f"{pdac154_best_method}={_format_ari(pdac154_best)}, and GSE263733 "
        f"RMTGuard mean pairwise ARI={_format_ari(pdac263_rmt)} versus "
        f"{pdac263_best_method}={_format_ari(pdac263_best)}."
    )


def build_caption() -> str:
    marker_row = _board_row("FDR_controlled_cluster_DE")
    external_row = _board_row("external_signature_transfer")
    pathway_row = _board_row("rank_based_pathway_layer")
    atlas_row = _board_row("published_atlas_marker_overlap")
    stability_row = _board_row("subsampling_stability_context")
    forbidden = (
        "No panel is used to claim a new PDAC mechanism, a new CAF subtype, "
        "clinical validation, prognosis, therapy-response prediction, "
        "patient-level utility, spatial validation, or protein validation."
    )
    lines = [
        "**Figure 4 | Bounded public-data PDAC/TME application of RMTGuard.**",
        "(A) Evidence board summarizing the claim-bounded PDAC/TME application "
        "layers and the corresponding stop rules.",
        "(B) Marker-program heatmap for RMTGuard clusters in GSE154778 and "
        "GSE263733, highlighting ductal/malignant-context, myeloid, T/NK, "
        "B/plasma, CAF/fibroblast, and endothelial marker families.",
        f"(C) External signature transfer layer; {_clean_key_result(external_row.get('key_result', 'external signature transfer summarized'))}",
        f"(D) Rank-based pathway layer; {pathway_row.get('key_result', 'pathway enrichment summarized')}",
        f"(E) Published atlas-marker overlap layer; {atlas_row.get('key_result', 'atlas marker overlap summarized')}",
        f"(F) Stability boundary layer; {stability_row.get('key_result', _stability_sentence())}",
        f"Marker evidence: {marker_row.get('key_result', 'FDR-controlled marker evidence summarized')}",
        "All analyses use public scRNA-seq datasets and are presented as a "
        "hypothesis-generating methods showcase.",
        forbidden,
    ]
    return " ".join(line.strip() for line in lines)


def build_results_text() -> str:
    significant_de = _summary_value(DEEP_SUMMARY, "significant_de_marker_rows")
    skipped = _summary_value(DEEP_SUMMARY, "de_skipped_tiny_clusters")
    hallmark_n = _summary_value(PATHWAY_SUMMARY, "significant_hallmark_pathways")
    reactome_n = _summary_value(PATHWAY_SUMMARY, "significant_reactome_pathways")
    interpretable_n = _summary_value(
        PATHWAY_SUMMARY, "manuscript_interpretable_pathways"
    )
    atlas_rows = _summary_value(
        PATHWAY_SUMMARY, "atlas_supported_cluster_signature_rows"
    )
    public_support, cluster_support, shared = _external_signature_counts()
    pathway_examples = "; ".join(_top_pathway_examples())
    atlas_examples = "; ".join(_atlas_overlap_examples())

    return f"""# Results Draft: Figure 4 Strengthened PDAC/TME Application

Generated: {date.today().isoformat()}

## Bounded PDAC/TME Application

We next used public PDAC/TME scRNA-seq datasets as a bounded biological
application of RMTGuard. This analysis was designed to test whether callable
RMTGuard clusters could be interpreted with marker, pathway, external-signature,
and atlas-marker evidence, not to establish a new PDAC mechanism or clinical
biomarker.

FDR-controlled marker testing identified {significant_de} positive
cluster-marker rows at BH-FDR <=0.05, while {skipped} tiny clusters were skipped
by the pre-specified rule. Marker-score summaries separated interpretable
ductal/malignant-context, immune-myeloid, T/NK, B/plasma, CAF/fibroblast, and
endothelial programs across GSE154778 and GSE263733, supporting Figure 4 as a
cell-state interpretability showcase.

External-signature transfer provided additional public-data support but also
retained non-transferring cases as boundary evidence. In the external validation
layer, {public_support} primary signatures matched expected public labels,
{cluster_support} matched validation RMTGuard cluster signatures, and the
shared top marker families were {shared}. This supports selected ductal and
myeloid marker families as reproducible public-data signatures, while it does
not support a clinical-validation or mechanism-discovery claim.

The pathway and atlas-marker layers were used to add biological context without
overstating causality. Rank-based testing identified {hallmark_n} Hallmark and
{reactome_n} Reactome rows at BH-FDR <=0.05 with positive rank effect, of which
{interpretable_n} were retained as manuscript-interpretable after excluding
low-specificity labels. Representative pathway examples included {pathway_examples}.
Published atlas-marker comparison identified {atlas_rows} cluster-signature rows
with at least two marker overlaps, including {atlas_examples}. These results are
consistent with public PDAC/TME marker and pathway programs.

Importantly, the PDAC/TME application is not presented as a stability-superiority
result. {_stability_sentence()} We therefore use Figure 4 to demonstrate a
transparent, source-data-backed biological application with explicit boundaries:
no new PDAC mechanism, no new CAF subtype, no prognosis or therapy-response
claim, no patient-level clinical utility, and no spatial or protein validation
is claimed from the current evidence package.
"""


def build_audit_rows() -> list[dict[str, str]]:
    caption_file = _rel(OUT_CAPTION)
    results_file = _rel(OUT_RESULTS)
    return [
        {
            "claim_id": "fig4_caption_bounded_application",
            "manuscript_file": caption_file,
            "claim_text": "Figure 4 is a bounded public-data PDAC/TME application.",
            "evidence_path": _rel(BOARD_TSV),
            "evidence_level": "direct_summary",
            "status": "supported_with_limits",
            "boundary": "methods showcase only",
            "notes": "Does not claim mechanism or clinical validation.",
        },
        {
            "claim_id": "fig4_marker_interpretability",
            "manuscript_file": results_file,
            "claim_text": "FDR-controlled marker testing supports interpretable cluster programs.",
            "evidence_path": _rel(DEEP_SUMMARY),
            "evidence_level": "direct_result",
            "status": "supported",
            "boundary": "marker interpretation only",
            "notes": "Tiny clusters remain skipped by rule.",
        },
        {
            "claim_id": "fig4_external_signature_transfer",
            "manuscript_file": results_file,
            "claim_text": "Selected ductal and myeloid marker families transfer to GSE263733.",
            "evidence_path": _rel(EXTERNAL_SIGNATURE),
            "evidence_level": "direct_result",
            "status": "supported_with_partial_failures",
            "boundary": "public-data signature support only",
            "notes": "Non-transferring cases must remain visible.",
        },
        {
            "claim_id": "fig4_pathway_context",
            "manuscript_file": results_file,
            "claim_text": "Pathway rows provide PDAC/TME biological context.",
            "evidence_path": _rel(PATHWAY_SUMMARY),
            "evidence_level": "direct_result",
            "status": "supported",
            "boundary": "rank-based enrichment only",
            "notes": "No perturbation or functional causality.",
        },
        {
            "claim_id": "fig4_atlas_marker_overlap",
            "manuscript_file": results_file,
            "claim_text": "Cluster signatures overlap with cited public PDAC atlas markers.",
            "evidence_path": _rel(ATLAS_MAPPING),
            "evidence_level": "direct_result",
            "status": "supported",
            "boundary": "marker overlap only",
            "notes": "No orthogonal spatial or protein validation.",
        },
        {
            "claim_id": "fig4_stability_boundary",
            "manuscript_file": results_file,
            "claim_text": "PDAC/TME stability is disclosed as a boundary, not a superiority result.",
            "evidence_path": _rel(PDAC154_STABILITY) + ";" + _rel(PDAC263_STABILITY),
            "evidence_level": "direct_result",
            "status": "supported_as_boundary",
            "boundary": "no stability superiority claim",
            "notes": "Strongest baseline ARI remains higher on both PDAC/TME datasets.",
        },
        {
            "claim_id": "fig4_forbidden_claims",
            "manuscript_file": caption_file + ";" + results_file,
            "claim_text": "No mechanism, CAF-discovery, clinical, prognosis, therapy-response, spatial, protein, or patient-level claim.",
            "evidence_path": _rel(BOARD_TSV),
            "evidence_level": "claim_boundary",
            "status": "controlled_boundary",
            "boundary": "hard stop until orthogonal evidence exists",
            "notes": "Requires corresponding-author acknowledgement before presubmission use.",
        },
    ]


def build_audit_markdown(rows: list[dict[str, str]]) -> str:
    lines = [
        "# Figure 4 Strengthened Text Audit",
        "",
        "Generated by `python scripts/build_figure4_strengthened_text.py`.",
        "",
        "## Output Files",
        "",
        f"- Strengthened caption draft: `{_rel(OUT_CAPTION)}`",
        f"- Strengthened Results draft: `{_rel(OUT_RESULTS)}`",
        f"- Machine-readable audit: `{_rel(OUT_AUDIT_TSV)}`",
        f"- Figure manifest: `{_rel(FIGURE_MANIFEST)}`",
        f"- Figure source data: `{_rel(FIGURE_SOURCE)}`",
        "",
        "## Claim Audit",
        "",
        "| Claim ID | Status | Evidence | Boundary |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            + row["claim_id"]
            + " | `"
            + row["status"]
            + "` | `"
            + row["evidence_path"]
            + "` | "
            + row["boundary"]
            + " |"
        )
    lines.extend(
        [
            "",
            "## Editorial Boundary",
            "",
            "This text can support a Nature Methods-style biological application panel "
            "only after corresponding-author acknowledgement. It must not be used "
            "as evidence for a PDAC mechanism, clinical validation, prognosis, "
            "therapy response, patient-level utility, spatial validation, or "
            "protein validation.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    caption = build_caption()
    results_text = build_results_text()
    rows = build_audit_rows()
    _write_text(OUT_CAPTION, caption)
    _write_text(OUT_RESULTS, results_text)
    _write_tsv(OUT_AUDIT_TSV, rows)
    _write_text(OUT_AUDIT_MD, build_audit_markdown(rows))
    print(OUT_CAPTION)
    print(OUT_RESULTS)
    print(OUT_AUDIT_TSV)
    print(OUT_AUDIT_MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
