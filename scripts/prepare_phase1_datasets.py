from __future__ import annotations

import argparse
import gzip
import shutil
import tarfile
import time
import urllib.request
from pathlib import Path

import numpy as np
from scipy import io, sparse


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
GSE96583_SUPPL_BASE = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE96nnn/GSE96583/suppl"
GSE96583_RAW_URL = f"{GSE96583_SUPPL_BASE}/GSE96583_RAW.tar"
GSE96583_BATCH2_GENES_URL = f"{GSE96583_SUPPL_BASE}/GSE96583_batch2.genes.tsv.gz"
GSE96583_BATCH2_CELLS_URL = f"{GSE96583_SUPPL_BASE}/GSE96583_batch2.total.tsne.df.tsv.gz"
GSE84133_SUPPL_BASE = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE84nnn/GSE84133/suppl"
GSE84133_RAW_URL = f"{GSE84133_SUPPL_BASE}/GSE84133_RAW.tar"
PBMC68K_ZHENG_URL = "https://ndownloader.figshare.com/files/27686886"


def _copy_maybe_gzip(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix == ".gz":
        with gzip.open(src, "rb") as handle_in, dest.open("wb") as handle_out:
            shutil.copyfileobj(handle_in, handle_out)
    else:
        shutil.copy2(src, dest)


def _sample_adata(adata, max_cells: int | None, random_state: int):
    if max_cells is None or adata.n_obs <= max_cells:
        return adata
    rng = np.random.default_rng(random_state)
    idx = np.sort(rng.choice(adata.n_obs, size=max_cells, replace=False))
    return adata[idx].copy()


def _sample_adata_stratified(adata, max_cells: int | None, random_state: int, key: str, min_per_group: int = 5):
    if max_cells is None or adata.n_obs <= max_cells or key not in adata.obs:
        return _sample_adata(adata, max_cells, random_state)
    rng = np.random.default_rng(random_state)
    groups = {str(group): np.asarray(np.where(adata.obs[key].astype(str).to_numpy() == str(group))[0]) for group in adata.obs[key].astype(str).unique()}
    selected: list[int] = []
    for group_indices in groups.values():
        quota = max(min_per_group, int(round(max_cells * group_indices.size / adata.n_obs)))
        quota = min(quota, group_indices.size)
        if quota > 0:
            selected.extend(rng.choice(group_indices, size=quota, replace=False).tolist())
    if len(selected) > max_cells:
        selected = rng.choice(np.asarray(selected), size=max_cells, replace=False).tolist()
    elif len(selected) < max_cells:
        remaining = np.setdiff1d(np.arange(adata.n_obs), np.asarray(selected, dtype=int), assume_unique=False)
        extra_n = min(max_cells - len(selected), remaining.size)
        if extra_n > 0:
            selected.extend(rng.choice(remaining, size=extra_n, replace=False).tolist())
    return adata[np.sort(np.asarray(selected, dtype=int))].copy()


def prepare_pbmc3k(outdir: Path, max_cells: int | None, random_state: int, force: bool) -> Path:
    import scanpy as sc

    out = outdir / "pbmc3k_10x.h5ad"
    if out.exists() and not force:
        print(f"exists {out}")
        return out

    adata = sc.datasets.pbmc3k()
    adata.var_names_make_unique()
    adata.layers["counts"] = adata.X.copy()
    sc.pp.filter_cells(adata, min_genes=200)
    sc.pp.filter_genes(adata, min_cells=3)
    adata = _sample_adata(adata, max_cells, random_state)
    adata.obs["dataset_id"] = "pbmc3k_10x"
    adata.obs["condition"] = "healthy"
    adata.obs["batch"] = "pbmc3k"
    adata.write_h5ad(out)
    print(out)
    return out


def _remote_size(url: str) -> int:
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "RMTGuard/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return int(response.headers.get("Content-Length") or 0)
    except Exception:
        return 0


def _download(url: str, out: Path, retries: int = 3) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_size > 0:
        expected_existing = _remote_size(url)
        if expected_existing == 0 or out.stat().st_size == expected_existing:
            return out
        print(f"remove incomplete download {out} ({out.stat().st_size} of {expected_existing} bytes)")
        out.unlink()
    print(f"download {url}")
    tmp = out.with_suffix(out.suffix + ".tmp")
    for attempt in range(1, retries + 1):
        expected = _remote_size(url)
        resume_from = tmp.stat().st_size if tmp.exists() else 0
        headers = {"User-Agent": "RMTGuard/0.1"}
        if resume_from > 0 and (expected == 0 or resume_from < expected):
            headers["Range"] = f"bytes={resume_from}-"
            mode = "ab"
            print(f"resume {tmp} from {resume_from} bytes")
        else:
            mode = "wb"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                if resume_from > 0 and response.status == 200:
                    mode = "wb"
                    resume_from = 0
                with tmp.open(mode) as handle:
                    downloaded = resume_from
                    response_length = int(response.headers.get("Content-Length") or 0)
                    if expected == 0 and response.status == 200:
                        expected = response_length
                    if response.status == 206 and expected == 0:
                        expected = resume_from + response_length
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
                        downloaded += len(chunk)
            if expected and downloaded != expected:
                raise RuntimeError(f"download incomplete: got {downloaded} of {expected} bytes")
            tmp.replace(out)
            return out
        except Exception:
            if attempt == retries:
                raise
            time.sleep(2 * attempt)
    return out


def _extract_tar(tar_path: Path, outdir: Path) -> None:
    sentinel = outdir / ".extracted"
    if sentinel.exists():
        return
    outdir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "r:*") as handle:
        handle.extractall(outdir)
    sentinel.write_text("ok\n", encoding="utf-8")


