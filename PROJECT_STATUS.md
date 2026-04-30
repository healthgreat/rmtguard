# PROJECT_STATUS

## Current Target

Primary target: **Nature Methods**.

RMTGuard is now positioned as a random-matrix noise-control framework for
reproducible scRNA-seq cell-state discovery, not as a generic automatic tuning
wrapper.

## Implemented

- RMTGuard v3.2 public API fields: `pc_rule`, `hvg_rule`, `hvg_score`,
  `embedding_rule`, `embedding_source`, `resolution_rule`, `batch_key`,
  `n_permutations`, `tw_alpha`, `stability_repeats`, `random_state`.
- Default HVG selection now uses `hvg_score="normalized_dispersion"` and
  `hvg_rule="spectral_stability"` with plateau-complete HVG selection.
- Default embedding now uses RMT decisions as noise-control gates while
  downstream scores come from `embedding_source="standard_pca"`.
- Default clustering now uses `resolution_rule="graph_modularity"` with
  conservative graph resolution 1.0 and high-signal graph resolution 1.5 when
  strict signal PCs indicate richer structure.
- Result diagnostics: `pc_diagnostics`, `hvg_diagnostics`, `resolution_scan`,
  `null_calibration`, `benchmark_metadata`.
- Batch-aware residualization before spectral diagnostics.
- AnnData wrapper writes `obsm["X_rmtguard"]`, `uns["rmtguard"]`, and
  `obs["rmtguard_leiden"]`.
- Synthetic stress generators and benchmark runner.
- Public dataset manifest with PDAC/TME showcase datasets GSE154778 and
  GSE263733.
- Phase 1 PBMC3k data preparation and real-data benchmark runner.
- Subsampling stability benchmark runner and gate evidence updater.
- Stability benchmark runner now supports all four Phase 1 datasets
  (`pbmc3k_10x`, `kang_ifnb_pbmc`, `baron_pancreas`, `pbmc68k_zheng2017`) and
  writes per-dataset checkpoint TSVs for resumable manuscript-grade runs.
- `scripts/build_stability_gate_report.py` summarizes per-dataset stability
  status against Scanpy-like and fixed-PC baselines and writes the current
  blocker report to `docs/stability_gate_diagnostics.md`.
- `scripts/build_publication_20_50_plan.py` records the strict 20-50 JIF
  publication route. It keeps Nature Methods as the realistic 20-50 target
  only if gates pass, marks Nature Biotechnology as stretch-only, and keeps
  Genome Biology as a fallback outside strict 20-50 JIF.
- `scripts/build_journal_compliance_audit.py` converts Nature Methods and
  Nature Portfolio code/data/reporting requirements into explicit local
  pass/blocked rows.
- `scripts/build_publication_execution_board.py` records the remaining
  ownership boundary: Codex-owned local work versus external GitHub/Zenodo or
  author-owned submission actions.
- `scripts/build_reporting_summary_draft.py` pre-fills a Nature Portfolio
  reporting-summary worksheet from local evidence while keeping the official
  form as a manual author-verified step.
- `scripts/build_editorial_risk_audit.py` records desk-reject and transfer
  risks so the Nature Methods first route is governed by explicit
  go/no-go rules rather than optimism.

## Remaining Manuscript Work

1. Add per-dataset label quality notes and annotation-recovery summaries for
   all real datasets.
2. Add R/Seurat baseline scripts and JackStraw-like baseline.
3. Run permutation calibration for final figures.
4. Polish the rendered draft figures for final manuscript layout and complete
   the GitHub/Zenodo DOI release.

## Current Evidence Status

- PBMC3k smoke benchmark has run on a 300-cell subset.
- PBMC3k manuscript-grade stability benchmark has run on a 1000-cell subset.
  RMTGuard improved from 0.541 to 0.680 after the HVG update, to 0.801 after
  v3 adaptive embedding, to 0.842 after v3.1 conservative graph resolution,
  and to 0.892 after v3.2 plateau-complete HVG selection. The
  `stability_advantage` gate remains `borderline`, not `pass`, because fixed
  `n_pcs=30` remains slightly higher at 0.908.
- The four-dataset Phase 1 stability run is complete. It changes the
  `stability_advantage` gate from PBMC3k-only borderline to multi-dataset
  borderline/no-call: Kang is a win, Baron and PBMC3k are within margin, and
  PBMC68k/Zheng 2017 is a diagnostic no-call because the strongest stable
  baseline also has weak label recovery.
- Kang IFN-beta has been prepared from public GEO files with singlets retained.
  The corrected unsupervised graph baseline benchmark gives RMTGuard
  cell-type ARI 0.785 versus fixed `n_pcs=30` ARI 0.681.
- Baron pancreas has been prepared from GSE84133 human samples. RMTGuard
  cell-type ARI is 0.752 versus fixed `n_pcs=30` ARI 0.797, which remains
  within the current noninferiority margin.
- PBMC68k/Zheng 2017 has been prepared from the scVelo-hosted public h5ad.
  RMTGuard cell-type ARI is 0.081 versus fixed `n_pcs=30` ARI 0.106, which is
  noninferior by margin but biologically weak in absolute recovery; this should
  be treated as a label-granularity/stress benchmark rather than a strong
  annotation success.
