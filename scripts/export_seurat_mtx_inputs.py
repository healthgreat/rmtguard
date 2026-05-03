#!/usr/bin/env python
"""Export prepared h5ad datasets to MatrixMarket inputs for Seurat.

Author: RMTGuard development team
Date: 2026-05-03
Purpose: Provide a robust h5ad-independent bridge for official Seurat matched
baselines when zellkonverter cannot read a dataset's sparse matrix cleanly.
Data source: data/processed/*.h5ad.
Method notes: Counts are written as genes x cells MatrixMarket because Seurat
expects features by cells. Metadata and feature/cell names are TSV files.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import anndata as ad
import pandas as pd
from scipy import sparse
from scipy.io import mmwrite

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT_ROOT = ROOT / "data" / "processed" / "seurat_mtx"

DATASETS = {
    "pbmc3k_10x": "pbmc3k_10x.h5ad",
    "paul15_hematopoiesis": "paul15_hematopoiesis.h5ad",
    "kang_ifnb_pbmc": "kang_ifnb_pbmc.h5ad",
    "baron_pancreas": "baron_pancreas.h5ad",
    "pbmc68k_zheng2017": "pbmc68k_zheng2017.h5ad",
    "pdac_gse154778": "pdac_gse154778.h5ad",
    "pdac_gse263733": "pdac_gse263733.h5ad",
}


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _atomic_write_tsv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, sep="\t", index=False, quoting=csv.QUOTE_MINIMAL)
    tmp.replace(path)


def _atomic_write_text(lines: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def export_dataset(dataset_id: str, processed_dir: Path, out_root: Path) -> dict[str, str]:
    h5ad_path = processed_dir / DATASETS[dataset_id]
    if not h5ad_path.exists():
        raise FileNotFoundError(f"Missing prepared dataset: {_rel(h5ad_path)}")
    adata = ad.read_h5ad(h5ad_path)
    counts = adata.layers["counts"] if "counts" in adata.layers else adata.X
    counts = sparse.csc_matrix(counts).T.astype("float64")
    out_dir = out_root / dataset_id
    out_dir.mkdir(parents=True, exist_ok=True)
    matrix_tmp = out_dir / "counts.mtx.tmp"
    matrix_path = out_dir / "counts.mtx"
    with matrix_tmp.open("wb") as handle:
        mmwrite(handle, counts)
    matrix_tmp.replace(matrix_path)
    feature_names = [str(value) for value in adata.var_names]
    cell_names = [str(value) for value in adata.obs_names]
    _atomic_write_text(feature_names, out_dir / "features.tsv")
    _atomic_write_text(cell_names, out_dir / "barcodes.tsv")
    obs = adata.obs.copy()
    obs.insert(0, "cell_barcode", cell_names)
    _atomic_write_tsv(obs.reset_index(drop=True), out_dir / "obs.tsv")
    return {
        "dataset_id": dataset_id,
        "h5ad_path": _rel(h5ad_path),
        "matrix_path": _rel(matrix_path),
        "features_path": _rel(out_dir / "features.tsv"),
        "barcodes_path": _rel(out_dir / "barcodes.tsv"),
        "obs_path": _rel(out_dir / "obs.tsv"),
        "n_cells": str(adata.n_obs),
        "n_genes": str(adata.n_vars),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export h5ad datasets to Seurat mtx inputs.")
    parser.add_argument("--datasets", nargs="+", default=list(DATASETS), choices=sorted(DATASETS))
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED)
    parser.add_argument("--out-root", type=Path, default=OUT_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = [export_dataset(dataset, args.processed_dir, args.out_root) for dataset in args.datasets]
    manifest = args.out_root / "seurat_mtx_manifest.tsv"
    _atomic_write_tsv(pd.DataFrame(rows), manifest)
    print(_rel(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
