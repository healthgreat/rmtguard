from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from rmtguard import RMTGuard, RMTGuardConfig


ROOT = Path(__file__).resolve().parents[1]

SIGNATURES = {
    "caf_fibroblast": ["COL1A1", "COL1A2", "DCN", "LUM", "ACTA2", "TAGLN", "FAP"],
    "immune_myeloid": ["PTPRC", "LYZ", "LST1", "FCGR3A", "CD14", "MS4A7"],
    "t_nk": ["PTPRC", "CD3D", "CD3E", "NKG7", "GNLY", "TRAC"],
    "b_plasma": ["MS4A1", "CD79A", "CD74", "MZB1", "JCHAIN", "IGHG1"],
    "ductal_malignant_context": ["KRT8", "KRT18", "KRT19", "EPCAM", "MUC1", "TACSTD2"],
    "endothelial": ["PECAM1", "VWF", "KDR", "CLDN5", "RAMP2"],
}


def _normalize_log(x) -> np.ndarray:
    if hasattr(x, "toarray"):
        x = x.toarray()
    arr = np.asarray(x, dtype=float)
    totals = np.maximum(arr.sum(axis=1, keepdims=True), 1e-12)
    return np.log1p(arr / totals * 1e4)


def _signature_scores(adata) -> dict[str, np.ndarray]:
    x = _normalize_log(adata.layers["counts"] if "counts" in adata.layers else adata.X)
    gene_to_idx = {gene.upper(): idx for idx, gene in enumerate(adata.var_names.astype(str))}
    scores: dict[str, np.ndarray] = {}
    for name, genes in SIGNATURES.items():
        indices = [gene_to_idx[gene.upper()] for gene in genes if gene.upper() in gene_to_idx]
        if indices:
            scores[name] = np.asarray(x[:, indices].mean(axis=1)).ravel()
        else:
            scores[name] = np.zeros(adata.n_obs, dtype=float)
    return scores


def _cluster_rows(adata, labels: np.ndarray, scores: dict[str, np.ndarray]) -> list[dict[str, object]]:
    tissue = adata.obs["tissue_type"].astype(str).to_numpy() if "tissue_type" in adata.obs else np.repeat("", adata.n_obs)
    sample = adata.obs["sample_id"].astype(str).to_numpy() if "sample_id" in adata.obs else np.repeat("", adata.n_obs)
    cell_label = adata.obs["cell"].astype(str).to_numpy() if "cell" in adata.obs else None
    rows = []
    for cluster in sorted(np.unique(labels), key=lambda x: int(x)):
        mask = labels == cluster
        score_means = {name: float(values[mask].mean()) for name, values in scores.items()}
        top_signature = max(score_means, key=score_means.get)
        tissue_counts = {name: int(np.sum(tissue[mask] == name)) for name in sorted(set(tissue[mask]))}
        lower_tissue = np.char.lower(tissue[mask].astype(str))
        primary_mask = np.char.find(lower_tissue, "primary") >= 0
        metastasis_mask = np.char.find(lower_tissue, "metast") >= 0
        label_counts = {}
        if cell_label is not None:
            label_counts = {name: int(np.sum(cell_label[mask] == name)) for name in sorted(set(cell_label[mask]))}
        rows.append(
            {
                "cluster": int(cluster),
                "n_cells": int(np.sum(mask)),
                "n_samples": int(len(set(sample[mask]))),
                "primary_fraction": float(np.mean(primary_mask)) if mask.any() else float("nan"),
                "metastasis_fraction": float(np.mean(metastasis_mask)) if mask.any() else float("nan"),
                "top_signature": top_signature,
                **{f"score_{name}": value for name, value in score_means.items()},
                "cell_label_counts_json": json.dumps(label_counts, sort_keys=True),
                "tissue_counts_json": json.dumps(tissue_counts, sort_keys=True),
            }
        )
    return rows


