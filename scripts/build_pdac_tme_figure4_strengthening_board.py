from __future__ import annotations

"""Build a Figure 4 strengthening board for the PDAC/TME showcase.

Author: RMTGuard development team
Date: 2026-05-11
Purpose: Convert existing PDAC/TME computational validation outputs into a
claim-bounded Figure 4 evidence board and manuscript panel blueprint.
Data source: Public PDAC/TME validation tables generated from GSE154778 and
GSE263733 plus manuscript-grade stability benchmark summaries.
Method notes: This script summarizes existing public-data evidence only. It
does not create mechanistic, clinical, prognosis, therapy-response, spatial, or
wet-lab validation claims.
"""

import csv
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DEEP_SUMMARY = ROOT / "results" / "pdac_tme" / "deep_validation" / "pdac_deep_validation_summary.tsv"
EXTERNAL_SIGNATURE = ROOT / "results" / "pdac_tme" / "deep_validation" / "pdac_external_signature_validation.tsv"
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
WORDING_FREEZE = ROOT / "docs" / "figure4_pdac_tme_wording_freeze.md"
AUTHOR_TRACKER = ROOT / "metadata" / "corresponding_author_signoff_tracker.tsv"

OUT_TSV = ROOT / "results" / "submission" / "pdac_tme_figure4_strengthening_board.tsv"
OUT_MD = ROOT / "docs" / "pdac_tme_figure4_strengthening_board.md"
OUT_BLUEPRINT = ROOT / "manuscript" / "figure4_strengthened_panel_blueprint.md"


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


def _summary_value(path: Path, summary_id: str, default: str = "missing") -> str:
    for row in _read_tsv(path):
        if row.get("summary_id") == summary_id:
            return row.get("value", default)
    return default


def _summary_status(path: Path, summary_id: str, default: str = "missing") -> str:
    for row in _read_tsv(path):
        if row.get("summary_id") == summary_id:
            return row.get("status", default)
    return default


def _method_ari(path: Path, method: str) -> float | None:
    for row in _read_tsv(path):
        if row.get("method") == method:
            try:
                return float(row.get("mean_pairwise_ari", "nan"))
            except ValueError:
                return None
    return None


def _best_non_rmt_ari(path: Path) -> tuple[str, float | None]:
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


