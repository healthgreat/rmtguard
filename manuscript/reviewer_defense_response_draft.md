# Reviewer Defense Response Draft

Status: generated from current evidence. Do not send as a response letter until real reviewer comments exist.

## software_release

Potential concern: `blocks_all_submission_routes`.

Draft response:

We address this by keeping the claim limited to software_release: Complete GitHub repository, tagged release, GitHub Release, and Zenodo DOI before submission. Current evidence: results\release\release_readiness.tsv | Local release readiness checks passed 26/26; external release items pending: repository_url, github_remote, zenodo_doi.

For a Nature Methods route, we would keep the response aligned with: Do not submit to Nature Methods before public GitHub Release and archive evidence are real.

For a Genome Biology route, we would keep the response aligned with: Still blocked until public release; Genome Biology-style software framing requires the same repository and archive evidence.

Boundary: Do not state that code is DOI-archived or fully released before the external release exists.

## method_novelty

Potential concern: `nature_methods_editorial_fit`.

Draft response:

We address this by keeping the claim limited to noise_control_null: Center the paper on random-matrix null control, diagnostic contracts, and false-signal suppression. Current evidence: results\synthetic_benchmarks\synthetic_benchmark_summary.csv | pure_null n_signal_pcs=1.0..

For a Nature Methods route, we would keep the response aligned with: Lead with the random-matrix noise-control contract, diagnostic no-call behavior, and false-signal suppression rather than automatic parameter tuning.

For a Genome Biology route, we would keep the response aligned with: Frame novelty as an open genomics workflow that operationalizes random-matrix diagnostics and no-call boundaries.

Boundary: Do not invent new analyses, journal outcomes, or stronger benchmark results.

## stability_advantage

Potential concern: `blocks_broad_superiority_claim`.

Draft response:

We address this by keeping the claim limited to pbmc3k_stability: Frame PBMC68k as a pre-specified diagnostic no-call and keep the benchmark claim callability-aware rather than an overbroad performance claim. Current evidence: results\stability_benchmarks\stability_gate_diagnostics.tsv | RMTGuard stability had hard failures on 3/4 datasets..

For a Nature Methods route, we would keep the response aligned with: Use only a callability-aware stability/no-call claim; this remains a Nature Methods risk until Figure 3 and the abstract visibly disclose comparator tradeoffs.

For a Genome Biology route, we would keep the response aligned with: Turn the limitation into a transparent workflow feature: the package reports when the evidence supports no-call rather than forced discovery.

Boundary: Do not claim RMTGuard outperforms fixed-PC baselines on every dataset or that PBMC68k yields a positive cell-state discovery.

## benchmark_baselines

Potential concern: `controlled_reviewer_risk`.

Draft response:

We address this by keeping the claim limited to public_benchmark_breadth: Keep current benchmark as Phase 1 and add Seurat, elbow, permutation PCA, and JackStraw-like baselines. Current evidence: results\phase1_benchmarks\phase1_benchmark_summary.tsv | 4 real datasets benchmarked..

For a Nature Methods route, we would keep the response aligned with: Keep expanded baselines visible in the final tables and avoid hiding fixed-PC or elbow advantages.

For a Genome Biology route, we would keep the response aligned with: Use expanded baseline tables as evidence of a serious benchmark workflow.

Boundary: Do not invent new analyses, journal outcomes, or stronger benchmark results.

## null_calibration_scope

Potential concern: `controlled_reviewer_risk`.

Draft response:

We address this by keeping the claim limited to noise_control_null: State assumptions, include permutation calibration, and avoid exact type-I claims beyond tested settings. Current evidence: results\synthetic_benchmarks\synthetic_benchmark_summary.csv | pure_null n_signal_pcs=1.0..

For a Nature Methods route, we would keep the response aligned with: State RMT null assumptions and report tested-scenario calibration only; avoid exact universal type-I wording.

For a Genome Biology route, we would keep the response aligned with: Present calibration as benchmarked diagnostic behavior rather than universal theory.

Boundary: Do not claim exact type-I error calibration across all scRNA-seq settings without final permutation calibration.

## pbmc68k_label_quality

Potential concern: `controlled_reviewer_risk`.

Draft response:

We address this by keeping the claim limited to annotation_noninferiority: Frame PBMC68k as label-granularity stress evidence and rely on Kang and Baron for stronger annotation recovery. Current evidence: results\phase1_benchmarks\phase1_benchmark_summary.tsv | RMTGuard noninferior on 3/3 labeled datasets..

For a Nature Methods route, we would keep the response aligned with: Treat PBMC68k as label-granularity stress evidence and diagnostic no-call context, not as a positive annotation success.

For a Genome Biology route, we would keep the response aligned with: Use PBMC68k to motivate transparent stress testing and label-quality caveats.

Boundary: Do not frame PBMC68k as a strong positive annotation-recovery success.

## pdac_biology_depth

Potential concern: `controlled_reviewer_risk`.

Draft response:

We address this by keeping the claim limited to pdac_tme_showcase: Use PDAC/TME as public workflow validation, not as disease-mechanism proof. Current evidence: results\pdac_tme\showcase_summary.tsv | GSE154778 marker-smoke structure validated in GSE263733 with public cell-type ARI=0.568..

For a Nature Methods route, we would keep the response aligned with: Use PDAC/TME as a bounded public application, not as the central novelty claim.

For a Genome Biology route, we would keep the response aligned with: Keep PDAC/TME as an example of public reproducible use, not a disease-mechanism article.

Boundary: Do not claim a standalone CAF/fibroblast discovery from the current smoke showcase.

## rare_state_loss

Potential concern: `controlled_reviewer_risk`.

Draft response:

We address this by keeping the claim limited to rare_state_retention: Use rare-state synthetic ARI as current support and add real rare-state sensitivity if feasible. Current evidence: results\synthetic_benchmarks\synthetic_benchmark_summary.csv | rare_state ARI=0.9234648221808079; required >=0.9..

For a Nature Methods route, we would keep the response aligned with: Use the rare-state synthetic ARI as support, while acknowledging that real rare states still require dataset-specific interpretation.

For a Genome Biology route, we would keep the response aligned with: Keep rare-state retention as synthetic support and avoid biological guarantees.

Boundary: Do not imply all biological rare states are guaranteed to be retained.

## Non-Negotiable Boundary

These draft responses are pre-review scaffolds. They must be edited against actual reviewer wording and regenerated after any new analysis, public release, or route change.
