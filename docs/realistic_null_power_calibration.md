# Realistic null and rare-state power calibration

This draft calibration upgrades the synthetic evidence from pure Gaussian-like nulls to count-based scRNA-seq-like nulls.

## Scope

- Cells per run: 220
- Genes per run: 500
- Repeats per setting: 4
- False signal PC floor: >1 signal PCs
- Rare-state ARI floor: 0.8
- Rare-state F1 floor: 0.7
- Rare-state guard: adaptive_binary_split
- Rare-state guard fraction window: 0.015 to 0.15
- Rare-state guard separation/silhouette floors: 3.0 / 0.35

## Outputs

- null detail: `results/calibration/realistic_null_detail.tsv`
- null summary: `results/calibration/realistic_null_summary.tsv`
- power detail: `results/calibration/rare_state_power_detail.tsv`
- power summary: `results/calibration/rare_state_power_summary.tsv`

## Null Calibration Summary

| Null model | Repeats | False signal rate | False call rate | Mean signal PCs | No-call rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| gene_permutation_null | 4 | 0.000 | 0.000 | 0.00 | 1.000 |
| library_multinomial_null | 4 | 0.000 | 0.000 | 1.00 | 1.000 |
| library_stratified_gene_null | 4 | 0.000 | 0.000 | 1.00 | 1.000 |

## Rare-State Power Summary

| Prevalence | Effect size | Repeats | Power | Mean ARI | Rare F1 | fixed 30 PC rare F1 | Guard selected | No-call rate |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.020 | 2.50 | 4 | 0.250 | 0.010 | 0.277 | 0.061 | 0.250 | 0.750 |
| 0.020 | 4.00 | 4 | 0.500 | 0.028 | 0.518 | 0.050 | 0.500 | 0.500 |
| 0.020 | 6.00 | 4 | 1.000 | 0.054 | 1.000 | 0.077 | 1.000 | 0.000 |
| 0.040 | 2.50 | 4 | 0.750 | 0.095 | 0.904 | 0.098 | 1.000 | 0.000 |
| 0.040 | 4.00 | 4 | 1.000 | 0.111 | 1.000 | 0.124 | 1.000 | 0.000 |
| 0.040 | 6.00 | 4 | 1.000 | 0.130 | 1.000 | 0.150 | 1.000 | 0.000 |
| 0.080 | 2.50 | 4 | 1.000 | 0.178 | 1.000 | 0.177 | 1.000 | 0.000 |
| 0.080 | 4.00 | 4 | 1.000 | 0.187 | 1.000 | 0.404 | 1.000 | 0.000 |
| 0.080 | 6.00 | 4 | 1.000 | 0.196 | 1.000 | 1.000 | 1.000 | 0.000 |

## Interpretation Boundary

- Maximum observed false signal rate in this draft run: 0.000.
- Maximum observed false call rate in this draft run: 0.000.
- Minimum power at the lowest prevalence grid in this draft run: 0.250.
- These are draft local calibration values. They are useful for detecting failure modes and planning manuscript-grade runs, but final claims require more repeats and confidence intervals.
