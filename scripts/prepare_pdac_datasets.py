from __future__ import annotations

import argparse
import csv
import gzip
import re
from pathlib import Path

import numpy as np
from scipy import sparse

from prepare_phase1_datasets import _download


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
GSE154778_DGE_URL = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE154nnn/GSE154778/suppl/GSE154778_dgeMtx.csv.gz"
GSE154778_MATRIX_URL = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE154nnn/GSE154778/matrix/GSE154778_series_matrix.txt.gz"
GSE263733_COUNTS_URL = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE263nnn/GSE263733/suppl/GSE263733_Raw_counts.txt.gz"
GSE263733_ANNOTATION_URL = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE263nnn/GSE263733/suppl/GSE263733_Cell_annotation.txt.gz"


def _atomic_write_h5ad(adata, out: Path) -> None:
    tmp = out.with_name(out.stem + ".tmp" + out.suffix)
    if tmp.exists():
        tmp.unlink()
    adata.write_h5ad(tmp)
    tmp.replace(out)


def _parse_quoted_series_row(line: str) -> list[str]:
    parts = next(csv.reader([line.rstrip("\n")], delimiter="\t"))
    return [part.strip().strip('"') for part in parts[1:]]


def _load_gse154778_metadata(path: Path) -> dict[str, dict[str, str]]:
    titles: list[str] | None = None
    accessions: list[str] | None = None
    tissue_type: list[str] | None = None
    age: list[str] | None = None
    gender: list[str] | None = None
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith("!Sample_title"):
                titles = _parse_quoted_series_row(line)
            elif line.startswith("!Sample_geo_accession"):
                accessions = _parse_quoted_series_row(line)
            elif line.startswith("!Sample_characteristics_ch1"):
                values = _parse_quoted_series_row(line)
                if values and values[0].startswith("tissue type:"):
                    tissue_type = [v.split(":", 1)[1].strip() for v in values]
                elif values and values[0].startswith("age:"):
                    age = [v.split(":", 1)[1].strip() for v in values]
                elif values and values[0].startswith("gender:"):
                    gender = [v.split(":", 1)[1].strip() for v in values]
    if titles is None or accessions is None or tissue_type is None:
        raise ValueError(f"Could not parse required GSE154778 metadata from {path}")
    out: dict[str, dict[str, str]] = {}
    for idx, title in enumerate(titles):
        sample_id = title.split(":", 1)[0]
        out[sample_id] = {
            "geo_accession": accessions[idx],
            "sample_title": title,
            "tissue_type": tissue_type[idx],
            "age": age[idx] if age else "",
            "gender": gender[idx] if gender else "",
        }
    return out


def _read_cell_names(path: Path) -> list[str]:
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
    return header[1:]


