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
- RMTGuard v3.3 adds `rare_state_guard="adaptive_binary_split"`. It evaluates
  multiple RMT-embedding binary split candidates and PC-tail rare-state
  candidates, then accepts a split only when the candidate satisfies minimum
  cell count, rare-state fraction window, centroid separation, and silhouette
  thresholds.
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
- Publication-style PNG/PDF/TIFF main figures have been rendered under
  `figures/manuscript/`, with the render manifest at
  `figures/manuscript/rendered_figure_manifest.tsv`. The current visual pass
  removes large in-canvas titles, uses panel labels, cleans public-facing
  scenario/dataset/marker labels, and keeps all plotted values tied to
  `results/figures/source_data/`.
- `scripts/build_publication_tables.py` writes manuscript-ready Table 1-3 TSVs
  and a landscape Word table pack at
  `results/tables/manuscript/rmtguard_publication_tables.docx`. The tables
  summarize submission gates, public benchmark values, and the active external
  review action plan without changing any scientific calls.
- Local release readiness is summarized under `results/release/`. This records
  local audit status, metadata availability, figure/source-data readiness, and
  the local release-candidate tag. Public GitHub remote, GitHub Release, and
  Zenodo DOI evidence are still missing.
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
- `scripts/lint_claim_boundaries.py` writes
  `results/submission/claim_boundary_lint.tsv` and
  `docs/claim_boundary_lint.md`. It scans journal-facing Markdown/TXT files
  for unsupported acceptance guarantees, broad fixed-PC superiority claims,
  PBMC68k positive-discovery claims, premature DOI/release claims, and
  premature submission-ready language. Boundary/prohibited-claim statements
  are allowed as controlled mentions; any unqualified violation blocks
  submission packaging.
- `scripts/validate_claim_traceability.py` writes
  `results/submission/claim_traceability.tsv` and
  `docs/claim_traceability.md`. It verifies that figure panels,
  editor-facing pitch rows, route decisions, and figure-caption checklists
  trace back to the generated claim-evidence matrix or an explicit evidence
  path. Failed or pending claims are allowed only as caveats, blockers, or
  controlled route decisions.
- `scripts/build_submission_guard.py` writes
  `results/submission/submission_guard.tsv` and
  `docs/submission_guard.md`. This is the single top-level go/no-go table
  aggregating scientific gates, presubmission gatekeeper, public release
  objects, claim-boundary lint, traceability, route decision, and editor-send
  status. The current expected status is `do_not_submit`.
- `scripts/triage_external_review_feedback.py` writes
  `results/submission/external_review_feedback_triage.tsv` and
  `docs/external_review_feedback_triage.md`. External model or collaborator
  feedback should be pasted into either
  `metadata/external_review_feedback_active.tsv` or the template
  `metadata/external_review_feedback_template.tsv`; the triage script then
  converts comments into P0/P1/P2 revision tickets without upgrading claims
  or submission readiness automatically. The current active feedback table
  stores the SuperGrok pre-review comments.
- `scripts/build_external_review_action_plan.py` writes
  `results/submission/external_review_action_plan.tsv` and
  `docs/external_review_action_plan.md`. It condenses active external-review
  comments into ordered work packages: public release/DOI, route reframe,
  manuscript-grade stability baselines, realistic null calibration, ablation
  and no-call decision maps, biological showcase depth, and final
  figure/reporting/claim-language cleanup.
- `scripts/build_callability_decision_map.py` writes
  `results/callability/no_call_decision_map.tsv`,
  `results/figures/source_data/figure3_callability_decision_map.tsv`, and
  `docs/no_call_decision_map.md`. Figure 3D now uses this table directly, so
  real datasets are shown as `callable_with_caveat` or `diagnostic_no_call`
  according to explicit signal, stability, annotation, and cluster-count
  flags.
- `scripts/audit_publication_visual_assets.py` writes
  `results/submission/publication_visual_asset_audit.tsv` and
  `docs/publication_visual_asset_audit.md`. It checks rendered PNG/PDF/TIFF
  figures, source manifests, TSV tables, and the Word table pack for readable,
  nonblank publication-facing artifacts.
- `scripts/build_project_gantt.py` writes
  `results/project_management/rmtguard_project_gantt.tsv`,
  `results/project_management/rmtguard_project_gantt.md`, and
  `figures/project_management/rmtguard_project_gantt.png/.pdf`. It separates
  completed local work, blocked external release tasks, partial ablation work,
  and planned benchmark/statistical/manuscript phases through July 2026.
