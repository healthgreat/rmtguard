from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    script = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


artifact_manifest = _load_script("build_release_artifact_manifest")
staging_plan = _load_script("build_github_staging_plan")
stage_files = _load_script("stage_github_release_files")
github_handoff = _load_script("build_github_release_handoff")
external_release_record = _load_script("record_external_release")
repo_metadata = _load_script("update_repository_metadata")
external_release = _load_script("build_external_release_plan")
release_assets = _load_script("build_release_asset_bundle")
manuscript_evidence = _load_script("build_manuscript_evidence_package")
manuscript_draft = _load_script("build_manuscript_draft_package")
stability_gate = _load_script("build_stability_gate_report")
stability_utility = _load_script("build_stability_utility_report")
algorithm_rescue = _load_script("build_algorithm_rescue_probe_report")
no_call_report = _load_script("build_no_call_benchmark_report")
publication_plan = _load_script("build_publication_20_50_plan")
presubmission_package = _load_script("build_presubmission_package")
journal_compliance = _load_script("build_journal_compliance_audit")
publication_board = _load_script("build_publication_execution_board")
github_release = _load_script("execute_github_release")
submission_finalizer = _load_script("finalize_submission_release")
reporting_summary = _load_script("build_reporting_summary_draft")
editorial_risk = _load_script("build_editorial_risk_audit")
release_audit = _load_script("release_audit")