def _author_ack_status() -> str:
    rows = _read_tsv(AUTHOR_TRACKER)
    if not rows:
        return "missing_tracker"
    confirmed = sum(1 for row in rows if row.get("status") == "confirmed")
    if confirmed == len(rows) and rows:
        return "all_confirmed"
    return f"pending_author_reply_{confirmed}_of_{len(rows)}"


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "evidence_layer",
        "current_status",
        "evidence_path",
        "key_result",
        "supports_methods_figure4",
        "supports_pdac_mechanism_claim",
        "allowed_wording",
        "missing_for_mechanism_upgrade",
        "next_action",
        "priority",
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
    significant_de = _summary_value(DEEP_SUMMARY, "significant_de_marker_rows")
    de_skipped = _summary_value(DEEP_SUMMARY, "de_skipped_tiny_clusters")
    public_support = _summary_value(
        DEEP_SUMMARY, "external_label_supported_primary_signatures"
    )
    cluster_support = _summary_value(
        DEEP_SUMMARY, "external_cluster_signature_supported_primary_signatures"
    )
    shared_signatures = _summary_value(DEEP_SUMMARY, "shared_top_signatures")
    hallmark_n = _summary_value(PATHWAY_SUMMARY, "significant_hallmark_pathways")
    reactome_n = _summary_value(PATHWAY_SUMMARY, "significant_reactome_pathways")
    atlas_rows = _summary_value(
        PATHWAY_SUMMARY, "atlas_supported_cluster_signature_rows"
    )

    pdac154_rmt = _method_ari(PDAC154_STABILITY, "rmtguard")
    pdac154_best_method, pdac154_best = _best_non_rmt_ari(PDAC154_STABILITY)
    pdac263_rmt = _method_ari(PDAC263_STABILITY, "rmtguard")
    pdac263_best_method, pdac263_best = _best_non_rmt_ari(PDAC263_STABILITY)

    stability_note = (
        f"GSE154778 RMTGuard ARI={pdac154_rmt:.3f} vs best baseline "
        f"{pdac154_best_method}={pdac154_best:.3f}; GSE263733 RMTGuard "
        f"ARI={pdac263_rmt:.3f} vs best baseline {pdac263_best_method}="
        f"{pdac263_best:.3f}."
        if None not in (pdac154_rmt, pdac154_best, pdac263_rmt, pdac263_best)
        else "PDAC stability summaries incomplete."
    )

    return [
        {
            "evidence_layer": "FDR_controlled_cluster_DE",
            "current_status": _summary_status(DEEP_SUMMARY, "significant_de_marker_rows"),
            "evidence_path": _rel(DEEP_SUMMARY),
            "key_result": (
                f"{significant_de} positive cluster-marker rows at BH-FDR <=0.05; "
                f"{de_skipped} tiny clusters skipped by rule."
            ),
            "supports_methods_figure4": "yes",
            "supports_pdac_mechanism_claim": "no",
            "allowed_wording": "RMTGuard clusters have interpretable marker programs in public PDAC/TME data.",
            "missing_for_mechanism_upgrade": "Independent biological validation of cell state function.",
            "next_action": "Use top FDR markers for panel heatmap/dotplot and source-data table.",
            "priority": "P0_main_figure",
        },
        {
            "evidence_layer": "external_signature_transfer",
            "current_status": "supported_with_partial_failures",
            "evidence_path": _rel(EXTERNAL_SIGNATURE),
            "key_result": (
                f"{public_support} primary signatures matched expected public labels; "
                f"{cluster_support} matched validation RMTGuard cluster signatures; "
                f"shared families: {shared_signatures}."
            ),
            "supports_methods_figure4": "yes",
            "supports_pdac_mechanism_claim": "no",
            "allowed_wording": "Selected ductal and myeloid marker families transfer to an external public PDAC/TME dataset.",
            "missing_for_mechanism_upgrade": "Prospective or orthogonal validation that the transferred state has a new biological function.",
            "next_action": "Show signature-transfer scores and mark non-transferring clusters explicitly.",
            "priority": "P0_main_figure",
        },
        {
            "evidence_layer": "rank_based_pathway_layer",
            "current_status": _summary_status(
                PATHWAY_SUMMARY, "significant_hallmark_pathways"
            ),
            "evidence_path": _rel(PATHWAY_SUMMARY),
            "key_result": (
                f"{hallmark_n} Hallmark and {reactome_n} Reactome pathways pass "
                "BH-FDR <=0.05 with positive rank effect."
            ),
            "supports_methods_figure4": "yes",
            "supports_pdac_mechanism_claim": "no",
            "allowed_wording": "The public-data clusters recover pathway-level programs consistent with PDAC/TME biology.",
            "missing_for_mechanism_upgrade": "Perturbation or functional evidence linking pathway activity to phenotype.",
            "next_action": "Use a compact pathway panel with low-specificity ribosomal/infection-proxy labels filtered.",
            "priority": "P0_main_figure",
        },
        {
            "evidence_layer": "published_atlas_marker_overlap",
            "current_status": _summary_status(
                PATHWAY_SUMMARY, "atlas_supported_cluster_signature_rows"
            ),
            "evidence_path": _rel(ATLAS_MAPPING),
            "key_result": f"{atlas_rows} cluster-signature rows have >=2 marker overlaps with cited PDAC atlas/reference marker families.",
            "supports_methods_figure4": "yes",
            "supports_pdac_mechanism_claim": "no",
            "allowed_wording": "Cluster identities are consistent with published PDAC atlas marker families.",
            "missing_for_mechanism_upgrade": "New validation beyond marker overlap, ideally spatial/protein/functional data.",
            "next_action": "Add a small atlas-overlap table beside marker/pathway panels.",
            "priority": "P0_main_figure",
        },
        {
            "evidence_layer": "subsampling_stability_context",
            "current_status": "caution_baseline_higher",
            "evidence_path": _rel(PDAC154_STABILITY) + ";" + _rel(PDAC263_STABILITY),
            "key_result": stability_note,
            "supports_methods_figure4": "yes_with_boundary",
            "supports_pdac_mechanism_claim": "no",
            "allowed_wording": "PDAC/TME is a bounded callability-aware use case, not a stability-superiority example.",
            "missing_for_mechanism_upgrade": "Stable biological validation across independent modalities, not only clustering ARI.",
            "next_action": "Report stability as context or supplement; do not claim Figure 4 proves RMTGuard is more stable than all baselines.",
            "priority": "P0_claim_boundary",
        },
        {
            "evidence_layer": "bounded_wording_freeze",
            "current_status": "pass_if_author_acknowledged",
            "evidence_path": _rel(WORDING_FREEZE),
            "key_result": f"Current author acknowledgement status: {_author_ack_status()}.",
            "supports_methods_figure4": "yes_after_author_ack",
            "supports_pdac_mechanism_claim": "no",
            "allowed_wording": "Bounded public-data PDAC/TME showcase of RMTGuard callability.",
            "missing_for_mechanism_upgrade": "Author-approved change in scientific route plus new validation evidence.",
            "next_action": "Obtain corresponding-author acknowledgement before sending any Nature Methods inquiry.",
            "priority": "P0_author_gate",
        },
        {
            "evidence_layer": "spatial_or_protein_validation",
            "current_status": "missing_not_required_for_methods_showcase",
            "evidence_path": "not_available",
            "key_result": "No spatial transcriptomics, IHC/IF, flow cytometry, or proteomic validation is present in the current public-data package.",
            "supports_methods_figure4": "not_required",
            "supports_pdac_mechanism_claim": "no",
            "allowed_wording": "Do not claim orthogonal spatial or protein validation.",
            "missing_for_mechanism_upgrade": "Spatial localization or protein-level validation in independent PDAC samples.",
            "next_action": "Keep out of the methods-paper claim; consider a separate biology paper only if such data become available.",
            "priority": "P1_optional_biology_route",
        },
        {
            "evidence_layer": "clinical_or_survival_validation",
            "current_status": "missing_not_required_for_methods_showcase",
            "evidence_path": "not_available",
            "key_result": "No prognosis, therapy-response, patient-level, or clinical outcome validation is present in the current Figure 4 package.",
            "supports_methods_figure4": "not_required",
            "supports_pdac_mechanism_claim": "no",
            "allowed_wording": "Do not claim prognosis, therapy-response, clinical validation, or patient-level utility.",
            "missing_for_mechanism_upgrade": "Pre-specified clinical cohorts, covariate adjustment, outcome definitions, and ethics review.",
            "next_action": "Do not add clinical wording to the RMTGuard manuscript without a separate validated analysis plan.",
            "priority": "P1_optional_biology_route",
        },
    ]


