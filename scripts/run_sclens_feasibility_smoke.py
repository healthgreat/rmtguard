from __future__ import annotations

"""Run a minimal scLENSpy feasibility smoke test.

Author: RMTGuard development team
Date: 2026-05-12
Purpose: Verify whether the Python implementation of scLENS can be imported
and run locally before adding it to RMTGuard head-to-head benchmarks.
Data source: A small scLENSpy CSV example or a user-provided cell-by-gene CSV.
Method notes: scLENS/scLENSpy is third-party software by Kim et al. (Nature
Communications 2024, DOI: 10.1038/s41467-024-47884-3). This script does not
vendor scLENS code; it expects a local clone under external/scLENSpy or a path
provided by --sclens-path.
"""

import argparse
import csv
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCLENS_PATH = ROOT / "external" / "scLENSpy"
DEFAULT_INPUT = DEFAULT_SCLENS_PATH / "data" / "z_data_785.csv.gz"
DEFAULT_OUTPUT = ROOT / "results" / "submission" / "sclens_feasibility_smoke.tsv"


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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sclens-path", type=Path, default=DEFAULT_SCLENS_PATH)
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--n-rand-matrix", type=int, default=2)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--random-state", type=int, default=20260427)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    sclens_path = args.sclens_path.resolve()
    input_csv = args.input_csv.resolve()

    if not sclens_path.exists():
        raise FileNotFoundError(f"scLENSpy clone not found: {sclens_path}")
    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

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
            raise RuntimeError("Requested CUDA device, but torch.cuda.is_available() is False")
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    start = time.perf_counter()
    status = "pass"
    error = ""
    input_shape = ""
    preprocessed_shape = ""
    embedding_shape = ""
    robust_components = ""

    try:
        data = pd.read_csv(input_csv, index_col=0)
        input_shape = f"{data.shape[0]}x{data.shape[1]}"
        model = scLENS(n_rand_matrix=args.n_rand_matrix, device=device)
        preprocessed = model.preprocess(data, verb=True)
        embedding = model.fit_transform()
        preprocessed_shape = f"{preprocessed.shape[0]}x{preprocessed.shape[1]}"
        embedding_shape = f"{embedding.shape[0]}x{embedding.shape[1]}"
        robust_components = str(int(embedding.shape[1]))
    except Exception as exc:  # pragma: no cover - records third-party failures
        status = "fail"
        error = f"{type(exc).__name__}: {exc}"

    elapsed = time.perf_counter() - start
    cuda_memory_mb = ""
    if torch.cuda.is_available():
        cuda_memory_mb = f"{torch.cuda.max_memory_allocated() / 1024**2:.3f}"

    rows = [
        {
            "check_id": "sclens_python_smoke",
            "status": status,
            "input_csv": str(input_csv),
            "input_shape": input_shape,
            "preprocessed_shape": preprocessed_shape,
            "embedding_shape": embedding_shape,
            "robust_components": robust_components,
            "n_rand_matrix": str(args.n_rand_matrix),
            "device": str(device),
            "torch_version": torch.__version__,
            "torch_cuda_available": str(torch.cuda.is_available()),
            "cuda_peak_memory_mb": cuda_memory_mb,
            "elapsed_sec": f"{elapsed:.3f}",
            "python_executable": sys.executable,
            "sclens_path": str(sclens_path),
            "sclens_commit": _git_commit(sclens_path),
            "julia_available": str(shutil.which("julia") is not None),
            "error": error,
        }
    ]
    _atomic_write_tsv(args.output, rows)
    print(args.output)
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
