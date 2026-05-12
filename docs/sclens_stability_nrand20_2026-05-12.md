# scLENSpy n_rand_matrix=20 Stability Comparator

Date: 2026-05-12
Project: RMTGuard
Purpose: upgrade the scLENSpy direct RMT-like comparator from a pilot
`n_rand_matrix=2` run to a stronger `n_rand_matrix=20` repeated stability
benchmark on PBMC3k and Kang IFN-beta PBMC.

## Bottom Line

Status: `complete_nrand20_10repeat_pbmc3k_kang`.

The stronger scLENSpy setting completed successfully on both prepared h5ad
datasets. Compared with the earlier pilot, `n_rand_matrix=20` modestly
improved scLENSpy stability, but RMTGuard v3.2 still showed higher mean
pairwise ARI on PBMC3k and Kang IFN-beta PBMC under the same 10-repeat,
80%-subsampling design.

This closes the first direct RMT-like comparator blocker for PBMC3k and Kang.
It does not close the full Nature Methods evidence gate because the broader
benchmark still needs realistic count-preserving nulls, topology stress tests,
and more datasets.

## Command

```bash
python benchmarks/run_sclens_stability_benchmark.py \
  --datasets pbmc3k_10x kang_ifnb_pbmc \
  --n-repeats 10 \
  --sample-fraction 0.8 \
  --n-rand-matrix 20 \
  --outdir results/sclens_stability_benchmarks_nrand20 \
  --force
```

## Runtime And Environment

- Wall time: approximately 4.5 minutes for two datasets and 20 total repeats.
- scLENSpy commit: `bf267224753af88c3f11bf31be1ee6916d3351b3`
- PyTorch: `2.7.0+cu118`
- PyTorch CUDA available: `True`
- CUDA warning: CuPy could not detect `CUDA_PATH`, but the run completed using
  PyTorch CUDA.
- Mean peak CUDA memory:
  - PBMC3k: `314.44 MB`
  - Kang IFN-beta PBMC: `232.48 MB`

## Results

| Dataset | Method | Mean pairwise ARI | 95% CI | Repeats | Mean clusters | Annotation ARI | Runtime/run | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---|
| PBMC3k | RMTGuard v3.2 | 0.867 | NA | 10 | 4.3 | NA | NA | Existing manuscript stability benchmark |
| PBMC3k | scLENSpy `n_rand_matrix=20` | 0.694 | 0.667-0.721 | 10 | 4.3 | NA | 13.44 s | Direct RMT-like comparator |
| Kang IFN-beta PBMC | RMTGuard v3.2 | 0.789 | NA | 10 | 4.9 | NA | NA | Existing manuscript stability benchmark |
| Kang IFN-beta PBMC | scLENSpy `n_rand_matrix=20` | 0.586 | 0.551-0.622 | 10 | 4.4 | 0.541 | 12.86 s | Direct RMT-like comparator |

Machine-readable comparison:

```text
results/submission/sclens_vs_rmtguard_stability_nrand20.tsv
```

Raw output files:

```text
results/sclens_stability_benchmarks_nrand20/sclens_stability_summary.tsv
results/sclens_stability_benchmarks_nrand20/sclens_stability_runs.tsv
results/sclens_stability_benchmarks_nrand20/sclens_stability_pairwise.tsv
results/sclens_stability_benchmarks_nrand20/sclens_stability_metadata.json
```

## Evidence Boundary

Direct evidence:

- scLENSpy can be run locally with a stronger random-matrix ensemble setting.
- On PBMC3k and Kang IFN-beta PBMC, RMTGuard v3.2 has higher 10-repeat
  subsampling stability than scLENSpy under this graph-clustering protocol.
- The direct competitor result is no longer limited to the weak
  `n_rand_matrix=2` pilot.

Still not supported:

- Broad superiority over all Scanpy/Seurat/fixed-PC/elbow workflows.
- Atlas-scale scLENS comparison.
- A Nature Methods-ready claim without realistic null and topology stress
  evidence.

## Manuscript Use

Acceptable wording:

```text
In a direct two-dataset comparison against the Python implementation of scLENS
using n_rand_matrix=20, RMTGuard showed higher subsampling stability on PBMC3k
and Kang IFN-beta PBMC, while we retained broader workflow comparisons and
diagnostic no-call boundaries as separate evidence layers.
```

Avoid:

```text
RMTGuard outperforms scLENS.
```

That sentence is too broad because only PBMC3k and Kang have been tested under
this direct comparator protocol.
