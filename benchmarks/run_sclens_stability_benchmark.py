"""Run repeated scLENSpy stability benchmarks on prepared h5ad datasets.

Author: RMTGuard development team
Date: 2026-05-12
Purpose: Add a direct scLENS/scLENSpy comparator to RMTGuard stability
benchmarks for PBMC3k and Kang PBMC.
Data source: Prepared AnnData files under data/processed/.
Method notes: scLENSpy is third-party software associated with Kim et al.,
Nature Communications 2024, DOI: 10.1038/s41467-024-47884-3. This script uses
the local clone under external/scLENSpy and records its commit. Results from
low n_rand_matrix values are pilot comparators, not final manuscript-grade
claims.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import random
import subprocess
import sys
import time
from itertools import combinations
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from rmtguard.cluster import graph_modularity_labels


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCLENS_PATH = ROOT / "external" / "scLENSpy"
DEFAULT_OUTDIR = ROOT / "results" / "sclens_stability_benchmarks"

DATASET_FILENAMES = {
    "pbmc3k_10x": "pbmc3k_10x.h5ad",
    "kang_ifnb_pbmc": "kang_ifnb_pbmc.h5ad",
}


def _write_tsv_atomic(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row}) if rows else ["empty"]
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)
    tmp.replace(path)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


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


def _choose_label_key(adata: ad.AnnData, requested: str) -> str:
    if requested != "auto":
        return requested if requested in adata.obs else ""
    for key in ("cell_type", "celltype", "seurat_annotations", "cell", "label"):
        if key in adata.obs and adata.obs[key].astype(str).nunique() > 1:
            return key
    return ""


def _safe_metric(labels_true, labels_pred, metric) -> float:
    if labels_true is None:
        return float("nan")
    truth = np.asarray(labels_true).astype(str)
    pred = np.asarray(labels_pred).astype(str)
    if truth.size == 0 or np.unique(truth).size < 2 or pred.size != truth.size:
        return float("nan")
    return float(metric(truth, pred))


def _set_seeds(seed: int, torch_module) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch_module.manual_seed(seed)
    if torch_module.cuda.is_available():
        torch_module.cuda.manual_seed_all(seed)
        torch_module.cuda.empty_cache()
        torch_module.cuda.reset_peak_memory_stats()


def _run_sclens_once(
    adata: ad.AnnData,
    selected: np.ndarray,
    label_key: str,
    args: argparse.Namespace,
    scLENS,
    torch_module,
) -> dict:
    seed = int(args.random_state + int(args.current_run_id))
    _set_seeds(seed, torch_module)

    if args.device == "auto":
        device = torch_module.device("cuda" if torch_module.cuda.is_available() else "cpu")
    elif args.device == "cuda":
        if not torch_module.cuda.is_available():
            raise RuntimeError("Requested CUDA device, but torch CUDA is unavailable")
        device = torch_module.device("cuda")
    else:
        device = torch_module.device("cpu")

    subset = adata[selected].copy()
    x = subset.layers[args.layer] if args.layer in subset.layers else subset.X
    x = _as_dense(x)
    frame = pd.DataFrame(
        x,
        index=subset.obs_names.astype(str),
        columns=subset.var_names.astype(str),
    )

    start = time.perf_counter()
    status = "pass"
    error = ""
    preprocessed_shape = ""
    embedding_shape = ""
    robust_components = 0
    labels = np.zeros(frame.shape[0], dtype=int)

    try:
        model = scLENS(n_rand_matrix=args.n_rand_matrix, device=device)
        if args.quiet_third_party:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
                io.StringIO()
            ):
                preprocessed = model.preprocess(frame, verb=False)
                embedding = model.fit_transform()
        else:
            preprocessed = model.preprocess(frame, verb=True)
            embedding = model.fit_transform()
        preprocessed_shape = f"{preprocessed.shape[0]}x{preprocessed.shape[1]}"
        embedding_shape = f"{embedding.shape[0]}x{embedding.shape[1]}"
        robust_components = int(embedding.shape[1])
        if robust_components > 0 and embedding.shape[0] > args.n_neighbors:
            labels = graph_modularity_labels(
                embedding,
                n_neighbors=args.n_neighbors,
                resolution=args.resolution,
            )
    except Exception as exc:  # pragma: no cover - records third-party failures
        status = "fail"
        error = f"{type(exc).__name__}: {exc}"

    elapsed = time.perf_counter() - start
    cuda_memory_mb = float("nan")
    if torch_module.cuda.is_available():
        cuda_memory_mb = float(torch_module.cuda.max_memory_allocated() / 1024**2)

    truth = subset.obs[label_key] if label_key else None
    ari = _safe_metric(truth, labels, adjusted_rand_score)
    nmi = _safe_metric(truth, labels, normalized_mutual_info_score)

    return {
        "status": status,
        "seed": seed,
        "n_cells": int(frame.shape[0]),
        "input_genes": int(frame.shape[1]),
        "preprocessed_shape": preprocessed_shape,
        "embedding_shape": embedding_shape,
        "robust_components": int(robust_components),
        "cluster_n": int(np.unique(labels).size),
        "label_key": label_key,
        "annotation_ari": ari,
        "annotation_nmi": nmi,
        "elapsed_sec": float(elapsed),
        "cuda_peak_memory_mb": cuda_memory_mb,
        "device": str(device),
        "cell_indices": selected.astype(int).tolist(),
        "labels": np.asarray(labels).astype(str).tolist(),
        "error": error,
    }


def _pairwise_records(dataset_id: str, run_rows: list[dict]) -> list[dict]:
    records = []
    successful = [row for row in run_rows if row.get("status") == "pass"]
    for left, right in combinations(successful, 2):
        left_map = {cell: label for cell, label in zip(left["cell_indices"], left["labels"])}
        right_map = {cell: label for cell, label in zip(right["cell_indices"], right["labels"])}
        common = sorted(set(left_map) & set(right_map))
        if len(common) < 5:
            continue
        records.append(
            {
                "dataset_id": dataset_id,
                "method": "scLENSpy",
                "left_run_id": int(left["run_id"]),
                "right_run_id": int(right["run_id"]),
                "pair_key": f"{left['run_id']}__{right['run_id']}",
                "overlap_n": int(len(common)),
                "pairwise_ari": float(
                    adjusted_rand_score(
                        [left_map[i] for i in common],
                        [right_map[i] for i in common],
                    )
                ),
            }
        )
    return records


def _mean_sd_ci(values: list[float]) -> tuple[float, float, float, float]:
    arr = np.asarray([v for v in values if np.isfinite(v)], dtype=float)
    if arr.size == 0:
        return float("nan"), float("nan"), float("nan"), float("nan")
    mean = float(np.mean(arr))
    sd = float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0
    half_width = float(1.96 * sd / np.sqrt(arr.size)) if arr.size > 1 else 0.0
    return mean, sd, mean - half_width, mean + half_width


def _summary_row(
    dataset_id: str,
    runs: list[dict],
    pairwise: list[dict],
    args: argparse.Namespace,
    sclens_commit: str,
    torch_module,
) -> dict:
    pair_values = [float(row["pairwise_ari"]) for row in pairwise]
    mean_ari, sd_ari, ci_low, ci_high = _mean_sd_ci(pair_values)
    annotation_aris = [float(row["annotation_ari"]) for row in runs]
    annotation_nmis = [float(row["annotation_nmi"]) for row in runs]
    mean_ann_ari, _, ann_ari_low, ann_ari_high = _mean_sd_ci(annotation_aris)
    mean_ann_nmi, _, ann_nmi_low, ann_nmi_high = _mean_sd_ci(annotation_nmis)
    cluster_ns = [float(row["cluster_n"]) for row in runs if row.get("status") == "pass"]
    runtime = [float(row["elapsed_sec"]) for row in runs if row.get("status") == "pass"]
    memory = [float(row["cuda_peak_memory_mb"]) for row in runs if row.get("status") == "pass"]
    robust = [float(row["robust_components"]) for row in runs if row.get("status") == "pass"]
    return {
        "dataset_id": dataset_id,
        "method": "scLENSpy",
        "status": "pass" if all(row.get("status") == "pass" for row in runs) else "partial_or_fail",
        "n_repeats": int(args.n_repeats),
        "successful_repeats": int(sum(row.get("status") == "pass" for row in runs)),
        "sample_fraction": float(args.sample_fraction),
        "n_rand_matrix": int(args.n_rand_matrix),
        "mean_pairwise_ari": mean_ari,
        "sd_pairwise_ari": sd_ari,
        "ci95_pairwise_ari_low": ci_low,
        "ci95_pairwise_ari_high": ci_high,
        "pairwise_n": int(len(pairwise)),
        "mean_cluster_n": float(np.mean(cluster_ns)) if cluster_ns else float("nan"),
        "sd_cluster_n": float(np.std(cluster_ns, ddof=1)) if len(cluster_ns) > 1 else 0.0,
        "mean_robust_components": float(np.mean(robust)) if robust else float("nan"),
        "mean_annotation_ari": mean_ann_ari,
        "ci95_annotation_ari_low": ann_ari_low,
        "ci95_annotation_ari_high": ann_ari_high,
        "mean_annotation_nmi": mean_ann_nmi,
        "ci95_annotation_nmi_low": ann_nmi_low,
        "ci95_annotation_nmi_high": ann_nmi_high,
        "mean_runtime_sec": float(np.mean(runtime)) if runtime else float("nan"),
        "mean_cuda_peak_memory_mb": float(np.mean(memory)) if memory else float("nan"),
        "torch_version": torch_module.__version__,
        "torch_cuda_available": bool(torch_module.cuda.is_available()),
        "sclens_commit": sclens_commit,
        "pilot_status": "pilot_n_rand_matrix_lt_20" if args.n_rand_matrix < 20 else "manuscript_grade_n_rand_matrix",
    }


def _dataset_paths(processed_dir: Path) -> dict[str, Path]:
    return {dataset_id: processed_dir / filename for dataset_id, filename in DATASET_FILENAMES.items()}


def _checkpoint_paths(outdir: Path, dataset_id: str) -> tuple[Path, Path, Path]:
    return (
        outdir / f"{dataset_id}_sclens_stability_summary.tsv",
        outdir / f"{dataset_id}_sclens_stability_runs.tsv",
        outdir / f"{dataset_id}_sclens_stability_pairwise.tsv",
    )


def _run_dataset(
    dataset_id: str,
    path: Path,
    args: argparse.Namespace,
    scLENS,
    torch_module,
    sclens_commit: str,
) -> tuple[list[dict], list[dict], list[dict]]:
    summary_path, runs_path, pairwise_path = _checkpoint_paths(args.outdir, dataset_id)
    if (
        not args.force
        and summary_path.exists()
        and runs_path.exists()
        and pairwise_path.exists()
    ):
        return _read_tsv(summary_path), _read_tsv(runs_path), _read_tsv(pairwise_path)

    adata = ad.read_h5ad(path)
    label_key = _choose_label_key(adata, args.label_key)
    rng = np.random.default_rng(args.random_state)
    n_sample = max(10, int(round(adata.n_obs * args.sample_fraction)))
    n_sample = min(n_sample, adata.n_obs)
    runs = []

    for run_id in range(args.n_repeats):
        selected = np.sort(rng.choice(adata.n_obs, size=n_sample, replace=False))
        args.current_run_id = run_id
        print(f"[scLENSpy] {dataset_id} run {run_id + 1}/{args.n_repeats} cells={n_sample}")
        run = _run_sclens_once(adata, selected, label_key, args, scLENS, torch_module)
        runs.append({"dataset_id": dataset_id, "run_id": run_id, "method": "scLENSpy", **run})

    pairwise = _pairwise_records(dataset_id, runs)
    summary = [_summary_row(dataset_id, runs, pairwise, args, sclens_commit, torch_module)]

    run_rows = [
        {key: value for key, value in row.items() if key not in {"cell_indices", "labels"}}
        for row in runs
    ]
    full_run_rows = [
        {
            **row,
            "cell_indices": json.dumps(row["cell_indices"], separators=(",", ":")),
            "labels": json.dumps(row["labels"], separators=(",", ":")),
        }
        for row in runs
    ]
    _write_tsv_atomic(summary_path, summary)
    _write_tsv_atomic(runs_path, run_rows)
    _write_tsv_atomic(outdir_labels_path(args.outdir, dataset_id), full_run_rows)
    _write_tsv_atomic(pairwise_path, pairwise)
    return summary, run_rows, pairwise


def outdir_labels_path(outdir: Path, dataset_id: str) -> Path:
    return outdir / f"{dataset_id}_sclens_stability_run_labels.tsv"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", type=Path, default=ROOT / "data" / "processed")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--datasets", nargs="+", default=["pbmc3k_10x", "kang_ifnb_pbmc"])
    parser.add_argument("--sclens-path", type=Path, default=DEFAULT_SCLENS_PATH)
    parser.add_argument("--layer", default="counts")
    parser.add_argument("--label-key", default="auto")
    parser.add_argument("--n-repeats", type=int, default=10)
    parser.add_argument("--sample-fraction", type=float, default=0.8)
    parser.add_argument("--n-rand-matrix", type=int, default=2)
    parser.add_argument("--n-neighbors", type=int, default=15)
    parser.add_argument("--resolution", type=float, default=1.0)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--random-state", type=int, default=20260427)
    parser.add_argument("--quiet-third-party", action="store_true", default=True)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    sclens_path = args.sclens_path.resolve()
    if not sclens_path.exists():
        raise FileNotFoundError(f"scLENSpy clone not found: {sclens_path}")
    sys.path.insert(0, str(sclens_path))

    import torch  # noqa: PLC0415
    from scLENS import scLENS  # noqa: PLC0415

    paths = _dataset_paths(args.processed_dir)
    sclens_commit = _git_commit(sclens_path)
    summary_rows: list[dict] = []
    run_rows: list[dict] = []
    pairwise_rows: list[dict] = []

    for dataset_id in args.datasets:
        if dataset_id not in paths:
            raise KeyError(f"Unknown dataset '{dataset_id}'. Available: {sorted(paths)}")
        if not paths[dataset_id].exists():
            raise FileNotFoundError(f"Prepared dataset not found: {paths[dataset_id]}")
        summary, runs, pairwise = _run_dataset(
            dataset_id, paths[dataset_id], args, scLENS, torch, sclens_commit
        )
        summary_rows.extend(summary)
        run_rows.extend(runs)
        pairwise_rows.extend(pairwise)

    summary_path = args.outdir / "sclens_stability_summary.tsv"
    runs_path = args.outdir / "sclens_stability_runs.tsv"
    pairwise_path = args.outdir / "sclens_stability_pairwise.tsv"
    metadata_path = args.outdir / "sclens_stability_metadata.json"
    _write_tsv_atomic(summary_path, summary_rows)
    _write_tsv_atomic(runs_path, run_rows)
    _write_tsv_atomic(pairwise_path, pairwise_rows)
    _write_json_atomic(
        metadata_path,
        {
            **vars(args),
            "sclens_commit": sclens_commit,
            "python_executable": sys.executable,
            "torch_version": torch.__version__,
            "torch_cuda_available": torch.cuda.is_available(),
            "dataset_filenames": DATASET_FILENAMES,
        },
    )

    print(summary_path)
    print(runs_path)
    print(pairwise_path)
    print(metadata_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