- `scripts/run_realistic_null_power_calibration.py` and
  `scripts/render_calibration_figures.py` now create a draft calibration
  layer under `results/calibration/` and `figures/calibration/`. This adds
  count-preserving null models and a rare-state prevalence/effect-size power
  grid to the local review package.
- `scripts/build_jif20_50_gap_assessment.py` writes
  `results/submission/jif20_50_gap_assessment.tsv`,
  `results/submission/jif20_50_journal_route.tsv`, and
  `docs/jif20_50_gap_assessment.md`. It records the current distance to a
  strict 20-50 JIF submission route, separates Nature Methods from realistic
  below-20 fallback journals, and lists the missing evidence blocks that must
  be filled before route escalation.
- `benchmarks/run_stability_benchmark.py` now writes per-method pairwise
  subsampling ARI tables, and
  `scripts/build_manuscript_stability_statistical_report.py` writes
  `results/manuscript_stability_benchmarks/manuscript_stability_statistics.tsv`,
  `results/manuscript_stability_benchmarks/manuscript_stability_paired_deltas.tsv`,
  and `docs/manuscript_grade_stability_statistics.md`. The current 10-repeat
  pilot covers all four Phase 1 datasets. PBMC3k gives RMTGuard mean pairwise
  ARI 0.867 with bootstrap CI 0.836-0.898; Kang gives 0.789 with CI
  0.752-0.827; Baron gives 0.878 with CI 0.868-0.888; PBMC68k/Zheng 2017 gives
  0.624 with CI 0.489-0.758 and mean cluster count 1.6. RMTGuard is above
  Scanpy-like/fixed50/parallel-analysis/JackStraw-like on all four datasets
  and above fixed `n_pcs=30` on Kang and Baron, but the strongest stability
  comparator remains higher on every dataset: elbow-rule on PBMC3k/Kang/Baron
  and fixed `n_pcs=30` on PBMC68k.
- `scripts/build_route_reframe_package.py` writes
  `results/submission/route_reframe_decision.tsv`,
  `docs/route_reframe_package.md`,
  `manuscript/genome_biology_reframed_abstract.md`, and
  `manuscript/nature_methods_hold_statement.md`. It implements the local part
  of the SuperGrok P0 route correction: freeze Nature Methods as a current
  no-go route, downgrade the central claim to callability-aware diagnostics,
  and prepare a Genome Biology working abstract that does not claim broad
  stability superiority.
- `scripts/build_post_feedback_journal_route_gate.py` writes
  `results/submission/post_feedback_journal_route_gate.tsv` and
  `docs/post_feedback_journal_route_gate.md`. This is the post-feedback
  routing control: active P0/P1 external feedback pauses route escalation,
  Nature Methods remains on hold unless the generated submission guard becomes
  candidate, and the Genome Biology fallback activates only through the
  bounded reproducible-workflow route after public release completion.
- `scripts/build_genome_biology_transfer_package.py` writes
  `results/submission/genome_biology_transfer_checklist.tsv`,
  `docs/genome_biology_transfer_package.md`, and
  `manuscript/genome_biology_cover_letter_draft.md`. It converts the current
  `genome_biology_after_release` route into a fallback execution package while
  preserving PBMC68k diagnostic no-call wording, Figure 3 stability caveats,
  PDAC/TME public-use-case boundaries, and the requirement for real GitHub and
  Zenodo release evidence before any cover letter is sent.
- `scripts/build_reviewer_defense_package.py` writes
  `results/submission/reviewer_defense_matrix.tsv`,
  `docs/reviewer_defense_package.md`, and
  `manuscript/reviewer_defense_response_draft.md`. It prepares route-specific
  reviewer-defense language for Nature Methods and Genome Biology while
  preserving the software-release blocker, the stability reframe, PBMC68k
  no-call boundary, and PDAC/TME public-use-case scope.
- `scripts/build_author_release_execution_packet.py` writes
  `results/release/author_release_execution_checklist.tsv`,
  `docs/author_release_execution_packet.md`, and
  `manuscript/code_availability_finalization_draft.md`. It reduces the
  remaining GitHub/Zenodo blocker to the minimal author-owned external actions
  plus the local Codex rerun commands needed after a real repository URL and
  DOI exist.
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

SuperGrok external pre-review has been accepted into the control plane as
active P0/P1 feedback. The current post-feedback route decision is
`pause_for_p0_feedback`; Nature Methods presubmission is no-go in the current
state, Genome Biology is conditional after public release and reframe, and
the default narrative is now `callability-aware diagnostic workflow` rather
than `stability-superior clustering method`.