def _find_one(files: list[Path], gsm: str, tokens: tuple[str, ...]) -> Path:
    candidates = []
    for file in files:
        name = file.name.lower()
        if gsm.lower() in name and all(token in name for token in tokens):
            candidates.append(file)
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        return sorted(candidates, key=lambda p: len(p.name))[0]
    preview = "\n".join(str(p.name) for p in files[:60])
    raise FileNotFoundError(f"Could not find {gsm} file with tokens {tokens}. Available files include:\n{preview}")


def _read_vector(path: Path) -> list[str]:
    opener = gzip.open if path.suffix == ".gz" else open
    values = []
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2 and parts[1]:
                values.append(parts[1])
            elif parts and parts[0]:
                values.append(parts[0])
    return values


def _read_mtx(extract_dir: Path, gsm: str) -> sparse.csr_matrix:
    files = [p for p in extract_dir.rglob("*") if p.is_file()]
    matrix_file = _find_one(files, gsm, ("mtx",))

    matrix = io.mmread(matrix_file)
    if not sparse.issparse(matrix):
        matrix = sparse.coo_matrix(matrix)
    return matrix.tocsr()


def prepare_kang_ifnb(outdir: Path, raw_dir: Path, max_cells: int | None, random_state: int, force: bool) -> Path:
    import anndata as ad
    import pandas as pd
    import scanpy as sc

    out = outdir / "kang_ifnb_pbmc.h5ad"
    if out.exists() and not force:
        print(f"exists {out}")
        return out

    tar_path = _download(GSE96583_RAW_URL, raw_dir / "GSE96583_RAW.tar")
    genes_path = _download(GSE96583_BATCH2_GENES_URL, raw_dir / "GSE96583_batch2.genes.tsv.gz")
    cells_path = _download(GSE96583_BATCH2_CELLS_URL, raw_dir / "GSE96583_batch2.total.tsne.df.tsv.gz")
    extract_dir = raw_dir / "GSE96583_RAW"
    _extract_tar(tar_path, extract_dir)

    control = _read_mtx(extract_dir, "GSM2560248")
    stim = _read_mtx(extract_dir, "GSM2560249")
    counts_gene_by_cell = sparse.hstack([control, stim], format="csr")
    gene_md = pd.read_csv(genes_path, sep="\t", header=None, names=["ensembl_id", "gene_symbol"])
    cell_md = pd.read_csv(cells_path, sep="\t")
    if counts_gene_by_cell.shape[0] != gene_md.shape[0]:
        raise ValueError(f"Kang gene count mismatch: matrix={counts_gene_by_cell.shape}, genes={gene_md.shape}")
    if counts_gene_by_cell.shape[1] != cell_md.shape[0]:
        cell_md = pd.DataFrame(index=[f"kang_cell_{i}" for i in range(counts_gene_by_cell.shape[1])])
        cell_md["condition"] = ["control"] * control.shape[1] + ["stimulated"] * stim.shape[1]
    elif "stim" in cell_md.columns:
        cell_md["condition"] = cell_md["stim"].astype(str)
    elif "condition" not in cell_md.columns:
        cell_md["condition"] = ["control"] * control.shape[1] + ["stimulated"] * stim.shape[1]

    adata = ad.AnnData(counts_gene_by_cell.T.tocsr())
    adata.obs = cell_md.copy()
    adata.obs_names = [f"kang_batch2_cell_{i}" for i in range(adata.n_obs)]
    adata.var_names = gene_md["gene_symbol"].astype(str).to_list()
    adata.var["ensembl_id"] = gene_md["ensembl_id"].astype(str).to_numpy()
    adata.var_names_make_unique()
    adata.obs["dataset_id"] = "kang_ifnb_pbmc"
    if "multiplets" in adata.obs:
        adata = adata[adata.obs["multiplets"].astype(str) == "singlet"].copy()
    adata.obs["batch"] = adata.obs["ind"].astype(str).to_numpy() if "ind" in adata.obs else "batch2"
    sc.pp.filter_cells(adata, min_genes=200)
    sc.pp.filter_genes(adata, min_cells=3)
    adata = _sample_adata(adata, max_cells, random_state)
    adata.layers["counts"] = adata.X.copy()
    adata.write_h5ad(out)
    print(out)
    return out


