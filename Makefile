.PHONY: install test demo benchmark no-call phase1 stability stability-phase1 seurat-baseline stability-report stability-utility algorithm-rescue pdac-depth publication-plan claim-scope journal-compliance publication-board reporting-summary-draft editorial-risk public-release-blockers top-paper-route editorial-presubmission claim-boundary-lint claim-traceability submission-guard external-review-packet github-release-dry-run finalize-release-dry-run gates gate-results release-manifests audit clean

install:
	python -m pip install -e ".[scanpy,dev]"

test:
	python -m unittest discover -s tests

demo:
	python examples/run_synthetic.py

benchmark:
	python benchmarks/run_synthetic_benchmark.py

no-call:
	python scripts/build_no_call_benchmark_report.py

phase1:
	python scripts/prepare_phase1_datasets.py --dataset pbmc3k_10x --max-cells 1000
	python benchmarks/run_phase1_benchmark.py --datasets pbmc3k_10x

stability:
	python benchmarks/run_stability_benchmark.py --datasets pbmc3k_10x

stability-phase1:
	python benchmarks/run_stability_benchmark.py --datasets pbmc3k_10x kang_ifnb_pbmc baron_pancreas pbmc68k_zheng2017 --methods rmtguard rmtguard_strict_signal scanpy_default_like fixed_pcs_30 fixed_pcs_50 elbow_rule parallel_analysis jackstraw_like

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
	python scripts/render_main_figures.py
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
	python scripts/export_current_article_review_packet.py
	python scripts/build_release_artifact_manifest.py
	python scripts/build_release_asset_bundle.py

audit:
	python scripts/release_audit.py

clean:
	python scripts/clean_artifacts.py