The local route reframe package has been added, so the route-reframe work
package can be treated as implemented locally but still pending feedback
closure. This does not clear the public-release DOI blocker or the
manuscript-grade benchmark/statistical P1 blockers.

The first realistic null/power calibration draft has also been added to the
control plane. After the v3.3 rare-state guard, the current 220-cell,
500-gene, 4-repeat draft run keeps count-preserving null false signal rate at
0.000 and false call rate at 0.000. Rare-state power improves from the prior
all-fail grid to power 1.000 for prevalence/effect settings 0.02/6.0,
0.04/4.0, 0.04/6.0, 0.08/2.5, 0.08/4.0, and 0.08/6.0, with partial power at
0.02/4.0 and 0.04/2.5. This is an algorithmic improvement, but not a final
manuscript-grade pass because weak-effect/lowest-prevalence settings still
fail and the calibration has only draft repeats.

The first manuscript-grade stability statistics pilot now covers all four
Phase 1 datasets with 10 repeats and explicit pairwise ARI records. PBMC3k
reaches RMTGuard mean pairwise ARI 0.867, but `rmtguard_minus_elbow_rule` has
mean delta -0.117 with bootstrap CI -0.148 to -0.086 and p-value 0.0002. Kang
reaches 0.789 and beats fixed `n_pcs=30`, Scanpy-like, parallel-analysis, and
JackStraw-like baselines, but still trails elbow-rule with mean delta -0.052,
bootstrap CI -0.094 to -0.012, and p-value 0.022. Baron reaches 0.878 and
beats fixed `n_pcs=30`, Scanpy-like, parallel-analysis, and JackStraw-like
baselines, but still trails elbow-rule with mean delta -0.046, bootstrap CI
-0.076 to -0.012, and p-value 0.009. PBMC68k/Zheng 2017 reaches only 0.624
with mean cluster count 1.6 and trails fixed `n_pcs=30` with mean delta -0.159,
bootstrap CI -0.307 to -0.017, and p-value 0.039. This completes the
four-dataset CI layer but does not rescue the Nature Methods
stability-superiority gate.

The component-ablation evidence control matrix is now part of the local
submission package. `scripts/build_component_ablation_evidence.py` writes
`results/ablation/component_ablation_evidence.tsv`,
`results/ablation/component_ablation_gap_matrix.tsv`, and
`docs/component_ablation_evidence.md`. This improves traceability for the
20-50 JIF route by separating direct component evidence from missing P0
experiments, but it is not a substitute for the final MP/TW/permutation,
HVG plateau, adaptive embedding, rare-state guard, no-call, and
batch-residualization ablation runs.

The first resumable draft component-ablation benchmark has also been run.
`scripts/run_component_ablation_benchmark.py` now writes
`results/ablation/component_ablation_detail.tsv`,
`results/ablation/component_ablation_summary.tsv`, and
`docs/component_ablation_benchmark.md`. The draft screen contains 135 detail
rows across PC calibration, HVG rule, adaptive embedding, rare-state guard,
forced no-call bypass, and whitening variants. It supports two useful
negative/positive controls: forcing 10 embedding PCs drives null false-call
rate to 1.000, and turning the rare-state guard off drops rare-state power to
0.000 in the current draft grid. This is still not manuscript-grade because
repeat count is 3 and real-data/annotation ablation checks remain pending.

The same draft component-ablation runner now includes a synthetic batch-effect
scenario without rerunning completed null/rare rows. The current detail table
has 165 rows. In the batch-effect screen, default RMTGuard has label ARI 0.934
and batch ARI -0.003, while forced `min_embedding_pcs=10` drops label ARI to
0.563 and raises batch ARI to 0.321. Batch-residualized fitting keeps batch
ARI near zero (-0.002) with label ARI 0.820. These values are useful draft
evidence for no-call/PC guarding and batch-aware preprocessing, but they still
need 20-50 repeats, confidence intervals, and Kang IFN-beta or other real-data
batch checks before manuscript use.

The first public real-data annotation ablation screen has now been added.
`scripts/run_realdata_ablation_annotation.py` writes
`results/ablation/realdata_ablation_annotation_detail.tsv`,
`results/ablation/realdata_ablation_annotation_summary.tsv`, and
`docs/realdata_ablation_annotation.md`. The draft screen covers Kang IFN-beta
PBMC, Baron pancreas, and PBMC68k/Zheng 2017 across seven component variants.
Default RMTGuard v3.3 has mean label ARI 0.473 across the three datasets
versus 0.451 for the forced-minimum-10-PC variant. Kang remains strong
(default label ARI 0.783, batch ARI 0.020), Baron shows that
batch-residualized fitting can improve label ARI while lowering batch ARI
(0.687 label ARI, 0.031 batch ARI), and PBMC68k remains biologically weak
(default label ARI 0.084). This adds real-data annotation checks to the
component-ablation control plane, but it remains draft evidence until expanded
to 10-50 repeats with confidence intervals and matched Seurat/JackStraw
baselines.

