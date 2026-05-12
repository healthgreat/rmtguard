# scLENS Feasibility Check

Date: 2026-05-12
Project: RMTGuard
Purpose: determine whether scLENS can be used as a direct RMT-like comparator
for RMTGuard benchmarks.

## Bottom Line

Status: `partial_pass_python_and_h5ad_smoke; julia_missing`.

The original Julia scLENS implementation was cloned successfully, but this
workstation currently has no `julia` command on PATH. The Python implementation
(`scLENSpy`) was cloned and passed a minimal smoke test on the bundled Zheng
example dataset.

This means scLENS is feasible as a comparator through the Python implementation
for the next benchmark phase, provided that we freeze the exact commit and
record the dependency/runtime environment. A manuscript-grade comparison still
requires repeated subsampling and confidence intervals.

## Local Repositories

- Julia scLENS clone: `external/scLENS`
- Julia scLENS commit: `e44017fad5cf55c539f87b6739bac28dbdc0f9c5`
- Python scLENSpy clone: `external/scLENSpy`
- Python scLENSpy commit: `bf267224753af88c3f11bf31be1ee6916d3351b3`

Both local clones are under `external/`, which is excluded from Git. The
project records commits and run scripts, not vendored third-party code.

## Environment Findings

- Julia availability: `False`; `julia --version` is not recognized.
- Python executable: `D:\BioSoft\python\Python311\python.exe`
- PyTorch: `2.7.0+cu118`
- CUDA through PyTorch: `True`
- Added missing small dependency: `tqdm-joblib 0.0.5`
- Pip cache was directed to `E:\BioSoft\pip-cache` during installation to avoid
  C-drive runtime/cache writes.

## Bundled Example Smoke Test

Command:

```bash
python scripts/run_sclens_feasibility_smoke.py
```

Input:

```text
external/scLENSpy/data/z_data_785.csv.gz
```

Result table:

```text
results/submission/sclens_feasibility_smoke.tsv
```

Observed output:

- Status: `pass`
- Input shape: `778x4803`
- Preprocessed shape: `778x4782`
- Embedding shape: `778x11`
- Robust components: `11`
- Device: `cuda`
- Peak CUDA memory: approximately `292 MB`
- Runtime: approximately `6.5 s`

## RMTGuard h5ad Smoke Tests

Adapter command:

```bash
python benchmarks/run_sclens_h5ad_smoke.py \
  --dataset-id pbmc3k_10x \
  --h5ad data/processed/pbmc3k_10x.h5ad \
  --n-rand-matrix 2 \
  --max-cells 1000

python benchmarks/run_sclens_h5ad_smoke.py \
  --dataset-id kang_ifnb_pbmc \
  --h5ad data/processed/kang_ifnb_pbmc.h5ad \
  --n-rand-matrix 2 \
  --max-cells 1000
```

Machine-readable outputs:

- `results/sclens_comparator/pbmc3k_10x_sclens_h5ad_smoke.tsv`
- `results/sclens_comparator/kang_ifnb_pbmc_sclens_h5ad_smoke.tsv`
- `results/submission/sclens_h5ad_smoke_summary.tsv`

Observed outputs:

| Dataset | Status | Input shape | Preprocessed shape | Embedding | Robust PCs | Cluster n | Label key | ARI | NMI | Runtime | Peak CUDA memory |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| PBMC3k | pass | 1000x13714 | 1000x7770 | 1000x9 | 9 | 5 | none | NA | NA | 13.485 s | 426.687 MB |
| Kang IFN-beta PBMC | pass | 1000x15701 | 1000x5813 | 1000x15 | 15 | 5 | cell | 0.571479 | 0.644012 | 12.327 s | 318.576 MB |

## Interpretation

This is a feasibility smoke test only. It proves that the Python implementation
can import and produce a scLENS embedding on a small bundled dataset. It does
not prove performance superiority, annotation recovery, stability, or
publication-grade comparability.

The next manuscript-grade step is to convert this adapter into a repeated
fair-comparison benchmark:

1. convert AnnData matrices to the cell-by-gene CSV/DataFrame format expected
   by scLENSpy;
2. run scLENSpy with frozen commit, seed, input preprocessing, and runtime log;
3. cluster the resulting `X_pca_sclens` embedding under the same graph and
   stability protocol as RMTGuard baselines;
4. report mean pairwise ARI, annotation ARI/NMI, cluster-number variance,
   runtime, and memory across at least 10 repeats.

## Current Gate Impact

The scLENS comparator gate moves from `pending` to
`in_progress_h5ad_smoke_pass_julia_missing`.

Nature Methods readiness is not unlocked by this smoke test. It only removes
one uncertainty: a direct RMT-like comparator is technically reachable through
Python scLENSpy on the same PBMC3k and Kang h5ad files used by RMTGuard.

## Sources

- scLENS paper: https://www.nature.com/articles/s41467-024-47884-3
- scLENS Julia repository: https://github.com/Mathbiomed/scLENS
- scLENSpy Python repository: https://github.com/Mathbiomed/scLENSpy
