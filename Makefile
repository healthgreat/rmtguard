.PHONY: install test demo benchmark topology-stress realdata-topology no-call callability-decision-map component-ablation-benchmark realdata-ablation-annotation realdata-ablation-assets matched-baseline-design matched-baseline-pilot seurat-mtx-inputs seurat-matched-report seurat-jackstraw-feasibility-report component-ablation-evidence visual-asset-audit project-gantt calibration calibration-figures jif20-50-gap phase1 stability stability-phase1 manuscript-stability-pilot manuscript-stability-statistics seurat-baseline stability-report stability-utility algorithm-rescue pdac-depth publication-plan publication-tables claim-scope journal-compliance publication-board reporting-summary-draft editorial-risk public-release-blockers top-paper-route editorial-presubmission claim-boundary-lint claim-traceability submission-guard external-review-packet external-review-triage external-review-action-plan post-feedback-route route-reframe gb-transfer reviewer-defense author-release github-release-dry-run finalize-release-dry-run gates gate-results release-manifests audit clean

install:
	python -m pip install -e ".[scanpy,dev]"

test:
	python -m unittest discover -s tests

demo:
	python examples/run_synthetic.py

benchmark:
	python benchmarks/run_synthetic_benchmark.py

topology-stress:
	python benchmarks/run_topology_stress_benchmark.py
	python scripts/render_topology_stress_figure.py

realdata-topology:
	python benchmarks/run_realdata_topology_benchmark.py

no-call:
	python scripts/build_no_call_benchmark_report.py

callability-decision-map:
	python scripts/build_callability_decision_map.py
	python scripts/render_no_call_decision_map.py

component-ablation-evidence:
	python scripts/build_component_ablation_evidence.py

component-ablation-benchmark:
	python scripts/run_component_ablation_benchmark.py
	python scripts/build_component_ablation_evidence.py

realdata-ablation-annotation:
	python scripts/run_realdata_ablation_annotation.py
	python scripts/build_component_ablation_evidence.py

realdata-ablation-assets:
	python scripts/build_realdata_ablation_assets.py

matched-baseline-design:
	python scripts/build_matched_baseline_design.py

matched-baseline-pilot:
	python scripts/run_matched_baseline_pilot.py

seurat-mtx-inputs:
	python scripts/export_seurat_mtx_inputs.py --datasets kang_ifnb_pbmc baron_pancreas pbmc68k_zheng2017 pdac_gse263733

seurat-matched-report:
	python scripts/build_seurat_matched_baseline_report.py

seurat-jackstraw-feasibility-report:
	python scripts/build_seurat_jackstraw_feasibility_report.py

phase1:
	python scripts/prepare_phase1_datasets.py --dataset pbmc3k_10x --max-cells 1000
	python benchmarks/run_phase1_benchmark.py --datasets pbmc3k_10x

stability:
	python benchmarks/run_stability_benchmark.py --datasets pbmc3k_10x

stability-phase1:
	python benchmarks/run_stability_benchmark.py --datasets pbmc3k_10x kang_ifnb_pbmc baron_pancreas pbmc68k_zheng2017 --methods rmtguard rmtguard_strict_signal scanpy_default_like fixed_pcs_30 fixed_pcs_50 elbow_rule parallel_analysis jackstraw_like

manuscript-stability-pilot:
	python benchmarks/run_stability_benchmark.py --outdir results/manuscript_stability_benchmarks --datasets pbmc3k_10x --methods rmtguard rmtguard_strict_signal scanpy_default_like fixed_pcs_30 fixed_pcs_50 elbow_rule parallel_analysis jackstraw_like --n-repeats 10 --sample-fraction 0.8 --baseline-permutations 20
	python scripts/build_manuscript_stability_statistical_report.py

manuscript-stability-statistics:
	python scripts/build_manuscript_stability_statistical_report.py

seurat-baseline:
	Rscript benchmarks/run_seurat_baseline.R --input data/processed/pbmc3k_10x.h5ad --dataset-id pbmc3k_10x

stability-report:
	python scripts/build_stability_gate_report.py

stability-utility:
	python scripts/build_stability_utility_report.py

algorithm-rescue:
	python scripts/build_algorithm_rescue_probe_report.py

pdac-depth:
	python scripts/build_pdac_showcase_depth_report.py

publication-plan:
	python scripts/build_publication_20_50_plan.py

publication-tables:
	python scripts/build_publication_tables.py

visual-asset-audit:
	python scripts/audit_publication_visual_assets.py

project-gantt:
	python scripts/build_project_gantt.py

calibration:
	python scripts/run_realistic_null_power_calibration.py
	python scripts/render_calibration_figures.py

calibration-figures:
	python scripts/render_calibration_figures.py

jif20-50-gap:
	python scripts/build_jif20_50_gap_assessment.py

claim-scope:
	python scripts/build_claim_scope_decision.py

journal-compliance:
	python scripts/build_journal_compliance_audit.py

publication-board:
	python scripts/build_publication_execution_board.py

reporting-summary-draft:
	python scripts/build_reporting_summary_draft.py

editorial-risk:
	python scripts/build_editorial_risk_audit.py

