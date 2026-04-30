from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    script = ROOT / "benchmarks" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


phase1 = _load_script("run_phase1_benchmark")
stability = _load_script("run_stability_benchmark")


class BaselinePcRulesTest(unittest.TestCase):
    def test_elbow_rule_returns_bounded_pc_count(self) -> None:
        variance_ratio = np.array([0.45, 0.25, 0.12, 0.06, 0.04, 0.03, 0.02, 0.015, 0.01, 0.005])
        selected = phase1._choose_elbow_n_pcs(variance_ratio, min_pcs=3)
        self.assertGreaterEqual(selected, 3)
        self.assertLessEqual(selected, variance_ratio.size)

    def test_parallel_analysis_detects_low_rank_signal(self) -> None:
        rng = np.random.default_rng(42)
        scores = rng.normal(size=(80, 2))
        loadings = rng.normal(size=(2, 40))
        x = scores @ loadings + rng.normal(scale=0.2, size=(80, 40))
        selected = phase1._choose_parallel_analysis_n_pcs(
            x,
            max_pcs=10,
            n_permutations=5,
            random_state=42,
        )
        self.assertGreaterEqual(selected, 1)
        self.assertLessEqual(selected, 10)

    def test_parallel_analysis_uses_contiguous_leading_pcs(self) -> None:
        observed = np.array([3.0, 1.0, 2.0])
        threshold = np.array([2.0, 1.5, 1.5])
        self.assertEqual(phase1._count_contiguous_leading_passes(observed, threshold), 1)
        self.assertEqual(stability._count_contiguous_leading_passes(observed, threshold), 1)

    def test_stability_pc_rule_labeler_returns_metadata_for_all_rules(self) -> None:
        rng = np.random.default_rng(123)
        x = np.exp(rng.normal(size=(60, 30)))

        class Args:
            max_pcs = 12
            baseline_permutations = 3

        for method in ["elbow_rule", "parallel_analysis", "jackstraw_like"]:
            labels, metadata = stability._pc_rule_pca_labels(x, method, Args(), random_state=123)
            self.assertEqual(labels.shape[0], x.shape[0])
            self.assertIn("baseline_selected_pcs", metadata)
            self.assertIn("baseline_embedding_pcs", metadata)
            self.assertIn("baseline_pc_rule", metadata)
            self.assertGreaterEqual(metadata["baseline_embedding_pcs"], 1)


if __name__ == "__main__":
    unittest.main()
