from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "benchmarks" / "run_stability_benchmark.py"
spec = importlib.util.spec_from_file_location("run_stability_benchmark", SCRIPT)
assert spec is not None and spec.loader is not None
stability_benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stability_benchmark)


class StabilityBenchmarkTest(unittest.TestCase):
    def test_phase1_dataset_filenames_are_registered(self) -> None:
        self.assertEqual(
            {
                "pbmc3k_10x",
                "kang_ifnb_pbmc",
                "baron_pancreas",
                "pbmc68k_zheng2017",
            },
            set(stability_benchmark.DATASET_FILENAMES),
        )

    def test_atomic_tsv_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rows.tsv"
            stability_benchmark._write_tsv_atomic(path, [{"dataset_id": "pbmc3k_10x", "value": "1"}])
            with path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(rows, [{"dataset_id": "pbmc3k_10x", "value": "1"}])


if __name__ == "__main__":
    unittest.main()