public-release-blockers:
	python scripts/build_public_release_blocker_report.py

top-paper-route:
	python scripts/build_top_paper_route_package.py

editorial-presubmission:
	python scripts/build_editorial_presubmission_packet.py

claim-boundary-lint:
	python scripts/lint_claim_boundaries.py

claim-traceability:
	python scripts/validate_claim_traceability.py

submission-guard:
	python scripts/build_submission_guard.py

external-review-packet:
	python scripts/export_current_article_review_packet.py

external-review-triage:
	python scripts/triage_external_review_feedback.py

external-review-action-plan:
	python scripts/build_external_review_action_plan.py

post-feedback-route:
	python scripts/build_post_feedback_journal_route_gate.py

route-reframe:
	python scripts/build_route_reframe_package.py

gb-transfer:
	python scripts/build_genome_biology_transfer_package.py

reviewer-defense:
	python scripts/build_reviewer_defense_package.py

author-release:
	python scripts/build_author_release_execution_packet.py

github-release-dry-run:
	python scripts/execute_github_release.py --repo-url https://github.com/your-lab/rmtguard

finalize-release-dry-run:
	python scripts/finalize_submission_release.py

gates:
	python scripts/evaluate_submission_gates.py

gate-results:
	python scripts/build_no_call_benchmark_report.py
	python scripts/build_stability_gate_report.py
	python scripts/build_stability_utility_report.py
	python scripts/build_algorithm_rescue_probe_report.py
	python scripts/build_pdac_showcase_depth_report.py
	python scripts/update_gate_evidence_from_results.py
	python scripts/evaluate_submission_gates.py --evidence results/gates/gate_evidence.tsv --out results/gates/gate_report.tsv
	python scripts/build_publication_20_50_plan.py
	python scripts/build_claim_scope_decision.py

release-manifests:
	python scripts/build_release_artifact_manifest.py
	python scripts/build_release_asset_bundle.py
	python scripts/build_external_release_plan.py
	python scripts/build_public_release_blocker_report.py
	python scripts/build_github_staging_plan.py
	python scripts/stage_github_release_files.py
	python scripts/build_github_release_handoff.py
	python scripts/update_repository_metadata.py
	python scripts/record_external_release.py
	python scripts/build_no_call_benchmark_report.py
	python scripts/build_stability_gate_report.py
	python scripts/build_stability_utility_report.py
	python scripts/build_algorithm_rescue_probe_report.py
	python scripts/build_pdac_showcase_depth_report.py
	python scripts/build_publication_20_50_plan.py
	python scripts/build_claim_scope_decision.py
	python scripts/build_figure_source_data.py
	python scripts/build_callability_decision_map.py
	python scripts/render_main_figures.py
	python scripts/build_publication_tables.py
	python scripts/audit_publication_visual_assets.py
	python scripts/build_component_ablation_evidence.py
	python scripts/build_project_gantt.py
	python scripts/run_realistic_null_power_calibration.py
	python scripts/render_calibration_figures.py
	python scripts/run_component_ablation_benchmark.py
	python scripts/run_realdata_ablation_annotation.py
	python scripts/build_realdata_ablation_assets.py
	python scripts/build_matched_baseline_design.py
	python scripts/run_matched_baseline_pilot.py
	python scripts/export_seurat_mtx_inputs.py --datasets kang_ifnb_pbmc baron_pancreas pbmc68k_zheng2017 pdac_gse263733
	python scripts/build_seurat_matched_baseline_report.py
	python scripts/build_seurat_jackstraw_feasibility_report.py
	python scripts/build_component_ablation_evidence.py
	python scripts/build_manuscript_stability_statistical_report.py
	python scripts/build_jif20_50_gap_assessment.py
	python scripts/build_manuscript_evidence_package.py
	python scripts/build_manuscript_draft_package.py
	python scripts/build_journal_compliance_audit.py
	python scripts/build_publication_execution_board.py
	python scripts/build_reporting_summary_draft.py
	python scripts/build_editorial_risk_audit.py
	python scripts/build_top_paper_route_package.py
	python scripts/build_editorial_presubmission_packet.py
	python scripts/lint_claim_boundaries.py
	python scripts/validate_claim_traceability.py
	python scripts/build_submission_guard.py
	python scripts/build_release_readiness.py
	python scripts/build_journal_compliance_audit.py
	python scripts/build_publication_execution_board.py
	python scripts/build_reporting_summary_draft.py
	python scripts/build_editorial_risk_audit.py
	python scripts/build_presubmission_package.py
	python scripts/triage_external_review_feedback.py
	python scripts/build_external_review_action_plan.py
	python scripts/build_post_feedback_journal_route_gate.py
	python scripts/build_route_reframe_package.py
	python scripts/build_genome_biology_transfer_package.py
	python scripts/build_reviewer_defense_package.py
	python scripts/build_author_release_execution_packet.py
	python scripts/export_current_article_review_packet.py
	python scripts/build_release_artifact_manifest.py
	python scripts/build_release_asset_bundle.py

audit:
	python scripts/release_audit.py

clean:
	python scripts/clean_artifacts.py
