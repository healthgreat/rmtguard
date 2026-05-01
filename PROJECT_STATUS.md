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
- `scripts/build_stability_utility_report.py` quantifies stability-versus-
  annotation tradeoffs so the manuscript cannot turn a higher-stability but
  lower-annotation comparator into a false RMTGuard superiority claim.
- `scripts/build_algorithm_rescue_probe_report.py` records local rescue probes
  that should not be promoted to the default algorithm, including failed
  resolution-path and PBMC68k low-signal probes.
- RMTGuard now exposes an optional, default-off
  `low_signal_rescue_rule="null_calibrated_stable_embedding"` probe. It
  requires subsampling stability to exceed a gene-permutation null and a
  near-edge eigenvalue-ratio guard before any sub-edge PCs can be used.
- `scripts/build_publication_20_50_plan.py` records the strict 20-50 JIF
  publication route. It keeps Nature Methods as the realistic 20-50 target
  only if gates pass, marks Nature Biotechnology as stretch-only, and keeps
  Genome Biology as a fallback outside strict 20-50 JIF.
- `scripts/build_claim_scope_decision.py` now locks the current claim boundary:
  strict 20-50 submission is blocked by `stability_advantage` and
  `software_release`, while the only usable manuscript story is a
  callability-aware random-matrix noise-control claim with diagnostic no-call
  boundaries.
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
- Phase 1 and stability benchmark runners now include reviewer-facing PC-rule
  baselines (`elbow_rule`, `parallel_analysis`, `jackstraw_like`), and
  `benchmarks/run_seurat_baseline.R` provides an optional Seurat v5-like
  baseline runner for prepared h5ad datasets.

## Remaining Manuscript Work

1. Resolve the strict expanded-baseline `stability_advantage` failure, or
   formally narrow the manuscript away from broad stability superiority.
2. Add per-dataset label quality notes and annotation-recovery summaries for
   all real datasets.
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
- The four-dataset Phase 1 stability run is complete. After adding elbow,
  permutation PCA, JackStraw-like, and Seurat-facing baseline support, the
  `stability_advantage` gate is now `fail`: PBMC3k and Baron are below the
  strongest stability comparator, Kang shows a stability-versus-annotation
  tradeoff, and PBMC68k/Zheng 2017 remains a diagnostic no-call stress case.
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
- Multi-dataset stability diagnostics: RMTGuard is above Scanpy-like and
  fixed-PC baselines on Kang annotation recovery, but `elbow_rule` has higher
  raw stability with lower annotation ARI. Baron pancreas has a fixed
  `n_pcs=30` row that is noninferior on stability and higher on annotation.
  PBMC3k is an unlabeled stability deficit against `elbow_rule` and fixed
  `n_pcs=30`. PBMC68k/Zheng 2017 is below floor with RMTGuard mean pairwise
  ARI 0.600 and mean cluster count 1.4, and must remain a diagnostic no-call
  context rather than a positive discovery claim.
- `docs/stability_utility_tradeoff.md` now records the stability-annotation
  Pareto audit. It explicitly states that this audit does not rescue the
  failed stability gate; it only controls wording and reviewer-risk scope.
- `docs/algorithm_rescue_probe_report.md` records the current rescue attempts:
  graph-resolution path improves PBMC3k locally but hurts Kang IFN-beta PBMC,
  while near-edge-window 2.0, MP-only edge, optional stable low-signal PC
  rescue, null-calibrated low-signal rescue, and coarse-to-fine rescue do not
  rescue PBMC68k. The null-calibrated version restores synthetic pure-null
  no-call in smoke testing but leaves PBMC68k mean pairwise ARI at 0.600.
  These probes are not promoted to the default algorithm.
- Gate status is now: synthetic noise control `pass`, diagnostic no-call
  validation `pass`, rare-state retention `pass`, annotation noninferiority
  `pass` on 3/3 labeled datasets, real dataset count `pass` with 4 datasets,
  PDAC/TME interpretability `pass`, figure source data `pass`,
  `stability_advantage` `fail`, and software release `pending`.
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
- `docs/claim_scope_decision.md` and
  `results/submission/claim_scope_decision.tsv` explicitly prohibit guarantee
  language and PBMC68k positive-discovery claims. They mark the strict
  Nature Methods 20-50 route as `blocked_by_stability_advantage` in the
  current evidence snapshot.
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
- `scripts/build_public_release_blocker_report.py` writes
  `results/release/public_release_blockers.tsv` and
  `docs/public_release_blocker_report.md`, converting the still-missing
  GitHub remote, release tag, GitHub Release, Zenodo DOI, and metadata
  replacement steps into explicit owner/action/status rows. This report
  preserves the no-acceptance-guarantee boundary while making the public
  release blocker auditable before submission.
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
  active non-blocking risks are method novelty framing and stability claim
  scope. Baseline sufficiency is controlled after the expanded Phase 1 and
  stability tables were regenerated with elbow, permutation PCA,
  JackStraw-like, and Seurat v5-like baseline support. PDAC/TME biological
  application depth is controlled only as a bounded public immune/ductal use
  case, not as a disease-mechanism claim.
- `scripts/build_top_paper_route_package.py` writes
  `results/submission/top_paper_route_decision.tsv`,
  `docs/top_paper_route_package.md`,
  `manuscript/top_paper_claim_ladder.md`, and
  `manuscript/genome_biology_conversion_draft.md`. It formalizes the current
  route: Nature Methods first remains on hold until gates and public release
  pass, while the most realistic fallback is a Genome Biology-style
  reproducible genomics workflow after GitHub/Zenodo release completion.
- `scripts/build_editorial_presubmission_packet.py` writes the editor-facing
  controlled drafts: `docs/editorial_presubmission_packet.md`,
  `manuscript/nature_methods_presubmission_inquiry.md`,
  `manuscript/reviewer_response_playbook.md`,
  `manuscript/figure_claim_checklist.md`, and their TSV source tables. These
  materials bind the abstract, cover-letter pitch, figure claims, and reviewer
  responses to the generated claim matrix and keep the current do-not-send
  boundary explicit.
- Gate recommendation remains `continue_benchmarking` until the stability
  claim is rescued or narrowed and the external software-release evidence is
  complete.

## Current Publication Blocker

RMTGuard v3.2 reaches the pre-specified 0.80 floor on PBMC3k, exceeds the
Scanpy-like PBMC3k stability baseline, but the expanded baseline rerun shows
that elbow-rule PCA is more stable on PBMC3k, Kang IFN-beta PBMC, and Baron
pancreas. The `stability_advantage` gate is therefore `fail` under the strict
expanded-baseline table, even though annotation noninferiority, synthetic
noise control, rare-state retention, baseline sufficiency, and the bounded
PDAC/TME public use case are controlled. This is not yet a Nature Methods-ready
performance package.

The active 20-50 JIF blockers are now twofold: the algorithm still needs a
stability claim rescue or a narrower manuscript route, and a real public
GitHub repository, remote push, GitHub Release, Zenodo DOI, and final
reporting-summary form are required before Nature Methods submission can be
marked ready.
