#!/usr/bin/env python
"""Run claim-bounded PDAC/TME deep validation for the RMTGuard manuscript.

Author: RMTGuard development team
Date: 2026-05-10
Purpose: Generate cell-level RMTGuard assignments, FDR-controlled cluster
markers, marker-set enrichment, external signature transfer, and Figure 4
source data for the public PDAC/TME showcase.
Data source: data/processed/pdac_gse154778.h5ad and
data/processed/pdac_gse263733.h5ad.
Method notes: RMTGuard clustering is run with batch-aware residualization.
Differential expression uses Scanpy's Wilcoxon rank-sum implementation with
Benjamini-Hochberg adjusted p values. Marker-set enrichment uses a
hypergeometric over-representation test over curated canonical PDAC/pancreas
cell-state marker families; it is not a full MSigDB/Reactome GSEA replacement.
All claims remain public-data, non-clinical, and hypothesis-generating.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import hypergeom
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rmtguard import RMTGuardConfig  # noqa: E402
from rmtguard.scanpy_api import fit_anndata  # noqa: E402


PRIMARY_H5AD = ROOT / "data" / "processed" / "pdac_gse154778.h5ad"
VALIDATION_H5AD = ROOT / "data" / "processed" / "pdac_gse263733.h5ad"
OUT_DIR = ROOT / "results" / "pdac_tme" / "deep_validation"
FIGURE_SOURCE = ROOT / "results" / "figures" / "source_data" / "figure4_pdac_tme_deep_validation.tsv"
REPORT_MD = ROOT / "docs" / "pdac_tme_deep_validation.md"

ASSIGNMENTS = OUT_DIR / "pdac_cell_assignments.tsv"
DE_MARKERS = OUT_DIR / "pdac_de_markers_fdr.tsv"
ENRICHMENT = OUT_DIR / "pdac_marker_set_enrichment.tsv"
EXTERNAL_VALIDATION = OUT_DIR / "pdac_external_signature_validation.tsv"
SUMMARY = OUT_DIR / "pdac_deep_validation_summary.tsv"
MANIFEST = OUT_DIR / "pdac_deep_validation_manifest.tsv"


MARKER_SETS: dict[str, list[str]] = {
    "ductal_malignant_context": [
        "EPCAM",
        "KRT8",
        "KRT18",
        "KRT19",
        "KRT7",
        "KRT17",
        "MUC1",
        "SOX9",
        "TACSTD2",
        "CEACAM6",
    ],
    "immune_myeloid": [
        "LYZ",
        "LST1",
        "S100A8",
        "S100A9",
        "FCGR3A",
        "CD14",
        "CTSS",
        "TYROBP",
        "FCER1G",
        "MS4A7",
    ],
    "t_nk": [
        "CD3D",
        "CD3E",
        "TRAC",
        "CD2",
        "CD247",
        "NKG7",
        "GNLY",
        "GZMB",
        "PRF1",
        "CCL5",
    ],
    "b_plasma": [
        "MS4A1",
        "CD79A",
        "CD79B",
        "MZB1",
        "JCHAIN",
        "IGHG1",
        "IGKC",
        "SDC1",
        "CD74",
        "HLA-DRA",
    ],
    "caf_fibroblast": [
        "COL1A1",
        "COL1A2",
        "COL3A1",
        "DCN",
        "LUM",
        "ACTA2",
        "TAGLN",
        "FAP",
        "PDGFRA",
        "PDGFRB",
    ],
    "endothelial": [
        "PECAM1",
        "VWF",
        "KDR",
        "FLT1",
        "ENG",
        "CLDN5",
        "CDH5",
        "ESAM",
        "RAMP2",
        "PLVAP",
    ],
    "acinar": [
        "PRSS1",
        "PRSS2",
        "CPA1",
        "CTRB1",
        "CTRC",
        "REG1A",
        "PNLIP",
        "CLPS",
        "CELA3A",
        "AMY2A",
    ],
}

EXPECTED_LABEL_BY_SIGNATURE = {
    "ductal_malignant_context": "Ductal cell",
    "immune_myeloid": "Myeloid",
    "t_nk": "T cell",
    "b_plasma": "B cell",
    "caf_fibroblast": "Fibroblast",
    "endothelial": "Endothelial cell",
    "acinar": "Acinar cell",
}


@dataclass(frozen=True)
class DatasetResult:
    dataset_id: str
    adata: object
    log_adata: object
    labels: np.ndarray
    top_signature_by_cluster: dict[str, str]
    signature_scores: pd.DataFrame


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_tsv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
    tmp.replace(path)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _bh_adjust(p_values: Iterable[float]) -> list[float]:
    values = np.asarray([float(p) if np.isfinite(float(p)) else 1.0 for p in p_values], dtype=float)
    n = values.size
    if n == 0:
        return []
    order = np.argsort(values)
    ranked = values[order]
    adjusted = np.empty(n, dtype=float)
    running = 1.0
    for idx in range(n - 1, -1, -1):
        rank = idx + 1
        running = min(running, ranked[idx] * n / rank)
        adjusted[order[idx]] = min(running, 1.0)
    return adjusted.tolist()


def _gene_lookup(var_names: Iterable[str]) -> dict[str, str]:
    return {str(name).upper(): str(name) for name in var_names}


def _matched_genes(var_names: Iterable[str], genes: Iterable[str]) -> list[str]:
    lookup = _gene_lookup(var_names)
    out: list[str] = []
    seen: set[str] = set()
    for gene in genes:
        matched = lookup.get(str(gene).upper())
        if matched is not None and matched not in seen:
            out.append(matched)
            seen.add(matched)
    return out


def _matrix_col_mean(matrix) -> np.ndarray:
    if sparse.issparse(matrix):
        return np.asarray(matrix.mean(axis=1)).ravel()
    return np.asarray(matrix).mean(axis=1)


def _signature_scores(log_adata) -> pd.DataFrame:
    scores: dict[str, np.ndarray] = {}
    for signature, genes in MARKER_SETS.items():
        matched = _matched_genes(log_adata.var_names, genes)
        if matched:
            scores[f"score_{signature}"] = _matrix_col_mean(log_adata[:, matched].X)
        else:
            scores[f"score_{signature}"] = np.zeros(log_adata.n_obs, dtype=float)
    return pd.DataFrame(scores, index=log_adata.obs_names.astype(str))


def _copy_log_normalized(adata):
    import scanpy as sc

    log_adata = adata.copy()
    log_adata.X = log_adata.layers["counts"].copy() if "counts" in log_adata.layers else log_adata.X.copy()
    sc.pp.normalize_total(log_adata, target_sum=1e4)
    sc.pp.log1p(log_adata)
    return log_adata


def _fit_dataset(dataset_id: str, path: Path, force: bool) -> DatasetResult:
    import anndata as ad

    adata = ad.read_h5ad(path)
    config = RMTGuardConfig(
        batch_key="batch" if "batch" in adata.obs.columns else None,
        random_state=20260427,
        resolution_rule="graph_modularity",
        graph_resolution_grid=(1.0, 1.5, 2.0),
    )
    result = fit_anndata(
        adata,
        config=config,
        layer="counts" if "counts" in adata.layers else None,
        already_log_normalized=False,
        key="rmtguard_deep",
    )
    labels = np.asarray(result.cluster_labels).astype(str)
    adata.obs["rmtguard_deep_cluster"] = labels
    log_adata = _copy_log_normalized(adata)
    log_adata.obs["rmtguard_deep_cluster"] = labels
    scores = _signature_scores(log_adata)
    for col in scores.columns:
        log_adata.obs[col] = scores[col].to_numpy()
        adata.obs[col] = scores[col].to_numpy()
    top_by_cluster: dict[str, str] = {}
    for cluster in sorted(set(labels), key=lambda x: int(x) if str(x).isdigit() else str(x)):
        mask = labels == cluster
        cluster_means = scores.loc[mask].mean(axis=0)
        if cluster_means.empty:
            top_by_cluster[cluster] = "unassigned"
        else:
            top_by_cluster[cluster] = str(cluster_means.idxmax()).replace("score_", "")
    return DatasetResult(dataset_id, adata, log_adata, labels, top_by_cluster, scores)


def _assignment_rows(results: list[DatasetResult]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for res in results:
        obs = res.adata.obs
        for cell_id, row in obs.iterrows():
            cluster = str(row["rmtguard_deep_cluster"])
            out = {
                "dataset_id": res.dataset_id,
                "cell_id": str(cell_id),
                "sample_id": row.get("sample_id", ""),
                "batch": row.get("batch", ""),
                "tissue_type": row.get("tissue_type", ""),
                "public_label": row.get("cell", ""),
                "rmtguard_cluster": cluster,
                "top_signature": res.top_signature_by_cluster.get(cluster, "unassigned"),
            }
            for signature in MARKER_SETS:
                out[f"score_{signature}"] = float(row.get(f"score_{signature}", 0.0))
            rows.append(out)
    return rows


def _rank_genes_rows(res: DatasetResult, top_n: int, min_cells: int) -> list[dict[str, object]]:
    import scanpy as sc

    adata = res.log_adata.copy()
    adata.obs["rmtguard_deep_cluster"] = adata.obs["rmtguard_deep_cluster"].astype(str)
    counts = adata.obs["rmtguard_deep_cluster"].value_counts()
    groups = [
        str(group)
        for group, count in counts.items()
        if int(count) >= min_cells and int(adata.n_obs - count) >= min_cells
    ]
    skipped = [
        {
            "dataset_id": res.dataset_id,
            "cluster": str(group),
            "cluster_top_signature": res.top_signature_by_cluster.get(str(group), "unassigned"),
            "rank": 0,
            "gene": "",
            "score": float("nan"),
            "logfoldchange": float("nan"),
            "p_value": float("nan"),
            "p_adj_bh": float("nan"),
            "significant_fdr_0_05": False,
            "de_test_status": f"skipped_min_cells_lt_{min_cells}",
        }
        for group, count in counts.items()
        if str(group) not in groups
    ]
    if not groups:
        return skipped
    sc.tl.rank_genes_groups(
        adata,
        groupby="rmtguard_deep_cluster",
        groups=groups,
        method="wilcoxon",
        corr_method="benjamini-hochberg",
        pts=True,
    )
    result = adata.uns["rank_genes_groups"]
    result_groups = [str(group) for group in result["names"].dtype.names]
    rows: list[dict[str, object]] = skipped
    for group in result_groups:
        names = result["names"][group][:top_n]
        scores = result["scores"][group][:top_n]
        logfcs = result["logfoldchanges"][group][:top_n]
        pvals = result["pvals"][group][:top_n]
        padj = result["pvals_adj"][group][:top_n]
        cluster_signature = res.top_signature_by_cluster.get(group, "unassigned")
        for rank, gene in enumerate(names, start=1):
            rows.append(
                {
                    "dataset_id": res.dataset_id,
                    "cluster": group,
                    "cluster_top_signature": cluster_signature,
                    "rank": rank,
                    "gene": str(gene),
                    "score": float(scores[rank - 1]),
                    "logfoldchange": float(logfcs[rank - 1]),
                    "p_value": float(pvals[rank - 1]),
                    "p_adj_bh": float(padj[rank - 1]),
                    "significant_fdr_0_05": bool(float(padj[rank - 1]) <= 0.05),
                    "de_test_status": "tested",
                }
            )
    return rows


def _enrichment_rows(de_rows: list[dict[str, object]], universe: set[str], fdr: float, top_n: int) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], list[dict[str, object]]] = {}
    for row in de_rows:
        if row.get("de_test_status") != "tested":
            continue
        key = (str(row["dataset_id"]), str(row["cluster"]), str(row["cluster_top_signature"]))
        groups.setdefault(key, []).append(row)

    raw_rows: list[dict[str, object]] = []
    universe_upper = {gene.upper() for gene in universe}
    m = len(universe_upper)
    for (dataset_id, cluster, top_signature), rows in groups.items():
        sig = [row for row in rows if bool(row.get("significant_fdr_0_05")) and float(row.get("logfoldchange", 0.0)) > 0.0]
        if not sig:
            sig = rows[:top_n]
        selected = {str(row["gene"]).upper() for row in sig[:top_n]}
        n = len(selected)
        for marker_set, marker_genes in MARKER_SETS.items():
            marker_upper = {gene.upper() for gene in marker_genes} & universe_upper
            marker_n = len(marker_upper)
            overlap = sorted(selected & marker_upper)
            x = len(overlap)
            p_value = float(hypergeom.sf(x - 1, m, marker_n, n)) if x > 0 and n > 0 and marker_n > 0 else 1.0
            raw_rows.append(
                {
                    "dataset_id": dataset_id,
                    "cluster": cluster,
                    "cluster_top_signature": top_signature,
                    "marker_set": marker_set,
                    "universe_n": m,
                    "selected_gene_n": n,
                    "marker_gene_n": marker_n,
                    "overlap_n": x,
                    "overlap_genes": ",".join(overlap),
                    "p_value": p_value,
                    "enrichment_status": "pending",
                }
            )
    adjusted = _bh_adjust([float(row["p_value"]) for row in raw_rows])
    for row, padj in zip(raw_rows, adjusted):
        row["p_adj_bh"] = padj
        row["enrichment_status"] = "significant" if padj <= fdr and int(row["overlap_n"]) > 0 else "not_significant"
    return raw_rows


def _top_de_genes_by_primary_cluster(de_rows: list[dict[str, object]], top_n: int) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for row in de_rows:
        if row["dataset_id"] != "pdac_gse154778":
            continue
        if row.get("de_test_status") != "tested":
            continue
        cluster = str(row["cluster"])
        out.setdefault(cluster, [])
        if len(out[cluster]) < top_n and float(row["p_adj_bh"]) <= 0.05 and float(row["logfoldchange"]) > 0:
            out[cluster].append(str(row["gene"]))
    for row in de_rows:
        if row["dataset_id"] != "pdac_gse154778":
            continue
        if row.get("de_test_status") != "tested":
            continue
        cluster = str(row["cluster"])
        out.setdefault(cluster, [])
        if len(out[cluster]) < top_n and str(row["gene"]) not in out[cluster]:
            out[cluster].append(str(row["gene"]))
    return out


def _score_gene_set(log_adata, genes: list[str]) -> np.ndarray:
    matched = _matched_genes(log_adata.var_names, genes)
    if not matched:
        return np.zeros(log_adata.n_obs, dtype=float)
    return _matrix_col_mean(log_adata[:, matched].X)


def _external_validation_rows(primary: DatasetResult, validation: DatasetResult, de_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    signatures = _top_de_genes_by_primary_cluster(de_rows, top_n=30)
    rows: list[dict[str, object]] = []
    validation_obs = validation.log_adata.obs.copy()
    validation_obs["rmtguard_deep_cluster"] = validation.labels
    for primary_cluster, genes in signatures.items():
        primary_signature = primary.top_signature_by_cluster.get(primary_cluster, "unassigned")
        scores = _score_gene_set(validation.log_adata, genes)
        validation_obs["_transfer_score"] = scores
        by_label = (
            validation_obs.groupby("cell")["_transfer_score"].mean().sort_values(ascending=False)
            if "cell" in validation_obs.columns
            else pd.Series(dtype=float)
        )
        by_cluster = validation_obs.groupby("rmtguard_deep_cluster")["_transfer_score"].mean().sort_values(ascending=False)
        top_label = str(by_label.index[0]) if not by_label.empty else ""
        top_label_score = float(by_label.iloc[0]) if not by_label.empty else float("nan")
        top_cluster = str(by_cluster.index[0]) if not by_cluster.empty else ""
        top_cluster_score = float(by_cluster.iloc[0]) if not by_cluster.empty else float("nan")
        expected = EXPECTED_LABEL_BY_SIGNATURE.get(primary_signature, "")
        label_support = bool(expected and expected.lower() in top_label.lower())
        validation_cluster_signature = validation.top_signature_by_cluster.get(top_cluster, "unassigned")
        rows.append(
            {
                "primary_dataset_id": primary.dataset_id,
                "primary_cluster": primary_cluster,
                "primary_top_signature": primary_signature,
                "signature_gene_n": len(genes),
                "signature_genes": ",".join(genes),
                "validation_dataset_id": validation.dataset_id,
                "top_validation_public_label": top_label,
                "expected_public_label": expected,
                "public_label_support": label_support,
                "top_validation_public_label_score": top_label_score,
                "top_validation_cluster": top_cluster,
                "top_validation_cluster_signature": validation_cluster_signature,
                "top_validation_cluster_score": top_cluster_score,
                "signature_match_support": bool(primary_signature == validation_cluster_signature),
            }
        )
    return rows


def _summary_rows(
    results: list[DatasetResult],
    de_rows: list[dict[str, object]],
    enrichment_rows: list[dict[str, object]],
    external_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    tested_de_rows = [row for row in de_rows if row.get("de_test_status") == "tested"]
    skipped_de_rows = [row for row in de_rows if row.get("de_test_status") != "tested"]
    significant_de = [row for row in tested_de_rows if bool(row["significant_fdr_0_05"]) and float(row["logfoldchange"]) > 0]
    significant_enrichment = [row for row in enrichment_rows if row["enrichment_status"] == "significant"]
    external_label_support = [row for row in external_rows if bool(row["public_label_support"])]
    external_signature_support = [row for row in external_rows if bool(row["signature_match_support"])]
    shared_signatures = sorted(
        set(results[0].top_signature_by_cluster.values()) & set(results[1].top_signature_by_cluster.values())
        if len(results) >= 2
        else set()
    )
    status = "main_figure_candidate_partial_support"
    if significant_de and significant_enrichment and (external_label_support or external_signature_support):
        status = "main_figure_candidate_supported_with_limits"
    return [
        {
            "summary_id": "pdac_deep_validation_status",
            "status": status,
            "value": status,
            "notes": "Supports a bounded public biological use case; not a clinical or disease-mechanism proof.",
        },
        {
            "summary_id": "datasets_validated",
            "status": "pass",
            "value": ",".join(res.dataset_id for res in results),
            "notes": "Both public PDAC/TME datasets were analyzed from prepared h5ad files.",
        },
        {
            "summary_id": "significant_de_marker_rows",
            "status": "pass" if significant_de else "fail",
            "value": len(significant_de),
            "notes": "Rows with BH-FDR <=0.05 and positive log fold change.",
        },
        {
            "summary_id": "de_skipped_tiny_clusters",
            "status": "controlled_boundary",
            "value": len(skipped_de_rows),
            "notes": "Clusters below the pre-specified minimum cell count are not tested for DE.",
        },
        {
            "summary_id": "significant_marker_set_enrichments",
            "status": "pass" if significant_enrichment else "fail",
            "value": len(significant_enrichment),
            "notes": "Hypergeometric marker-set enrichments with BH-FDR <=0.05; not full pathway GSEA.",
        },
        {
            "summary_id": "external_label_supported_primary_signatures",
            "status": "pass" if external_label_support else "warning",
            "value": len(external_label_support),
            "notes": "Primary cluster DE signatures whose top validation public label matched the expected marker family.",
        },
        {
            "summary_id": "external_cluster_signature_supported_primary_signatures",
            "status": "pass" if external_signature_support else "warning",
            "value": len(external_signature_support),
            "notes": "Primary cluster DE signatures whose top validation RMTGuard cluster had the same marker family.",
        },
        {
            "summary_id": "shared_top_signatures",
            "status": "pass" if {"ductal_malignant_context", "immune_myeloid"} & set(shared_signatures) else "warning",
            "value": ",".join(shared_signatures),
            "notes": "Shared cluster-level marker families between primary and validation datasets.",
        },
        {
            "summary_id": "claim_boundary",
            "status": "controlled_boundary",
            "value": "public_data_nonclinical_hypothesis_generating",
            "notes": "Do not claim PDAC mechanism, prognosis, therapy, CAF discovery, or clinical validation.",
        },
    ]


def _figure_rows(
    summary_rows: list[dict[str, object]],
    de_rows: list[dict[str, object]],
    enrichment_rows: list[dict[str, object]],
    external_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in summary_rows:
        rows.append({"panel": "A_summary", **row})
    for row in de_rows[:80]:
        rows.append({"panel": "B_de_markers", **row})
    for row in enrichment_rows:
        if row["enrichment_status"] == "significant" or row["marker_set"] == row["cluster_top_signature"]:
            rows.append({"panel": "C_marker_enrichment", **row})
    for row in external_rows:
        rows.append({"panel": "D_external_signature_validation", **row})
    return rows


def _manifest_rows(force: bool) -> list[dict[str, object]]:
    paths = [PRIMARY_H5AD, VALIDATION_H5AD, ASSIGNMENTS, DE_MARKERS, ENRICHMENT, EXTERNAL_VALIDATION, SUMMARY, FIGURE_SOURCE]
    return [
        {
            "path": _rel(path),
            "exists": path.exists(),
            "sha256": _sha256(path) if path.exists() and path.is_file() else "",
            "force": force,
        }
        for path in paths
    ]


def _build_report(summary_rows: list[dict[str, object]]) -> str:
    status = next((row["value"] for row in summary_rows if row["summary_id"] == "pdac_deep_validation_status"), "unknown")
    lines = [
        "# PDAC/TME Deep Validation",
        "",
        "Generated by `python scripts/run_pdac_tme_deep_validation.py`.",
        "",
        "## Bottom Line",
        "",
        f"- Current status: `{status}`.",
        "- The analysis adds FDR-controlled marker DE, marker-set enrichment, external signature transfer, and Figure 4 source data.",
        "- Marker-set enrichment is a lightweight over-representation layer, not full MSigDB/Reactome GSEA.",
        "- Evidence boundary: public-data, non-clinical, hypothesis-generating.",
        "",
        "## Summary Table",
        "",
        "| Summary | Status | Value | Notes |",
        "| --- | --- | --- | --- |",
    ]
    for row in summary_rows:
        lines.append(f"| {row['summary_id']} | `{row['status']}` | {row['value']} | {row['notes']} |")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- Allowed: RMTGuard identifies reproducible immune/ductal-context marker structure in public PDAC/TME datasets with bounded external support.",
            "- Not allowed: new PDAC mechanism, clinical validation, prognosis, therapy response, patient-level reproducibility, or standalone CAF discovery.",
            "",
            "## Source Artifacts",
            "",
            f"- Cell assignments: `{_rel(ASSIGNMENTS)}`",
            f"- DE markers: `{_rel(DE_MARKERS)}`",
            f"- Marker-set enrichment: `{_rel(ENRICHMENT)}`",
            f"- External signature validation: `{_rel(EXTERNAL_VALIDATION)}`",
            f"- Summary: `{_rel(SUMMARY)}`",
            f"- Figure 4 source data: `{_rel(FIGURE_SOURCE)}`",
            f"- Manifest: `{_rel(MANIFEST)}`",
        ]
    )
    return "\n".join(lines)


def run(force: bool, top_de_n: int, enrichment_top_n: int, fdr: float, min_de_cells: int) -> None:
    import anndata  # noqa: F401

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = [
        _fit_dataset("pdac_gse154778", PRIMARY_H5AD, force=force),
        _fit_dataset("pdac_gse263733", VALIDATION_H5AD, force=force),
    ]
    assignment_rows = _assignment_rows(results)
    assignment_fields = [
        "dataset_id",
        "cell_id",
        "sample_id",
        "batch",
        "tissue_type",
        "public_label",
        "rmtguard_cluster",
        "top_signature",
        *[f"score_{sig}" for sig in MARKER_SETS],
    ]
    _write_tsv(ASSIGNMENTS, assignment_rows, assignment_fields)

    de_rows: list[dict[str, object]] = []
    for result in results:
        de_rows.extend(_rank_genes_rows(result, top_n=top_de_n, min_cells=min_de_cells))
    _write_tsv(
        DE_MARKERS,
        de_rows,
        [
            "dataset_id",
            "cluster",
            "cluster_top_signature",
            "rank",
            "gene",
            "score",
            "logfoldchange",
            "p_value",
            "p_adj_bh",
            "significant_fdr_0_05",
            "de_test_status",
        ],
    )

    universe = {str(gene) for result in results for gene in result.log_adata.var_names}
    enrichment_rows = _enrichment_rows(de_rows, universe=universe, fdr=fdr, top_n=enrichment_top_n)
    _write_tsv(
        ENRICHMENT,
        enrichment_rows,
        [
            "dataset_id",
            "cluster",
            "cluster_top_signature",
            "marker_set",
            "universe_n",
            "selected_gene_n",
            "marker_gene_n",
            "overlap_n",
            "overlap_genes",
            "p_value",
            "p_adj_bh",
            "enrichment_status",
        ],
    )

    external_rows = _external_validation_rows(results[0], results[1], de_rows)
    _write_tsv(
        EXTERNAL_VALIDATION,
        external_rows,
        [
            "primary_dataset_id",
            "primary_cluster",
            "primary_top_signature",
            "signature_gene_n",
            "signature_genes",
            "validation_dataset_id",
            "top_validation_public_label",
            "expected_public_label",
            "public_label_support",
            "top_validation_public_label_score",
            "top_validation_cluster",
            "top_validation_cluster_signature",
            "top_validation_cluster_score",
            "signature_match_support",
        ],
    )

    summary_rows = _summary_rows(results, de_rows, enrichment_rows, external_rows)
    _write_tsv(SUMMARY, summary_rows, ["summary_id", "status", "value", "notes"])

    figure_rows = _figure_rows(summary_rows, de_rows, enrichment_rows, external_rows)
    figure_fields = sorted({key for row in figure_rows for key in row.keys()})
    _write_tsv(FIGURE_SOURCE, figure_rows, figure_fields)

    _write_tsv(MANIFEST, _manifest_rows(force=force), ["path", "exists", "sha256", "force"])
    _write_text(REPORT_MD, _build_report(summary_rows))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PDAC/TME deep validation.")
    parser.add_argument("--force", action="store_true", help="Recompute outputs even if files exist.")
    parser.add_argument("--top-de-n", type=int, default=80, help="Top DE genes per cluster to export.")
    parser.add_argument("--enrichment-top-n", type=int, default=50, help="Top genes per cluster for enrichment fallback.")
    parser.add_argument("--fdr", type=float, default=0.05, help="BH-FDR threshold.")
    parser.add_argument("--min-de-cells", type=int, default=10, help="Minimum cells per cluster and comparator for DE.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run(
        force=args.force,
        top_de_n=args.top_de_n,
        enrichment_top_n=args.enrichment_top_n,
        fdr=args.fdr,
        min_de_cells=args.min_de_cells,
    )
    print(_rel(ASSIGNMENTS))
    print(_rel(DE_MARKERS))
    print(_rel(ENRICHMENT))
    print(_rel(EXTERNAL_VALIDATION))
    print(_rel(SUMMARY))
    print(_rel(FIGURE_SOURCE))
    print(_rel(REPORT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