The real-data annotation ablation runner now supports `run_label`,
`subsample_fraction`, filtered `ablation_ids`, and summary-level 95% CI fields.
A `subsample80_pilot10` run has been completed on Kang IFN-beta PBMC and
Baron pancreas using 80% cell subsampling, ten repeats, and five key variants:
default v3.3, strict-signal embedding, forced minimum 10 embedding PCs,
rare-state guard off, and batch-residualized fitting. In this pilot, Baron
default label ARI is 0.561 with 95% CI 0.539-0.583, while batch-residualized
fitting reaches 0.620 with 95% CI 0.557-0.683 and lower batch ARI
(0.045 versus 0.064). Kang default label ARI is 0.626 with 95% CI 0.558-0.694,
while batch-residualized fitting is 0.612 with 95% CI 0.523-0.702 and lower
batch ARI (0.011 versus 0.016). This gives a more stable real-data CI layer:
batch residualization is clearly useful for Baron and lowers batch alignment
in Kang, but it is not a universal annotation-recovery improvement. Final
manuscript use still requires 20-50 repeats plus matched Seurat/JackStraw
baselines on the same splits.

The same `subsample80_pilot10` run has now been extended to PBMC68k/Zheng 2017
and the PDAC/TME external validation dataset GSE263733. PBMC68k remains a
diagnostic stress case: default RMTGuard has label ARI 0.003 with 90% no-call
rate, while forcing 10 embedding PCs increases label ARI only to 0.089 and
removes the no-call guard, so this remains negative-control evidence rather
than a rescue. In GSE263733, default RMTGuard has label ARI 0.519 with 95% CI
0.472-0.567 and batch ARI 0.055, while batch-residualized fitting has label
ARI 0.528 with 95% CI 0.499-0.558 and lower batch ARI 0.035. This supports a
bounded batch-aware interpretation on the external PDAC/TME dataset, but the
claim still requires matched Seurat/JackStraw baselines and 20-50 repeat
confirmation before manuscript use.

The `subsample80_pilot10` real-data ablation layer now has publication-facing
pilot assets. `scripts/build_realdata_ablation_assets.py` writes
`results/figures/source_data/figure5_realdata_ablation_delta_summary.tsv`,
`figures/manuscript/figure5_realdata_ablation_forest.png/.pdf/.tiff`,
`results/tables/manuscript/supplemental_realdata_ablation_table.tsv`,
`results/tables/manuscript/supplemental_realdata_ablation_table.docx`, and
`docs/realdata_ablation_figure_table.md`. These files make the current
four-dataset 10-repeat ablation results easier to review, but they do not
upgrade the evidence to final manuscript grade.

The matched-baseline experiment has also been specified as an execution design.
`scripts/build_matched_baseline_design.py` writes
`results/submission/matched_baseline_design.tsv` and
`docs/matched_baseline_design.md`, covering RMTGuard default,
batch-residualized RMTGuard, forced-min-PC negative control, Scanpy default,
elbow-rule Scanpy, Seurat v5 default, Seurat v5 JackStraw, and
permutation/parallel-analysis PCA across Kang, Baron, PBMC68k, and PDAC
GSE263733. This began as a design artifact; official Seurat fixed-PC, elbow,
and JackStraw matched results are now present for the first four prepared
datasets, while additional datasets remain pending.

The local Python portion of the matched-baseline design has now been executed
as a pilot. `scripts/run_matched_baseline_pilot.py` writes
`results/submission/matched_baseline_pilot_detail.tsv`,
`results/submission/matched_baseline_pilot_summary.tsv`,
`results/submission/matched_baseline_external_blockers.tsv`, and
`docs/matched_baseline_pilot.md`. It imports the already-computed RMTGuard
pilot rows and adds local Python baselines on the same 80% subsampling repeat
framework: Scanpy-like fixed 50 PCs, fixed 30 PCs, elbow-rule PCA,
parallel-analysis PCA, and a JackStraw-like permutation proxy. In the current
10-repeat pilot, batch-residualized RMTGuard is the top label-ARI row for
Baron pancreas and PDAC GSE263733, while Kang IFN-beta PBMC has a higher
forced-min-PC row that must remain a negative control rather than a default
recommendation. PBMC68k/Zheng 2017 is still a diagnostic no-call stress case:
local PCA baselines recover weak label ARI around 0.16, whereas default
RMTGuard intentionally no-calls most repeats. The later official Seurat layer
now closes the fixed-PC, elbow, and JackStraw execution blockers on these four
prepared datasets.

