from __future__ import annotations

import importlib.util
from pathlib import Path
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
no_call_report = _load_script("build_no_call_benchmark_report")
publication_plan = _load_script("build_publication_20_50_plan")
presubmission_package = _load_script("build_presubmission_package")
journal_compliance = _load_script("build_journal_compliance_audit")
publication_board = _load_script("build_publication_execution_board")


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


if __name__ == "__main__":
    unittest.main()
