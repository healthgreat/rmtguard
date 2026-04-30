# RMTGuard Nature Methods Benchmark Plan

## Primary Claim

RMTGuard improves reproducibility and noise control in scRNA-seq cell-state
discovery by allowing only RMT-supported structure to drive PCA, neighborhood
construction, and clustering.

## Algorithms and Ablations

- RMTGuard v2: MP edge plus Tracy-Widom proxy, optional permutation calibration,
  spectral-plateau HVG selection, noise-PC stability, and batch-aware
  residualization.
- Ablations: no biwhitening, no RMT edge, no noise-PC stability, fixed HVG,
  fixed PC count, and no batch residualization.
- Baselines: Scanpy default, Seurat default, fixed `n_pcs=30/50`, elbow,
  permutation/parallel PCA, JackStraw-like baseline where feasible, optional
  scVI latent baseline.

## Datasets

- Synthetic: pure null, planted low-rank signal, rare cell state, batch effect,
  dropout stress, continuous trajectory, and overclustering stress.
- Core public benchmarks: PBMC3k, PBMC68k/Zheng 2017, Kang IFN-beta PBMC, Baron
  pancreas, selected Tabula Sapiens tissues.
- PDAC/TME showcase: GSE154778 primary analysis and GSE263733 external
  validation.

Dataset order is fixed in `metadata/benchmark_phases.tsv`: PBMC3k and Kang
IFN-beta first, Baron pancreas and PBMC68k second, PDAC/TME third, and Tabula
Sapiens only if earlier results justify a Nature Methods submission.

Phase 1 entry points:

```bash
python scripts/prepare_phase1_datasets.py --dataset pbmc3k_10x --max-cells 1000
python benchmarks/run_phase1_benchmark.py --datasets pbmc3k_10x
python benchmarks/run_stability_benchmark.py --datasets pbmc3k_10x
```

Kang IFN-beta requires the GEO `GSE96583_RAW.tar` supplementary archive plus
batch2 gene and cell metadata files. The preparation script supports resumable
downloads through `.tmp` files for slow connections.

Smoke-scale benchmark outputs are useful for debugging but are not accepted as
Nature Methods gate evidence. Stability gate evidence requires at least 5
subsampling repeats and at least 500 mean cells per run.

Current PBMC3k evidence fails the stability gate. See
`docs/method_risk_log.md`. This should guide algorithm development before any
Nature Methods submission claim is made.

## Metrics

- Annotation recovery: ARI, NMI, homogeneity, completeness.
- Stability: seed sensitivity, bootstrap/subsampling ARI, cluster preservation.
- Noise control: selected signal PCs, MP bulk KS, null false-positive rate,
  permutation max-eigenvalue distribution.
- Biological coherence: marker enrichment, conserved marker recovery, pathway
  coherence, and PDAC/TME state interpretability.
- Usability: runtime, peak memory, install time, demo runtime, failed-run rate.

## Statistical Notes

- Treat datasets, not cells, as the primary independent units for method
  comparison.
- Use paired tests or bootstrap confidence intervals for method comparisons
  across datasets.
- Apply Benjamini-Hochberg correction within prespecified metric families.
- Report failures, memory limits, and parameter settings; do not omit difficult
  datasets silently.
