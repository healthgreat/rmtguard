from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import numpy as np


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

    def test_coarse_pca_labeler_is_label_free_and_bounded(self) -> None:
        rng = np.random.default_rng(42)
        x = np.exp(rng.normal(size=(72, 36)))
        args = SimpleNamespace(
            max_pcs=12,
            baseline_permutations=3,
            coarse_pc_rule="elbow_rule",
            coarse_min_pcs=3,
            coarse_max_pcs=12,
            coarse_max_clusters=5,
        )
        labels, metadata = stability_benchmark._coarse_pca_labels(x, args, random_state=42)
        self.assertEqual(labels.shape[0], x.shape[0])
        self.assertGreaterEqual(np.unique(labels).size, 2)
        self.assertLessEqual(np.unique(labels).size, args.coarse_max_clusters)
        self.assertIn("coarse_selected_pcs", metadata)
        self.assertIn("coarse_embedding_pcs", metadata)

    def test_coarse_to_fine_probe_returns_metadata(self) -> None:
        rng = np.random.default_rng(7)
        latent = rng.normal(size=(90, 3))
        loadings = rng.normal(size=(3, 60))
        rates = np.exp(0.2 * (latent @ loadings) + 1.0)
        x = rng.poisson(rates).astype(float)
        args = SimpleNamespace(
            hvg_grid=(30, 50),
            max_pcs=10,
            min_embedding_pcs=0,
            whiten="biwhiten",
            pc_rule="mp_tw",
            hvg_rule="spectral_stability",
            hvg_score="normalized_dispersion",
            embedding_rule="adaptive_near_edge",
            embedding_source="standard_pca",
            near_edge_window=1.25,
            embedding_stability_repeats=2,
            embedding_stability_threshold=0.75,
            embedding_subsample_fraction=0.8,
            low_signal_rescue_rule="off",
            low_signal_rescue_max_pcs=12,
            low_signal_rescue_min_pcs=2,
            low_signal_rescue_stability_threshold=0.9,
            low_signal_rescue_null_permutations=2,
            low_signal_rescue_null_quantile=0.95,
            low_signal_rescue_min_eigen_ratio=0.95,
            resolution_rule="kmeans_stability",
            graph_resolution_grid=(1.0,),
            low_signal_graph_resolution=1.0,
            low_signal_pc_threshold=3,
            high_signal_graph_resolution=1.5,
            high_signal_pc_threshold=10,
            n_permutations=0,
            tw_alpha=0.01,
            stability_repeats=2,
            max_clusters=5,
            baseline_permutations=3,
            coarse_pc_rule="elbow_rule",
            coarse_min_pcs=3,
            coarse_max_pcs=10,
            coarse_max_clusters=4,
            coarse_min_cells=15,
        )
        labels, metadata = stability_benchmark._rmtguard_coarse_to_fine_run(x, args, seed=7)
        self.assertEqual(labels.shape[0], x.shape[0])
        self.assertEqual(metadata["analysis_status"], "experimental_probe")
        self.assertIn("fine_callable_compartments", metadata)
        self.assertIn("fine_no_call_compartments", metadata)


if __name__ == "__main__":
    unittest.main()