def _choose_cells(cells: list[str], max_cells: int | None, random_state: int) -> list[str]:
    if max_cells is None or len(cells) <= max_cells:
        return cells
    by_sample: dict[str, list[str]] = {}
    for cell in cells:
        sample = cell.split(":", 1)[0]
        by_sample.setdefault(sample, []).append(cell)
    rng = np.random.default_rng(random_state)
    selected: list[str] = []
    min_per_sample = min(20, max(1, max_cells // max(1, len(by_sample))))
    for sample_cells in by_sample.values():
        quota = max(min_per_sample, int(round(max_cells * len(sample_cells) / len(cells))))
        quota = min(quota, len(sample_cells))
        selected.extend(rng.choice(np.asarray(sample_cells), size=quota, replace=False).tolist())
    if len(selected) > max_cells:
        selected = rng.choice(np.asarray(selected), size=max_cells, replace=False).tolist()
    elif len(selected) < max_cells:
        remaining = np.asarray([cell for cell in cells if cell not in set(selected)])
        extra = min(max_cells - len(selected), remaining.size)
        if extra > 0:
            selected.extend(rng.choice(remaining, size=extra, replace=False).tolist())
    cell_order = {cell: idx for idx, cell in enumerate(cells)}
    return sorted(selected, key=lambda cell: cell_order[cell])


def prepare_gse154778(outdir: Path, raw_dir: Path, max_cells: int | None, random_state: int, force: bool) -> Path:
    import anndata as ad
    import pandas as pd
    import scanpy as sc

    out = outdir / "pdac_gse154778.h5ad"
    if out.exists() and not force:
        print(f"exists {out}")
        return out

    dge_path = _download(GSE154778_DGE_URL, raw_dir / "GSE154778_dgeMtx.csv.gz")
    matrix_path = _download(GSE154778_MATRIX_URL, raw_dir / "GSE154778_series_matrix.txt.gz")
    sample_metadata = _load_gse154778_metadata(matrix_path)
    all_cells = _read_cell_names(dge_path)
    selected_cells = _choose_cells(all_cells, max_cells, random_state)
    cell_to_column = {cell: idx + 1 for idx, cell in enumerate(all_cells)}
    usecols = [0] + [cell_to_column[cell] for cell in selected_cells]
    frame = pd.read_csv(dge_path, usecols=usecols, index_col=0)
    frame.index = frame.index.astype(str)
    frame = frame.loc[~frame.index.duplicated(keep="first")]
    counts = sparse.csr_matrix(frame.T.to_numpy(dtype=np.float32))
    obs_rows = []
    for cell in frame.columns.astype(str):
        sample_id = cell.split(":", 1)[0]
        metadata = sample_metadata.get(sample_id, {})
        obs_rows.append(
            {
                "cell_id": cell,
                "sample_id": sample_id,
                "batch": sample_id,
                "dataset_id": "pdac_gse154778",
                "tissue_type": metadata.get("tissue_type", ""),
                "geo_accession": metadata.get("geo_accession", ""),
                "sample_title": metadata.get("sample_title", ""),
                "age": metadata.get("age", ""),
                "gender": metadata.get("gender", ""),
            }
        )
    obs = pd.DataFrame(obs_rows, index=frame.columns.astype(str))
    adata = ad.AnnData(counts, obs=obs)
    adata.var_names = frame.index.astype(str).to_list()
    adata.var_names_make_unique()
    sc.pp.filter_cells(adata, min_genes=200)
    sc.pp.filter_genes(adata, min_cells=3)
    adata.layers["counts"] = adata.X.copy()
    outdir.mkdir(parents=True, exist_ok=True)
    _atomic_write_h5ad(adata, out)
    print(out)
    return out


def _choose_annotation_cells(annotation, max_cells: int | None, random_state: int, key: str) -> list[str]:
    if max_cells is None or annotation.shape[0] <= max_cells:
        return annotation["Barcodes"].astype(str).to_list()
    rng = np.random.default_rng(random_state)
    selected: list[str] = []
    groups = annotation.groupby(key, sort=False)
    min_per_group = min(25, max(1, max_cells // max(1, len(groups))))
    for _group, frame in groups:
        quota = max(min_per_group, int(round(max_cells * frame.shape[0] / annotation.shape[0])))
        quota = min(quota, frame.shape[0])
        selected.extend(rng.choice(frame["Barcodes"].astype(str).to_numpy(), size=quota, replace=False).tolist())
    if len(selected) > max_cells:
        selected = rng.choice(np.asarray(selected), size=max_cells, replace=False).tolist()
    elif len(selected) < max_cells:
        remaining = annotation.loc[~annotation["Barcodes"].astype(str).isin(selected), "Barcodes"].astype(str).to_numpy()
        extra = min(max_cells - len(selected), remaining.size)
        if extra > 0:
            selected.extend(rng.choice(remaining, size=extra, replace=False).tolist())
    return selected


def prepare_gse263733(outdir: Path, raw_dir: Path, max_cells: int | None, random_state: int, force: bool) -> Path:
    import anndata as ad
    import pandas as pd
    import scanpy as sc

    out = outdir / "pdac_gse263733.h5ad"
    if out.exists() and not force:
        print(f"exists {out}")
        return out

    counts_path = _download(GSE263733_COUNTS_URL, raw_dir / "GSE263733_Raw_counts.txt.gz")
    annotation_path = _download(GSE263733_ANNOTATION_URL, raw_dir / "GSE263733_Cell_annotation.txt.gz")
    annotation = pd.read_csv(annotation_path, sep="\t")
    annotation["Barcodes"] = annotation["Barcodes"].astype(str)
    selected_cells = _choose_annotation_cells(annotation, max_cells, random_state, key="Celltypes")
    frame = pd.read_csv(counts_path, sep="\t", usecols=selected_cells)
    frame.index = frame.index.astype(str)
    frame = frame.loc[~frame.index.duplicated(keep="first")]
    counts = sparse.csr_matrix(frame.T.to_numpy(dtype=np.float32))
    obs = annotation.set_index("Barcodes").loc[frame.columns.astype(str)].copy()
    obs = obs.rename(columns={"Patients": "patient_id", "Origins": "origin", "Celltypes": "cell"})
    obs["cell_id"] = obs.index.astype(str)
    obs["sample_id"] = obs["cell_id"].str.split("_", n=1).str[0]
    obs["batch"] = obs["patient_id"].astype(str).to_numpy()
    obs["dataset_id"] = "pdac_gse263733"
    obs["tissue_type"] = obs["origin"].astype(str).map(
        {
            "Pm0": "Primary",
            "Pm1": "Primary",
            "Pn": "Adjacent/normal",
            "Lm": "Liver metastasis",
        }
    ).fillna(obs["origin"].astype(str))
    adata = ad.AnnData(counts, obs=obs)
    adata.var_names = frame.index.astype(str).to_list()
    adata.var_names_make_unique()
    sc.pp.filter_cells(adata, min_genes=200)
    sc.pp.filter_genes(adata, min_cells=3)
    adata.layers["counts"] = adata.X.copy()
    outdir.mkdir(parents=True, exist_ok=True)
    _atomic_write_h5ad(adata, out)
    print(out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare public PDAC/TME showcase datasets.")
    parser.add_argument("--dataset", choices=["gse154778", "gse263733"], default="gse154778")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--outdir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--max-cells", type=int, default=1200)
    parser.add_argument("--random-state", type=int, default=20260427)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.dataset == "gse154778":
        prepare_gse154778(args.outdir, args.raw_dir, args.max_cells, args.random_state, args.force)
    if args.dataset == "gse263733":
        prepare_gse263733(args.outdir, args.raw_dir, args.max_cells, args.random_state, args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