class ReleasePlanTest(unittest.TestCase):
    def test_artifact_classification_keeps_processed_h5ad_out_of_git(self) -> None:
        path = ROOT / "data" / "processed" / "pbmc3k_10x.h5ad"
        artifact_type, destination, required, _notes = artifact_manifest._classify(path, ignored=True)
        self.assertEqual(artifact_type, "processed_public_data")
        self.assertEqual(destination, "do_not_commit_rebuild_or_archive_large_outputs")
        self.assertEqual(required, "yes")

    def test_stage_action_rejects_non_github_artifacts(self) -> None:
        row = {
            "path": "results/figures/source_data/table.tsv",
            "release_destination": "zenodo_or_github_release_asset",
            "git_ignored": "True",
        }
        action, _reason = staging_plan._stage_action(row)
        self.assertEqual(action, "do_not_stage")

    def test_stageable_paths_only_accepts_unignored_github_rows(self) -> None:
        rows = [
            {"action": "stage_for_initial_commit", "path": "README.md", "git_ignored": "False"},
            {"action": "do_not_stage", "path": "data/pbmc3k_raw.h5ad", "git_ignored": "True"},
        ]
        self.assertEqual(stage_files.stageable_paths(rows), ["README.md"])

    def test_stageable_paths_refuses_ignored_stage_row(self) -> None:
        rows = [{"action": "stage_for_initial_commit", "path": "README.md", "git_ignored": "True"}]
        with self.assertRaises(ValueError):
            stage_files.stageable_paths(rows)

    def test_repository_url_normalization(self) -> None:
        self.assertEqual(
            repo_metadata.normalize_repo_url("https://github.com/example-lab/rmtguard.git"),
            "https://github.com/example-lab/rmtguard",
        )

    def test_github_handoff_bundle_path_is_tag_scoped(self) -> None:
        path = github_handoff._bundle_path("v0.1.0-rc1")
        self.assertEqual(path.name, "rmtguard_v0.1.0-rc1_source.bundle")

    def test_external_release_metadata_validates_doi(self) -> None:
        self.assertEqual(external_release_record.normalize_doi("https://doi.org/10.5281/zenodo.12345"), "10.5281/zenodo.12345")
        with self.assertRaises(ValueError):
            external_release_record.normalize_doi("zenodo pending")

    def test_external_release_metadata_plan_requires_inputs(self) -> None:
        rows = external_release_record.planned_rows(None, None)
        self.assertTrue(rows)
        self.assertTrue(all(row["status"] == "pending" for row in rows))

    def test_repository_url_rejects_non_github_url(self) -> None:
        with self.assertRaises(ValueError):
            repo_metadata.normalize_repo_url("https://example.com/rmtguard")

    def test_release_audit_supports_source_only_ci_mode(self) -> None:
        self.assertEqual(release_audit.main(["--source-only"]), 0)

    def test_external_release_plan_keeps_external_steps_pending(self) -> None:
        rows = external_release.build_steps()
        status_by_step = {row["step_id"]: row["status"] for row in rows}
        command_by_step = {row["step_id"]: row["command"] for row in rows}
        self.assertEqual(status_by_step["01_create_github_repo"], "pending_external")
        self.assertEqual(status_by_step["11_archive_with_zenodo"], "pending_external")
        self.assertIn("stage_github_release_files.py --execute", command_by_step["05_stage_approved_files"])

    def test_release_asset_selection_excludes_data_paths(self) -> None:
        rows = [
            {
                "path": "data/processed/pbmc3k_10x.h5ad",
                "release_destination": "zenodo_or_github_release_asset",
                "required_for_submission_package": "yes",
                "artifact_type": "processed_public_data",
                "size_bytes": "1",
            },
            {
                "path": "README.md",
                "release_destination": "github_repository",
                "required_for_submission_package": "yes",
                "artifact_type": "source_code_or_metadata",
                "size_bytes": "1",
            },
        ]
        selected = release_assets.select_assets(rows)
        self.assertEqual(selected[0]["asset_status"], "excluded")
        self.assertEqual(len(selected), 1)

    def test_release_asset_selection_excludes_self_outputs(self) -> None:
        rows = [
            {
                "path": "results/release/release_asset_manifest.tsv",
                "release_destination": "zenodo_or_github_release_asset",
                "required_for_submission_package": "yes",
                "artifact_type": "manuscript_result_or_source_data",
                "size_bytes": "1",
            }
        ]
        selected = release_assets.select_assets(rows)
        self.assertEqual(selected[0]["asset_status"], "excluded")

    def test_manuscript_claims_include_software_release_boundary(self) -> None:
        claim_ids = {row["claim_id"] for row in manuscript_evidence.build_claim_rows()}
        self.assertIn("software_release", claim_ids)
        self.assertIn("pbmc3k_stability", claim_ids)

    def test_manuscript_draft_keeps_not_submission_ready_boundary(self) -> None:
        claims = manuscript_evidence.build_claim_rows()
        checklist = manuscript_evidence.build_checklist_rows()
        draft_text = "\n".join(manuscript_draft.build_presubmission_draft(claims, checklist))
        self.assertIn("not submission-ready", draft_text)
        self.assertIn("PBMC3k", draft_text)
        self.assertNotIn("Nature Methods ready", draft_text)

    def test_reviewer_objection_matrix_tracks_blockers(self) -> None:
        claims = manuscript_evidence.build_claim_rows()
        rows = manuscript_draft.build_reviewer_objection_matrix(claims)
        objection_ids = {row["objection_id"] for row in rows}
        self.assertIn("stability_advantage", objection_ids)
        self.assertIn("software_release", objection_ids)
        status_by_id = {row["objection_id"]: row["current_status"] for row in rows}
        self.assertIn(status_by_id["stability_advantage"], {"pass", "borderline", "fail"})
        self.assertEqual(status_by_id["software_release"], "pending")

    def test_storyline_map_preserves_callability_caveat_for_figure3(self) -> None:
        claims = manuscript_evidence.build_claim_rows()
        rows = manuscript_draft.build_storyline_panel_map(claims)
        figure3 = next(row for row in rows if row["figure"] == "Figure 3")
        self.assertIn(figure3["status"], {"pass", "borderline", "blocked"})
        self.assertIn("fixed", figure3["caveat"].lower())
        self.assertIn("no-call", figure3["caveat"].lower())

    def test_stability_gate_diagnostics_flags_below_floor(self) -> None:
        rows = [
            {"dataset_id": "pbmc68k", "method": "rmtguard", "mean_pairwise_ari": "0.60", "mean_cluster_n": "1.4", "n_repeats": "5", "sample_fraction": "0.8"},
            {"dataset_id": "pbmc68k", "method": "fixed_pcs_30", "mean_pairwise_ari": "0.81", "mean_cluster_n": "8", "n_repeats": "5", "sample_fraction": "0.8"},
        ]
        diagnostics = stability_gate.build_diagnostics(rows)
        self.assertEqual(diagnostics[0]["status"], "fail_below_floor")
        self.assertIn("collapses", diagnostics[0]["notes"])

    def test_stability_utility_separates_stability_from_annotation(self) -> None:
        stability_rows = [
            {"dataset_id": "kang", "method": "rmtguard", "mean_pairwise_ari": "0.82", "mean_cluster_n": "4"},
            {"dataset_id": "kang", "method": "elbow_rule", "mean_pairwise_ari": "0.88", "mean_cluster_n": "8"},
            {"dataset_id": "kang", "method": "fixed_pcs_30", "mean_pairwise_ari": "0.70", "mean_cluster_n": "8"},
        ]
        annotation_rows = [
            {"dataset_id": "kang", "method": "rmtguard", "ari": "0.78"},
            {"dataset_id": "kang", "method": "elbow_rule", "ari": "0.66"},
            {"dataset_id": "kang", "method": "fixed_pcs_30", "ari": "0.68"},
        ]
        diagnostics = [{"dataset_id": "kang", "status": "fail_below_best_baseline"}]
        rows = stability_utility.build_rows(stability_rows, annotation_rows, diagnostics)
        by_method = {row["method"]: row for row in rows}
        self.assertEqual(by_method["elbow_rule"]["utility_relation_vs_rmtguard"], "comparator_higher_stability_lower_annotation")
        self.assertEqual(by_method["elbow_rule"]["comparator_dominates_rmtguard"], "no")
        self.assertEqual(by_method["fixed_pcs_30"]["rmtguard_dominates_comparator"], "yes")

    def test_algorithm_rescue_report_rejects_harmful_probe(self) -> None:
        rows = algorithm_rescue.build_rows(
            [
                {
                    "probe_id": "resolution_path_min0p8",
                    "path": ROOT / "missing.tsv",
                    "tested_change": "missing probe",
                    "decision_rule": "reject missing",
                }
            ]
        )
        self.assertEqual(rows[0]["decision"], "incomplete_or_missing_probe")
        self.assertEqual(
            algorithm_rescue._decision("resolution_path_min0p8", "kang_ifnb_pbmc", 0.69, 5.6),
            "reject_hurts_kang_stability",
        )

    def test_no_call_report_validates_null_and_planted_signal(self) -> None:
        rows = no_call_report.build_rows(
            [
                {
                    "scenario": "pure_null",
                    "method": "rmtguard",
                    "analysis_status": "diagnostic_no_call",
                    "no_call_reason": "insufficient_signal_pcs_for_embedding",
                    "n_signal_pcs": "1",
                    "accepted_embedding_pcs": "0",
                    "cluster_n": "1",
                    "ari": "",
                },
                {
                    "scenario": "planted_low_rank",
                    "method": "rmtguard",
                    "analysis_status": "ok",
                    "n_signal_pcs": "4",
                    "accepted_embedding_pcs": "4",
                    "cluster_n": "3",
                    "ari": "0.95",
                },
                {
                    "scenario": "rare_state",
                    "method": "rmtguard",
                    "analysis_status": "ok",
                    "n_signal_pcs": "4",
                    "accepted_embedding_pcs": "4",
                    "cluster_n": "3",
                    "ari": "0.93",
                },
            ]
        )
        by_scenario = {row["scenario"]: row for row in rows}
        self.assertEqual(by_scenario["pure_null"]["decision"], "pass")
        self.assertEqual(by_scenario["planted_low_rank"]["decision"], "pass")
        self.assertEqual(by_scenario["rare_state"]["decision"], "pass")

    def test_publication_plan_keeps_genome_biology_below_20_boundary(self) -> None:
        gates = [
            {"gate_id": "stability_advantage", "status": "borderline"},
            {"gate_id": "software_release", "status": "pending"},
        ]
        rows = publication_plan.build_decision_rows(gates)
        by_journal = {row["journal"]: row for row in rows}
        self.assertEqual(by_journal["Nature Methods"]["within_20_50_jif"], "yes")
        self.assertEqual(by_journal["Genome Biology"]["within_20_50_jif"], "no")

    def test_presubmission_gatekeeper_blocks_without_zenodo(self) -> None:
        gates = [
            {"gate_id": "synthetic_null_false_signal", "status": "pass"},
            {"gate_id": "diagnostic_no_call_validation", "status": "pass"},
            {"gate_id": "rare_state_retention", "status": "pass"},
            {"gate_id": "real_dataset_count", "status": "pass"},
            {"gate_id": "stability_advantage", "status": "pass"},
            {"gate_id": "annotation_noninferiority", "status": "pass"},
            {"gate_id": "pdac_tme_interpretability", "status": "pass"},
            {"gate_id": "figure_source_data", "status": "pass"},
            {"gate_id": "software_release", "status": "pending"},
        ]
        release = [
            {"check_id": "repository_url", "status": "pass"},
            {"check_id": "github_remote", "status": "pass"},
            {"check_id": "github_release_tag", "status": "pass"},
            {"check_id": "zenodo_doi", "status": "pending"},
        ]
        rows = presubmission_package.evaluate_presubmission(gates, release)
        by_check = {row["check_id"]: row for row in rows}
        self.assertEqual(by_check["scientific_gate_package"]["status"], "pass")
        self.assertEqual(by_check["nature_methods_submission_ready"]["status"], "blocked")

    def test_journal_compliance_blocks_without_external_release(self) -> None:
        gates = [
            {"gate_id": "synthetic_null_false_signal", "status": "pass"},
            {"gate_id": "diagnostic_no_call_validation", "status": "pass"},
            {"gate_id": "rare_state_retention", "status": "pass"},
            {"gate_id": "real_dataset_count", "status": "pass"},
            {"gate_id": "stability_advantage", "status": "pass"},
            {"gate_id": "annotation_noninferiority", "status": "pass"},
            {"gate_id": "pdac_tme_interpretability", "status": "pass"},
            {"gate_id": "figure_source_data", "status": "pass"},
            {"gate_id": "software_release", "status": "pending"},
        ]
        release = [
            {"check_id": "local_release_audit", "status": "pass"},
            {"check_id": "ci_workflow", "status": "pass"},
            {"check_id": "dockerfile", "status": "pass"},
            {"check_id": "figure_source_data_manifest", "status": "pass"},
            {"check_id": "manuscript_evidence_package", "status": "pass"},
            {"check_id": "publication_20_50_plan", "status": "pass"},
            {"check_id": "repository_url", "status": "pending"},
            {"check_id": "github_remote", "status": "pending"},
            {"check_id": "github_release_tag", "status": "pass"},
            {"check_id": "zenodo_doi", "status": "pending"},
        ]
        presubmission = [{"check_id": "nature_methods_submission_ready", "status": "blocked"}]
        datasets = [{"dataset_id": "pbmc3k_10x", "github_policy": "accession_and_script_only"}]
        claims = [{"claim_id": "diagnostic_no_call_validation", "allowed_wording": "Diagnostic no-call validation passed."}]

        rows = journal_compliance.build_compliance_rows(gates, release, presubmission, datasets, claims)
        by_check = {row["check_id"]: row for row in rows}
        self.assertEqual(by_check["nature_methods_scope_fit"]["status"], "pass")
        self.assertEqual(by_check["code_availability"]["status"], "blocked")
        self.assertEqual(by_check["code_doi_repository"]["status"], "blocked")
        self.assertEqual(journal_compliance._overall_decision(rows), "not_submission_ready")

    def test_journal_compliance_never_promises_acceptance(self) -> None:
        lines = journal_compliance.build_markdown([])
        self.assertTrue(any("Acceptance guarantee: `not possible`" in line for line in lines))

    def test_publication_board_identifies_external_release_blockers(self) -> None:
        compliance = [
            {"check_id": "claim_boundary", "status": "pass"},
            {"check_id": "code_availability", "status": "blocked"},
            {"check_id": "code_doi_repository", "status": "blocked"},
            {"check_id": "reporting_summary", "status": "pending_manual"},
        ]
        release = [
            {"check_id": "repository_url", "status": "pending"},
            {"check_id": "github_remote", "status": "pending"},
            {"check_id": "github_release_tag", "status": "pass"},
            {"check_id": "zenodo_doi", "status": "pending"},
        ]
        presubmission = [{"check_id": "nature_methods_submission_ready", "status": "blocked"}]
        journals = [
            {
                "journal": "Nature Methods",
                "fit_for_current_project": "primary_target_if_gates_pass",
                "current_readiness": "not_ready",
            },
            {"journal": "Nature Biotechnology", "fit_for_current_project": "stretch_only"},
            {"journal": "Genome Biology", "fit_for_current_project": "realistic_fallback_if_strict_jif_relaxed"},
        ]
        rows = publication_board.build_board_rows(compliance, release, presubmission, journals)
        by_step = {row["step_id"]: row for row in rows}
        self.assertEqual(by_step["02_create_public_github_repository"]["status"], "blocked_external")
        self.assertEqual(by_step["05_create_github_release_and_zenodo_doi"]["status"], "blocked_external")
        self.assertEqual(publication_board._overall_status(rows), "blocked_before_submission")

    def test_publication_board_states_no_acceptance_guarantee(self) -> None:
        lines = publication_board.build_markdown([])
        self.assertTrue(any("Acceptance guarantee: `impossible`" in line for line in lines))

    def test_github_release_url_parsing_and_dry_run(self) -> None:
        self.assertEqual(
            github_release.normalize_repo_url("https://github.com/example-lab/rmtguard.git"),
            "https://github.com/example-lab/rmtguard",
        )
        self.assertEqual(github_release.parse_repo("https://github.com/example-lab/rmtguard"), ("example-lab", "rmtguard"))
        rows = github_release.build_plan("https://github.com/example-lab/rmtguard", "v0.1.0-rc1")
        by_step = {row["step_id"]: row for row in rows}
        self.assertIn(by_step["02_validate_github_token"]["status"], {"ready", "blocked_external"})
        self.assertEqual(by_step["05_create_github_release"]["status"], "would_run")

    def test_github_release_markdown_never_promises_acceptance(self) -> None:
        rows = github_release.build_plan("https://github.com/example-lab/rmtguard", "v0.1.0-rc1")
        lines = github_release.build_markdown(rows, "https://github.com/example-lab/rmtguard", "v0.1.0-rc1", execute_mode=False)
        self.assertTrue(any("Acceptance guarantee: `impossible`" in line for line in lines))

    def test_submission_finalizer_blocks_without_repo_and_doi(self) -> None:
        rows = submission_finalizer.build_plan(None, None, "v0.1.0-rc1")
        by_step = {row["step_id"]: row for row in rows}
        self.assertEqual(by_step["01_validate_inputs"]["status"], "blocked")
        self.assertEqual(by_step["04_record_external_metadata"]["status"], "blocked")

    def test_submission_finalizer_parses_valid_inputs_and_requires_manual_tag_review(self) -> None:
        rows = submission_finalizer.build_plan("https://github.com/example-lab/rmtguard", "10.5281/zenodo.12345", "v0.1.0-rc1")
        by_step = {row["step_id"]: row for row in rows}
        self.assertEqual(by_step["01_validate_inputs"]["status"], "ready")
        self.assertIn(by_step["03_validate_tag_state"]["status"], {"ready", "manual_review"})
        lines = submission_finalizer.build_markdown(rows, "https://github.com/example-lab/rmtguard", "10.5281/zenodo.12345", "v0.1.0-rc1", execute_mode=False)
        self.assertTrue(any("Acceptance guarantee: `impossible`" in line for line in lines))

    def test_reporting_summary_draft_marks_code_doi_blocked(self) -> None:
        datasets = [{"dataset_id": "pbmc3k_10x", "accession": "NA", "github_policy": "accession_and_script_only"}]
        claims = [{"claim_id": "noise_control_null", "allowed_wording": "Null control passes."}]
        release = [
            {"check_id": "repository_url", "status": "pending"},
            {"check_id": "zenodo_doi", "status": "pending"},
        ]
        compliance = [{"check_id": "reporting_summary", "status": "pending_manual"}]
        gates = [{"gate_id": "synthetic_null_false_signal", "status": "pass"}]
        rows = reporting_summary.build_rows(datasets, claims, release, compliance, gates)
        by_item = {row["item"]: row for row in rows}
        self.assertEqual(by_item["Code DOI"]["status"], "blocked")
        self.assertEqual(by_item["Official form status"]["status"], "pending_manual")
        lines = reporting_summary.build_markdown(rows)
        self.assertTrue(any("official Nature Portfolio reporting summary form" in line for line in lines))

    def test_editorial_risk_blocks_without_software_release(self) -> None:
        objections = [
            {
                "objection_id": "stability_advantage",
                "current_status": "pass",
                "likely_reviewer_concern": "stability concern",
                "response_strategy": "keep no-call wording",
            }
        ]
        compliance = [
            {"check_id": "code_availability", "status": "blocked"},
            {"check_id": "code_doi_repository", "status": "blocked"},
            {"check_id": "reporting_summary", "status": "pending_manual"},
        ]
        journals = [{"journal": "Nature Methods", "current_readiness": "not_ready", "fit_for_current_project": "primary_target_if_gates_pass"}]
        execution = [{"step_id": "02_create_public_github_repository", "status": "blocked_external"}]
        rows = editorial_risk.build_rows(objections, compliance, journals, execution)
        by_risk = {row["risk_id"]: row for row in rows}
        self.assertEqual(by_risk["software_release_desk_reject"]["status"], "blocked")
        self.assertEqual(editorial_risk.overall_status(rows), "blocked_before_editorial_submission")

    def test_editorial_risk_never_promises_acceptance(self) -> None:
        lines = editorial_risk.build_markdown([])
        self.assertTrue(any("Acceptance guarantee: `impossible`" in line for line in lines))

    def test_editorial_risk_distinguishes_baseline_implementation_from_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            phase1_runner = tmp / "run_phase1_benchmark.py"
            stability_runner = tmp / "run_stability_benchmark.py"
            seurat_runner = tmp / "run_seurat_baseline.R"
            marker_text = "elbow_rule parallel_analysis jackstraw_like"
            phase1_runner.write_text(marker_text, encoding="utf-8")
            stability_runner.write_text(marker_text, encoding="utf-8")
            seurat_runner.write_text("# seurat baseline\n", encoding="utf-8")
            phase1_summary = tmp / "phase1.tsv"
            stability_summary = tmp / "stability.tsv"
            seurat_result = tmp / "seurat.tsv"
            phase1_summary.write_text("method\nrmtguard\nfixed_pcs_30\n", encoding="utf-8")
            stability_summary.write_text("method\nrmtguard\nfixed_pcs_30\n", encoding="utf-8")
            seurat_result.write_text("method\nseurat_v5_like_pcs_30\n", encoding="utf-8")

            status = editorial_risk._baseline_support_status(
                phase1_runner=phase1_runner,
                stability_runner=stability_runner,
                seurat_runner=seurat_runner,
                phase1_summary=phase1_summary,
                stability_summary=stability_summary,
                seurat_result=seurat_result,
            )
            self.assertEqual(status["status"], "implementation_ready_not_benchmarked")

            expanded = "method\nelbow_rule\nparallel_analysis\njackstraw_like\n"
            phase1_summary.write_text(expanded, encoding="utf-8")
            stability_summary.write_text(expanded, encoding="utf-8")
            status = editorial_risk._baseline_support_status(
                phase1_runner=phase1_runner,
                stability_runner=stability_runner,
                seurat_runner=seurat_runner,
                phase1_summary=phase1_summary,
                stability_summary=stability_summary,
                seurat_result=seurat_result,
            )
            self.assertEqual(status["status"], "controlled")

    def test_editorial_risk_uses_pdac_depth_audit_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "pdac_depth.tsv"
            path.write_text(
                "item_id\tstatus\tevidence\tallowed_claim\tforbidden_claim\tnotes\n"
                "primary_marker_structure\tpass\tx\ty\tz\tn\n"
                "caf_fibroblast_boundary\tcontrolled_no_claim\tx\ty\tz\tn\n",
                encoding="utf-8",
            )
            status = editorial_risk._pdac_depth_status(path)
            self.assertEqual(status["status"], "controlled_with_public_use_case")

            path.write_text(
                "item_id\tstatus\tevidence\tallowed_claim\tforbidden_claim\tnotes\n"
                "primary_marker_structure\tfail\tx\ty\tz\tn\n",
                encoding="utf-8",
            )
            status = editorial_risk._pdac_depth_status(path)
            self.assertEqual(status["status"], "active_risk")


if __name__ == "__main__":
    unittest.main()