The official Seurat matched-baseline path is now a 20-repeat fixed-PC, elbow,
and JackStraw comparator layer across the four prepared real-data datasets.
Direct h5ad import works for some datasets, but PBMC68k/Zheng 2017 exposes a
zellkonverter sparse-matrix type failure on this Windows setup, so
`scripts/export_seurat_mtx_inputs.py` writes a reproducible MatrixMarket bridge
under `data/processed/seurat_mtx/`. `benchmarks/run_seurat_matched_baseline.R`
reads that bridge and runs official Seurat v5
`NormalizeData -> FindVariableFeatures -> ScaleData -> RunPCA -> FindNeighbors
-> FindClusters` on the same 80% subsampling seed framework.
`scripts/build_seurat_matched_baseline_report.py` writes
`results/submission/seurat_matched_baseline_summary.tsv`,
`results/submission/seurat_matched_baseline_status.tsv`, and
`docs/seurat_matched_baseline.md`. In the current
`seurat_jackstraw_subsample80_20x20_mtx` layer, fixed 30 PCs, fixed 50 PCs,
elbow-rule PCs, and JackStraw PCs all run for 20 repeats on Kang IFN-beta PBMC,
Baron pancreas, PBMC68k/Zheng 2017, and PDAC GSE263733. JackStraw uses 20
JackStraw replicates per repeat, with maximum mean runtime 30.016 seconds on
the prepared subsets. This closes the official Seurat repeat-depth blocker;
additional public datasets and final benchmark freeze remain open.

The paired RMTGuard-versus-official-Seurat annotation layer is now generated
from a same-seed 20-repeat RMTGuard default v3.3 run
(`run_label=subsample80_seurat_matched20`) and the official Seurat
fixed30/fixed50/elbow/JackStraw 20-repeat rows. `scripts/build_rmtguard_seurat_paired_statistics.py`
writes `results/submission/rmtguard_seurat_paired_detail.tsv`,
`results/submission/rmtguard_seurat_paired_stats.tsv`,
`results/submission/rmtguard_seurat_paired_status.tsv`,
`results/figures/source_data/figure3_official_seurat_paired_label_delta.tsv`,
and `docs/rmtguard_seurat_paired_statistics.md`, plus PNG/PDF/TIFF forest-plot
assets under `figures/manuscript/`. The current status is
`paired20_manuscript_candidate`: Kang and PDAC fixed-PC/JackStraw comparisons
favor RMTGuard on annotation ARI, Baron is statistically uncertain, and
PBMC68k favors Seurat but remains a weak-absolute-recovery diagnostic no-call
stress context. This closes the paired Seurat comparator blocker; additional
public datasets remain open.

The benchmark breadth layer has been expanded from four to seven public
datasets for repeated-subsampling stability. `scripts/prepare_phase1_datasets.py`
now prepares `paul15_hematopoiesis` through `scanpy.datasets.paul15()`, and
`benchmarks/run_stability_benchmark.py` now includes `paul15_hematopoiesis`,
`pdac_gse154778`, and `pdac_gse263733` in addition to PBMC3k, Kang, Baron, and
PBMC68k. The regenerated `docs/manuscript_grade_stability_statistics.md`
records 10-repeat 80% subsampling stability for all seven datasets. Paul15 was
also added to the same-seed RMTGuard-versus-official-Seurat paired annotation
layer, so `docs/rmtguard_seurat_paired_statistics.md` now covers five labeled
comparator datasets and four official Seurat methods. This closes the pure
data-breadth part of the `additional_datasets` blocker, but it also strengthens
the negative evidence against a broad stability-superiority claim: RMTGuard
trails the strongest elbow/Scanpy-like comparator on PBMC3k, Kang, Baron,
Paul15, PDAC GSE154778, and PDAC GSE263733. The remaining benchmark work is to
extend matched Seurat/JackStraw comparators to the remaining added datasets
where feasible, or explicitly label those added datasets as stability-only
breadth evidence. The official Seurat matched-baseline layer has now also been
extended to PBMC3k and PDAC GSE154778, so fixed30, fixed50, elbow, and
JackStraw rows exist for all seven prepared public datasets. Because PBMC3k and
PDAC GSE154778 lack reliable cell-state labels in the prepared h5ad files, they
must be treated as label-free stability/runtime evidence unless annotations are
added by a documented, reproducible procedure.
