# RMTGuard callability and no-call decision map

This report turns RMTGuard's diagnostic boundary into an auditable table for Figure 3 and manuscript review.

## Decision Rules

- `diagnostic_no_call`: insufficient signal/embedding PCs, or weak annotation recovery combined with unstable low cluster count.
- `callable_with_caveat`: callable run with a clear benchmark caveat, such as lower stability than the strongest comparator or low cluster count.
- `callable_bounded`: callable within the current evidence boundary.
- `positive_control_pass`: synthetic positive-control scenario passed.
- `stress_monitor`: synthetic stress test recorded for interpretation, not as a hard success gate.

## Decision Counts

- `callable_with_caveat`: 3
- `diagnostic_no_call`: 2
- `positive_control_pass`: 2
- `stress_monitor`: 4

## Figure Assets

- Source table: `results/callability/no_call_decision_map.tsv`
- Figure 3 source-data copy: `results/figures/source_data/figure3_callability_decision_map.tsv`
- Rendered PNG: `figures/manuscript/figure_no_call_decision_map.png`
- Rendered PDF: `figures/manuscript/figure_no_call_decision_map.pdf`
- Rendered TIFF: `figures/manuscript/figure_no_call_decision_map.tiff`
- Render manifest: `figures/manuscript/no_call_decision_map_manifest.tsv`

## Decision Map

| Unit type | Unit | Decision | Score | Main reason | Recommended claim |
| --- | --- | --- | ---: | --- | --- |
| synthetic | batch effect | stress_monitor | 0.50 | Stress scenario recorded for interpretation, not used as a hard no-call gate. | Use for stress-test interpretation only, not as a hard manuscript success gate. |
| synthetic | continuous trajectory | stress_monitor | 0.50 | Stress scenario recorded for interpretation, not used as a hard no-call gate. | Use for stress-test interpretation only, not as a hard manuscript success gate. |
| synthetic | dropout stress | stress_monitor | 0.50 | Stress scenario recorded for interpretation, not used as a hard no-call gate. | Use for stress-test interpretation only, not as a hard manuscript success gate. |
| synthetic | overclustering stress | stress_monitor | 0.50 | Stress scenario recorded for interpretation, not used as a hard no-call gate. | Use for stress-test interpretation only, not as a hard manuscript success gate. |
| synthetic | planted low-rank | positive_control_pass | 1.00 | Strong planted signal remained callable and recoverable. | Callable within current evidence boundary. |
| synthetic | pure null | diagnostic_no_call | 0.10 | insufficient signal pcs for embedding | Do not report as biological discovery; describe as diagnostic no-call or low-confidence context. |
| synthetic | rare state | positive_control_pass | 1.00 | Rare-state recovery passed the pre-specified ARI >=0.90 floor. | Callable within current evidence boundary. |
| real_public | Baron pancreas | callable_with_caveat | 0.55 | below strongest stability baseline | Report only as bounded benchmark evidence with explicit caveats. |
| real_public | Kang IFN-beta PBMC | callable_with_caveat | 0.55 | below strongest stability baseline | Report only as bounded benchmark evidence with explicit caveats. |
| real_public | PBMC3k | callable_with_caveat | 0.55 | low cluster count in the full run; below strongest stability baseline; no public annotation ARI available | Report only as bounded benchmark evidence with explicit caveats. |
| real_public | PBMC68k | diagnostic_no_call | 0.10 | low cluster count across subsampling; low cluster count in the full run; weak annotation recovery; below strongest stability baseline | Do not report as biological discovery; describe as diagnostic no-call or low-confidence context. |

## Interpretation Boundary

A no-call or caveated call is not a failed hidden result to relabel as a discovery. It is a manuscript-facing guardrail that limits the claim to what the data support.
