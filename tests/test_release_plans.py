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
claim_scope = _load_script("build_claim_scope_decision")
presubmission_package = _load_script("build_presubmission_package")
journal_compliance = _load_script("build_journal_compliance_audit")
publication_board = _load_script("build_publication_execution_board")
github_release = _load_script("execute_github_release")
submission_finalizer = _load_script("finalize_submission_release")
reporting_summary = _load_script("build_reporting_summary_draft")
editorial_risk = _load_script("build_editorial_risk_audit")
release_audit = _load_script("release_audit")
public_release_blockers = _load_script("build_public_release_blocker_report")
top_paper_route = _load_script("build_top_paper_route_package")
editorial_packet = _load_script("build_editorial_presubmission_packet")
claim_lint = _load_script("lint_claim_boundaries")
claim_traceability = _load_script("validate_claim_traceability")
submission_guard = _load_script("build_submission_guard")
external_review_packet = _load_script("export_current_article_review_packet")
external_review_triage = _load_script("triage_external_review_feedback")
post_feedback_route = _load_script("build_post_feedback_journal_route_gate")
gb_transfer = _load_script("build_genome_biology_transfer_package")
reviewer_defense = _load_script("build_reviewer_defense_package")
author_release = _load_script("build_author_release_execution_packet")


class ReleasePlanTest(unittest.TestCase):
    def test_artifact_classification_keeps_processed_h5ad_out_of_git(self) -> None:
        path = ROOT / "data" / "processed" / "pbmc3k_10x.h5ad"
        artifact_type, destination, required, _notes = artifact_manifest._classify(
            path, ignored=True
        )
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
            {
                "action": "stage_for_initial_commit",
                "path": "README.md",
                "git_ignored": "False",
            },
            {
                "action": "do_not_stage",
                "path": "data/pbmc3k_raw.h5ad",
                "git_ignored": "True",
            },
        ]
        self.assertEqual(stage_files.stageable_paths(rows), ["README.md"])

    def test_stageable_paths_refuses_ignored_stage_row(self) -> None:
        rows = [
            {
                "action": "stage_for_initial_commit",
                "path": "README.md",
                "git_ignored": "True",
            }
        ]
        with self.assertRaises(ValueError):
            stage_files.stageable_paths(rows)

    def test_repository_url_normalization(self) -> None:
        self.assertEqual(
            repo_metadata.normalize_repo_url(
                "https://github.com/example-lab/rmtguard.git"
            ),
            "https://github.com/example-lab/rmtguard",
        )

    def test_github_handoff_bundle_path_is_tag_scoped(self) -> None:
        path = github_handoff._bundle_path("v0.1.0-rc1")
        self.assertEqual(path.name, "rmtguard_v0.1.0-rc1_source.bundle")

    def test_external_release_metadata_validates_doi(self) -> None:
        self.assertEqual(
            external_release_record.normalize_doi(
                "https://doi.org/10.5281/zenodo.12345"
            ),
            "10.5281/zenodo.12345",
        )
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

    def test_external_review_packet_keeps_not_submission_ready_boundary(self) -> None:
        text = "\n".join(external_review_packet.build_packet())
        self.assertIn("Current submission guard: `do_not_submit`", text)
        self.assertIn("Acceptance guarantee: `impossible`", text)
        self.assertIn("### manuscript/nature_methods_presubmission_draft.md", text)
        self.assertIn("### results/manuscript/claim_evidence_matrix.tsv", text)
        self.assertIn("Binary Or Non-Text Assets Listed Only", text)

    def test_external_review_triage_blocks_fatal_novelty_feedback(self) -> None:
        rows = external_review_triage.triage_rows(
            [
                {
                    "feedback_id": "M1",
                    "reviewer_source": "model_a",
                    "reviewer_type": "model",
                    "section": "method novelty",
                    "comment": "The method is not novel enough for Nature Methods.",
                    "suggested_action": "",
                    "evidence_path": "manuscript/current_article_external_review_packet.md",
                    "severity_hint": "fatal",
                    "journal_route_hint": "Nature Methods",
                }
            ]
        )
        self.assertEqual(rows[0]["triage_category"], "fatal_blocker")
        self.assertEqual(rows[0]["priority"], "P0")
        self.assertEqual(rows[0]["route_impact"], "nature_methods_go_no_go")

    def test_external_review_triage_routes_release_feedback_to_gate(self) -> None:
        rows = external_review_triage.triage_rows(
            [
                {
                    "feedback_id": "M2",
                    "reviewer_source": "model_b",
                    "reviewer_type": "model",
                    "section": "code availability",
                    "comment": "Zenodo DOI and GitHub release are still missing.",
                    "suggested_action": "",
                    "evidence_path": "results/release/release_readiness.tsv",
                    "severity_hint": "blocking",
                    "journal_route_hint": "",
                }
            ]
        )
        self.assertEqual(rows[0]["triage_category"], "release_or_reproducibility")
        self.assertEqual(rows[0]["priority"], "P0")
        self.assertEqual(rows[0]["route_impact"], "software_release_gate")

    def test_external_review_triage_template_rows_wait_for_feedback(self) -> None:
        rows = external_review_triage.triage_rows(
            [
                {
                    "feedback_id": "TEMPLATE-001",
                    "reviewer_source": "external_model",
                    "reviewer_type": "model",
                    "section": "overall",
                    "comment": "Replace this row with one concrete review comment.",
                    "suggested_action": "",
                    "evidence_path": "manuscript/current_article_external_review_packet.md",
                    "severity_hint": "pending",
                    "journal_route_hint": "",
                }
            ]
        )
        self.assertEqual(rows[0]["triage_category"], "awaiting_external_feedback")
        self.assertEqual(rows[0]["status"], "awaiting_feedback")

    def test_post_feedback_route_pauses_for_p0_feedback(self) -> None:
        rows = post_feedback_route.build_route_gate_rows(
            triage_rows=[
                {
                    "feedback_id": "M1",
                    "priority": "P0",
                    "status": "open",
                }
            ],
            submission_guard_rows=[
                {
                    "guard_id": "overall_submission_guard",
                    "status": "submission_candidate",
                }
            ],
            route_rows=[
                {
                    "route_id": "nature_methods_first",
                    "decision": "submission_candidate",
                },
                {
                    "route_id": "genome_biology_fallback",
                    "decision": "standby",
                },
            ],
            release_rows=[
                {"check_id": "repository_url", "status": "pass"},
                {"check_id": "github_remote", "status": "pass"},
                {"check_id": "github_release_tag", "status": "pass"},
                {"check_id": "zenodo_doi", "status": "pass"},
            ],
            gate_rows=[{"gate_id": "software_release", "status": "pass"}],
        )
        by_id = {row["decision_id"]: row for row in rows}
        self.assertEqual(
            by_id["external_feedback_gate"]["decision"],
            "blocked_by_external_feedback",
        )
        self.assertEqual(
            by_id["overall_post_feedback_route"]["decision"],
            "pause_for_p0_feedback",
        )

    def test_post_feedback_route_current_hold_activates_gb_after_release(self) -> None:
        rows = post_feedback_route.build_route_gate_rows(
            triage_rows=[
                {
                    "feedback_id": "NO_EXTERNAL_FEEDBACK",
                    "priority": "P2",
                    "status": "awaiting_feedback",
                }
            ],
            submission_guard_rows=[
                {
                    "guard_id": "overall_submission_guard",
                    "status": "do_not_submit",
                }
            ],
            route_rows=[
                {
                    "route_id": "nature_methods_first",
                    "decision": "hold_pre_submission",
                },
                {
                    "route_id": "genome_biology_fallback",
                    "decision": "activate_after_software_release",
                },
            ],
            release_rows=[
                {"check_id": "repository_url", "status": "pending"},
                {"check_id": "github_remote", "status": "pending"},
                {"check_id": "github_release_tag", "status": "pass"},
                {"check_id": "zenodo_doi", "status": "pending"},
            ],
            gate_rows=[
                {"gate_id": "stability_advantage", "status": "fail"},
                {"gate_id": "software_release", "status": "pending"},
            ],
        )
        by_id = {row["decision_id"]: row for row in rows}
        self.assertEqual(
            by_id["nature_methods_gate"]["decision"], "hold_nature_methods"
        )
        self.assertEqual(
            by_id["genome_biology_gate"]["decision"], "activate_after_release"
        )
        self.assertEqual(
            by_id["overall_post_feedback_route"]["decision"],
            "genome_biology_after_release",
        )
        self.assertIn(
            "repository_url",
            by_id["software_release_gate"]["blocking_items"],
        )

    def test_post_feedback_route_markdown_never_promises_acceptance(self) -> None:
        rows = [
            {
                "decision_id": "overall_post_feedback_route",
                "decision": "genome_biology_after_release",
                "status": "fallback_after_release",
                "blocking_items": "zenodo_doi",
                "evidence_path": "results/submission/post_feedback_journal_route_gate.tsv",
                "required_action": "Finish release.",
                "notes": "Acceptance guarantee remains impossible.",
            }
        ]
        text = "\n".join(post_feedback_route.build_markdown(rows)).lower()
        self.assertIn("acceptance guarantee: `impossible`", text)
        self.assertNotIn("guaranteed acceptance", text)

    def test_gb_transfer_package_prepares_after_release(self) -> None:
        rows = gb_transfer.build_transfer_rows(
            post_feedback_rows=[
                {
                    "decision_id": "overall_post_feedback_route",
                    "decision": "genome_biology_after_release",
                    "status": "fallback_after_release",
                },
                {
                    "decision_id": "genome_biology_gate",
                    "decision": "activate_after_release",
                    "status": "ready_after_external_release",
                },
            ],
            claim_rows=[
                {
                    "claim_id": "software_release",
                    "status": "pending",
                    "allowed_wording": "Local release checks pass.",
                    "prohibited_wording": "Do not state DOI-archived release exists.",
                },
                {
                    "claim_id": "pbmc3k_stability",
                    "status": "fail",
                    "allowed_wording": "Use callability-aware wording.",
                    "prohibited_wording": "Do not claim broad fixed-PC superiority.",
                },
                {
                    "claim_id": "pdac_tme_showcase",
                    "status": "pass",
                    "allowed_wording": "PDAC/TME use case is bounded.",
                    "prohibited_wording": "Do not claim standalone CAF discovery.",
                },
            ],
            figure_rows=[
                {
                    "figure": "Figure 3",
                    "status": "blocked",
                    "allowed_caption_claim": "Use callability-aware benchmark evidence.",
                    "prohibited_caption_claim": "Do not claim broad superiority.",
                    "must_show_caveat": "PBMC68k is diagnostic no-call.",
                }
            ],
            release_rows=[
                {"check_id": "repository_url", "status": "pending"},
                {"check_id": "github_remote", "status": "pending"},
                {"check_id": "github_release_tag", "status": "pass"},
                {"check_id": "zenodo_doi", "status": "pending"},
            ],
        )
        by_id = {row["item_id"]: row for row in rows}
        self.assertEqual(by_id["route_activation"]["status"], "ready_after_release")
        self.assertEqual(
            by_id["public_release_completion"]["status"], "blocked_external"
        )
        self.assertEqual(by_id["figure3_reframe"]["status"], "needs_reframe")
        self.assertEqual(
            by_id["overall_genome_biology_transfer"]["status"],
            "prepare_after_release",
        )

    def test_gb_transfer_package_marks_candidate_after_release_passes(self) -> None:
        rows = gb_transfer.build_transfer_rows(
            post_feedback_rows=[
                {
                    "decision_id": "overall_post_feedback_route",
                    "decision": "genome_biology_conversion_candidate",
                    "status": "fallback_candidate",
                },
                {
                    "decision_id": "genome_biology_gate",
                    "decision": "conversion_candidate",
                    "status": "candidate",
                },
            ],
            claim_rows=[
                {
                    "claim_id": "software_release",
                    "status": "pass",
                    "prohibited_wording": "Do not overclaim release.",
                },
                {
                    "claim_id": "pbmc3k_stability",
                    "status": "fail",
                    "prohibited_wording": "Do not claim broad fixed-PC superiority.",
                },
                {
                    "claim_id": "pdac_tme_showcase",
                    "status": "pass",
                    "allowed_wording": "PDAC/TME use case is bounded.",
                    "prohibited_wording": "Do not claim standalone CAF discovery.",
                },
            ],
            figure_rows=[{"figure": "Figure 3", "status": "pass"}],
            release_rows=[
                {"check_id": "repository_url", "status": "pass"},
                {"check_id": "github_remote", "status": "pass"},
                {"check_id": "github_release_tag", "status": "pass"},
                {"check_id": "zenodo_doi", "status": "pass"},
            ],
        )
        by_id = {row["item_id"]: row for row in rows}
        self.assertEqual(
            by_id["overall_genome_biology_transfer"]["status"],
            "transfer_candidate",
        )

    def test_gb_transfer_outputs_never_promise_acceptance(self) -> None:
        rows = [
            {
                "item_id": "overall_genome_biology_transfer",
                "status": "prepare_after_release",
                "owner": "Codex",
                "evidence_path": "results/submission/genome_biology_transfer_checklist.tsv",
                "required_action": "Finish release.",
                "allowed_wording": "Use bounded workflow language.",
                "forbidden_wording": "Do not claim acceptance.",
                "notes": "zenodo_doi",
            }
        ]
        markdown = "\n".join(gb_transfer.build_markdown(rows)).lower()
        cover = "\n".join(gb_transfer.build_cover_letter(rows))
        self.assertIn("acceptance guarantee: `impossible`", markdown)
        self.assertNotIn("guaranteed acceptance", markdown)
        self.assertIn("[TO CONFIRM: public GitHub URL]", cover)
        self.assertIn("[TO CONFIRM: Zenodo DOI]", cover)

    def test_reviewer_defense_blocks_all_routes_on_software_release(self) -> None:
        rows = reviewer_defense.build_defense_rows(
            objection_rows=[
                {
                    "objection_id": "software_release",
                    "risk_level": "blocking",
                    "linked_gate_or_claim": "software_release",
                    "current_status": "pending",
                    "evidence": "results/release/release_readiness.tsv",
                    "response_strategy": "Complete the public release before submission.",
                    "required_before_submission": "Create public repository and archive.",
                }
            ],
            editorial_rows=[],
            claim_rows=[
                {
                    "claim_id": "software_release",
                    "prohibited_wording": "Do not state DOI-archived release exists.",
                }
            ],
            post_feedback_rows=[],
            gb_transfer_rows=[],
        )
        by_id = {row["defense_id"]: row for row in rows}
        self.assertEqual(
            by_id["software_release"]["status"], "blocked_until_public_release"
        )
        self.assertEqual(
            by_id["software_release"]["route_impact"], "blocks_all_submission_routes"
        )
        self.assertEqual(
            by_id["overall_reviewer_defense"]["status"],
            "not_sendable_before_release",
        )

    def test_reviewer_defense_reframes_stability_without_superiority(self) -> None:
        rows = reviewer_defense.build_defense_rows(
            objection_rows=[
                {
                    "objection_id": "stability_advantage",
                    "risk_level": "high",
                    "linked_gate_or_claim": "pbmc3k_stability",
                    "current_status": "fail",
                    "evidence": "results/stability_benchmarks/stability_gate_diagnostics.tsv",
                    "response_strategy": "Keep the benchmark claim callability-aware.",
                    "required_before_submission": "Rewrite Figure 3.",
                }
            ],
            editorial_rows=[
                {
                    "risk_id": "stability_advantage",
                    "status": "active_risk",
                }
            ],
            claim_rows=[
                {
                    "claim_id": "pbmc3k_stability",
                    "prohibited_wording": "Do not claim broad fixed-PC superiority.",
                }
            ],
            post_feedback_rows=[],
            gb_transfer_rows=[],
        )
        by_id = {row["defense_id"]: row for row in rows}
        self.assertEqual(
            by_id["stability_advantage"]["status"], "major_reframe_required"
        )
        self.assertIn(
            "no-call", by_id["stability_advantage"]["nature_methods_position"]
        )
        self.assertIn(
            "Do not claim broad fixed-PC superiority",
            by_id["stability_advantage"]["forbidden_response"],
        )

    def test_reviewer_defense_outputs_never_promise_acceptance(self) -> None:
        rows = [
            {
                "defense_id": "overall_reviewer_defense",
                "status": "not_sendable_before_release",
                "route_impact": "controls_language",
                "risk_level": "summary",
                "evidence_path": "results/submission/reviewer_defense_matrix.tsv",
                "safe_response": "Use evidence-bounded language.",
                "nature_methods_position": "Hold Nature Methods.",
                "genome_biology_position": "Use fallback after release.",
                "required_action": "software_release",
                "forbidden_response": "Do not claim acceptance.",
            }
        ]
        markdown = "\n".join(reviewer_defense.build_markdown(rows)).lower()
        response = "\n".join(reviewer_defense.build_response_draft(rows)).lower()
        self.assertIn("acceptance guarantee: `impossible`", markdown)
        self.assertNotIn("guaranteed acceptance", markdown)
        self.assertIn("pre-review scaffolds", response)

    def test_author_release_packet_blocks_until_repo_and_doi(self) -> None:
        rows = author_release.build_author_release_rows(
            release_rows=[
                {"check_id": "repository_url", "status": "pending"},
                {"check_id": "github_remote", "status": "pending"},
                {"check_id": "github_release_tag", "status": "pass"},
                {"check_id": "zenodo_doi", "status": "pending"},
            ],
            blocker_rows=[
                {
                    "blocker_id": "github_release_page",
                    "status": "blocked_external",
                }
            ],
            handoff_rows=[
                {
                    "artifact": "source_git_bundle",
                    "path": "results/release/rmtguard_v0.1.0-rc7_source.bundle",
                    "notes": "Contains tag v0.1.0-rc7 at commit abc123.",
                }
            ],
            post_feedback_rows=[
                {
                    "decision_id": "overall_post_feedback_route",
                    "decision": "genome_biology_after_release",
                }
            ],
            gb_transfer_rows=[
                {
                    "item_id": "overall_genome_biology_transfer",
                    "status": "prepare_after_release",
                }
            ],
            reviewer_defense_rows=[
                {
                    "defense_id": "overall_reviewer_defense",
                    "status": "not_sendable_before_release",
                }
            ],
        )
        by_id = {row["action_id"]: row for row in rows}
        self.assertEqual(
            by_id["overall_author_release_execution"]["status"],
            "blocked_waiting_author_release",
        )
        self.assertIn(
            "02_create_empty_public_github_repository",
            by_id["overall_author_release_execution"]["notes"],
        )
        self.assertIn(
            "v0.1.0-rc7",
            by_id["01_verify_local_release_candidate"]["notes"],
        )

    def test_author_release_packet_marks_release_ready_after_all_checks_pass(
        self,
    ) -> None:
        rows = author_release.build_author_release_rows(
            release_rows=[
                {"check_id": "repository_url", "status": "pass"},
                {"check_id": "github_remote", "status": "pass"},
                {"check_id": "github_release_tag", "status": "pass"},
                {"check_id": "zenodo_doi", "status": "pass"},
            ],
            blocker_rows=[{"blocker_id": "github_release_page", "status": "pass"}],
            handoff_rows=[
                {
                    "artifact": "source_git_bundle",
                    "path": "results/release/rmtguard_v0.1.0_source.bundle",
                    "notes": "Contains tag v0.1.0 at commit abc123.",
                }
            ],
            post_feedback_rows=[],
            gb_transfer_rows=[],
            reviewer_defense_rows=[],
        )
        by_id = {row["action_id"]: row for row in rows}
        self.assertEqual(
            by_id["overall_author_release_execution"]["status"],
            "release_evidence_ready_for_gate_refresh",
        )
        self.assertEqual(
            by_id["06_archive_github_release_with_zenodo"]["status"], "pass"
        )

    def test_author_release_packet_markdown_and_code_draft_keep_placeholders(
        self,
    ) -> None:
        rows = [
            {
                "action_id": "overall_author_release_execution",
                "phase": "summary",
                "owner": "Author + Codex",
                "status": "blocked_waiting_author_release",
                "blocking_input": "repository URL and DOI",
                "exact_action": "Complete release.",
                "verification": "Release readiness passes.",
                "evidence_path": "results/release/author_release_execution_checklist.tsv",
                "stop_condition": "Do not submit.",
                "notes": "blocked_actions=repo; route=hold.",
            }
        ]
        markdown = "\n".join(author_release.build_markdown(rows)).lower()
        draft = "\n".join(author_release.build_code_availability_draft(rows))
        self.assertIn("acceptance guarantee: `impossible`", markdown)
        self.assertNotIn("guaranteed acceptance", markdown)
        self.assertIn("[TO CONFIRM: public repository URL]", draft)
        self.assertIn("[TO CONFIRM: public archive DOI]", draft)

    def test_external_release_plan_keeps_external_steps_pending(self) -> None:
        rows = external_release.build_steps()
        status_by_step = {row["step_id"]: row["status"] for row in rows}
        command_by_step = {row["step_id"]: row["command"] for row in rows}
        self.assertEqual(status_by_step["01_create_github_repo"], "pending_external")
        self.assertEqual(status_by_step["11_archive_with_zenodo"], "pending_external")
        self.assertIn(
            "stage_github_release_files.py --execute",
            command_by_step["05_stage_approved_files"],
        )

    def test_public_release_blocker_report_blocks_without_remote_or_doi(self) -> None:
        rows = public_release_blockers.build_rows(
            release_readiness_rows=[
                {"check_id": "repository_url", "status": "pending"},
                {"check_id": "github_remote", "status": "pending"},
                {"check_id": "github_release_tag", "status": "pending"},
                {"check_id": "zenodo_doi", "status": "pending"},
            ],
            gh_path="",
            remote_url="",
            worktree_clean=True,
            head_tags=[],
            placeholder_repo_present=True,
            zenodo_doi_present=False,
        )
        by_id = {row["blocker_id"]: row for row in rows}
        self.assertEqual(
            by_id["github_cli_or_web_access"]["status"], "blocked_external"
        )
        self.assertEqual(by_id["github_remote"]["status"], "blocked_external")
        self.assertEqual(by_id["repository_url_metadata"]["status"], "blocked_external")
        self.assertEqual(by_id["zenodo_doi"]["status"], "blocked_external")
        self.assertEqual(by_id["software_release_gate"]["status"], "blocked")

    def test_public_release_blocker_markdown_never_promises_acceptance(self) -> None:
        rows = public_release_blockers.build_rows(
            release_readiness_rows=[
                {"check_id": "repository_url", "status": "pass"},
                {"check_id": "github_remote", "status": "pass"},
                {"check_id": "github_release_tag", "status": "pass"},
                {"check_id": "zenodo_doi", "status": "pass"},
            ],
            gh_path="gh",
            remote_url="https://github.com/example-lab/rmtguard.git",
            worktree_clean=True,
            head_tags=["v0.1.0"],
            placeholder_repo_present=False,
            zenodo_doi_present=True,
        )
        lines = public_release_blockers.build_markdown(rows)
        text = "\n".join(lines).lower()
        self.assertIn("acceptance guarantee: `impossible`", text)
        self.assertNotIn("guaranteed publication", text)

    def test_top_paper_route_holds_nature_methods_when_gates_are_blocked(self) -> None:
        gates = [
            {"gate_id": "diagnostic_no_call_validation", "status": "pass"},
            {"gate_id": "annotation_noninferiority", "status": "pass"},
            {"gate_id": "stability_advantage", "status": "fail"},
            {"gate_id": "software_release", "status": "pending"},
        ]
        claims = [
            {
                "claim_id": "noise_control_null",
                "status": "pass",
                "allowed_wording": "Pure-null benchmark passed.",
                "prohibited_wording": "Do not claim universal calibration.",
            },
            {
                "claim_id": "diagnostic_no_call_validation",
                "status": "pass",
                "allowed_wording": "Diagnostic no-call validation passed.",
                "prohibited_wording": "Do not call no-call outputs discoveries.",
            },
            {
                "claim_id": "rare_state_retention",
                "status": "pass",
                "allowed_wording": "Rare-state retention passed.",
                "prohibited_wording": "Do not guarantee all rare states.",
            },
            {
                "claim_id": "pdac_tme_showcase",
                "status": "pass",
                "allowed_wording": "PDAC/TME public use case is bounded.",
                "prohibited_wording": "Do not claim a standalone CAF discovery.",
            },
            {
                "claim_id": "public_benchmark_breadth",
                "status": "pass",
                "allowed_wording": "Four public real datasets are present.",
                "prohibited_wording": "Do not claim Tabula Sapiens is done.",
            },
            {
                "claim_id": "annotation_noninferiority",
                "status": "pass",
                "allowed_wording": "Annotation noninferiority passed.",
                "prohibited_wording": "Do not frame PBMC68k as strong.",
            },
            {
                "claim_id": "figure_source_data",
                "status": "pass",
                "allowed_wording": "Figure source data exist.",
                "prohibited_wording": "Do not call draft renders final.",
            },
            {
                "claim_id": "pbmc3k_stability",
                "status": "fail",
                "allowed_wording": "Use callability-aware stability/no-call wording.",
                "prohibited_wording": "Do not claim broad fixed-PC superiority.",
            },
            {
                "claim_id": "software_release",
                "status": "pending",
                "allowed_wording": "Local release checks pass.",
                "prohibited_wording": "Do not state DOI-archived release exists.",
            },
        ]
        compliance = [
            {"check_id": "nature_methods_scope_fit", "status": "blocked"},
            {"check_id": "article_content_type_fit", "status": "blocked"},
            {"check_id": "performance_comparison", "status": "blocked"},
            {"check_id": "code_availability", "status": "blocked"},
            {"check_id": "code_doi_repository", "status": "blocked"},
            {"check_id": "nature_methods_submission_ready", "status": "blocked"},
        ]
        release = [
            {"check_id": "repository_url", "status": "pending"},
            {"check_id": "github_remote", "status": "pending"},
            {"check_id": "github_release_tag", "status": "pending"},
            {"check_id": "zenodo_doi", "status": "pending"},
        ]
        blockers = [
            {"blocker_id": "github_remote", "status": "blocked_external"},
            {"blocker_id": "zenodo_doi", "status": "blocked_external"},
            {"blocker_id": "software_release_gate", "status": "blocked"},
        ]

        rows = top_paper_route.build_route_rows(
            gates, claims, compliance, release, blockers
        )
        by_route = {row["route_id"]: row for row in rows}
        self.assertEqual(
            by_route["nature_methods_first"]["decision"], "hold_pre_submission"
        )
        self.assertIn(
            "stability_advantage", by_route["nature_methods_first"]["blocking_items"]
        )
        self.assertEqual(
            by_route["genome_biology_fallback"]["decision"],
            "activate_after_software_release",
        )
        self.assertIn(
            "software_release_gate",
            by_route["public_release_action"]["blocking_items"],
        )

    def test_top_paper_route_outputs_do_not_promise_acceptance_or_mislabel_gb(
        self,
    ) -> None:
        rows = [
            {
                "route_id": "nature_methods_first",
                "journal": "Nature Methods",
                "decision": "hold_pre_submission",
                "claim_frame": "bounded",
                "allowed_claims": "x",
                "forbidden_claims": "y",
                "blocking_items": "stability_advantage",
                "next_action": "resolve blockers",
                "risk_level": "blocking",
                "evidence_path": "evidence.tsv",
            },
            {
                "route_id": "genome_biology_fallback",
                "journal": "Genome Biology",
                "decision": "activate_after_software_release",
                "claim_frame": "workflow",
                "allowed_claims": "x",
                "forbidden_claims": "y",
                "blocking_items": "software_release",
                "next_action": "release",
                "risk_level": "major",
                "evidence_path": "claims.tsv",
            },
        ]
        claims = [
            {
                "claim_id": "software_release",
                "status": "pending",
                "allowed_wording": "Local release checks pass.",
                "prohibited_wording": "Do not state DOI-archived release exists.",
                "manuscript_claim": "release",
                "evidence": "release.tsv",
            }
        ]
        lines = top_paper_route.build_route_markdown(rows, claims, [])
        text = "\n".join(lines).lower()
        self.assertIn("acceptance guarantee: `impossible`", text)
        self.assertNotIn("guaranteed publication", text)

        draft = "\n".join(
            top_paper_route.build_genome_biology_draft(claims, rows)
        ).lower()
        self.assertIn("not submission-ready", draft)
        self.assertIn(
            "do not present genome biology as a strict 20-50 jif target", draft
        )

    def test_editorial_packet_keeps_presubmission_inquiry_do_not_send(self) -> None:
        claims = [
            {
                "claim_id": "noise_control_null",
                "allowed_wording": "Pure-null benchmark passed.",
                "prohibited_wording": "Do not claim universal calibration.",
            },
            {
                "claim_id": "diagnostic_no_call_validation",
                "allowed_wording": "Diagnostic no-call validation passed.",
                "prohibited_wording": "Do not call no-calls discoveries.",
            },
            {
                "claim_id": "rare_state_retention",
                "allowed_wording": "Rare-state retention passed.",
                "prohibited_wording": "Do not guarantee all rare states.",
            },
            {
                "claim_id": "public_benchmark_breadth",
                "allowed_wording": "Four public datasets are present.",
                "prohibited_wording": "Do not claim extra datasets.",
            },
            {
                "claim_id": "pbmc3k_stability",
                "allowed_wording": "Use callability-aware benchmark wording.",
                "prohibited_wording": "Do not claim broad fixed-PC superiority.",
            },
        ]
        objections = [
            {
                "objection_id": "stability_advantage",
                "response_strategy": "Disclose diagnostic no-call boundaries.",
            }
        ]
        routes = [
            {
                "route_id": "nature_methods_first",
                "next_action": "Resolve software release and claim boundaries.",
            },
            {
                "route_id": "genome_biology_fallback",
                "decision": "activate_after_software_release",
                "next_action": "Complete public release.",
            },
        ]
        blockers = [
            {"blocker_id": "github_remote", "status": "blocked_external"},
            {"blocker_id": "zenodo_doi", "status": "blocked_external"},
        ]
        rows = editorial_packet.build_packet_rows(claims, objections, routes, blockers)
        by_id = {row["item_id"]: row for row in rows}
        self.assertEqual(by_id["send_status"]["status"], "do_not_send")
        self.assertEqual(by_id["software_release_disclosure"]["status"], "blocked")
        inquiry = "\n".join(editorial_packet.build_inquiry_markdown(rows)).lower()
        self.assertIn("status: do not send", inquiry)
        self.assertIn("acceptance guarantee: `impossible`", inquiry)
        self.assertNotIn("guaranteed publication", inquiry)

    def test_editorial_figure_checklist_preserves_prohibited_caption_claims(
        self,
    ) -> None:
        storyline = [
            {
                "figure": "Figure 3",
                "status": "blocked",
                "linked_claim_ids": "pbmc3k_stability",
                "caveat": "PBMC68k is diagnostic no-call.",
                "source_artifact": "figure3.tsv",
                "manuscript_use": "Use as callability-aware benchmark evidence.",
            }
        ]
        claims = [
            {
                "claim_id": "pbmc3k_stability",
                "allowed_wording": "Use callability-aware benchmark wording.",
                "prohibited_wording": "Do not claim broad fixed-PC superiority.",
            }
        ]
        rows = editorial_packet.build_figure_rows(storyline, claims)
        self.assertEqual(rows[0]["figure"], "Figure 3")
        self.assertIn("callability-aware", rows[0]["allowed_caption_claim"])
        self.assertIn("broad fixed-PC superiority", rows[0]["prohibited_caption_claim"])
        self.assertIn("diagnostic no-call", rows[0]["must_show_caveat"])

    def test_claim_boundary_lint_blocks_unqualified_acceptance_guarantee(self) -> None:
        rows = claim_lint.scan_text(
            ROOT / "manuscript" / "bad.md",
            "RMTGuard has guaranteed publication in a top journal.",
        )
        self.assertEqual(rows[0]["rule_id"], "acceptance_guarantee")
        self.assertEqual(rows[0]["status"], "violation")

    def test_claim_boundary_lint_allows_explicit_boundary_statement(self) -> None:
        rows = claim_lint.scan_text(
            ROOT / "docs" / "claim_boundary_lint.md",
            "Acceptance guarantee: `impossible`.",
        )
        self.assertEqual(rows[0]["rule_id"], "acceptance_guarantee")
        self.assertEqual(rows[0]["status"], "controlled_boundary")

    def test_claim_boundary_lint_blocks_pbmc68k_positive_discovery(self) -> None:
        rows = claim_lint.scan_text(
            ROOT / "manuscript" / "bad.md",
            "PBMC68k produced a positive cell-state discovery success.",
        )
        self.assertEqual(rows[0]["rule_id"], "pbmc68k_positive_discovery")
        self.assertEqual(rows[0]["status"], "violation")

    def test_claim_boundary_lint_markdown_reports_violations(self) -> None:
        rows = claim_lint.scan_text(
            ROOT / "manuscript" / "bad.md",
            "RMTGuard shows broad fixed-PC superiority.",
        )
        lines = claim_lint.build_markdown(rows)
        text = "\n".join(lines)
        self.assertIn("Violations: `1`", text)
        self.assertIn("broad_fixed_pc_superiority", text)

    def test_claim_boundary_lint_excludes_external_review_packet(self) -> None:
        path = ROOT / "manuscript" / "current_article_external_review_packet.md"
        self.assertTrue(claim_lint._is_excluded_path(path))
        self.assertTrue(
            claim_lint._is_excluded_path(ROOT / "docs" / "claim_boundary_lint.md")
        )

    def test_claim_traceability_flags_unknown_figure_claim(self) -> None:
        claims = {"noise_control_null": {"status": "pass"}}
        rows = claim_traceability.validate_storyline(
            [
                {
                    "figure": "Figure X",
                    "linked_claim_ids": "missing_claim",
                    "status": "pass",
                    "source_artifact": "README.md",
                }
            ],
            claims,
        )
        self.assertEqual(rows[0]["trace_status"], "violation")
        self.assertEqual(rows[0]["decision"], "unknown_claim")

    def test_claim_traceability_flags_failed_claim_used_as_positive(self) -> None:
        claims = {"pbmc3k_stability": {"status": "fail"}}
        rows = claim_traceability.validate_storyline(
            [
                {
                    "figure": "Figure 3",
                    "linked_claim_ids": "pbmc3k_stability",
                    "status": "pass",
                    "source_artifact": "README.md",
                }
            ],
            claims,
        )
        self.assertEqual(rows[0]["trace_status"], "violation")
        self.assertEqual(rows[0]["decision"], "failed_claim_not_blocked")

    def test_claim_traceability_allows_failed_claim_as_blocked_caveat(self) -> None:
        claims = {"pbmc3k_stability": {"status": "fail"}}
        rows = claim_traceability.validate_storyline(
            [
                {
                    "figure": "Figure 3",
                    "linked_claim_ids": "pbmc3k_stability",
                    "status": "blocked",
                    "source_artifact": "README.md",
                }
            ],
            claims,
        )
        self.assertEqual(rows[0]["trace_status"], "controlled")
        self.assertEqual(rows[0]["decision"], "caveated_claim_traceable")

    def test_claim_traceability_markdown_reports_violations(self) -> None:
        rows = [
            {
                "artifact": "storyline_panel_map",
                "item_id": "Figure X",
                "linked_claim_ids": "missing_claim",
                "claim_statuses": "missing_claim:missing",
                "trace_status": "violation",
                "evidence_path": "README.md",
                "decision": "unknown_claim",
                "notes": "missing",
            }
        ]
        text = "\n".join(claim_traceability.build_markdown(rows))
        self.assertIn("Violations: `1`", text)
        self.assertIn("unknown_claim", text)

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
        draft_text = "\n".join(
            manuscript_draft.build_presubmission_draft(claims, checklist)
        )
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
        self.assertIn(
            status_by_id["stability_advantage"], {"pass", "borderline", "fail"}
        )
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
            {
                "dataset_id": "pbmc68k",
                "method": "rmtguard",
                "mean_pairwise_ari": "0.60",
                "mean_cluster_n": "1.4",
                "n_repeats": "5",
                "sample_fraction": "0.8",
            },
            {
                "dataset_id": "pbmc68k",
                "method": "fixed_pcs_30",
                "mean_pairwise_ari": "0.81",
                "mean_cluster_n": "8",
                "n_repeats": "5",
                "sample_fraction": "0.8",
            },
        ]
        diagnostics = stability_gate.build_diagnostics(rows)
        self.assertEqual(diagnostics[0]["status"], "fail_below_floor")
        self.assertIn("collapses", diagnostics[0]["notes"])

    def test_stability_utility_separates_stability_from_annotation(self) -> None:
        stability_rows = [
            {
                "dataset_id": "kang",
                "method": "rmtguard",
                "mean_pairwise_ari": "0.82",
                "mean_cluster_n": "4",
            },
            {
                "dataset_id": "kang",
                "method": "elbow_rule",
                "mean_pairwise_ari": "0.88",
                "mean_cluster_n": "8",
            },
            {
                "dataset_id": "kang",
                "method": "fixed_pcs_30",
                "mean_pairwise_ari": "0.70",
                "mean_cluster_n": "8",
            },
        ]
        annotation_rows = [
            {"dataset_id": "kang", "method": "rmtguard", "ari": "0.78"},
            {"dataset_id": "kang", "method": "elbow_rule", "ari": "0.66"},
            {"dataset_id": "kang", "method": "fixed_pcs_30", "ari": "0.68"},
        ]
        diagnostics = [{"dataset_id": "kang", "status": "fail_below_best_baseline"}]
        rows = stability_utility.build_rows(
            stability_rows, annotation_rows, diagnostics
        )
        by_method = {row["method"]: row for row in rows}
        self.assertEqual(
            by_method["elbow_rule"]["utility_relation_vs_rmtguard"],
            "comparator_higher_stability_lower_annotation",
        )
        self.assertEqual(by_method["elbow_rule"]["comparator_dominates_rmtguard"], "no")
        self.assertEqual(
            by_method["fixed_pcs_30"]["rmtguard_dominates_comparator"], "yes"
        )

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
            algorithm_rescue._decision(
                "resolution_path_min0p8", "kang_ifnb_pbmc", 0.69, 5.6
            ),
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

    def test_claim_scope_blocks_strict_route_when_stability_fails(self) -> None:
        gates = [
            {"gate_id": "stability_advantage", "status": "fail"},
            {"gate_id": "software_release", "status": "pending"},
        ]
        journals = [
            {"journal": "Nature Methods", "current_readiness": "not_ready"},
        ]
        claims = [
            {
                "claim_id": "pbmc3k_stability",
                "status": "fail",
                "allowed_wording": "callability-aware wording",
                "prohibited_wording": "broad fixed-PC superiority",
            },
            {"claim_id": "noise_control_null", "status": "pass"},
            {"claim_id": "diagnostic_no_call_validation", "status": "pass"},
            {"claim_id": "rare_state_retention", "status": "pass"},
            {"claim_id": "public_benchmark_breadth", "status": "pass"},
        ]
        rows = claim_scope.build_rows(gates, journals, claims)
        by_id = {row["decision_id"]: row for row in rows}
        self.assertEqual(
            by_id["strict_20_50_methods_article"]["status"],
            "blocked_by_stability_advantage",
        )
        self.assertIn(
            "guaranteed", by_id["guarantee_language"]["forbidden_claim"].lower()
        )
        self.assertIn("PBMC68k", by_id["pbmc68k_boundary"]["allowed_claim"])

    def test_claim_scope_markdown_never_promises_acceptance(self) -> None:
        rows = claim_scope.build_rows([], [], [])
        text = "\n".join(claim_scope.build_markdown(rows))
        self.assertIn("Acceptance guarantee: `impossible`", text)
        self.assertIn("Strict 20-50 JIF route: `blocked`", text)

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
        self.assertEqual(
            by_check["nature_methods_submission_ready"]["status"], "blocked"
        )

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
        presubmission = [
            {"check_id": "nature_methods_submission_ready", "status": "blocked"}
        ]
        datasets = [
            {"dataset_id": "pbmc3k_10x", "github_policy": "accession_and_script_only"}
        ]
        claims = [
            {
                "claim_id": "diagnostic_no_call_validation",
                "allowed_wording": "Diagnostic no-call validation passed.",
            }
        ]

        rows = journal_compliance.build_compliance_rows(
            gates, release, presubmission, datasets, claims
        )
        by_check = {row["check_id"]: row for row in rows}
        self.assertEqual(by_check["nature_methods_scope_fit"]["status"], "pass")
        self.assertEqual(by_check["code_availability"]["status"], "blocked")
        self.assertEqual(by_check["code_doi_repository"]["status"], "blocked")
        self.assertEqual(
            journal_compliance._overall_decision(rows), "not_submission_ready"
        )

    def test_journal_compliance_never_promises_acceptance(self) -> None:
        lines = journal_compliance.build_markdown([])
        self.assertTrue(
            any("Acceptance guarantee: `not possible`" in line for line in lines)
        )

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
        presubmission = [
            {"check_id": "nature_methods_submission_ready", "status": "blocked"}
        ]
        journals = [
            {
                "journal": "Nature Methods",
                "fit_for_current_project": "primary_target_if_gates_pass",
                "current_readiness": "not_ready",
            },
            {
                "journal": "Nature Biotechnology",
                "fit_for_current_project": "stretch_only",
            },
            {
                "journal": "Genome Biology",
                "fit_for_current_project": "realistic_fallback_if_strict_jif_relaxed",
            },
        ]
        rows = publication_board.build_board_rows(
            compliance, release, presubmission, journals
        )
        by_step = {row["step_id"]: row for row in rows}
        self.assertEqual(
            by_step["02_create_public_github_repository"]["status"], "blocked_external"
        )
        self.assertEqual(
            by_step["05_create_github_release_and_zenodo_doi"]["status"],
            "blocked_external",
        )
        self.assertEqual(
            publication_board._overall_status(rows), "blocked_before_submission"
        )

    def test_publication_board_states_no_acceptance_guarantee(self) -> None:
        lines = publication_board.build_markdown([])
        self.assertTrue(
            any("Acceptance guarantee: `impossible`" in line for line in lines)
        )

    def test_github_release_url_parsing_and_dry_run(self) -> None:
        self.assertEqual(
            github_release.normalize_repo_url(
                "https://github.com/example-lab/rmtguard.git"
            ),
            "https://github.com/example-lab/rmtguard",
        )
        self.assertEqual(
            github_release.parse_repo("https://github.com/example-lab/rmtguard"),
            ("example-lab", "rmtguard"),
        )
        rows = github_release.build_plan(
            "https://github.com/example-lab/rmtguard", "v0.1.0-rc1"
        )
        by_step = {row["step_id"]: row for row in rows}
        self.assertIn(
            by_step["02_validate_github_token"]["status"], {"ready", "blocked_external"}
        )
        self.assertEqual(by_step["05_create_github_release"]["status"], "would_run")

    def test_github_release_markdown_never_promises_acceptance(self) -> None:
        rows = github_release.build_plan(
            "https://github.com/example-lab/rmtguard", "v0.1.0-rc1"
        )
        lines = github_release.build_markdown(
            rows,
            "https://github.com/example-lab/rmtguard",
            "v0.1.0-rc1",
            execute_mode=False,
        )
        self.assertTrue(
            any("Acceptance guarantee: `impossible`" in line for line in lines)
        )

    def test_submission_finalizer_blocks_without_repo_and_doi(self) -> None:
        rows = submission_finalizer.build_plan(None, None, "v0.1.0-rc1")
        by_step = {row["step_id"]: row for row in rows}
        self.assertEqual(by_step["01_validate_inputs"]["status"], "blocked")
        self.assertEqual(by_step["04_record_external_metadata"]["status"], "blocked")

    def test_submission_finalizer_parses_valid_inputs_and_requires_manual_tag_review(
        self,
    ) -> None:
        rows = submission_finalizer.build_plan(
            "https://github.com/example-lab/rmtguard",
            "10.5281/zenodo.12345",
            "v0.1.0-rc1",
        )
        by_step = {row["step_id"]: row for row in rows}
        self.assertEqual(by_step["01_validate_inputs"]["status"], "ready")
        self.assertIn(
            by_step["03_validate_tag_state"]["status"], {"ready", "manual_review"}
        )
        lines = submission_finalizer.build_markdown(
            rows,
            "https://github.com/example-lab/rmtguard",
            "10.5281/zenodo.12345",
            "v0.1.0-rc1",
            execute_mode=False,
        )
        self.assertTrue(
            any("Acceptance guarantee: `impossible`" in line for line in lines)
        )

    def test_reporting_summary_draft_marks_code_doi_blocked(self) -> None:
        datasets = [
            {
                "dataset_id": "pbmc3k_10x",
                "accession": "NA",
                "github_policy": "accession_and_script_only",
            }
        ]
        claims = [
            {
                "claim_id": "noise_control_null",
                "allowed_wording": "Null control passes.",
            }
        ]
        release = [
            {"check_id": "repository_url", "status": "pending"},
            {"check_id": "zenodo_doi", "status": "pending"},
        ]
        compliance = [{"check_id": "reporting_summary", "status": "pending_manual"}]
        gates = [{"gate_id": "synthetic_null_false_signal", "status": "pass"}]
        rows = reporting_summary.build_rows(
            datasets, claims, release, compliance, gates
        )
        by_item = {row["item"]: row for row in rows}
        self.assertEqual(by_item["Code DOI"]["status"], "blocked")
        self.assertEqual(by_item["Official form status"]["status"], "pending_manual")
        lines = reporting_summary.build_markdown(rows)
        self.assertTrue(
            any(
                "official Nature Portfolio reporting summary form" in line
                for line in lines
            )
        )

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
        journals = [
            {
                "journal": "Nature Methods",
                "current_readiness": "not_ready",
                "fit_for_current_project": "primary_target_if_gates_pass",
            }
        ]
        execution = [
            {
                "step_id": "02_create_public_github_repository",
                "status": "blocked_external",
            }
        ]
        rows = editorial_risk.build_rows(objections, compliance, journals, execution)
        by_risk = {row["risk_id"]: row for row in rows}
        self.assertEqual(by_risk["software_release_desk_reject"]["status"], "blocked")
        self.assertEqual(
            editorial_risk.overall_status(rows), "blocked_before_editorial_submission"
        )

    def test_editorial_risk_never_promises_acceptance(self) -> None:
        lines = editorial_risk.build_markdown([])
        self.assertTrue(
            any("Acceptance guarantee: `impossible`" in line for line in lines)
        )

    def test_editorial_risk_distinguishes_baseline_implementation_from_results(
        self,
    ) -> None:
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
            phase1_summary.write_text(
                "method\nrmtguard\nfixed_pcs_30\n", encoding="utf-8"
            )
            stability_summary.write_text(
                "method\nrmtguard\nfixed_pcs_30\n", encoding="utf-8"
            )
            seurat_result.write_text(
                "method\nseurat_v5_like_pcs_30\n", encoding="utf-8"
            )

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

    def test_submission_guard_blocks_current_not_ready_route(self) -> None:
        gates = [
            {"gate_id": "synthetic_null_false_signal", "status": "pass"},
            {"gate_id": "stability_advantage", "status": "fail"},
            {"gate_id": "software_release", "status": "pending"},
        ]
        presubmission = [
            {"check_id": "nature_methods_submission_ready", "status": "blocked"}
        ]
        release = [
            {"check_id": "repository_url", "status": "pending"},
            {"check_id": "github_remote", "status": "pending"},
            {"check_id": "github_release_tag", "status": "pending"},
            {"check_id": "zenodo_doi", "status": "pending"},
        ]
        routes = [
            {
                "route_id": "nature_methods_first",
                "decision": "hold_pre_submission",
            }
        ]
        editorial = [{"item_id": "send_status", "status": "do_not_send"}]

        rows = submission_guard.build_guard_rows(
            gates,
            presubmission,
            release,
            [],
            [],
            routes,
            editorial,
        )
        by_guard = {row["guard_id"]: row for row in rows}
        self.assertEqual(by_guard["scientific_gates"]["status"], "blocked")
        self.assertEqual(by_guard["external_release"]["status"], "blocked")
        self.assertEqual(
            by_guard["overall_submission_guard"]["status"], "do_not_submit"
        )
        self.assertIn(
            "stability_advantage", by_guard["scientific_gates"]["blocking_items"]
        )

    def test_submission_guard_marks_claim_lint_violation_as_integrity_issue(
        self,
    ) -> None:
        rows = submission_guard.build_guard_rows(
            [{"gate_id": "synthetic_null_false_signal", "status": "pass"}],
            [],
            [],
            [
                {
                    "rule_id": "acceptance_guarantee",
                    "status": "violation",
                    "path": "manuscript/cover_letter.md",
                    "line": "12",
                }
            ],
            [],
            [{"route_id": "nature_methods_first", "decision": "submission_candidate"}],
            [{"item_id": "send_status", "status": "send_ready"}],
        )
        by_guard = {row["guard_id"]: row for row in rows}
        self.assertEqual(
            by_guard["claim_boundary_lint"]["status"], "integrity_violation"
        )
        self.assertEqual(
            by_guard["overall_submission_guard"]["status"], "do_not_submit"
        )

    def test_submission_guard_parses_gate_report_preamble(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report = Path(tmpdir) / "gate_report.tsv"
            report.write_text(
                "RMTGuard submission gate summary\n"
                "recommendation\tcontinue_benchmarking\n"
                "gate_id\tstatus\tcategory\tnature_methods_requirement\n"
                "stability_advantage\tfail\tbenchmark\tNeed stronger stability.\n",
                encoding="utf-8",
            )
            rows = submission_guard._read_tsv_from_header(report, "gate_id")
        self.assertEqual(rows[0]["gate_id"], "stability_advantage")
        self.assertEqual(rows[0]["status"], "fail")

    def test_submission_guard_markdown_never_promises_acceptance(self) -> None:
        lines = submission_guard.build_markdown(
            [
                {
                    "guard_id": "overall_submission_guard",
                    "status": "do_not_submit",
                    "severity": "blocking",
                    "evidence_path": "results/submission/submission_guard.tsv",
                    "blocking_items": "scientific_gates",
                    "required_action": "Resolve blockers.",
                    "notes": "Acceptance guarantee remains impossible.",
                }
            ]
        )
        text = "\n".join(lines)
        self.assertIn("Acceptance guarantee: `impossible`", text)
        self.assertNotIn("guaranteed acceptance", text.lower())


if __name__ == "__main__":
    unittest.main()
