from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "update_gate_evidence_from_results.py"
spec = importlib.util.spec_from_file_location("update_gate_evidence_from_results", SCRIPT)
assert spec is not None and spec.loader is not None
gate_update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate_update)


class GateEvidenceUpdateTest(unittest.TestCase):
    def test_update_from_minimal_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            phase1 = tmp_path / "phase1.tsv"
            with phase1.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["dataset_id", "method", "ari"], delimiter="\t")
                writer.writeheader()
                writer.writerow({"dataset_id": "kang_ifnb_pbmc", "method": "rmtguard", "ari": "0.95"})
                writer.writerow({"dataset_id": "kang_ifnb_pbmc", "method": "fixed_pcs_30", "ari": "0.93"})

            synthetic = tmp_path / "synthetic.csv"
            with synthetic.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["scenario", "method", "n_signal_pcs", "ari"])
                writer.writeheader()
                writer.writerow({"scenario": "pure_null", "method": "rmtguard", "n_signal_pcs": "0", "ari": ""})
                writer.writerow({"scenario": "rare_state", "method": "rmtguard", "n_signal_pcs": "3", "ari": "0.8"})

            no_call = tmp_path / "no_call.tsv"
            with no_call.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "scenario",
                        "expected_behavior",
                        "analysis_status",
                        "no_call_reason",
                        "n_signal_pcs",
                        "accepted_embedding_pcs",
                        "cluster_n",
                        "ari",
                        "decision",
                        "notes",
                    ],
                    delimiter="\t",
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "scenario": "pure_null",
                        "expected_behavior": "diagnostic_no_call",
                        "analysis_status": "diagnostic_no_call",
                        "no_call_reason": "insufficient_signal_pcs_for_embedding",
                        "n_signal_pcs": "0",
                        "accepted_embedding_pcs": "0",
                        "cluster_n": "1",
                        "ari": "nan",
                        "decision": "pass",
                        "notes": "ok",
                    }
                )
                writer.writerow(
                    {
                        "scenario": "planted_low_rank",
                        "expected_behavior": "positive_call",
                        "analysis_status": "ok",
                        "no_call_reason": "",
                        "n_signal_pcs": "3",
                        "accepted_embedding_pcs": "3",
                        "cluster_n": "3",
                        "ari": "0.95",
                        "decision": "pass",
                        "notes": "ok",
                    }
                )
                writer.writerow(
                    {
                        "scenario": "rare_state",
                        "expected_behavior": "positive_call",
                        "analysis_status": "ok",
                        "no_call_reason": "",
                        "n_signal_pcs": "3",
                        "accepted_embedding_pcs": "3",
                        "cluster_n": "3",
                        "ari": "0.93",
                        "decision": "pass",
                        "notes": "ok",
                    }
                )

            out = tmp_path / "evidence.tsv"
            stability_diagnostics = tmp_path / "missing_stability_diagnostics.tsv"
            stability = tmp_path / "stability.tsv"
            with stability.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["dataset_id", "method", "mean_pairwise_ari", "n_repeats", "mean_n_cells"], delimiter="\t")
                writer.writeheader()
                writer.writerow({"dataset_id": "pbmc3k_10x", "method": "rmtguard", "mean_pairwise_ari": "0.8", "n_repeats": "5", "mean_n_cells": "600"})
                writer.writerow({"dataset_id": "pbmc3k_10x", "method": "fixed_pcs_30", "mean_pairwise_ari": "0.7", "n_repeats": "5", "mean_n_cells": "600"})

            pdac = tmp_path / "pdac.tsv"
            with pdac.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "dataset_id",
                        "n_cells",
                        "cluster_n",
                        "has_immune_cluster",
                        "has_ductal_context_cluster",
                        "has_caf_or_fibroblast_cluster",
                        "label_ari",
                    ],
                    delimiter="\t",
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "dataset_id": "pdac_gse154778",
                        "n_cells": "1200",
                        "cluster_n": "4",
                        "has_immune_cluster": "True",
                        "has_ductal_context_cluster": "True",
                        "has_caf_or_fibroblast_cluster": "False",
                        "label_ari": "nan",
                    }
                )
                writer.writerow(
                    {
                        "dataset_id": "pdac_gse263733",
                        "n_cells": "1200",
                        "cluster_n": "7",
                        "has_immune_cluster": "True",
                        "has_ductal_context_cluster": "True",
                        "has_caf_or_fibroblast_cluster": "False",
                        "label_ari": "0.56",
                    }
                )

            figure_source = tmp_path / "figure_reproducibility.tsv"
            with figure_source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "figure_id",
                        "panel",
                        "source_data_path",
                        "input_paths",
                        "regeneration_command",
                        "status",
                        "notes",
                    ],
                    delimiter="\t",
                )
                writer.writeheader()
                for idx in range(1, 6):
                    writer.writerow(
                        {
                            "figure_id": f"Figure {idx}",
                            "panel": "source data",
                            "source_data_path": f"results/figures/source_data/figure{idx}.tsv",
                            "input_paths": "results/example.tsv",
                            "regeneration_command": "python scripts/build_figure_source_data.py",
                            "status": "ready",
                            "notes": "test row",
                        }
                    )

            release_readiness = tmp_path / "release_readiness.tsv"
            with release_readiness.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["check_id", "status", "evidence_path", "notes"],
                    delimiter="\t",
                )
                writer.writeheader()
                for check_id in [
                    "local_release_audit",
                    "license",
                    "citation_metadata",
                    "zenodo_metadata",
                    "ci_workflow",
                    "dockerfile",
                    "dataset_manifest",
                    "figure_source_data_manifest",
                    "rendered_figure_manifest",
                    "release_artifact_manifest",
                    "github_staging_plan",
                    "github_stage_dry_run",
                    "github_release_handoff",
                    "repository_metadata_update_plan",
                    "external_release_metadata_plan",
                    "external_release_plan",
                    "release_asset_manifest",
                    "manuscript_evidence_package",
                    "manuscript_draft_package",
                    "stability_gate_report",
                    "no_call_benchmark_report",
                    "publication_20_50_plan",
                    "journal_compliance_audit",
                    "publication_execution_board",
                    "reporting_summary_draft",
                    "editorial_risk_audit",
                ]:
                    writer.writerow({"check_id": check_id, "status": "pass", "evidence_path": "x", "notes": "ok"})
                writer.writerow({"check_id": "github_release_tag", "status": "pending", "evidence_path": "x", "notes": "not tagged"})
                writer.writerow({"check_id": "zenodo_doi", "status": "pending", "evidence_path": "x", "notes": "no DOI"})

            code = gate_update.main(
                [
                    "--phase1",
                    str(phase1),
                    "--synthetic",
                    str(synthetic),
                    "--no-call",
                    str(no_call),
                    "--stability",
                    str(stability),
                    "--stability-diagnostics",
                    str(stability_diagnostics),
                    "--pdac",
                    str(pdac),
                    "--figure-source",
                    str(figure_source),
                    "--release-readiness",
                    str(release_readiness),
                    "--out",
                    str(out),
                ]
            )
            self.assertEqual(code, 0)
            text = out.read_text(encoding="utf-8")
            self.assertIn("synthetic_null_false_signal\tpass", text)
            self.assertIn("diagnostic_no_call_validation\tpass", text)
            self.assertIn("annotation_noninferiority\tpass", text)
            self.assertIn("stability_advantage\tpass", text)
            self.assertIn("pdac_tme_interpretability\tpass", text)
            self.assertIn("figure_source_data\tpass", text)
            self.assertIn("software_release\tpending", text)
            self.assertIn("Local release readiness checks passed 26/26", text)


if __name__ == "__main__":
    unittest.main()
