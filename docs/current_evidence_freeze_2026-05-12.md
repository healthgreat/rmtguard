# RMTGuard current evidence freeze

Date: 2026-05-12
Project: RMTGuard

## Purpose

This freeze records the current manuscript-facing evidence assets, their
source files, checksums, claim boundaries, and next actions. It is a
quality-control artifact, not a statement that the manuscript is ready for
submission.

## Freeze Status

- Items checked: `31`
- Missing items: `0`
- Manifest: `results/submission/current_evidence_freeze_manifest.tsv`

## Category Counts

- `competitor`: 1
- `figure`: 10
- `journal_route`: 3
- `manual_blocker`: 1
- `manuscript_text`: 4
- `project_management`: 1
- `release`: 3
- `source_data`: 5
- `statistics`: 3

## Current 20-50 JIF Distance

- Stronger than the earlier state: public code/DOI, scLENSpy comparator,
  realistic null/power calibration, synthetic topology stress, real-data
  topology monitor, no-call decision map, and strengthened Figure 4 assets
  are now present.
- Still not a guaranteed Nature Methods package: the strongest defensible
  claim is diagnostic random-matrix callability with transparent
  trade-offs, not broad superiority over all fixed-PC or elbow baselines.
- Remaining high-impact risks: final source-data/figure freeze after all
  benchmark decisions, corresponding-author Figure 4 acknowledgement,
  and optional second real trajectory/perturbation topology dataset if
  Nature Methods remains the preferred route.

## Frozen Items

