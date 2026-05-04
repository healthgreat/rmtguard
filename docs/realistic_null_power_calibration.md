# Realistic null and rare-state power calibration

This manuscript-grade calibration upgrades the synthetic evidence from pure Gaussian-like nulls to count-based scRNA-seq-like nulls.

## Scope

- Cells per run: 220
- Genes per run: 500
- Repeats per setting: 50
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
| gene_permutation_null | 50 | 0.000 (0.000-0.000) | 0.000 (0.000-0.000) | 0.00 | 1.000 |
| library_multinomial_null | 50 | 0.000 (0.000-0.000) | 0.000 (0.000-0.000) | 1.00 | 1.000 |
| library_stratified_gene_null | 50 | 0.000 (0.000-0.000) | 0.000 (0.000-0.000) | 1.00 | 1.000 |

## Rare-State Power Summary

| Prevalence | Effect size | Repeats | Power | Mean ARI | Rare F1 | fixed 30 PC rare F1 | Guard selected | No-call rate |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.020 | 2.50 | 50 | 0.120 (0.029-0.211) | 0.007 (0.001-0.012) | 0.151 (0.064-0.239) | 0.054 (0.051-0.057) | 0.120 | 0.880 |
| 0.020 | 4.00 | 50 | 0.520 (0.380-0.660) | 0.030 (0.022-0.038) | 0.537 (0.402-0.672) | 0.052 (0.048-0.055) | 0.520 | 0.480 |
| 0.020 | 6.00 | 50 | 0.880 (0.789-0.971) | 0.051 (0.045-0.057) | 0.884 (0.797-0.972) | 0.060 (0.056-0.064) | 0.880 | 0.120 |
| 0.040 | 2.50 | 50 | 0.840 (0.737-0.943) | 0.106 (0.098-0.114) | 0.938 (0.899-0.978) | 0.103 (0.097-0.108) | 1.000 | 0.000 |
| 0.040 | 4.00 | 50 | 1.000 (1.000-1.000) | 0.118 (0.113-0.122) | 1.000 (1.000-1.000) | 0.114 (0.108-0.121) | 1.000 | 0.000 |
| 0.040 | 6.00 | 50 | 1.000 (1.000-1.000) | 0.118 (0.113-0.124) | 1.000 (1.000-1.000) | 0.138 (0.129-0.146) | 1.000 | 0.000 |
| 0.080 | 2.50 | 50 | 0.980 (0.941-1.000) | 0.198 (0.185-0.210) | 0.986 (0.958-1.000) | 0.210 (0.177-0.243) | 0.980 | 0.000 |
| 0.080 | 4.00 | 50 | 0.980 (0.941-1.000) | 0.198 (0.186-0.210) | 0.985 (0.955-1.000) | 0.385 (0.293-0.477) | 0.980 | 0.000 |
| 0.080 | 6.00 | 50 | 0.980 (0.941-1.000) | 0.202 (0.192-0.212) | 0.992 (0.975-1.000) | 0.563 (0.462-0.663) | 0.980 | 0.000 |

## Interpretation Boundary

- Maximum observed false signal rate in this manuscript-grade run: 0.000.
- Maximum observed false call rate in this manuscript-grade run: 0.000.
- Minimum power at the lowest prevalence grid in this manuscript-grade run: 0.120.
- These values are evidence for calibration only. They support bounded noise-control and power-curve claims, not a guarantee of broad superiority or universal rare-state recovery.
