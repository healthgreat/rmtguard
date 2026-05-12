# CONCORD-style topology stress benchmark

Date: 2026-05-12
Project: RMTGuard

## Scope

- Scenarios: `linear_trajectory, branching_trajectory, cyclic_loop`
- Methods: `rmtguard, rmtguard_strict_signal, fixed_pcs_30, fixed_pcs_50`
- Repeats per scenario: `20`
- Cells/genes per run: `300` / `700`
- Topology kNN size: `15`

## Summary Table

| Scenario | Method | kNN recall | Trustworthiness | Continuity | Distance rho | Mean clusters | Status |
|---|---|---:|---:|---:|---:|---:|---|
| branching_trajectory | fixed_pcs_30 | 0.223 | 0.872 | 0.757 | 0.328 | 3.50 | comparator |
| branching_trajectory | fixed_pcs_50 | 0.198 | 0.847 | 0.706 | 0.229 | 3.80 | comparator |
| branching_trajectory | rmtguard | 0.301 | 0.924 | 0.881 | 0.669 | 3.50 | topology_preserved_monitor |
| branching_trajectory | rmtguard_strict_signal | 0.325 | 0.935 | 0.900 | 0.725 | 3.75 | comparator |
| cyclic_loop | fixed_pcs_30 | 0.314 | 0.917 | 0.837 | 0.436 | 4.05 | comparator |
| cyclic_loop | fixed_pcs_50 | 0.272 | 0.899 | 0.789 | 0.347 | 4.15 | comparator |
| cyclic_loop | rmtguard | 0.422 | 0.951 | 0.933 | 0.661 | 3.55 | topology_preserved_monitor |
| cyclic_loop | rmtguard_strict_signal | 0.429 | 0.953 | 0.937 | 0.676 | 3.60 | comparator |
| linear_trajectory | fixed_pcs_30 | 0.201 | 0.879 | 0.758 | 0.458 | 3.90 | comparator |
| linear_trajectory | fixed_pcs_50 | 0.178 | 0.860 | 0.712 | 0.373 | 4.25 | comparator |
| linear_trajectory | rmtguard | 0.301 | 0.933 | 0.881 | 0.754 | 3.00 | topology_preserved_monitor |
| linear_trajectory | rmtguard_strict_signal | 0.343 | 0.947 | 0.901 | 0.801 | 3.00 | comparator |

## Interpretation Boundary

- This is synthetic topology stress evidence, not proof of biological
  trajectory correctness in every real dataset.
- RMTGuard should be described as monitoring topology/no-call behavior;
  do not claim that it is a dedicated trajectory inference method.
- Strong results here support keeping Figure 2/3 topology panels in the
  Nature Methods-facing evidence arc; weak results should be reported as
  fragmentation risk rather than hidden.

## Outputs

- Detail table: `results/topology_stress_benchmarks/topology_stress_detail.tsv`
- Summary table: `results/topology_stress_benchmarks/topology_stress_summary.tsv`

## Next Use

Use this report to update the CONCORD/scLENS benchmark upgrade checklist
and later regenerate Figure 2/5 source-data panels after benchmark freeze.