def _write_combined_summary(path: Path, row: dict[str, object]) -> None:
    rows = []
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
    rows = [existing for existing in rows if existing.get("dataset_id") != str(row["dataset_id"])]
    rows.append({key: str(value) for key, value in row.items()})
    fieldnames = sorted({key for existing in rows for key in existing})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run RMTGuard PDAC/TME marker showcase.")
    parser.add_argument("--h5ad", type=Path, default=ROOT / "data" / "processed" / "pdac_gse154778.h5ad")
    parser.add_argument("--dataset-id", default="pdac_gse154778")
    parser.add_argument("--outdir", type=Path, default=ROOT / "results" / "pdac_tme")
    parser.add_argument("--hvg-grid", type=int, nargs="+", default=[500, 1000, 2000])
    parser.add_argument("--max-pcs", type=int, default=50)
    parser.add_argument("--random-state", type=int, default=20260427)
    args = parser.parse_args()

    import scanpy as sc

    adata = sc.read_h5ad(args.h5ad)
    matrix = adata.layers["counts"] if "counts" in adata.layers else adata.X
    batches = adata.obs["sample_id"].astype(str).to_numpy() if "sample_id" in adata.obs else None
    result = RMTGuard(
        RMTGuardConfig(
            hvg_grid=tuple(args.hvg_grid),
            max_pcs=args.max_pcs,
            embedding_rule="adaptive_near_edge",
            embedding_source="standard_pca",
            resolution_rule="graph_modularity",
            random_state=args.random_state,
            batch_key="sample_id" if batches is not None else None,
        )
    ).fit(matrix, batches=batches, benchmark_metadata={"dataset_id": args.dataset_id})
    scores = _signature_scores(adata)
    cluster_rows = _cluster_rows(adata, result.cluster_labels, scores)

    args.outdir.mkdir(parents=True, exist_ok=True)
    cluster_path = args.outdir / f"{args.dataset_id}_cluster_marker_summary.tsv"
    fieldnames = sorted({key for row in cluster_rows for key in row})
    with cluster_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(cluster_rows)

    showcase = {
        "dataset_id": args.dataset_id,
        "n_cells": int(adata.n_obs),
        "n_genes": int(adata.n_vars),
        "cluster_n": int(result.cluster_n or 0),
        "selected_hvg_n": int(result.selected_hvg_n),
        "strict_signal_pcs": int(result.embedding_diagnostics.get("strict_signal_pcs", result.n_signal_pcs)),
        "accepted_embedding_pcs": int(result.embedding_diagnostics.get("accepted_embedding_pcs", result.n_embedding_pcs)),
        "top_signatures": sorted({row["top_signature"] for row in cluster_rows}),
        "has_caf_or_fibroblast_cluster": any(row["top_signature"] == "caf_fibroblast" for row in cluster_rows),
        "has_immune_cluster": any(row["top_signature"] in {"immune_myeloid", "t_nk", "b_plasma"} for row in cluster_rows),
        "has_ductal_context_cluster": any(row["top_signature"] == "ductal_malignant_context" for row in cluster_rows),
        "label_ari": float("nan"),
        "label_nmi": float("nan"),
        "status": "smoke_marker_showcase",
        "limitation": "Marker signatures are coarse labels inferred from public counts; no author cell-type labels are available in GSE154778 supplementary files.",
    }
    if "cell" in adata.obs and adata.obs["cell"].astype(str).nunique() >= 2:
        labels_true = adata.obs["cell"].astype(str).to_numpy()
        showcase["label_ari"] = float(adjusted_rand_score(labels_true, result.cluster_labels.astype(str)))
        showcase["label_nmi"] = float(normalized_mutual_info_score(labels_true, result.cluster_labels.astype(str)))
        showcase["status"] = "external_label_validation"
        showcase["limitation"] = "Cell-type labels are public annotations; marker signatures remain coarse state labels."
    summary_path = args.outdir / "showcase_summary.tsv"
    _write_combined_summary(summary_path, showcase)

    details_path = args.outdir / f"{args.dataset_id}_rmtguard_details.json"
    with details_path.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "pc_diagnostics": result.pc_diagnostics,
                "hvg_diagnostics": result.hvg_diagnostics,
                "embedding_diagnostics": result.embedding_diagnostics,
                "resolution_scan": result.resolution_scan,
                "benchmark_metadata": result.benchmark_metadata,
            },
            handle,
            indent=2,
        )

    print(summary_path)
    print(cluster_path)
    print(details_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
