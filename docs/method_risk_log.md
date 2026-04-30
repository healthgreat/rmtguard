# Method Risk Log

## PBMC3k Stability Gate

Date: 2026-04-27, updated 2026-04-29

Observation: On a 1000-cell PBMC3k subset with 5 repeats and 80% subsampling,
RMTGuard did not outperform fixed-PC baselines on raw pairwise clustering ARI.

Evidence:

- `results/stability_benchmarks/stability_summary.tsv`
- RMTGuard v3.2 mean pairwise ARI after plateau-complete HVG selection,
  adaptive embedding with `embedding_source="standard_pca"`, and
  signal-adaptive graph modularity: 0.892
- RMTGuard v3.1 mean pairwise ARI after adaptive embedding with
  `embedding_source="standard_pca"` and `resolution_rule="graph_modularity"`
  at conservative resolution 1.0: 0.842
- RMTGuard v3 mean pairwise ARI after adaptive embedding with
  `embedding_source="standard_pca"` and `resolution_rule="graph_modularity"`:
  0.801
- RMTGuard v2 mean pairwise ARI after `spectral_stability` +
  `normalized_dispersion`: 0.680
- Earlier RMTGuard mean pairwise ARI before the HVG update: 0.541
- Scanpy default-like mean pairwise ARI: 0.821
- fixed `n_pcs=30` mean pairwise ARI: 0.908
- fixed `n_pcs=50` mean pairwise ARI: 0.821

Diagnostics:

- Biwhitened RMTGuard retained only 4 signal PCs on PBMC3k.
- `rmtguard_fixed_k` using the RMTGuard embedding but fixed `k=8` was less
  stable than auto-k RMTGuard, indicating the embedding rather than only the
  automatic cluster count is unstable.
- `zscore` preprocessing retained many PCs but produced unstable and overly
  coarse fallback clusters.
- `min_embedding_pcs=10` and `min_embedding_pcs=20` did not improve stability.
- `resolution_rule=consensus_stability` using repeated subsampling co-association
  clustering produced mean pairwise ARI 0.537 on the same PBMC3k gate probe,
  slightly below the KMeans fallback and far below fixed-PC baselines.
- Replacing raw dispersion with mean-binned normalized dispersion and selecting
  HVG counts by `spectral_stability` improved PBMC3k stability to 0.680 and
  stabilized `selected_hvg_n=500`, `n_signal_pcs=5-6`, and `cluster_n=7`.
- The decisive v3 diagnostic was that using the same RMTGuard HVGs with
  standard PCA scores recovered stable PBMC structure; fixed `k=8` reached
  about 0.976 in a manual probe, showing that the earlier blocker was the
  biwhitened RMT embedding.
- The implemented v3 default reached 0.801 without fixed k by combining
  adaptive near-edge PC admission, standard-PCA embedding scores, and graph
  modularity clustering at resolution 1.5.
- The implemented v3.1 default uses the full 500/1000/2000/3000 HVG grid and
  conservative graph modularity resolution 1.0. It improved PBMC3k stability
  to 0.842 and moved Kang IFN-beta cell-type recovery into the noninferiority
  margin against unsupervised graph fixed-PC baselines.
- The implemented v3.2 default uses a 500/1000/2000 HVG grid, selects the
  largest HVG set that remains inside the signal-PC plateau, and uses a
  high-signal graph resolution for spectra with at least 10 strict signal PCs.
  It improved PBMC3k stability to 0.892 and kept Kang and Baron pancreas inside
  the annotation noninferiority margin.
- `min_embedding_pcs=10` reached 0.823, but this is kept as an ablation only
  because the project plan explicitly forbids passing the gate by manually
  forcing extra PCs.
- `resolution_rule=consensus_stability` on the v3 embedding failed badly
  (0.151), confirming consensus clustering is not the solution.

Interpretation:

The v3.2 update keeps the PBMC3k gate at borderline: it reaches the predefined
0.80 floor and exceeds Scanpy-like stability, but it remains slightly below
fixed `n_pcs=30`. This is progress, not a Nature Methods-ready claim.

Action:

- Keep the gate as `borderline`, not `pass`, for manuscript-grade PBMC3k
  stability evidence.
- Do not use small smoke runs as Nature Methods gate evidence.
- Do not tune further only on PBMC3k. The next stability gate should run the
  same subsampling stability benchmark across all four Phase 1 datasets using
  `make stability-phase1`, then decide whether PBMC3k is a single-dataset
  caveat or a global performance blocker.

## Multi-Dataset Stability Gate

Date: 2026-04-30

Observation: The four-dataset stability run changes the gate from PBMC3k-only
borderline to a true multi-dataset stability failure.

Evidence:

- `results/stability_benchmarks/stability_summary.tsv`
- `results/stability_benchmarks/stability_gate_diagnostics.tsv`
- `docs/stability_gate_diagnostics.md`

