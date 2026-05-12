# scLENSpy Stability Pilot

Date: 2026-05-12
Project: RMTGuard
Purpose: convert the scLENS feasibility check into a repeated stability pilot
on the same prepared PBMC3k and Kang PBMC h5ad files used by RMTGuard.

## Bottom Line

Status: `pilot_10repeat_complete_stronger_nrand_pending`.

The Python scLENSpy comparator is now runnable as a repeated stability
benchmark on PBMC3k and Kang IFN-beta PBMC. Under this pilot setting
(`n_rand_matrix=2`, 10 repeats, 80% subsampling), scLENSpy produced lower
pairwise clustering stability than RMTGuard v3.2 on both tested datasets.

This is useful comparator evidence, but it is not a final manuscript-grade
claim about scLENS because the scLENSpy random-matrix ensemble was intentionally
kept small for a first local pilot. A stronger run with `n_rand_matrix>=20`,
plus at least the same reporting fields, is still required before any final
head-to-head language.

## Command

```bash
python benchmarks/run_sclens_stability_benchmark.py \
  --datasets pbmc3k_10x kang_ifnb_pbmc \
  --n-repeats 10 \
  --sample-fraction 0.8 \
  --n-rand-matrix 2 \
  --outdir results/sclens_stability_benchmarks \
  --force
```

## Environment

- scLENSpy repository: `external/scLENSpy`
- scLENSpy commit: `bf267224753af88c3f11bf31be1ee6916d3351b3`
- Python executable: `D:\BioSoft\python\Python311\python.exe`
- PyTorch: `2.7.0+cu118`
- PyTorch CUDA available: `True`
- Pilot setting: `n_rand_matrix=2`

## Pilot Results

| Dataset | Method | Mean pairwise ARI | 95% CI | Repeats | Mean clusters | Annotation ARI | Runtime/run | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---|
| PBMC3k | scLENSpy | 0.668 | 0.646-0.690 | 10 | 4.7 | NA | 7.94 s | Pilot, `n_rand_matrix=2` |
| Kang IFN-beta PBMC | scLENSpy | 0.549 | 0.513-0.585 | 10 | 4.6 | 0.535 | 6.97 s | Pilot, `n_rand_matrix=2` |
| PBMC3k | RMTGuard v3.2 | 0.867 | NA | 10 | 4.3 | NA | NA | Existing manuscript stability benchmark |
| Kang IFN-beta PBMC | RMTGuard v3.2 | 0.789 | NA | 10 | 4.9 | NA | NA | Existing manuscript stability benchmark |

Full machine-readable comparison:

```text
results/submission/sclens_vs_rmtguard_stability_pilot.tsv
```

Raw scLENSpy pilot outputs:

```text
results/sclens_stability_benchmarks/sclens_stability_summary.tsv
results/sclens_stability_benchmarks/sclens_stability_runs.tsv
results/sclens_stability_benchmarks/sclens_stability_pairwise.tsv
results/sclens_stability_benchmarks/sclens_stability_metadata.json
```

## Interpretation For The Paper

Direct evidence:

- scLENSpy can be run locally on the same prepared h5ad inputs used by
  RMTGuard.
- On this pilot setting, RMTGuard v3.2 has higher mean pairwise ARI than
  scLENSpy on PBMC3k and Kang IFN-beta PBMC.
- Kang IFN-beta PBMC has cell-type labels, and scLENSpy pilot annotation ARI
  was 0.535 under the selected graph clustering protocol.

Evidence boundary:

- Do not claim final superiority over scLENS from this run alone.
- Do not write that scLENS was fully benchmarked unless a stronger
  `n_rand_matrix>=20` run is completed or a runtime-limited justification is
  documented.
- The current result supports a next-step claim: "the direct RMT-like
  comparator is technically reachable and early pilot evidence does not remove
  the need for RMTGuard."

## Next Required Run

Run a stronger scLENSpy comparator setting if runtime permits:

```bash
python benchmarks/run_sclens_stability_benchmark.py \
  --datasets pbmc3k_10x kang_ifnb_pbmc \
  --n-repeats 10 \
  --sample-fraction 0.8 \
  --n-rand-matrix 20 \
  --outdir results/sclens_stability_benchmarks_nrand20 \
  --force
```

Acceptance for manuscript-grade comparator inclusion:

- identical prepared datasets;
- at least 10 repeats;
- confidence intervals for pairwise ARI and annotation metrics where labels
  exist;
- runtime and memory recorded;
- explicit statement of scLENSpy commit and `n_rand_matrix`.