def prepare_baron_pancreas(outdir: Path, raw_dir: Path, max_cells: int | None, random_state: int, force: bool) -> Path:
    import anndata as ad
    import pandas as pd
    import scanpy as sc

    out = outdir / "baron_pancreas.h5ad"
    if out.exists() and not force:
        print(f"exists {out}")
        return out

    tar_path = _download(GSE84133_RAW_URL, raw_dir / "GSE84133_RAW.tar")
    extract_dir = raw_dir / "GSE84133_RAW"
    _extract_tar(tar_path, extract_dir)
    human_files = sorted(extract_dir.glob("*human*_umifm_counts.csv.gz"))
    if not human_files:
        raise FileNotFoundError(f"No human Baron pancreas count files found in {extract_dir}")

    obs_frames = []
    matrices = []
    genes: list[str] | None = None
    for path in human_files:
        frame = pd.read_csv(path)
        if "assigned_cluster" not in frame.columns or "barcode" not in frame.columns:
            raise ValueError(f"Unexpected Baron pancreas columns in {path}")
        sample_id = path.name.split("_umifm_counts", 1)[0].split("_", 1)[1]
        cell_ids = frame.iloc[:, 0].astype(str).to_numpy()
        current_genes = [c for c in frame.columns if c not in {frame.columns[0], "barcode", "assigned_cluster"}]
        if genes is None:
            genes = current_genes
        elif genes != current_genes:
            raise ValueError(f"Gene columns differ in {path}")
        obs = pd.DataFrame(
            {
                "barcode": frame["barcode"].astype(str).to_numpy(),
                "cell": frame["assigned_cluster"].astype(str).to_numpy(),
                "sample_id": sample_id,
                "batch": sample_id,
                "dataset_id": "baron_pancreas",
            },
            index=[f"{sample_id}_{cell_id}" for cell_id in cell_ids],
        )
        obs_frames.append(obs)
        matrices.append(sparse.csr_matrix(frame[current_genes].to_numpy(dtype=np.float32)))

    if genes is None:
        raise ValueError("No genes were parsed from Baron pancreas files.")
    counts = sparse.vstack(matrices, format="csr")
    obs = pd.concat(obs_frames, axis=0)
    adata = ad.AnnData(counts, obs=obs)
    adata.var_names = genes
    adata.var_names_make_unique()
    sc.pp.filter_cells(adata, min_genes=200)
    sc.pp.filter_genes(adata, min_cells=3)
    adata = _sample_adata(adata, max_cells, random_state)
    adata.layers["counts"] = adata.X.copy()
    adata.write_h5ad(out)
    print(out)
    return out


def prepare_pbmc68k_zheng2017(outdir: Path, raw_dir: Path, max_cells: int | None, random_state: int, force: bool) -> Path:
    import scanpy as sc

    out = outdir / "pbmc68k_zheng2017.h5ad"
    if out.exists() and not force:
        print(f"exists {out}")
        return out

    raw_h5ad = _download(PBMC68K_ZHENG_URL, raw_dir / "pbmc68k_zheng2017.h5ad")
    adata = sc.read_h5ad(raw_h5ad)
    adata.var_names_make_unique()
    if "celltype" in adata.obs:
        adata.obs["cell"] = adata.obs["celltype"].astype(str).to_numpy()
    adata.obs["dataset_id"] = "pbmc68k_zheng2017"
    adata.obs["batch"] = "pbmc68k_zheng2017"
    sc.pp.filter_cells(adata, min_genes=50)
    sc.pp.filter_genes(adata, min_cells=3)
    adata = _sample_adata_stratified(adata, max_cells, random_state, key="cell")
    adata.layers["counts"] = adata.X.copy()
    adata.write_h5ad(out)
    print(out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Phase 1 public benchmark datasets.")
    parser.add_argument(
        "--dataset",
        choices=["all", "pbmc3k_10x", "kang_ifnb_pbmc", "baron_pancreas", "pbmc68k_zheng2017"],
        default="all",
    )
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--outdir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--max-cells", type=int, default=None)
    parser.add_argument("--random-state", type=int, default=20260427)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    if args.dataset in {"all", "pbmc3k_10x"}:
        prepare_pbmc3k(args.outdir, args.max_cells, args.random_state, args.force)
    if args.dataset in {"all", "kang_ifnb_pbmc"}:
        prepare_kang_ifnb(args.outdir, args.raw_dir, args.max_cells, args.random_state, args.force)
    if args.dataset in {"all", "baron_pancreas"}:
        prepare_baron_pancreas(args.outdir, args.raw_dir, args.max_cells, args.random_state, args.force)
    if args.dataset in {"all", "pbmc68k_zheng2017"}:
        prepare_pbmc68k_zheng2017(args.outdir, args.raw_dir, args.max_cells, args.random_state, args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