| ID | Category | Exists | Role | Claim boundary | Next action |
| --- | --- | --- | --- | --- | --- |
| release_github_zenodo | release | True | Public code/release evidence | Supports code availability only; does not prove scientific acceptance. | Re-check repository, release, and DOI immediately before submission. |
| nature_go_no_go | journal_route | True | Nature Methods go/no-go control packet | Presubmission may be considered; full submission remains gated. | Update after final author acknowledgement and figure freeze. |
| genome_biology_fallback | journal_route | True | Genome Biology fallback packet | Fallback route if Nature Methods novelty/stability bar is not met. | Refresh after any editorial feedback. |
| figure1_algorithm | figure | True | Figure 1 algorithm diagnostics PDF | Algorithm overview and diagnostic logic; avoid claiming mathematical novelty beyond RMT-guarded workflow. | Regenerate after final algorithm text freeze. |
| figure1_source | source_data | True | Figure 1 source data | Supports plotted diagnostic examples only. | Verify exact panel mapping before submission. |
| figure2_synthetic | figure | True | Figure 2 synthetic benchmark PDF | Supports null/rare-state and synthetic behavior claims under tested settings. | Cross-check against 50-repeat calibration before final text. |
| realistic_null_calibration | statistics | True | 50-repeat realistic null and rare-state calibration report | Supports controlled false-signal behavior in tested null families; weak rare-state setting remains a limitation. | Keep low-prevalence weak-effect limitation visible. |
| figure3_public_benchmark | figure | True | Figure 3 public benchmark PDF | Does not support broad stability superiority against all baselines. | Use bounded language and include no-call decision map. |
| figure3_seurat_paired | figure | True | Official Seurat paired comparison forest plot | Supports paired comparison reporting; not a universal RMTGuard win. | Ensure comparator methods and paired-test assumptions are stated. |
| no_call_decision_map | figure | True | Figure 3 callability/no-call decision map | Supports transparent no-call/caveat behavior; no-call rows cannot be converted into discovery claims. | Keep in main or supplement depending on final Figure 3 layout. |
| no_call_source | source_data | True | Figure 3 no-call source data | Machine-readable basis for no-call/caveat decisions. | Verify thresholds remain consistent with Methods. |
| topology_stress | figure | True | Synthetic topology stress benchmark PDF | Supports synthetic topology preservation monitor; not proof of real trajectory correctness. | Keep together with real-data topology monitor. |
| topology_stress_source | source_data | True | Synthetic topology stress summary | 20-repeat synthetic line/branch/loop evidence. | Mention CONCORD-style inspiration without claiming CONCORD reimplementation. |
| realdata_topology | figure | True | Paul15 real-data topology monitor PDF | Mixed trade-off evidence; supports topology monitoring, not broad topology superiority. | Optional: add second real trajectory/perturbation dataset if targeting Nature Methods. |
| realdata_topology_source | source_data | True | Paul15 real-data topology source data | Annotation-derived topology metrics only; not experimentally measured pseudotime. | Keep limitation in legend and Results. |
| sclens_direct_comparator | competitor | True | Direct scLENSpy n_rand_matrix=20 comparator report | Supports direct competitor coverage on PBMC3k/Kang only. | Avoid claiming all scLENS variants or all datasets are covered. |
| figure4_strengthened | figure | True | Strengthened PDAC/TME Figure 4 PDF | Bounded public-data application; no mechanism, prognosis, therapy-response, spatial, or protein-validation claim. | Needs corresponding-author acknowledgement before external use. |
| figure4_source | source_data | True | Strengthened Figure 4 source data | Supports marker/pathway/atlas-use-case panels only. | Confirm caption wording with authors. |
| figure5_ablation | figure | True | Real-data ablation forest plot | Supports component contribution discussion with tested datasets and repeats only. | Avoid universal component-necessity wording. |
| component_ablation_report | statistics | True | 20-repeat synthetic component ablation report | Supports marginal component discussion for tested synthetic settings. | Pair with real-data ablation annotation report. |
| realdata_ablation_report | statistics | True | Real-data ablation annotation report | Supports annotation/batch ablation checks on included labeled datasets. | Keep dataset coverage explicit. |
| gantt | project_management | True | Current project Gantt chart | Project-management status only; not scientific evidence. | Refresh after each major benchmark addition. |
| manual_author_actions | manual_blocker | True | Manual author action checklist | Tracks actions Codex cannot certify alone. | Authors must verify funding, COI, ethics, and Figure 4 acknowledgement. |
| results_freeze_aligned_draft | manuscript_text | True | Freeze-aligned Results draft | Draft Results text only; every paragraph remains bounded by current evidence and is not final journal prose. | Use as source-controlled starting text for the next manuscript assembly pass. |
| figure_legends_freeze_aligned | manuscript_text | True | Freeze-aligned figure legends draft | Draft captions only; legends must not upgrade caveated or no-call evidence. | Use as caption source and revise only after final figure layout is chosen. |
| freeze_aligned_text_audit | manuscript_text | True | Machine-readable claim audit for freeze-aligned text | Controls wording boundaries; does not certify journal acceptance. | Re-run after any Results or legend change. |
| external_review_docx | manuscript_text | True | Word packet for external scientific review | Handoff document only; it packages evidence boundaries and reviewer questions but does not certify submission readiness. | Share with external reviewers and route their comments through the feedback triage pipeline. |
| nature_reporting_summary_draft | journal_route | True | Nature Portfolio reporting-summary worksheet | Draft worksheet only; it pre-fills reproducibility, data, statistics and software answers but requires corresponding-author verification. | Transfer verified content into the official Nature Portfolio form only after final figure/source-data freeze. |
| figure_caption_source_audit | figure | True | Figure-caption-source consistency audit | Confirms rendered assets, source data and frozen legends exist while preserving claim boundaries; does not certify journal acceptance. | Keep Figure 4 author acknowledgement as the remaining figure-level manual blocker. |
| post_release_version_coverage_audit | release | True | Post-release version coverage audit | Shows whether the current manuscript-facing branch is covered by the archived DOI; does not create a new release. | Prepare v0.1.1 only after Figure 4 acknowledgement, final author declarations, and final figure/source-data freeze. |
| v0_1_1_release_preflight | release | True | v0.1.1 no-action release preflight | Blocks premature release creation until author declarations, Figure 4 acknowledgement, reporting-summary verification, claim integrity, and version coverage are controlled. | Rerun immediately before any v0.1.1 tag or Zenodo archive. |

## Use In Manuscript Planning

Use this file as the source-of-truth checklist before drafting Results,
figure legends, cover letter claims, and response-to-reviewer language.
Any claim not represented here should be treated as unsupported until a
new evidence item is added and this freeze is regenerated.
