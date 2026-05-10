#!/usr/bin/env python
"""Run PDAC/TME pathway and atlas-marker validation.

Author: RMTGuard development team
Date: 2026-05-10
Purpose: Upgrade the public PDAC/TME showcase from marker-set smoke evidence to
rank-based Hallmark/Reactome pathway evidence and literature-backed atlas marker
mapping.
Data source: results/pdac_tme/deep_validation/pdac_de_markers_fdr.tsv and
public MSigDB 2025.1.Hs GMT files downloaded into data/external/gene_sets/.
Method notes: Pathway testing uses a rank-based Mann-Whitney/Wilcoxon gene-set
test on signed cluster marker scores with Benjamini-Hochberg FDR correction.
This is a lightweight, reproducible preranked pathway enrichment layer; it is
not the Broad GSEA desktop permutation implementation. All claims remain
public-data, non-clinical, and hypothesis-generating.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu


ROOT = Path(__file__).resolve().parents[1]
DE_MARKERS = ROOT / "results" / "pdac_tme" / "deep_validation" / "pdac_de_markers_fdr.tsv"
OUT_DIR = ROOT / "results" / "pdac_tme" / "pathway_atlas_validation"
GENE_SET_DIR = ROOT / "data" / "external" / "gene_sets"

PATHWAY_ENRICHMENT = OUT_DIR / "pdac_pathway_rank_enrichment.tsv"
ATLAS_MAPPING = OUT_DIR / "pdac_atlas_marker_citation_mapping.tsv"
SUMMARY = OUT_DIR / "pdac_pathway_atlas_validation_summary.tsv"
MANIFEST = OUT_DIR / "pdac_pathway_atlas_validation_manifest.tsv"
FIGURE_SOURCE = (
    ROOT / "results" / "figures" / "source_data" / "figure4_pdac_tme_pathway_atlas_source.tsv"
)
REPORT_MD = ROOT / "docs" / "pdac_tme_pathway_atlas_validation.md"


@dataclass(frozen=True)
class GeneSetResource:
    collection: str
    filename: str
    url: str
    source_note: str


GENE_SET_RESOURCES = [
    GeneSetResource(
        collection="hallmark",
        filename="h.all.v2025.1.Hs.symbols.gmt",
        url="https://data.broadinstitute.org/gsea-msigdb/msigdb/release/2025.1.Hs/h.all.v2025.1.Hs.symbols.gmt",
        source_note="MSigDB 2025.1.Hs Hallmark collection, H gene symbols.",
    ),
    GeneSetResource(
        collection="reactome",
        filename="c2.cp.reactome.v2025.1.Hs.symbols.gmt",
        url="https://data.broadinstitute.org/gsea-msigdb/msigdb/release/2025.1.Hs/c2.cp.reactome.v2025.1.Hs.symbols.gmt",
        source_note="MSigDB 2025.1.Hs curated Reactome subset, C2:CP:Reactome gene symbols.",
    ),
]


ATLAS_MARKER_REFERENCES = [
    {
        "signature": "ductal_malignant_context",
        "expected_cluster_label": "ductal/malignant-context",
        "reference": "Peng et al., Cell Research 2019",
        "doi": "10.1038/s41422-019-0195-y",
        "url": "https://www.nature.com/articles/s41422-019-0195-y",
        "marker_genes": "KRT19;KRT7;TSPAN8;MUC1;CEACAM6;SOX9;EPCAM;MMP7",
        "evidence_note": "PDAC scRNA-seq atlas used ductal markers and reported malignant ductal context markers.",
    },
    {
        "signature": "caf_fibroblast",
        "expected_cluster_label": "CAF/fibroblast",
        "reference": "Elyada et al., Cancer Discovery 2019",
        "doi": "10.1158/2159-8290.CD-19-0094",
        "url": "https://doi.org/10.1158/2159-8290.CD-19-0094",
        "marker_genes": "COL1A1;COL1A2;DCN;LUM;ACTA2;TAGLN;FAP;PDGFRA;PDGFRB;CD74",
        "evidence_note": "Cross-species PDAC scRNA-seq defined CAF heterogeneity including myCAF/iCAF/apCAF contexts.",
    },
    {
        "signature": "immune_myeloid",
        "expected_cluster_label": "myeloid/macrophage",
        "reference": "Peng et al., Cell Research 2019",
        "doi": "10.1038/s41422-019-0195-y",
        "url": "https://www.nature.com/articles/s41422-019-0195-y",
        "marker_genes": "AIF1;CD14;CD68;LYZ;LST1;FCGR3A;S100A8;S100A9;CTSS;TYROBP",
        "evidence_note": "The atlas used macrophage/myeloid markers for PDAC immune cell typing.",
    },
    {
        "signature": "t_nk",
        "expected_cluster_label": "T/NK cell",
        "reference": "Oh et al., Nature Communications 2023",
        "doi": "10.1038/s41467-023-40895-6",
        "url": "https://www.nature.com/articles/s41467-023-40895-6",
        "marker_genes": "CD3D;CD3E;CD4;CD8A;TRAC;CD2;NKG7;GNLY;GZMB;PRF1",
        "evidence_note": "Integrated PDAC TME atlas describes immune and stromal landscapes across public studies.",
    },
    {
        "signature": "b_plasma",
        "expected_cluster_label": "B/plasma cell",
        "reference": "Peng et al., Cell Research 2019",
        "doi": "10.1038/s41422-019-0195-y",
        "url": "https://www.nature.com/articles/s41422-019-0195-y",
        "marker_genes": "MS4A1;CD79A;CD79B;CD52;MZB1;JCHAIN;IGHG1;IGKC;SDC1;CD74",
        "evidence_note": "The atlas used B-cell markers and supports coarse B/plasma identity mapping.",
    },
    {
        "signature": "endothelial",
        "expected_cluster_label": "endothelial cell",
        "reference": "Peng et al., Cell Research 2019",
        "doi": "10.1038/s41422-019-0195-y",
        "url": "https://www.nature.com/articles/s41422-019-0195-y",
        "marker_genes": "CDH5;PLVAP;VWF;CLDN5;PECAM1;KDR;FLT1;ENG;ESAM;RAMP2",
        "evidence_note": "The atlas used canonical endothelial markers for PDAC cell typing.",
    },
    {
        "signature": "acinar",
        "expected_cluster_label": "acinar cell",
        "reference": "Peng et al., Cell Research 2019",
        "doi": "10.1038/s41422-019-0195-y",
        "url": "https://www.nature.com/articles/s41422-019-0195-y",
        "marker_genes": "PRSS1;CTRB1;CTRB2;REG1B;CPA1;CTRC;PNLIP;CLPS;CELA3A;AMY2A",
        "evidence_note": "The atlas used acinar markers for pancreatic cell typing.",
    },
]

LOW_SPECIFICITY_PATHWAY_KEYWORDS = [
    "TRANSLATION",
    "RIBOSOM",
    "NONSENSE_MEDIATED_DECAY",
    "SRP_DEPENDENT",
    "INFLUENZA",
    "VIRAL",
    "INFECTIOUS_DISEASE",
    "SARS",
]

MANUSCRIPT_PRIORITY_PATHWAY_KEYWORDS = [
    "TNFA",
    "NFKB",
    "EPITHELIAL_MESENCHYMAL",
    "HYPOXIA",
    "ANGIOGENESIS",
    "APOPTOSIS",
    "P53",
    "INTERFERON",
    "INFLAMMATORY",
    "CYTOKINE",
    "CHEMOKINE",
    "TCR",
    "ANTIGEN",
    "MHC",
    "EXTRACELLULAR_MATRIX",
    "COLLAGEN",
    "INTEGRIN",
    "JUNCTION",
]


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


def _bh_adjust(p_values: Iterable[float]) -> list[float]:
    values = np.asarray(
        [float(p) if np.isfinite(float(p)) else 1.0 for p in p_values], dtype=float
    )
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


def _download_atomic(resource: GeneSetResource, force: bool, max_tries: int = 5) -> Path:
    GENE_SET_DIR.mkdir(parents=True, exist_ok=True)
    target = GENE_SET_DIR / resource.filename
    ok = target.with_suffix(target.suffix + ".ok")
    if target.exists() and ok.exists() and not force:
        return target
    tmp = target.with_suffix(target.suffix + ".tmp")
    last_error: Exception | None = None
    for attempt in range(1, max_tries + 1):
        try:
            with urllib.request.urlopen(resource.url, timeout=60) as response:
                with tmp.open("wb") as handle:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
            tmp.replace(target)
            ok.write_text(_sha256(target) + "\n", encoding="utf-8")
            return target
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if tmp.exists():
                tmp.unlink()
            time.sleep(min(2**attempt, 30))
    raise RuntimeError(f"Failed to download {resource.url}: {last_error}")


def _parse_gmt(path: Path, collection: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            genes = sorted({gene.upper() for gene in parts[2:] if gene})
            rows.append(
                {
                    "collection": collection,
                    "pathway_name": parts[0],
                    "description": parts[1],
                    "genes": genes,
                }
            )
    return rows


def _ranked_cluster_tables(de: pd.DataFrame) -> dict[tuple[str, str, str], pd.DataFrame]:
    tested = de[de["de_test_status"].astype(str) == "tested"].copy()
    tested = tested[tested["gene"].astype(str).str.len() > 0]
    for col in ["score", "logfoldchange", "p_value", "p_adj_bh", "rank"]:
        tested[col] = pd.to_numeric(tested[col], errors="coerce")
    tested = tested[np.isfinite(tested["score"]) | np.isfinite(tested["logfoldchange"])]
    fallback = np.sign(tested["logfoldchange"].fillna(0.0)) * (
        -np.log10(tested["p_value"].fillna(1.0).clip(lower=1e-300))
    )
    tested["ranking_metric"] = tested["score"].where(np.isfinite(tested["score"]), fallback)
    tested["gene_upper"] = tested["gene"].astype(str).str.upper()
    out: dict[tuple[str, str, str], pd.DataFrame] = {}
    group_cols = ["dataset_id", "cluster", "cluster_top_signature"]
    for key, group in tested.groupby(group_cols, dropna=False):
        ranked = (
            group.sort_values(["ranking_metric", "rank"], ascending=[False, True])
            .drop_duplicates("gene_upper", keep="first")
            .reset_index(drop=True)
        )
        out[(str(key[0]), str(key[1]), str(key[2]))] = ranked
    return out


def _pathway_priority_label(pathway_name: str) -> str:
    name = pathway_name.upper()
    if any(keyword in name for keyword in LOW_SPECIFICITY_PATHWAY_KEYWORDS):
        return "low_specificity_housekeeping_or_infection_proxy"
    if any(keyword in name for keyword in MANUSCRIPT_PRIORITY_PATHWAY_KEYWORDS):
        return "manuscript_interpretable_candidate"
    return "background_significant_pathway"


def _pathway_rows(
    ranked_tables: dict[tuple[str, str, str], pd.DataFrame],
    gene_sets: list[dict[str, object]],
    min_size: int,
    max_size: int,
    fdr: float,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for (dataset_id, cluster, signature), ranked in ranked_tables.items():
        ranked_genes = set(ranked["gene_upper"])
        metrics = ranked.set_index("gene_upper")["ranking_metric"].astype(float)
        if len(metrics) < min_size * 2:
            continue
        for gene_set in gene_sets:
            overlap = [gene for gene in gene_set["genes"] if gene in ranked_genes]
            if len(overlap) < min_size or len(overlap) > max_size:
                continue
            outside_n = len(metrics) - len(overlap)
            if outside_n < min_size:
                continue
            in_values = metrics.loc[overlap].to_numpy(dtype=float)
            out_values = metrics.drop(index=overlap).to_numpy(dtype=float)
            if np.nanstd(np.concatenate([in_values, out_values])) == 0:
                p_value = 1.0
                auc_delta = 0.0
            else:
                test = mannwhitneyu(in_values, out_values, alternative="greater")
                p_value = float(test.pvalue)
                auc_delta = float(test.statistic / (len(in_values) * len(out_values)) - 0.5)
            rows.append(
                {
                    "dataset_id": dataset_id,
                    "cluster": cluster,
                    "cluster_top_signature": signature,
                    "collection": gene_set["collection"],
                    "pathway_name": gene_set["pathway_name"],
                    "pathway_size_in_ranked_genes": len(overlap),
                    "ranked_gene_n": len(metrics),
                    "mean_metric_in_pathway": float(np.nanmean(in_values)),
                    "mean_metric_background": float(np.nanmean(out_values)),
                    "auc_delta": auc_delta,
                    "p_value": p_value,
                    "p_adj_bh": 1.0,
                    "significant_fdr_0_05": False,
                    "leading_overlap_genes": ";".join(overlap[:30]),
                }
            )
    adjusted = _bh_adjust(row["p_value"] for row in rows)
    for row, p_adj in zip(rows, adjusted):
        row["p_adj_bh"] = p_adj
        row["significant_fdr_0_05"] = bool(p_adj <= fdr and float(row["auc_delta"]) > 0)
        row["pathway_priority_label"] = _pathway_priority_label(str(row["pathway_name"]))
    rows.sort(
        key=lambda row: (
            str(row["dataset_id"]),
            str(row["cluster"]),
            str(row["collection"]),
            float(row["p_adj_bh"]),
            -float(row["auc_delta"]),
        )
    )
    return rows


def _atlas_rows(de: pd.DataFrame, fdr: float) -> list[dict[str, object]]:
    tested = de[de["de_test_status"].astype(str) == "tested"].copy()
    tested["p_adj_bh"] = pd.to_numeric(tested["p_adj_bh"], errors="coerce")
    tested["logfoldchange"] = pd.to_numeric(tested["logfoldchange"], errors="coerce")
    tested["gene_upper"] = tested["gene"].astype(str).str.upper()
    tested = tested[(tested["p_adj_bh"] <= fdr) & (tested["logfoldchange"] > 0)]
    rows: list[dict[str, object]] = []
    group_cols = ["dataset_id", "cluster", "cluster_top_signature"]
    for key, group in tested.groupby(group_cols, dropna=False):
        dataset_id, cluster, signature = str(key[0]), str(key[1]), str(key[2])
        sig_genes = set(group["gene_upper"])
        for ref in ATLAS_MARKER_REFERENCES:
            if ref["signature"] != signature:
                continue
            ref_genes = {gene.upper() for gene in str(ref["marker_genes"]).split(";")}
            overlap = sorted(sig_genes & ref_genes)
            rows.append(
                {
                    "dataset_id": dataset_id,
                    "cluster": cluster,
                    "cluster_top_signature": signature,
                    "expected_cluster_label": ref["expected_cluster_label"],
                    "reference": ref["reference"],
                    "doi": ref["doi"],
                    "url": ref["url"],
                    "reference_marker_genes": ref["marker_genes"],
                    "overlap_marker_genes": ";".join(overlap),
                    "overlap_n": len(overlap),
                    "support_status": "supported" if len(overlap) >= 2 else "weak_or_not_detected",
                    "evidence_note": ref["evidence_note"],
                }
            )
    rows.sort(key=lambda row: (str(row["dataset_id"]), str(row["cluster"]), -int(row["overlap_n"])))
    return rows


def _summary_rows(
    pathway_rows: list[dict[str, object]],
    atlas_rows: list[dict[str, object]],
    resources: list[GeneSetResource],
) -> list[dict[str, object]]:
    significant = [row for row in pathway_rows if row["significant_fdr_0_05"]]
    significant_hallmark = [row for row in significant if row["collection"] == "hallmark"]
    significant_reactome = [row for row in significant if row["collection"] == "reactome"]
    priority_pathways = [
        row
        for row in significant
        if row.get("pathway_priority_label") == "manuscript_interpretable_candidate"
    ]
    supported_atlas = [row for row in atlas_rows if row["support_status"] == "supported"]
    shared_collections = sorted({row["collection"] for row in significant})
    status = (
        "pathway_atlas_supported_with_limits"
        if significant_hallmark and significant_reactome and len(supported_atlas) >= 3
        else "pathway_atlas_incomplete"
    )
    return [
        {
            "summary_id": "pdac_pathway_atlas_validation_status",
            "status": status,
            "value": status,
            "notes": "Supports pathway/atlas layer with public data limits; not clinical or mechanistic proof.",
        },
        {
            "summary_id": "significant_hallmark_pathways",
            "status": "pass" if significant_hallmark else "warning",
            "value": len(significant_hallmark),
            "notes": "BH-FDR <=0.05 and positive pathway rank effect.",
        },
        {
            "summary_id": "significant_reactome_pathways",
            "status": "pass" if significant_reactome else "warning",
            "value": len(significant_reactome),
            "notes": "MSigDB C2 Reactome subset; BH-FDR <=0.05 and positive pathway rank effect.",
        },
        {
            "summary_id": "atlas_supported_cluster_signature_rows",
            "status": "pass" if len(supported_atlas) >= 3 else "warning",
            "value": len(supported_atlas),
            "notes": "Rows with >=2 overlap markers against a cited PDAC atlas/reference marker family.",
        },
        {
            "summary_id": "manuscript_interpretable_pathways",
            "status": "pass" if priority_pathways else "warning",
            "value": len(priority_pathways),
            "notes": "Significant pathways not dominated by low-specificity translation/ribosomal/infection-proxy labels.",
        },
        {
            "summary_id": "gene_set_collections_with_signal",
            "status": "pass" if shared_collections else "warning",
            "value": ",".join(shared_collections),
            "notes": "Collections with at least one significant pathway.",
        },
        {
            "summary_id": "gene_set_resources",
            "status": "controlled_boundary",
            "value": ";".join(f"{res.collection}:{res.filename}" for res in resources),
            "notes": "GMT files are downloaded on demand and not committed as raw external resources.",
        },
        {
            "summary_id": "claim_boundary",
            "status": "controlled_boundary",
            "value": "public_data_nonclinical_hypothesis_generating_rank_based_pathway_layer",
            "notes": "Do not claim prognosis, therapy response, clinical validation, or new PDAC mechanism.",
        },
    ]


def _manifest_rows(resources: list[GeneSetResource], force_download: bool) -> list[dict[str, object]]:
    rows = []
    for res in resources:
        path = GENE_SET_DIR / res.filename
        rows.append(
            {
                "resource": res.collection,
                "path": _rel(path),
                "exists": path.exists(),
                "sha256": _sha256(path) if path.exists() else "",
                "url": res.url,
                "source_note": res.source_note,
                "force_download": force_download,
            }
        )
    for path in [PATHWAY_ENRICHMENT, ATLAS_MAPPING, SUMMARY, FIGURE_SOURCE, REPORT_MD]:
        rows.append(
            {
                "resource": path.stem,
                "path": _rel(path),
                "exists": path.exists(),
                "sha256": _sha256(path) if path.exists() else "",
                "url": "",
                "source_note": "generated local artifact",
                "force_download": force_download,
            }
        )
    return rows


def _figure_rows(
    summary_rows: list[dict[str, object]],
    pathway_rows: list[dict[str, object]],
    atlas_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in summary_rows:
        rows.append({"panel": "figure4_pathway_atlas_summary", **row})
    for row in pathway_rows:
        if row["significant_fdr_0_05"]:
            rows.append({"panel": "figure4_pathway_top_hits", **row})
        if (
            row["significant_fdr_0_05"]
            and row.get("pathway_priority_label") == "manuscript_interpretable_candidate"
        ):
            rows.append({"panel": "figure4_pathway_interpretable_hits", **row})
    for row in atlas_rows:
        if row["support_status"] == "supported":
            rows.append({"panel": "figure4_atlas_marker_mapping", **row})
    return rows


def _build_report(
    summary_rows: list[dict[str, object]],
    pathway_rows: list[dict[str, object]],
    atlas_rows: list[dict[str, object]],
) -> str:
    summary = {row["summary_id"]: row for row in summary_rows}
    significant = [row for row in pathway_rows if row["significant_fdr_0_05"]]
    top_pathways = sorted(
        [
            row
            for row in significant
            if row.get("pathway_priority_label") == "manuscript_interpretable_candidate"
        ],
        key=lambda row: (float(row["p_adj_bh"]), -float(row["auc_delta"])),
    )[:12]
    if not top_pathways:
        top_pathways = sorted(
            significant, key=lambda row: (float(row["p_adj_bh"]), -float(row["auc_delta"]))
        )[:12]
    supported_atlas = [row for row in atlas_rows if row["support_status"] == "supported"]
    lines = [
        "# PDAC/TME Pathway And Atlas Validation",
        "",
        "Generated by `python scripts/run_pdac_tme_pathway_atlas_validation.py`.",
        "",
        "## Bottom Line",
        "",
        f"- Current status: `{summary['pdac_pathway_atlas_validation_status']['value']}`.",
        f"- Significant Hallmark pathways: `{summary['significant_hallmark_pathways']['value']}`.",
        f"- Significant Reactome pathways: `{summary['significant_reactome_pathways']['value']}`.",
        f"- Atlas-supported cluster/signature rows: `{summary['atlas_supported_cluster_signature_rows']['value']}`.",
        f"- Manuscript-interpretable significant pathways: `{summary['manuscript_interpretable_pathways']['value']}`.",
        "- Method boundary: rank-based Wilcoxon/Mann-Whitney gene-set enrichment, not Broad GSEA desktop permutation output.",
        "- Evidence boundary: public-data, non-clinical, hypothesis-generating.",
        "",
        "## Summary Table",
        "",
        "| Summary | Status | Value | Notes |",
        "| --- | --- | --- | --- |",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['summary_id']} | `{row['status']}` | {row['value']} | {row['notes']} |"
        )
    lines.extend(
        [
            "",
            "## Top Pathway Hits",
            "",
            "| Dataset | Cluster | Signature | Collection | Pathway | Priority | FDR | AUC delta | Leading overlap |",
            "| --- | --- | --- | --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    for row in top_pathways:
        lines.append(
            "| {dataset_id} | {cluster} | {cluster_top_signature} | {collection} | {pathway_name} | {pathway_priority_label} | {p_adj_bh:.3g} | {auc_delta:.3f} | {leading_overlap_genes} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Atlas Marker Mapping",
            "",
            "| Dataset | Cluster | Signature | Reference | DOI | Overlap n | Overlap genes | Status |",
            "| --- | --- | --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for row in supported_atlas:
        lines.append(
            f"| {row['dataset_id']} | {row['cluster']} | {row['cluster_top_signature']} | {row['reference']} | {row['doi']} | {row['overlap_n']} | {row['overlap_marker_genes']} | `{row['support_status']}` |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- Allowed: pathway/atlas evidence supports a bounded public PDAC/TME use case for method demonstration.",
            "- Not allowed: new PDAC mechanism, prognosis, therapy response, clinical validation, patient-level reproducibility, or standalone CAF discovery.",
            "",
            "## Source Artifacts",
            "",
            f"- Pathway enrichment: `{_rel(PATHWAY_ENRICHMENT)}`",
            f"- Atlas marker mapping: `{_rel(ATLAS_MAPPING)}`",
            f"- Summary: `{_rel(SUMMARY)}`",
            f"- Figure 4 source data: `{_rel(FIGURE_SOURCE)}`",
            f"- Manifest: `{_rel(MANIFEST)}`",
        ]
    )
    return "\n".join(lines)


def run(force_download: bool, min_size: int, max_size: int, fdr: float) -> None:
    if not DE_MARKERS.exists():
        raise FileNotFoundError(f"Missing DE table: {DE_MARKERS}")
    paths = [_download_atomic(resource, force=force_download) for resource in GENE_SET_RESOURCES]
    gene_sets: list[dict[str, object]] = []
    for resource, path in zip(GENE_SET_RESOURCES, paths):
        gene_sets.extend(_parse_gmt(path, resource.collection))

    de = pd.read_csv(DE_MARKERS, sep="\t")
    ranked_tables = _ranked_cluster_tables(de)
    pathway_rows = _pathway_rows(
        ranked_tables=ranked_tables,
        gene_sets=gene_sets,
        min_size=min_size,
        max_size=max_size,
        fdr=fdr,
    )
    atlas_rows = _atlas_rows(de, fdr=fdr)
    summary_rows = _summary_rows(pathway_rows, atlas_rows, GENE_SET_RESOURCES)
    figure_rows = _figure_rows(summary_rows, pathway_rows, atlas_rows)

    _write_tsv(
        PATHWAY_ENRICHMENT,
        pathway_rows,
        [
            "dataset_id",
            "cluster",
            "cluster_top_signature",
            "collection",
            "pathway_name",
            "pathway_size_in_ranked_genes",
            "ranked_gene_n",
            "mean_metric_in_pathway",
            "mean_metric_background",
            "auc_delta",
            "p_value",
            "p_adj_bh",
            "significant_fdr_0_05",
            "pathway_priority_label",
            "leading_overlap_genes",
        ],
    )
    _write_tsv(
        ATLAS_MAPPING,
        atlas_rows,
        [
            "dataset_id",
            "cluster",
            "cluster_top_signature",
            "expected_cluster_label",
            "reference",
            "doi",
            "url",
            "reference_marker_genes",
            "overlap_marker_genes",
            "overlap_n",
            "support_status",
            "evidence_note",
        ],
    )
    _write_tsv(SUMMARY, summary_rows, ["summary_id", "status", "value", "notes"])
    figure_fields = sorted({key for row in figure_rows for key in row.keys()})
    _write_tsv(FIGURE_SOURCE, figure_rows, figure_fields)
    _write_tsv(
        MANIFEST,
        _manifest_rows(GENE_SET_RESOURCES, force_download=force_download),
        ["resource", "path", "exists", "sha256", "url", "source_note", "force_download"],
    )
    _write_text(REPORT_MD, _build_report(summary_rows, pathway_rows, atlas_rows))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PDAC/TME pathway and atlas validation.")
    parser.add_argument("--force-download", action="store_true", help="Redownload external GMT resources.")
    parser.add_argument("--min-size", type=int, default=10, help="Minimum pathway genes present in ranked DE table.")
    parser.add_argument("--max-size", type=int, default=500, help="Maximum pathway genes present in ranked DE table.")
    parser.add_argument("--fdr", type=float, default=0.05, help="BH-FDR threshold.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run(force_download=args.force_download, min_size=args.min_size, max_size=args.max_size, fdr=args.fdr)
    print(_rel(PATHWAY_ENRICHMENT))
    print(_rel(ATLAS_MAPPING))
    print(_rel(SUMMARY))
    print(_rel(FIGURE_SOURCE))
    print(_rel(REPORT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
