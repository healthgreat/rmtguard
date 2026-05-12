# P0 Benchmark Upgrade Status After scLENSpy n_rand_matrix=20

Date: 2026-05-12
Project: RMTGuard
Purpose: reconcile the CONCORD/scLENS benchmark-upgrade checklist after the
direct scLENSpy comparator run and the already-completed realistic null/power
calibration assets.

## Bottom Line

The P0 benchmark story is stronger than the older checklist suggested:

- Direct scLENS-like comparator: complete on PBMC3k and Kang using Python
  scLENSpy with `n_rand_matrix=20`.
- Realistic count-preserving null: complete at 50 repeats with CI and an
  explicit rare-state claim boundary.
- Component ablation: complete at the current 20-repeat synthetic and
  real-data annotation layer, according to `docs/p0_science_sprint_status.md`.

The remaining high-impact methods gap is not "no calibration". After the
20-repeat topology run, it is now:

1. optional real-data topology validation if we want a stronger Nature Methods
   argument;
2. final figure/source-data regeneration after benchmark freeze;
3. author-controlled PDAC/TME route confirmation.

## Evidence Snapshot

| Work package | Current status | Evidence | Interpretation |
|---|---|---|---|
| scLENSpy direct comparator | `complete_nrand20_10repeat_pbmc3k_kang` | `docs/sclens_stability_nrand20_2026-05-12.md` | RMTGuard is more stable than scLENSpy on PBMC3k and Kang under the tested protocol. |
| realistic count-preserving null | `done_with_limit_50repeat_ci` | `docs/realistic_null_power_calibration.md` | False signal/call rates are controlled in tested null families. |
| rare-state power grid | `done_with_limit_50repeat_ci` | `docs/rare_state_claim_boundary.md` | Moderate prevalence/effect settings are supported; lowest prevalence/weakest effect is an explicit limitation. |
| component ablation | `done_current_20repeat_ci` | `docs/p0_science_sprint_status.md` | Current component-level evidence exists; avoid universal component-necessity wording. |
| CONCORD-style topology stress | `done_20repeat_line_branch_loop` | `docs/topology_stress_benchmark_2026-05-12.md` | RMTGuard preserves synthetic line, branch, and loop topology better than fixed-PC baselines across kNN recall, trustworthiness, continuity, and distance-rank metrics. |
| PBMC3k/Kang comparator refresh | `partial_scLENSpy_nrand20_added` | `results/submission/sclens_vs_rmtguard_stability_nrand20.tsv` | Direct scLENSpy is added; broader Seurat/Scanpy CI refresh remains useful before final freeze. |

## Current 20-50 JIF Distance

For a strict 20-50 JIF target, the project is no longer blocked by public
release, direct scLENS-like comparator, basic null calibration, or synthetic
topology stress evidence. The current distance is now mainly scientific
positioning and final manuscript defensibility:

- Nature Methods remains high risk unless topology/no-call evidence is made
  visually compelling and the claim is kept as diagnostic random-matrix
  callability rather than broad superiority.
- Genome Biology-style fallback is increasingly realistic if the paper is
  framed as a reproducible genomics workflow with transparent no-call
  boundaries.
- Bioinformatics/NAR Genomics and Bioinformatics remain safe fallbacks if the
  final novelty judgment is incremental.

## Next Action

Freeze the benchmark evidence and regenerate final source-data/figure tables,
or add one real public trajectory dataset if the Nature Methods route remains
the preferred target.
