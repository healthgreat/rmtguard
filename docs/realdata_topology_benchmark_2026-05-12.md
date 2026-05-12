# Real-data topology benchmark on Paul15 hematopoiesis

Date: 2026-05-12
Project: RMTGuard

## Scope

- Dataset: `paul15_hematopoiesis` from the prepared public h5ad input.
- Repeats: `10` subsampling repeats.
- Subsampling fraction: `0.8`.
- Methods: `rmtguard, rmtguard_strict_signal, fixed_pcs_30, fixed_pcs_50`.
- Reference: annotation-derived Paul15 cluster/lineage graph, not
  experimentally measured pseudotime.

## Summary Table

| Method | Tree rho | Edge recall | Neighbor tree distance | Same-lineage kNN | Annotation ARI | Mean clusters | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| Fixed 30 PCs | 0.246 | 0.639 | 1.289 | 0.702 | 0.176 | 4.20 | comparator |
| Fixed 50 PCs | 0.236 | 0.650 | 1.435 | 0.675 | 0.088 | 5.10 | comparator |
| RMTGuard | 0.232 | 0.600 | 1.153 | 0.737 | 0.270 | 5.70 | real_topology_caveat |
| RMTGuard strict | 0.233 | 0.589 | 1.147 | 0.739 | 0.265 | 5.60 | comparator |

## Interpretation Boundary

- This is a real public-data topology monitor, not a de novo trajectory
  inference claim.
- The Paul15 cluster graph is annotation-derived. It can support a
  manuscript statement that RMTGuard was checked against a known
  hematopoietic annotation structure, but it cannot prove new lineage
  biology.
- Use these results to strengthen the benchmark evidence arc only if the
  figure and source data remain claim-bounded.

## Outputs

- Detail table: `results/realdata_topology/realdata_topology_detail.tsv`
- Summary table: `results/realdata_topology/realdata_topology_summary.tsv`
- Figure source data: `results/figures/source_data/figure_realdata_topology_source.tsv`
- Figure asset: `figures/manuscript/figure_realdata_topology_benchmark.png`
- Figure asset: `figures/manuscript/figure_realdata_topology_benchmark.pdf`
- Figure asset: `figures/manuscript/figure_realdata_topology_benchmark.tiff`
- Figure asset: `figures/manuscript/figure_realdata_topology_manifest.tsv`