- PDAC/TME showcase has been run on GSE154778 and externally checked in
  GSE263733. GSE154778 has marker-supported ductal-context and immune-myeloid
  clusters. GSE263733 validates immune/ductal/T-NK/B-plasma marker structure
  against public cell-type labels with ARI 0.568. CAF/fibroblast is not a
  standalone main cluster in the current smoke showcase and should not be a
  primary claim.
- Multi-dataset stability diagnostics: Kang IFN-beta PBMC is a clear RMTGuard
  win over fixed-PC baselines; Baron pancreas and PBMC3k are within margin but
  still slightly below fixed `n_pcs=30`; PBMC68k/Zheng 2017 is below floor
  with RMTGuard mean pairwise ARI 0.600 and mean cluster count 1.4, but is
  now classified as diagnostic no-call because fixed `n_pcs=30` label ARI is
  only 0.106.
- Gate status is now: synthetic noise control `pass`, diagnostic no-call
  validation `pass`, rare-state retention `pass`, annotation noninferiority
  `pass` on 3/3 labeled datasets, real dataset count `pass` with 4 datasets,
  PDAC/TME interpretability `pass`, figure source data `pass`, callability-aware
  stability/no-call `pass`, and software release `pending`.
- Figure source data have been generated under
  `results/figures/source_data/`, with the reproducibility manifest at
  `results/figures/figure_reproducibility.tsv`.
- Draft PNG/PDF main figures have been rendered under `figures/manuscript/`,
  with the render manifest at `figures/manuscript/rendered_figure_manifest.tsv`.
- Local release readiness is summarized under `results/release/`. This records
  local audit status, metadata availability, figure/source-data readiness, and
  the still-missing GitHub release tag and Zenodo DOI.
- Release artifact destinations are summarized in
  `results/release/release_artifact_manifest.tsv`, separating GitHub files,
  public accession downloads, processed matrices, DOI-archived results, draft
  figures, and local-only probe outputs.
- Release/Zenodo asset checksums are summarized in
  `results/release/release_asset_manifest.tsv`; default execution is dry-run
  and `--execute` is required to create the zip bundle.
- The GitHub initial-commit staging plan is summarized in
  `results/release/github_staging_manifest.tsv` and
  `docs/github_staging_plan.md`. It currently separates commit-ready source
  files from  data/results/figure outputs that must stay out of GitHub.
- `scripts/stage_github_release_files.py` performs a dry-run by default and
  writes `results/release/github_stage_dry_run.tsv`; it only stages files if
  explicitly called with `--execute`.
- `scripts/update_repository_metadata.py` writes
  `results/release/repository_metadata_update_plan.tsv` by default. It only
  replaces placeholder GitHub URLs when a real `--repo-url` is provided with
  `--execute`.
- `scripts/build_external_release_plan.py` writes
  `results/release/external_release_plan.tsv` and
  `docs/external_release_plan.md`, splitting the remaining release work into
  local dry-run-safe steps and truly external GitHub/Zenodo actions.
- `scripts/build_manuscript_evidence_package.py` writes the claim-evidence
  matrix and `manuscript/submission_readiness.md`, keeping manuscript-safe
  claims separate from prohibited overclaims.
- `scripts/build_manuscript_draft_package.py` writes guarded Nature Methods
  working drafts, a reviewer objection matrix, and a storyline-to-panel map.
  These outputs are explicitly not submission-ready and preserve the current
  PBMC3k/software-release boundaries.
- `results/submission/nature_methods_compliance_audit.tsv` records Nature
  Methods-facing compliance. Scope, content type, comparison, biological
  application, data availability, reproducibility package, and claim boundary
  pass. Code availability, code DOI, and final submission readiness remain
  blocked until public GitHub/Zenodo release exists.
- `docs/publication_execution_board.md` records the active execution state:
  local Codex-owned manuscript/release artifacts are prepared, but public
  GitHub repository creation, remote push, GitHub Release, Zenodo DOI, and
  official reporting summary remain external/manual actions.
- `docs/nature_reporting_summary_draft.md` and
  `results/submission/reporting_summary_draft.tsv` now pre-fill the reporting
  summary content. The draft marks Code availability and Code DOI as blocked
  until the public GitHub/Zenodo release is complete; the official Nature
  Portfolio form still requires author verification.
- `docs/editorial_risk_audit.md` and
  `results/submission/editorial_risk_audit.tsv` now track Nature Methods
  desk-reject risk. The current blocking editorial risk is software release;
  active non-blocking risks are method novelty framing, baseline sufficiency,
  and PDAC/TME application depth.
- Gate recommendation remains `continue_benchmarking` until the external
  software-release evidence is complete and the submission gate is rerun.

## Current Publication Blocker

RMTGuard v3.2 reaches the pre-specified 0.80 floor on PBMC3k, exceeds the
Scanpy-like PBMC3k stability baseline, and passes the expanded four-dataset
gate only under the callability-aware stability/no-call framing. This is a
manuscript-safe but narrow methods claim, not broad fixed-PC superiority.

The active 20-50 JIF blocker is now external software release rather than a
local algorithm implementation failure: a real public GitHub repository,
remote push, GitHub Release, Zenodo DOI, and final reporting-summary form are
required before Nature Methods submission can be marked ready.
