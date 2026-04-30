# RMTGuard diagnostic no-call benchmark

This report validates that RMTGuard can distinguish a guarded diagnostic no-call from a positive cell-state discovery claim.

## Inputs

- Synthetic benchmark summary: `results/synthetic_benchmarks/synthetic_benchmark_summary.csv`
- No-call summary table: `results/no_call_benchmarks/no_call_summary.tsv`

## Hard-gate summary

- Required no-call/positive-call checks passed: 3/3
- Pure-null matrices are expected to return `diagnostic_no_call` and <=1 signal PC.
- Planted low-rank and rare-state matrices are expected to remain positive calls.

## Scenario decisions

| Scenario | Expected | Status | Reason | n_signal_pcs | accepted_embedding_pcs | ARI | Decision |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| pure_null | diagnostic_no_call | diagnostic_no_call | insufficient_signal_pcs_for_embedding | 1.000000 | 0.000000 | nan | pass |
| planted_low_rank | positive_call | ok |  | 5.000000 | 5.000000 | 1.000000 | pass |
| rare_state | positive_call | ok |  | 3.000000 | 7.000000 | 0.923465 | pass |
| batch_effect | stress_monitor | ok |  | 5.000000 | 6.000000 | 0.970152 | monitor |
| dropout_stress | stress_monitor | ok |  | 5.000000 | 6.000000 | 0.960390 | monitor |
| continuous_trajectory | stress_monitor | ok |  | 2.000000 | 3.000000 | 0.218230 | monitor |
| overclustering_stress | stress_monitor | ok |  | 4.000000 | 6.000000 | 0.912876 | monitor |

## Interpretation boundary

A `diagnostic_no_call` is not reported as a biological discovery. It is a guarded output indicating that the random-matrix noise-control layer found insufficient stable signal for downstream cell-state claims.