def _status_summary(rows: list[dict[str, str]]) -> tuple[str, str]:
    p0_rows = [row for row in rows if row["priority"].startswith("P0")]
    if all(row["supports_methods_figure4"].startswith("yes") for row in p0_rows):
        figure_status = "computational_methods_showcase_supported_with_limits"
    else:
        figure_status = "incomplete_methods_showcase"
    mechanism_status = "mechanism_upgrade_no_go_without_orthogonal_validation"
    return figure_status, mechanism_status


def build_markdown(rows: list[dict[str, str]]) -> str:
    figure_status, mechanism_status = _status_summary(rows)
    lines = [
        "# PDAC/TME Figure 4 Strengthening Board",
        "",
        "Generated by `python scripts/build_pdac_tme_figure4_strengthening_board.py`.",
        "",
        "## Mentor Decision",
        "",
        f"- Figure 4 route: `{figure_status}`.",
        f"- PDAC mechanism route: `{mechanism_status}`.",
        "- Recommendation: strengthen Figure 4 as a public-data biological application, but do not convert RMTGuard into a PDAC mechanism paper.",
        "",
        "## Evidence Board",
        "",
        "| Evidence layer | Status | Key result | Figure 4 support | Mechanism claim support | Next action |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['evidence_layer']} | `{row['current_status']}` | {row['key_result']} | "
            f"`{row['supports_methods_figure4']}` | `{row['supports_pdac_mechanism_claim']}` | "
            f"{row['next_action']} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "Allowed: RMTGuard produces interpretable, externally checkable, pathway/atlas-consistent cell-state calls in public PDAC/TME data.",
            "",
            "Not allowed: new PDAC mechanism, new CAF subtype discovery, prognosis, therapy-response prediction, clinical validation, patient-level utility, or spatial/protein validation.",
            "",
            "## Why We Still Need Author Confirmation",
            "",
            "The computational evidence is sufficient for a bounded methods-paper showcase, but the clinical and biological interpretation belongs to the corresponding authors. Their confirmation prevents the final manuscript from drifting into unsupported disease-mechanism language.",
            "",
            "## Machine-Readable Table",
            "",
            f"- `{_rel(OUT_TSV)}`",
        ]
    )
    return "\n".join(lines)


