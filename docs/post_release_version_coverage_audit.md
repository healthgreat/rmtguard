# Post-release version coverage audit

Generated: 2026-05-12

## Boundary

This audit compares the archived `v0.1.0` release with the current branch. It does not create a tag, push a release, or mint a new DOI.

## Bottom Line

- Commits after `v0.1.0`: `44`.
- Changed files after `v0.1.0`: `257`.
- Manuscript-facing changed files: `247`.
- Recommendation: `prepare_v0.1.1_after_author_ack`.
- Candidate next release: `v0.1.1`.

## Audit Rows

| Audit ID | Status | Evidence | Required action | Notes |
| --- | --- | --- | --- | --- |
| release_tag | present | v0.1.0 | Keep v0.1.0 immutable. | v0.1.0 commit 053b84ad3bf04ebc1193b5fff420b770946a3845. |
| current_head | tracked | d29c9636eb5ab678f69698851b02edc867bcb5ff | Use this commit or a later clean commit as the basis for any v0.1.1 release. | 44 commits after v0.1.0. |
| worktree_cleanliness | clean | none | Commit or intentionally ignore all changes before release. | A clean worktree is required before tagging a new release. |
| manuscript_facing_delta | needs_new_release_if_submitted | 247 | Create v0.1.1 only after Figure 4 acknowledgement and final figure/source-data freeze if these post-release files are cited. | Manuscript-facing files changed after the archived v0.1.0 DOI. |
| figure_source_delta | changed | 27 | Ensure final figures and source data are included in the next release if used in submission. | Figure/source-data changes after v0.1.0 affect reproducibility coverage. |
| pipeline_code_delta | changed | 49 | Archive updated scripts/benchmarks in the same release as the submitted source data. | Code changes after v0.1.0 affect rerun parity. |
| release_recommendation | prepare_v0.1.1_after_author_ack | v0.1.1 | Do not tag the new release until manual Figure 4 and author-declaration blockers are resolved. | The release refresh is a submission-readiness action, not a current scientific pass. |

## Changed File Classes

| Class | Count |
| --- | ---: |
| ablation_result | 5 |
| benchmark_code | 4 |
| calibration_figure | 3 |
| calibration_result | 5 |
| competitor_result | 26 |
| figure_source_data | 6 |
| handoff_document | 3 |
| handoff_email | 3 |
| journal_figure | 18 |
| manuscript_text | 16 |
| metadata | 4 |
| other | 9 |
| pdac_result | 10 |
| pipeline_code | 45 |
| release_metadata | 2 |
| repository_doc | 1 |
| reproducibility_entrypoint | 1 |
| shared_export | 1 |
| submission_doc | 52 |
| submission_table | 37 |
| topology_result | 6 |

## Change Status Counts

| Git status | Count |
| --- | ---: |
| A | 215 |
| M | 42 |

## Example Manuscript-facing Changed Files

| Status | Class | Path |
| --- | --- | --- |
| M | release_metadata | `.zenodo.json` |
| M | release_metadata | `CITATION.cff` |
| M | reproducibility_entrypoint | `Makefile` |
| M | repository_doc | `README.md` |
| A | benchmark_code | `benchmarks/run_realdata_topology_benchmark.py` |
| A | benchmark_code | `benchmarks/run_sclens_h5ad_smoke.py` |
| A | benchmark_code | `benchmarks/run_sclens_stability_benchmark.py` |
| A | benchmark_code | `benchmarks/run_topology_stress_benchmark.py` |
| A | submission_doc | `docs/added_dataset_annotation_boundary.md` |
| M | submission_doc | `docs/author_declarations_and_credit_roles.md` |
| M | submission_doc | `docs/author_metadata_status.md` |
| M | submission_doc | `docs/author_release_execution_packet.md` |
| A | submission_doc | `docs/benchmark_upgrade_from_concord_sclens_2026-05-12.md` |
| M | submission_doc | `docs/claim_boundary_lint.md` |
| M | submission_doc | `docs/claim_traceability.md` |
| A | submission_doc | `docs/competitor_positioning_concord_sclens_2026-05-12.md` |
| M | submission_doc | `docs/component_ablation_benchmark.md` |
| A | submission_doc | `docs/corresponding_author_proxy_assumption.md` |
| A | submission_doc | `docs/corresponding_author_reply_intake_runbook.md` |
| A | submission_doc | `docs/corresponding_author_signoff_tracker.md` |
| A | submission_doc | `docs/current_evidence_freeze_2026-05-12.md` |
| M | submission_doc | `docs/editorial_presubmission_packet.md` |
| A | submission_doc | `docs/figure4_pdac_tme_wording_freeze.md` |
| A | submission_doc | `docs/figure4_strengthened_text_audit.md` |
| A | submission_doc | `docs/figure_caption_source_audit.md` |
| A | submission_doc | `docs/genome_biology_fallback_v2_packet.md` |
| M | submission_doc | `docs/jif20_50_gap_assessment.md` |
| M | submission_doc | `docs/manual_author_execution_steps.md` |
| A | submission_doc | `docs/manual_next_actions_20_50.md` |
| A | submission_doc | `docs/manuscript_grade_null_power_grid_design.md` |
| A | submission_doc | `docs/mentor_journal_decision_2026-05-10.md` |
| A | submission_doc | `docs/nature_methods_48h_execution_packet.md` |
| A | submission_doc | `docs/nature_methods_go_no_go_final.md` |
| A | submission_doc | `docs/nature_methods_next_round_gate_board.md` |
| A | submission_doc | `docs/nature_methods_official_route_verification.md` |
| A | submission_doc | `docs/nature_methods_presubmission_send_runbook.md` |
| M | submission_doc | `docs/nature_reporting_summary_draft.md` |
| M | submission_doc | `docs/no_call_decision_map.md` |
| A | submission_doc | `docs/p0_benchmark_upgrade_status_2026-05-12.md` |
| A | submission_doc | `docs/p0_component_ablation_run_sheet.md` |

## Interpretation

- The existing DOI covers `v0.1.0`. It should not be described as covering later manuscript-facing changes unless a new release is made.
- If the submitted manuscript cites current figures, source data, reporting-summary worksheets or post-release scripts, prepare `v0.1.1` after all author-controlled blockers are resolved.
- Do not create the new release before Figure 4 bounded wording and author declarations are confirmed, because a release should archive the exact submission state.
