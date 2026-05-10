#!/usr/bin/env python
"""Build PDAC/TME dual-route preflight and execution runbooks.

Author: RMTGuard development team
Date: 2026-05-04
Purpose: Inspect the current public PDAC/TME artifacts and prepare both
possible manuscript routes: main-figure deepening and supplement demotion.
Data source: data/processed/pdac_gse154778.h5ad,
data/processed/pdac_gse263733.h5ad, and results/pdac_tme/*.tsv.
Method notes: This script is a preflight/report generator. It does not perform
differential expression, pathway enrichment, trajectory inference, or clinical
validation. Public human data are treated as de-identified public data; no
clinical decision claim is allowed from these outputs.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import anndata as ad


ROOT = Path(__file__).resolve().parents[1]
PRIMARY_H5AD = ROOT / "data" / "processed" / "pdac_gse154778.h5ad"
VALIDATION_H5AD = ROOT / "data" / "processed" / "pdac_gse263733.h5ad"
SHOWCASE_SUMMARY = ROOT / "results" / "pdac_tme" / "showcase_summary.tsv"
PRIMARY_MARKERS = ROOT / "results" / "pdac_tme" / "pdac_gse154778_cluster_marker_summary.tsv"
VALIDATION_MARKERS = ROOT / "results" / "pdac_tme" / "pdac_gse263733_cluster_marker_summary.tsv"
PRIMARY_DETAILS = ROOT / "results" / "pdac_tme" / "pdac_gse154778_rmtguard_details.json"
VALIDATION_DETAILS = ROOT / "results" / "pdac_tme" / "pdac_gse263733_rmtguard_details.json"
DEEP_VALIDATION_SUMMARY = (
    ROOT / "results" / "pdac_tme" / "deep_validation" / "pdac_deep_validation_summary.tsv"
)
DEEP_VALIDATION_DE = (
    ROOT / "results" / "pdac_tme" / "deep_validation" / "pdac_de_markers_fdr.tsv"
)
DEEP_VALIDATION_ENRICHMENT = (
    ROOT / "results" / "pdac_tme" / "deep_validation" / "pdac_marker_set_enrichment.tsv"
)
DEEP_VALIDATION_EXTERNAL = (
    ROOT / "results" / "pdac_tme" / "deep_validation" / "pdac_external_signature_validation.tsv"
)
PATHWAY_ATLAS_SUMMARY = (
    ROOT
    / "results"
    / "pdac_tme"
    / "pathway_atlas_validation"
    / "pdac_pathway_atlas_validation_summary.tsv"
)
PATHWAY_RANK_ENRICHMENT = (
    ROOT
    / "results"
    / "pdac_tme"
    / "pathway_atlas_validation"
    / "pdac_pathway_rank_enrichment.tsv"
)
ATLAS_MARKER_MAPPING = (
    ROOT
    / "results"
    / "pdac_tme"
    / "pathway_atlas_validation"
    / "pdac_atlas_marker_citation_mapping.tsv"
)

PREFLIGHT_TSV = ROOT / "results" / "submission" / "pdac_tme_dual_route_preflight.tsv"
RUNBOOK_TSV = ROOT / "results" / "submission" / "pdac_tme_dual_route_runbook.tsv"
PREFLIGHT_MD = ROOT / "docs" / "pdac_tme_dual_route_preflight.md"
RUNBOOK_MD = ROOT / "docs" / "pdac_tme_dual_route_runbook.md"


@dataclass(frozen=True)
class DatasetMeta:
    dataset_id: str
    path: Path
    exists: bool
    n_cells: int | None = None
    n_genes: int | None = None
    obs_columns: tuple[str, ...] = ()
    var_columns: tuple[str, ...] = ()
    layers: tuple[str, ...] = ()
    obsm_keys: tuple[str, ...] = ()


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


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def _dataset_meta(dataset_id: str, path: Path) -> DatasetMeta:
    if not path.exists():
        return DatasetMeta(dataset_id=dataset_id, path=path, exists=False)
    data = ad.read_h5ad(path, backed="r")
    return DatasetMeta(
        dataset_id=dataset_id,
        path=path,
        exists=True,
        n_cells=int(data.n_obs),
        n_genes=int(data.n_vars),
        obs_columns=tuple(str(col) for col in data.obs.columns),
        var_columns=tuple(str(col) for col in data.var.columns),
        layers=tuple(str(key) for key in data.layers.keys()),
        obsm_keys=tuple(str(key) for key in data.obsm.keys()),
    )


def _status(condition: bool, fail_status: str = "blocker") -> str:
    return "pass" if condition else fail_status


def _has_any(items: Iterable[str], choices: Iterable[str]) -> bool:
    item_set = set(items)
    return any(choice in item_set for choice in choices)


def build_preflight_rows() -> list[dict[str, str]]:
    primary = _dataset_meta("pdac_gse154778", PRIMARY_H5AD)
    validation = _dataset_meta("pdac_gse263733", VALIDATION_H5AD)
    showcase_rows = _read_tsv(SHOWCASE_SUMMARY)
    primary_marker_rows = _read_tsv(PRIMARY_MARKERS)
    validation_marker_rows = _read_tsv(VALIDATION_MARKERS)
    primary_details = _read_json(PRIMARY_DETAILS)
    validation_details = _read_json(VALIDATION_DETAILS)
    deep_summary = {row.get("summary_id", ""): row for row in _read_tsv(DEEP_VALIDATION_SUMMARY)}
    pathway_summary = {row.get("summary_id", ""): row for row in _read_tsv(PATHWAY_ATLAS_SUMMARY)}

    primary_obs = set(primary.obs_columns)
    validation_obs = set(validation.obs_columns)
    primary_signatures = {
        row.get("top_signature", "") for row in primary_marker_rows if row.get("top_signature")
    }
    validation_signatures = {
        row.get("top_signature", "") for row in validation_marker_rows if row.get("top_signature")
    }
    shared_signatures = sorted(primary_signatures & validation_signatures)
    validation_labels = validation_obs & {"cell", "cell_type", "cell_label", "annotation"}
    primary_labels = primary_obs & {"cell", "cell_type", "cell_label", "annotation"}

    rows = [
        {
            "check_id": "primary_public_h5ad",
            "status": _status(primary.exists),
            "route_implication": "required_for_both_routes",
            "evidence": f"{_rel(primary.path)} exists={primary.exists}; shape={primary.n_cells}x{primary.n_genes}.",
            "next_action": "Use as GSE154778 primary public showcase input.",
        },
        {
            "check_id": "validation_public_h5ad",
            "status": _status(validation.exists),
            "route_implication": "required_for_both_routes",
            "evidence": f"{_rel(validation.path)} exists={validation.exists}; shape={validation.n_cells}x{validation.n_genes}.",
            "next_action": "Use as GSE263733 external validation input.",
        },
        {
            "check_id": "count_layers_available",
            "status": _status("counts" in primary.layers and "counts" in validation.layers),
            "route_implication": "enables_DE_and_reproducibility",
            "evidence": f"primary_layers={list(primary.layers)}; validation_layers={list(validation.layers)}.",
            "next_action": "Use counts layer for DE and keep log-normalization/checkpoints separate.",
        },
        {
            "check_id": "sample_or_batch_covariates",
            "status": _status(
                _has_any(primary_obs, ["sample_id", "batch"]) and _has_any(validation_obs, ["sample_id", "batch", "patient_id"])
            ),
            "route_implication": "enables_batch_aware_and_split_stability",
            "evidence": f"primary_obs={sorted(primary_obs)}; validation_obs={sorted(validation_obs)}.",
            "next_action": "Run repeated split/stability by sample_id or patient_id; avoid patient-level clinical claims.",
        },
        {
            "check_id": "validation_public_labels",
            "status": _status(bool(validation_labels), "warning"),
            "route_implication": "supports_external_annotation_check",
            "evidence": f"validation_label_columns={sorted(validation_labels)}.",
            "next_action": "Use GSE263733 labels for coarse external validation only.",
        },
        {
            "check_id": "primary_public_labels",
            "status": _status(bool(primary_labels), "warning"),
            "route_implication": "limits_GSE154778_annotation_claims",
            "evidence": f"primary_label_columns={sorted(primary_labels)}.",
            "next_action": "Keep GSE154778 label-free unless a defensible public annotation source is added.",
        },
        {
            "check_id": "marker_signature_concordance",
            "status": _status({"ductal_malignant_context", "immune_myeloid"}.issubset(shared_signatures), "warning"),
            "route_implication": "supports_bounded_biological_showcase",
            "evidence": f"shared_top_signatures={shared_signatures}.",
            "next_action": "Use as descriptive marker evidence; do not call it mechanism discovery.",
        },
        {
            "check_id": "rmtguard_diagnostics_present",
            "status": _status(bool(primary_details) and bool(validation_details)),
            "route_implication": "supports_methods_diagnostics",
            "evidence": (
                "primary_keys="
                f"{sorted(primary_details.keys())}; validation_keys={sorted(validation_details.keys())}."
            ),
            "next_action": "Use diagnostics for MP/TW/embedding/resolution evidence, not clinical biology.",
        },
        {
            "check_id": "formal_de_results_present",
            "status": "pass"
            if DEEP_VALIDATION_DE.exists()
            and deep_summary.get("significant_de_marker_rows", {}).get("status") == "pass"
            else "blocker",
            "route_implication": "blocks_main_figure_claim",
            "evidence": (
                f"{_rel(DEEP_VALIDATION_DE)} exists; significant_DE_rows="
                f"{deep_summary.get('significant_de_marker_rows', {}).get('value', 'NA')}."
                if DEEP_VALIDATION_DE.exists()
                else "No FDR-controlled PDAC/TME differential-expression table is present yet."
            ),
            "next_action": "Use only FDR-controlled DE rows; do not test tiny clusters below the pre-specified minimum cell threshold.",
        },
        {
            "check_id": "pathway_gsea_results_present",
            "status": "pass"
            if PATHWAY_RANK_ENRICHMENT.exists()
            and pathway_summary.get("pdac_pathway_atlas_validation_status", {}).get("status")
            == "pathway_atlas_supported_with_limits"
            else "partial_pass"
            if DEEP_VALIDATION_ENRICHMENT.exists()
            and deep_summary.get("significant_marker_set_enrichments", {}).get("status") == "pass"
            else "blocker",
            "route_implication": "supports_main_figure_with_limits",
            "evidence": (
                f"{_rel(PATHWAY_RANK_ENRICHMENT)} exists; significant_hallmark_pathways="
                f"{pathway_summary.get('significant_hallmark_pathways', {}).get('value', 'NA')}; "
                f"significant_reactome_pathways={pathway_summary.get('significant_reactome_pathways', {}).get('value', 'NA')}; "
                f"manuscript_interpretable_pathways={pathway_summary.get('manuscript_interpretable_pathways', {}).get('value', 'NA')}. "
                "This is rank-based pathway enrichment, not Broad GSEA desktop permutation output."
                if PATHWAY_RANK_ENRICHMENT.exists()
                else (
                f"{_rel(DEEP_VALIDATION_ENRICHMENT)} exists; significant_marker_set_enrichments="
                f"{deep_summary.get('significant_marker_set_enrichments', {}).get('value', 'NA')}. "
                "This is marker-set over-representation, not full MSigDB/Reactome GSEA."
                if DEEP_VALIDATION_ENRICHMENT.exists()
                else "No PDAC/TME pathway/GSEA table is present yet."
                )
            ),
            "next_action": "Use only manuscript-interpretable pathway hits in main Figure 4; keep low-specificity translation/ribosomal hits in source data rather than main text.",
        },
        {
            "check_id": "published_atlas_marker_comparison_present",
            "status": "pass"
            if ATLAS_MARKER_MAPPING.exists()
            and pathway_summary.get("atlas_supported_cluster_signature_rows", {}).get("status") == "pass"
            else "partial_pass"
            if DEEP_VALIDATION_EXTERNAL.exists()
            else "blocker",
            "route_implication": "supports_main_figure_with_limits",
            "evidence": (
                f"{_rel(ATLAS_MARKER_MAPPING)} exists; atlas_supported_cluster_signature_rows="
                f"{pathway_summary.get('atlas_supported_cluster_signature_rows', {}).get('value', 'NA')}."
                if ATLAS_MARKER_MAPPING.exists()
                else (
                f"{_rel(DEEP_VALIDATION_EXTERNAL)} exists; external_label_supported_primary_signatures="
                f"{deep_summary.get('external_label_supported_primary_signatures', {}).get('value', 'NA')}. "
                "Published-atlas citation mapping still needs final literature-backed labels."
                if DEEP_VALIDATION_EXTERNAL.exists()
                else "No published PDAC atlas marker-comparison table is present yet."
                )
            ),
            "next_action": "Use citation-mapped marker overlaps as bounded atlas support; do not convert them into new mechanism claims.",
        },
        {
            "check_id": "trajectory_or_state_transition_present",
            "status": "optional_warning",
            "route_implication": "optional_for_main_figure",
            "evidence": "No trajectory/state-transition result is present; not mandatory unless the manuscript claims trajectories.",
            "next_action": "Add only if it sharpens a real biological use case; avoid decorative trajectory claims.",
        },
    ]
    return rows


def build_runbook_rows() -> list[dict[str, str]]:
    return [
        {
            "route_id": "deepen_as_main_figure",
            "step_order": "1",
            "step_name": "export_cluster_assignments",
            "purpose": "Create stable cell-level RMTGuard cluster/signature assignments for both PDAC datasets.",
            "expected_output": "results/pdac_tme/deep_validation/pdac_cell_assignments.tsv",
            "resume_rule": "Skip if output exists and checksum manifest is current.",
        },
        {
            "route_id": "deepen_as_main_figure",
            "step_order": "2",
            "step_name": "cluster_or_signature_DE",
            "purpose": "Run FDR-controlled marker differential expression using counts/log-normalized data with sample-aware sensitivity checks.",
            "expected_output": "results/pdac_tme/deep_validation/pdac_de_markers_fdr.tsv",
            "resume_rule": "Checkpoint per dataset and per cluster; write temp files then atomic rename.",
        },
        {
            "route_id": "deepen_as_main_figure",
            "step_order": "3",
            "step_name": "pathway_enrichment",
            "purpose": "Run rank-based Hallmark/Reactome enrichment for supported states with explicit gene universe and BH-FDR.",
            "expected_output": "results/pdac_tme/pathway_atlas_validation/pdac_pathway_rank_enrichment.tsv",
            "resume_rule": "Checkpoint per gene-set database and state.",
        },
        {
            "route_id": "deepen_as_main_figure",
            "step_order": "4",
            "step_name": "external_signature_validation",
            "purpose": "Transfer signatures from GSE154778 to GSE263733 and quantify label/state agreement.",
            "expected_output": "results/pdac_tme/deep_validation/pdac_external_signature_validation.tsv",
            "resume_rule": "Skip if signature hash and validation h5ad hash match manifest.",
        },
        {
            "route_id": "deepen_as_main_figure",
            "step_order": "5",
            "step_name": "atlas_marker_citation_mapping",
            "purpose": "Map supported cluster signatures to cited PDAC atlas/reference marker families.",
            "expected_output": "results/pdac_tme/pathway_atlas_validation/pdac_atlas_marker_citation_mapping.tsv",
            "resume_rule": "Regenerate after DE table or reference marker mapping changes.",
        },
        {
            "route_id": "deepen_as_main_figure",
            "step_order": "6",
            "step_name": "figure4_source_data",
            "purpose": "Generate source data and publication panels only for claims that pass the evidence gate.",
            "expected_output": "results/figures/source_data/figure4_pdac_tme_pathway_atlas_source.tsv",
            "resume_rule": "Regenerate only after source tables change.",
        },
        {
            "route_id": "demote_to_supplement",
            "step_order": "1",
            "step_name": "freeze_supplement_claim_boundary",
            "purpose": "Move PDAC/TME to a bounded public-use-case supplement with no disease-mechanism claim.",
            "expected_output": "docs/pdac_tme_supplement_claim_boundary.md",
            "resume_rule": "Regenerate after author decision only.",
        },
        {
            "route_id": "demote_to_supplement",
            "step_order": "2",
            "step_name": "screen_replacement_application",
            "purpose": "Find a stronger public application with reliable labels, perturbation, or orthogonal ground truth.",
            "expected_output": "results/submission/replacement_application_screen.tsv",
            "resume_rule": "One row per candidate dataset; skip evaluated candidates.",
        },
        {
            "route_id": "demote_to_supplement",
            "step_order": "3",
            "step_name": "rewrite_figure4_plan",
            "purpose": "Replace main Figure 4 with the strongest validated application and keep PDAC/TME as supplement.",
            "expected_output": "docs/figure4_replacement_plan.md",
            "resume_rule": "Run after replacement screen is approved.",
        },
    ]


def _overall_status(rows: list[dict[str, str]]) -> str:
    blockers = [row for row in rows if row["status"] == "blocker"]
    if blockers:
        return "ready_for_author_route_decision_but_main_figure_not_validated"
    partial = [row for row in rows if row["status"] == "partial_pass"]
    if partial:
        return "main_figure_candidate_supported_with_limits"
    warnings = [row for row in rows if row["status"] in {"warning", "optional_warning"}]
    if warnings:
        return "ready_with_warnings"
    return "ready"


def build_preflight_markdown(rows: list[dict[str, str]]) -> str:
    status = _overall_status(rows)
    blockers = [row for row in rows if row["status"] == "blocker"]
    warnings = [row for row in rows if row["status"] in {"warning", "optional_warning"}]
    lines = [
        "# PDAC/TME Dual-Route Preflight",
        "",
        "Generated by `python scripts/build_pdac_tme_dual_route_preflight.py`.",
        "",
        "## Bottom Line",
        "",
        f"- Overall status: `{status}`.",
        f"- Blocking main-figure validation gaps: `{len(blockers)}`.",
        f"- Warnings or optional gaps: `{len(warnings)}`.",
        "- Interpretation: the public datasets are available and usable, and the first-pass PDAC/TME deep-validation layer supports a bounded main-figure candidate with limits; it is still not a validated disease-mechanism figure.",
        "- Ethics/privacy boundary: public de-identified data only; no clinical decision or patient-level claim.",
        "",
        "## Preflight Table",
        "",
        "| Check | Status | Route implication | Evidence | Next action |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['check_id']} | `{row['status']}` | {row['route_implication']} | {row['evidence']} | {row['next_action']} |"
        )
    lines.extend(
        [
            "",
            "## Route Recommendation",
            "",
            "- If the target remains strict 20-50 JIF / Nature Methods: choose `PDAC/TME route: deepen as main figure`, then freeze bounded Figure 4 wording using the completed DE/signature/pathway/atlas evidence.",
            "- If the target is a faster defensible genomics software paper: choose `PDAC/TME route: demote to supplement`, then screen a stronger main application.",
            "",
            "## Manual Author Reply Needed",
            "",
            "```text",
            "PDAC/TME route: deepen as main figure",
            "```",
            "",
            "or",
            "",
            "```text",
            "PDAC/TME route: demote to supplement",
            "```",
        ]
    )
    return "\n".join(lines)


def build_runbook_markdown(rows: list[dict[str, str]]) -> str:
    lines = [
        "# PDAC/TME Dual-Route Runbook",
        "",
        "Generated by `python scripts/build_pdac_tme_dual_route_preflight.py`.",
        "",
        "## Purpose",
        "",
        "This runbook keeps both manuscript routes ready while the final author decision is pending. The first-pass deep-validation layer supports a bounded main-figure candidate with limits, but it does not mark PDAC/TME as a validated disease-mechanism figure.",
        "",
        "## Runbook Table",
        "",
        "| Route | Step | Name | Purpose | Expected output | Resume rule |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['route_id']} | {row['step_order']} | {row['step_name']} | {row['purpose']} | `{row['expected_output']}` | {row['resume_rule']} |"
        )
    lines.extend(
        [
            "",
            "## Execution Boundary",
            "",
            "- The first-pass deep-validation workflow has been run; do not finalize main-figure wording until authors confirm the route and full pathway/atlas support is added.",
            "- Do not write PDAC/TME mechanism, clinical, prognosis, therapy, CAF-discovery, or patient-level claims from the current public-data layer.",
            "- All long-running downstream workflows must be resumable, idempotent, and checkpointed.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    preflight_rows = build_preflight_rows()
    runbook_rows = build_runbook_rows()
    _write_tsv(
        PREFLIGHT_TSV,
        preflight_rows,
        ["check_id", "status", "route_implication", "evidence", "next_action"],
    )
    _write_tsv(
        RUNBOOK_TSV,
        runbook_rows,
        ["route_id", "step_order", "step_name", "purpose", "expected_output", "resume_rule"],
    )
    _write_text(PREFLIGHT_MD, build_preflight_markdown(preflight_rows))
    _write_text(RUNBOOK_MD, build_runbook_markdown(runbook_rows))
    print(_rel(PREFLIGHT_TSV))
    print(_rel(PREFLIGHT_MD))
    print(_rel(RUNBOOK_TSV))
    print(_rel(RUNBOOK_MD))
    print(f"overall_status\t{_overall_status(preflight_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
