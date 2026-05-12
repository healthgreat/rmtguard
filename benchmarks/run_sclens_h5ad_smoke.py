from __future__ import annotations

"""Run scLENSpy on an RMTGuard prepared h5ad file.

Author: RMTGuard development team
Date: 2026-05-12
Purpose: Smoke-test scLENSpy as a direct comparator on RMTGuard benchmark h5ad
datasets before adding manuscript-grade repeated stability runs.
Data source: Prepared AnnData files under data/processed/.
Method notes: scLENS/scLENSpy is third-party software by Kim et al. (Nature
Communications 2024, DOI: 10.1038/s41467-024-47884-3). This adapter records
runtime and embedding size only; it is not a manuscript-grade head-to-head
benchmark until repeated subsampling, confidence intervals, and annotation
checks are run.
"""

import argparse
import csv
import random
import subprocess
import sys
import time
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from rmtguard.cluster import graph_modularity_labels


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCLENS_PATH = ROOT / "external" / "scLENSpy"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "sclens_comparator"


def _atomic_write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    fieldnames = list(rows[0].keys())
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _git_commit(path: Path) -> str:
    if not (path / ".git").exists():
        return "not_a_git_clone"
    cmd = [
        "git",
        "-c",
        f"safe.directory={path.resolve().as_posix()}",
        "-C",
        str(path),
        "rev-parse",
        "HEAD",
    ]
    try:
        completed = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:  # pragma: no cover - diagnostic only
        return f"unavailable:{type(exc).__name__}"
    return completed.stdout.strip()


def _as_dense(x) -> np.ndarray:
    if hasattr(x, "toarray"):
        x = x.toarray()
    return np.asarray(x)


def _safe_metric(labels_true, labels_pred, metric) -> str:
    if labels_true is None:
        return "nan"
    truth = np.asarray(labels_true).astype(str)
    pred = np.asarray(labels_pred).astype(str)
    if truth.size == 0 or np.unique(truth).size < 2 or pred.size != truth.size:
        return "nan"
    return f"{float(metric(truth, pred)):.6g}"


def _choose_label_key(adata: ad.AnnData, requested: str) -> str:
    if requested != "auto":
        return requested if requested in adata.obs else ""
    for key in ("cell_type", "celltype", "seurat_annotations", "cell", "label"):
        if key in adata.obs and adata.obs[key].astype(str).nunique() > 1:
            return key
    return ""


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--h5ad", type=Path, required=True)
    parser.add_argument("--sclens-path", type=Path, default=DEFAULT_SCLENS_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--layer", default="counts")
    parser.add_argument("--label-key", default="auto")
    parser.add_argument("--max-cells", type=int, default=1000)
    parser.add_argument("--n-rand-matrix", type=int, default=2)
    parser.add_argument("--n-neighbors", type=int, default=15)
    parser.add_argument("--resolution", type=float, default=1.0)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--random-state", type=int, default=20260427)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    sclens_path = args.sclens_path.resolve()
    h5ad_path = args.h5ad.resolve()
    if not sclens_path.exists():
        raise FileNotFoundError(f"scLENSpy clone not found: {sclens_path}")
    if not h5ad_path.exists():
        raise FileNotFoundError(f"h5ad file not found: {h5ad_path}")

    sys.path.insert(0, str(sclens_path))

    import torch  # noqa: PLC0415
    from scLENS import scLENS  # noqa: PLC0415

    random.seed(args.random_state)
    np.random.seed(args.random_state)
    torch.manual_seed(args.random_state)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.random_state)
        torch.cuda.reset_peak_memory_stats()

    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    elif args.device == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("Requested CUDA device, but torch CUDA is unavailable")
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    adata = ad.read_h5ad(h5ad_path)
    if 0 < args.max_cells < adata.n_obs:
        rng = np.random.default_rng(args.random_state)
        idx = np.sort(rng.choice(adata.n_obs, size=args.max_cells, replace=False))
        adata = adata[idx].copy()

    label_key = _choose_label_key(adata, args.label_key)
    x = adata.layers[args.layer] if args.layer in adata.layers else adata.X
    x = _as_dense(x)
    frame = pd.DataFrame(x, index=adata.obs_names.astype(str), columns=adata.var_names.astype(str))

    status = "pass"
    error = ""
    embedding_shape = ""
    preprocessed_shape = ""
    robust_components = ""
    cluster_n = ""
    ari = "nan"
    nmi = "nan"
    start = time.perf_counter()
    try:
        model = scLENS(n_rand_matrix=args.n_rand_matrix, device=device)
        preprocessed = model.preprocess(frame, verb=True)
        embedding = model.fit_transform()
        preprocessed_shape = f"{preprocessed.shape[0]}x{preprocessed.shape[1]}"
        embedding_shape = f"{embedding.shape[0]}x{embedding.shape[1]}"
        robust_components = str(int(embedding.shape[1]))
        if embedding.shape[1] > 0 and embedding.shape[0] > args.n_neighbors:
            labels = graph_modularity_labels(
                embedding,
                n_neighbors=args.n_neighbors,
                resolution=args.resolution,
            )
            cluster_n = str(int(np.unique(labels).size))
            truth = adata.obs[label_key] if label_key else None
            ari = _safe_metric(truth, labels, adjusted_rand_score)
            nmi = _safe_metric(truth, labels, normalized_mutual_info_score)
    except Exception as exc:  # pragma: no cover - records third-party failures
        status = "fail"
        error = f"{type(exc).__name__}: {exc}"

    elapsed = time.perf_counter() - start
    cuda_memory_mb = ""
    if torch.cuda.is_available():
        cuda_memory_mb = f"{torch.cuda.max_memory_allocated() / 1024**2:.3f}"

    rows = [
        {
            "dataset_id": args.dataset_id,
            "method": "scLENSpy_smoke",
            "status": status,
            "h5ad_path": str(h5ad_path),
            "input_shape": f"{adata.n_obs}x{adata.n_vars}",
            "preprocessed_shape": preprocessed_shape,
            "embedding_shape": embedding_shape,
            "robust_components": robust_components,
            "cluster_n": cluster_n,
            "label_key": label_key,
            "ari": ari,
            "nmi": nmi,
            "n_rand_matrix": str(args.n_rand_matrix),
            "device": str(device),
            "torch_version": torch.__version__,
            "torch_cuda_available": str(torch.cuda.is_available()),
            "cuda_peak_memory_mb": cuda_memory_mb,
            "elapsed_sec": f"{elapsed:.3f}",
            "python_executable": sys.executable,
            "sclens_commit": _git_commit(sclens_path),
            "error": error,
        }
    ]
    output = args.output_dir / f"{args.dataset_id}_sclens_h5ad_smoke.tsv"
    _atomic_write_tsv(output, rows)
    print(output)
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
