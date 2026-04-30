from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_submission_gates.py"
spec = importlib.util.spec_from_file_location("evaluate_submission_gates", SCRIPT)
assert spec is not None and spec.loader is not None
gates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gates)


class SubmissionGateTest(unittest.TestCase):
    def test_template_is_not_ready_for_submission(self) -> None:
        evidence = gates.read_tsv(ROOT / "metadata" / "gate_evidence_template.tsv")
        statuses = gates.gate_status(evidence)
        self.assertEqual(gates.recommendation(statuses), "continue_benchmarking")

    def test_all_pass_recommends_nature_methods(self) -> None:
        statuses = {gate: "pass" for gate in gates.NM_REQUIRED}
        self.assertEqual(gates.recommendation(statuses), "submit_nature_methods")

    def test_borderline_core_recommends_genome_biology(self) -> None:
        statuses = {gate: "pending" for gate in gates.NM_REQUIRED}
        statuses.update(
            {
                "software_release": "pass",
                "real_dataset_count": "borderline",
                "annotation_noninferiority": "pass",
            }
        )
        self.assertEqual(gates.recommendation(statuses), "prepare_genome_biology_fallback")

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "gate_report.tsv"
            code = gates.main(["--out", str(out)])
            self.assertEqual(code, 0)
            self.assertIn("recommendation", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