Interpretation:

RMTGuard beats all non-RMTGuard baselines on Kang IFN-beta PBMC and is within
margin on Baron pancreas and PBMC3k, but PBMC68k/Zheng 2017 falls below the
0.80 stability floor and collapses to fewer than two clusters on average.
This should be treated as an algorithmic failure mode, not a manuscript caveat
that can be explained away.

Action:

- Keep `stability_advantage` as `fail` until PBMC68k is fixed or an explicit,
  pre-specified exclusion rule is justified before analysis.
- Do not submit Nature Methods with the current stability gate.
- The next algorithmic fix should target low-signal / fine-label immune data
  where RMTGuard underclusters relative to fixed-PC baselines.

## PDAC/TME Showcase Boundary

Date: 2026-04-29

Observation: GSE154778 and GSE263733 support a marker-smoke PDAC/TME showcase,
but the current result is immune/ductal-centered, not CAF-centered.

Evidence:

- `results/pdac_tme/showcase_summary.tsv`
- GSE154778: 1200 cells, 4 RMTGuard clusters, marker-supported
  `ductal_malignant_context` and `immune_myeloid` signatures.
- GSE263733: 1200 cells, 7 RMTGuard clusters, public cell-type label ARI
  0.568 and NMI 0.687.
- GSE263733 cluster summaries include T/NK, immune-myeloid, ductal-context,
  and B/plasma marker signatures.

Interpretation:

The PDAC/TME gate can be marked as pass for an immune/ductal marker-supported
showcase with external validation. It should not be written as a CAF discovery
claim unless a later larger run identifies stable fibroblast/CAF states.

## PBMC68k Label-Recovery Caveat

Date: 2026-04-29

Observation: The PBMC68k/Zheng 2017 benchmark reaches noninferiority by margin,
but all graph-based methods have low absolute ARI on the 1000-cell stratified
subset.

Evidence:

- `results/phase1_benchmarks/phase1_benchmark_summary.tsv`
- RMTGuard ARI: 0.081
- fixed `n_pcs=30` ARI: 0.106
- Scanpy-like / fixed `n_pcs=50` ARI: 0.044

Interpretation:

This dataset should count toward benchmark breadth, but not as a strong
positive annotation-recovery example. The labels contain fine immune subtypes
that are difficult to recover with the current unsupervised graph benchmark
settings. Use Kang IFN-beta and Baron pancreas as the stronger labeled
annotation evidence unless a better PBMC68k baseline/label hierarchy is added.

## Figure Source-Data Gate

Date: 2026-04-29

Observation: Source-data readiness for the five planned main figures is now a
scripted local artifact rather than a hand-maintained checklist.

Evidence:

- `scripts/build_figure_source_data.py`
- `results/figures/figure_reproducibility.tsv`
- `results/figures/source_data/figure1_algorithm_diagnostics.tsv`
- `results/figures/source_data/figure2_synthetic_benchmark_summary.csv`
- `results/figures/source_data/figure3_public_benchmark_summary.tsv`
- `results/figures/source_data/figure4_pdac_tme_showcase_summary.tsv`
- `results/figures/source_data/figure5_runtime_memory_summary.tsv`

Interpretation:

The `figure_source_data` gate can be marked as `pass` because each planned main
figure has at least one ready source-data table and a regeneration command. This
does not mean journal-quality rendered figures are complete; it only means the
source-data package is reproducible from the current benchmark outputs.

## Draft Figure Rendering Boundary

Date: 2026-04-29

Observation: The five planned main figures can now be rendered automatically
from the source-data tables.

Evidence:

- `scripts/render_main_figures.py`
- `figures/manuscript/rendered_figure_manifest.tsv`
- `figures/manuscript/figure1_rmtguard_algorithm_diagnostics.png`
- `figures/manuscript/figure2_synthetic_benchmarks.png`
- `figures/manuscript/figure3_public_benchmarks.png`
- `figures/manuscript/figure4_pdac_tme_showcase.png`
- `figures/manuscript/figure5_reproducibility_release_audit.png`

Interpretation:

These figures are reproducibility and assembly drafts. They are useful for
checking whether each claim has source data, but they still need visual design,
panel labeling, and final journal formatting before submission.

## Software Release Boundary

Date: 2026-04-29

Observation: Local release readiness can now be summarized automatically, but
the software-release gate remains externally blocked.

Evidence:

- `scripts/build_release_readiness.py`
- `results/release/release_readiness.tsv`
- `results/release/release_audit_summary.txt`

Interpretation:

Passing local checks is not equivalent to a manuscript-ready software release.
The `software_release` gate should remain `pending` until repository URLs are
replaced with the real GitHub location, a release tag exists, a GitHub Release
is created, and Zenodo returns a DOI.

