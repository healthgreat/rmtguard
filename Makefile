.PHONY: install test demo benchmark no-call phase1 stability stability-phase1 seurat-baseline stability-report publication-plan journal-compliance publication-board reporting-summary-draft editorial-risk github-release-dry-run finalize-release-dry-run gates gate-results release-manifests audit clean

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

publication-plan:
	python scripts/build_publication_20_50_plan.py

journal-compliance:
	python scripts/build_journal_compliance_audit.py

publication-board:
	python scripts/build_publication_execution_board.py

reporting-summary-draft:
	python scripts/build_reporting_summary_draft.py

editorial-risk:
	python scripts/build_editorial_risk_audit.py

github-release-dry-run:
	python scripts/execute_github_release.py --repo-url https://github.com/your-lab/rmtguard

finalize-release-dry-run:
	python scripts/finalize_submission_release.py

gates:
	python scripts/evaluate_submission_gates.py

gate-results:
	python scripts/build_no_call_benchmark_report.py
	python scripts/build_stability_gate_report.py
	python scripts/update_gate_evidence_from_results.py
	python scripts/evaluate_submission_gates.py --evidence results/gates/gate_evidence.tsv
	python scripts/build_publication_20_50_plan.py

release-manifests:
	python scripts/build_release_artifact_manifest.py
	python scripts/build_release_asset_bundle.py
	python scripts/build_external_release_plan.py
	python scripts/build_github_staging_plan.py
	python scripts/stage_github_release_files.py
	python scripts/build_github_release_handoff.py
	python scripts/update_repository_metadata.py
	python scripts/record_external_release.py
	python scripts/build_no_call_benchmark_report.py
	python scripts/build_stability_gate_report.py
	python scripts/build_publication_20_50_plan.py
	python scripts/build_figure_source_data.py
	python scripts/render_main_figures.py
	python scripts/build_manuscript_evidence_package.py
	python scripts/build_manuscript_draft_package.py
	python scripts/build_journal_compliance_audit.py
	python scripts/build_publication_execution_board.py
	python scripts/build_reporting_summary_draft.py
	python scripts/build_editorial_risk_audit.py
	python scripts/build_release_readiness.py
	python scripts/build_journal_compliance_audit.py
	python scripts/build_publication_execution_board.py
	python scripts/build_reporting_summary_draft.py
	python scripts/build_editorial_risk_audit.py
	python scripts/build_presubmission_package.py
	python scripts/build_release_artifact_manifest.py
	python scripts/build_release_asset_bundle.py

audit:
	python scripts/release_audit.py

clean:
	python scripts/clean_artifacts.py
