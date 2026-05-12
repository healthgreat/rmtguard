# RMTGuard Benchmark Upgrade Checklist From CONCORD and scLENS

Date: 2026-05-12

## Strategic Goal

Use CONCORD as the recent high-impact benchmark standard and scLENS as the
direct RMT-like competitor to harden RMTGuard before any Nature Methods or
Genome Biology decision.

## P0 Experiments

1. scLENS feasibility check
   - Goal: determine whether scLENS can be installed and run locally on PBMC3k
     and Kang PBMC.
   - Acceptance: installable workflow, exact versions recorded, runtime and
     memory captured, and either successful output or a documented blocker.
   - Reason: reviewers may ask whether RMTGuard is incremental versus scLENS.
   - Current status: Python scLENSpy smoke tests passed on the bundled Zheng
     example and on the prepared PBMC3k/Kang h5ad files; 10-repeat stability
     runs are complete for both `n_rand_matrix=2` and `n_rand_matrix=20`;
     Julia scLENS remains blocked because `julia` is not on PATH. See
     `docs/sclens_feasibility_check_2026-05-12.md` and
     `docs/sclens_stability_nrand20_2026-05-12.md`.

2. CONCORD-style topology stress simulation
   - Goal: add continuous trajectory, branch, and loop-like simulated
     structures.
   - Acceptance: report structure recovery metrics in addition to ARI/NMI.
   - Reason: high-impact embedding papers now test whether latent spaces
     preserve biological geometry, not only cluster agreement.

3. realistic count-preserving null
   - Goal: preserve library-size variation, dropout, and gene mean-variance
     structure while destroying biological labels.
   - Acceptance: false signal PC rate stays near the stated alpha under this
     null, not only under Gaussian pure-noise simulations.
   - Reason: this is the strongest response to type-I-error criticism.

4. PBMC3k/Kang direct comparator refresh
   - Goal: rerun RMTGuard, Scanpy-like, fixed-PC, elbow, and any feasible
     scLENS output under identical subsampling and preprocessing rules.
   - Acceptance: 10 repeats minimum, confidence intervals, cluster-number
     variance, annotation recovery, runtime, and memory.
   - Reason: the current stability story is not strong enough for a top methods
     journal.

## P1 Experiments

5. no-call decision map
   - Goal: convert diagnostic no-call behavior into a readable decision heatmap.
   - Acceptance: each dataset has explicit call/no-call reasons and thresholds.

6. real-data topology benchmark
   - Goal: include one public trajectory dataset with known differentiation or
     perturbation structure.
   - Acceptance: RMTGuard does not fragment the known trajectory more than
     reasonable baselines and clearly reports uncertainty.

7. component ablation refresh
   - Goal: quantify marginal value of MP edge, TW proxy, permutation
     calibration, HVG plateau, near-edge stability gate, and no-call contract.
   - Acceptance: 20-50 repeats where synthetic, 10 repeats where real-data
     runtime is limiting, with confidence intervals.

## Manuscript Changes Required

- Introduction: explicitly separate high-impact embedding literature
  (CONCORD-like) from RMT signal-detection literature (scLENS-like).
- Methods: state that RMTGuard uses RMT as a workflow guard, not as a new
  mathematical discovery.
- Results: add topology and realistic-null panels before claiming high-impact
  readiness.
- Discussion: state that deep latent models may outperform RMTGuard for some
  embedding tasks, while RMTGuard prioritizes interpretability, diagnostic
  callability, and single-workstation reproducibility.

## Current Publication Impact

Nature Methods remains possible only if the P0 experiments strengthen the
evidence arc. Genome Biology becomes more realistic if the work is framed as an
open reproducible callability workflow with transparent boundaries. Without
the P0 additions, the paper should not be sold as a 20-50 JIF-ready method.

## 2026-05-12 Update

The direct scLENSpy comparator has moved beyond feasibility smoke testing. The
new runner `benchmarks/run_sclens_stability_benchmark.py` completed 10 repeats
on PBMC3k and Kang IFN-beta PBMC under both the pilot `n_rand_matrix=2` setting
and the stronger `n_rand_matrix=20` setting. Under `n_rand_matrix=20`, scLENSpy
stability remained lower than RMTGuard v3.2 on both datasets. This closes the
first direct scLENS-like comparator blocker for PBMC3k/Kang, but not the full
Nature Methods benchmark gate.