## Release Artifact Boundary

Date: 2026-04-29

Observation: A release artifact manifest now separates commit-ready repository
files from data and generated outputs that require accession-based downloads or
DOI-backed archives.

Evidence:

- `scripts/build_release_artifact_manifest.py`
- `results/release/release_artifact_manifest.tsv`
- `results/release/release_artifact_summary.tsv`

Interpretation:

The GitHub repository should contain source code, workflows, metadata, docs,
and lightweight placeholders. Raw public data, processed `.h5ad` matrices,
figure source data, benchmark tables, and rendered draft figures should be
recreated from scripts or archived as release/Zenodo assets. Development probe
outputs are local history and should not be presented as manuscript evidence.

## GitHub Staging Boundary

Date: 2026-04-29

Observation: A generated staging plan now separates the first GitHub commit set
from files that should stay ignored or move to release/Zenodo assets.

Evidence:

- `scripts/build_github_staging_plan.py`
- `results/release/github_staging_manifest.tsv`
- `results/release/github_staging_summary.tsv`
- `docs/github_staging_plan.md`

Interpretation:

The staging plan is a safety guide, not an executed commit. It should be
reviewed before running `git add`; raw data, processed matrices, result tables,
rendered figures, and development probes should not enter the source-code
repository unless a later release policy explicitly changes that.

`scripts/stage_github_release_files.py` provides the executable layer for this
boundary. It defaults to dry-run output and requires `--execute` before it calls
`git add`.

## Repository Metadata Boundary

Date: 2026-04-29

Observation: Repository URL replacement is now scripted but remains dry-run by
default because the real GitHub repository URL has not been supplied.

Evidence:

- `scripts/update_repository_metadata.py`
- `results/release/repository_metadata_update_plan.tsv`

Interpretation:

Do not replace `your-lab/rmtguard` with an invented URL. The placeholder should
be replaced only after the actual GitHub repository exists, using
`python scripts/update_repository_metadata.py --repo-url <real-url> --execute`.

## External Release Boundary

Date: 2026-04-29

Observation: The remaining GitHub/Zenodo tasks are now represented as an
external release plan, but none of those tasks has been executed.

Evidence:

- `scripts/build_external_release_plan.py`
- `results/release/external_release_plan.tsv`
- `docs/external_release_plan.md`

Interpretation:

The plan is useful for sequencing the real release, but it cannot satisfy the
`software_release` gate by itself. That gate still requires a real GitHub
repository, a clean source commit, an annotated release tag, a GitHub Release,
and a Zenodo DOI.

## Release Asset Bundle Boundary

Date: 2026-04-29

Observation: Release/Zenodo candidate assets now have a checksum manifest, but
the default command does not create or upload an archive.

Evidence:

- `scripts/build_release_asset_bundle.py`
- `results/release/release_asset_manifest.tsv`
- `results/release/release_asset_summary.tsv`
- `results/release/release_asset_bundle_notes.md`

Interpretation:

The asset manifest is a local packaging aid. Raw public downloads, processed
matrices, development probes, and bundle self-outputs are excluded. Creating a
zip with `--execute` still does not satisfy `software_release`; the archive must
be attached to a real GitHub Release or deposited with Zenodo and assigned a DOI.

## Manuscript Evidence Boundary

Date: 2026-04-29

Observation: Manuscript claims now have a generated claim-evidence matrix and
submission readiness note.

Evidence:

- `scripts/build_manuscript_evidence_package.py`
- `results/manuscript/claim_evidence_matrix.tsv`
- `results/manuscript/nature_methods_submission_checklist.tsv`
- `manuscript/submission_readiness.md`

Interpretation:

The manuscript can safely state passed synthetic, benchmark breadth,
annotation-noninferiority, PDAC/TME immune/ductal-context, and figure-source
claims. It should not state that Nature Methods submission is ready, that
RMTGuard beats fixed `n_pcs=30` on PBMC3k, that a standalone CAF discovery was
made, or that the software has a GitHub/Zenodo DOI-backed release.

## Manuscript Draft Package Boundary

Date: 2026-04-29

Observation: The claim-evidence matrix can now be converted into guarded
manuscript working drafts and reviewer-risk tables.

Evidence:

- `scripts/build_manuscript_draft_package.py`
- `manuscript/nature_methods_presubmission_draft.md`
- `manuscript/abstract_draft.md`
- `manuscript/cover_letter_draft.md`
- `results/manuscript/reviewer_objection_matrix.tsv`
- `results/manuscript/storyline_panel_map.tsv`

Interpretation:

These files are drafting aids, not a submission package. They preserve the
current decision boundary: Nature Methods is not ready while PBMC3k stability
is borderline and the public GitHub/Zenodo release is pending. The reviewer
objection matrix should be treated as the next execution board for hardening
the manuscript.