def build_blueprint(rows: list[dict[str, str]]) -> str:
    return f"""# Figure 4 Strengthened Panel Blueprint

Generated by `python scripts/build_pdac_tme_figure4_strengthening_board.py`.

## Figure Title

RMTGuard provides a bounded public-data PDAC/TME cell-state showcase with
marker, pathway, external-signature, and atlas-marker support.

## Proposed Main Panels

| Panel | Content | Source data | Claim |
| --- | --- | --- | --- |
| 4a | RMTGuard cluster/callability overview for GSE154778 and GSE263733 | `results/pdac_tme/showcase_summary.tsv`; `results/pdac_tme/deep_validation/pdac_cell_assignments.tsv` | Public-data use-case overview only. |
| 4b | FDR-controlled marker heatmap/dotplot for interpretable ductal, myeloid, T/NK, and CAF/fibroblast programs | `results/pdac_tme/deep_validation/pdac_de_markers_fdr.tsv` | Clusters have interpretable marker programs. |
| 4c | External signature transfer from GSE154778 to GSE263733, including matched and non-matched examples | `results/pdac_tme/deep_validation/pdac_external_signature_validation.tsv` | Selected marker families transfer to an external public dataset. |
| 4d | Hallmark/Reactome ranked pathway layer after filtering low-specificity labels | `results/pdac_tme/pathway_atlas_validation/pdac_pathway_rank_enrichment.tsv` | Clusters recover pathway-level PDAC/TME programs. |
| 4e | Published PDAC atlas marker overlap table | `results/pdac_tme/pathway_atlas_validation/pdac_atlas_marker_citation_mapping.tsv` | Cluster labels are consistent with cited public PDAC atlas marker families. |
| 4f | Boundary inset or supplement pointer: PDAC stability context and no clinical/mechanism claim | `results/manuscript_stability_benchmarks/pdac_gse154778_stability_summary.tsv`; `results/manuscript_stability_benchmarks/pdac_gse263733_stability_summary.tsv` | Callability-aware use case, not stability-superiority or mechanism proof. |

## Legend Wording Guard

Use: "public-data PDAC/TME showcase", "marker/pathway/atlas-consistent",
"external-signature support", "hypothesis-generating biological application".

Do not use: "new PDAC mechanism", "new CAF subtype", "clinical validation",
"predicts prognosis", "predicts therapy response", "patient-level utility",
"spatially validated", or "protein validated".

## Current Board

- Evidence board: `{_rel(OUT_MD)}`
- Machine-readable board: `{_rel(OUT_TSV)}`
"""


def main() -> int:
    rows = build_rows()
    _write_tsv(OUT_TSV, rows)
    _write_text(OUT_MD, build_markdown(rows))
    _write_text(OUT_BLUEPRINT, build_blueprint(rows))
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print(_rel(OUT_BLUEPRINT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
