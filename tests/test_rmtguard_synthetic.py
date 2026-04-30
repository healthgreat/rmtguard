from __future__ import annotations

import unittest

import numpy as np

from rmtguard import RMTGuard, RMTGuardConfig, simulate_low_rank_counts, simulate_null_counts
from rmtguard.core import HVGScanRecord
from rmtguard.scanpy_api import fit_anndata


class RMTGuardSyntheticTest(unittest.TestCase):
    def test_spectral_stability_prefers_complete_plateau_hvg(self) -> None:
        records = [
            HVGScanRecord(500, 18, 2.0, 1.0, 0.05, 1.0),
            HVGScanRecord(1000, 17, 3.0, 1.0, 0.08, 1.0),
            HVGScanRecord(2000, 16, 4.0, 1.0, 0.09, 1.0),
        ]
        guard = RMTGuard(RMTGuardConfig(hvg_rule="spectral_stability", plateau_fraction=0.90))
        selected = guard._select_hvg_record(records)
        self.assertEqual(selected.n_hvg, 2000)

    def test_pure_null_has_few_signal_pcs(self) -> None:
        counts, _ = simulate_null_counts(n_cells=90, n_genes=160, random_state=1)
        result = RMTGuard(
            RMTGuardConfig(hvg_grid=(80, 140), max_pcs=20, pc_rule="mp_tw", embedding_stability_repeats=2)
        ).fit(counts)
        self.assertLessEqual(result.n_signal_pcs, 1)
        self.assertEqual(result.analysis_status, "diagnostic_no_call")
        self.assertIn("signal", result.no_call_reason)
        self.assertIn("selected_edge", result.pc_diagnostics)
        self.assertIn("pc_records", result.embedding_diagnostics)
        self.assertLessEqual(result.embedding_diagnostics["accepted_embedding_pcs"], 3)

    def test_low_signal_rescue_keeps_pure_null_no_call(self) -> None:
        counts, _ = simulate_null_counts(n_cells=90, n_genes=160, random_state=11)
        result = RMTGuard(
            RMTGuardConfig(
                hvg_grid=(80, 140),
                max_pcs=20,
                pc_rule="mp_tw",
                embedding_stability_repeats=2,
                low_signal_rescue_rule="stable_embedding",
                low_signal_rescue_stability_threshold=0.95,
            )
        ).fit(counts)
        self.assertLessEqual(result.n_signal_pcs, 1)
        self.assertEqual(result.analysis_status, "diagnostic_no_call")
        self.assertEqual(result.embedding_diagnostics["low_signal_rescue_rule"], "stable_embedding")

    def test_low_rank_signal_is_detected(self) -> None:
        counts, _labels, _batch = simulate_low_rank_counts(
            n_cells=140,
            n_genes=260,
            n_states=3,
            markers_per_state=25,
            random_state=2,
        )
        result = RMTGuard(
            RMTGuardConfig(
                hvg_grid=(80, 160),
                max_pcs=25,
                cluster_grid=tuple(range(2, 7)),
                embedding_stability_repeats=2,
            )
        ).fit(counts)
        self.assertGreaterEqual(result.n_signal_pcs, 2)
        self.assertEqual(result.embedding_diagnostics["strict_signal_pcs"], result.n_signal_pcs)
        self.assertGreaterEqual(result.embedding_diagnostics["accepted_embedding_pcs"], result.n_signal_pcs)
        self.assertIn(result.selected_hvg_n, {80, 160})
        self.assertEqual(result.embedding.shape[0], counts.shape[0])
        self.assertEqual(result.cluster_labels.shape[0], counts.shape[0])
        self.assertEqual(result.analysis_status, "ok")

    def test_rare_state_is_not_removed_by_default(self) -> None:
        counts, labels, _batch = simulate_low_rank_counts(
            n_cells=180,
            n_genes=320,
            n_states=3,
            markers_per_state=30,
            rare_fraction=0.05,
            random_state=3,
        )
        result = RMTGuard(
            RMTGuardConfig(
                hvg_grid=(100, 220),
                max_pcs=25,
                cluster_grid=tuple(range(2, 8)),
                embedding_stability_repeats=2,
            )
        ).fit(counts)
        rare_label = int(np.max(labels))
        rare_cells = labels == rare_label
        self.assertGreaterEqual(result.n_signal_pcs, 2)
        self.assertGreater(np.unique(result.cluster_labels[rare_cells]).size, 0)

    def test_consensus_resolution_rule_runs(self) -> None:
        counts, _labels, _batch = simulate_low_rank_counts(
            n_cells=100,
            n_genes=180,
            n_states=3,
            markers_per_state=20,
            random_state=7,
        )
        result = RMTGuard(
            RMTGuardConfig(
                hvg_grid=(80, 140),
                max_pcs=20,
                cluster_grid=tuple(range(2, 6)),
                resolution_rule="consensus_stability",
                stability_repeats=3,
                embedding_stability_repeats=2,
                random_state=7,
            )
        ).fit(counts)
        self.assertEqual(result.cluster_labels.shape[0], counts.shape[0])
        self.assertEqual(result.benchmark_metadata["resolution_rule"], "consensus_stability")
        self.assertGreaterEqual(np.unique(result.cluster_labels).size, 2)

    def test_strict_signal_embedding_rule_matches_signal_pc_count(self) -> None:
        counts, _labels, _batch = simulate_low_rank_counts(
            n_cells=120,
            n_genes=220,
            n_states=3,
            markers_per_state=20,
            random_state=8,
        )
        result = RMTGuard(
            RMTGuardConfig(
                hvg_grid=(80, 160),
                max_pcs=20,
                embedding_rule="strict_signal",
                cluster_grid=tuple(range(2, 6)),
            )
        ).fit(counts)
        self.assertEqual(result.embedding_diagnostics["rule"], "strict_signal")
        self.assertEqual(result.embedding_diagnostics["accepted_embedding_pcs"], result.n_signal_pcs)
        self.assertEqual(result.embedding.shape[1], result.n_signal_pcs)

    def test_batch_aware_reduces_batch_driven_signal(self) -> None:
        counts, _labels, batch = simulate_low_rank_counts(
            n_cells=160,
            n_genes=300,
            n_states=3,
            markers_per_state=10,
            batch_effect=True,
            random_state=4,
        )
        cfg = RMTGuardConfig(hvg_grid=(100, 200), max_pcs=30, pc_rule="mp_tw", embedding_stability_repeats=2)
        no_batch = RMTGuard(cfg).fit(counts)
        batch_aware = RMTGuard(cfg).fit(counts, batches=batch)
        self.assertLessEqual(batch_aware.n_signal_pcs, no_batch.n_signal_pcs)
        self.assertTrue(batch_aware.benchmark_metadata["batch_aware"])

    def test_permutation_calibration_records_null_edges(self) -> None:
        counts, _ = simulate_null_counts(n_cells=70, n_genes=120, random_state=6)
        result = RMTGuard(
            RMTGuardConfig(
                hvg_grid=(60, 100),
                max_pcs=15,
                pc_rule="mp_tw_permutation",
                n_permutations=3,
                tw_alpha=0.1,
                embedding_stability_repeats=2,
                random_state=6,
            )
        ).fit(counts)
        self.assertEqual(result.null_calibration["n_permutations"], 3)
        self.assertEqual(len(result.null_calibration["permutation_max_edges"]), 3)

    def test_anndata_dense_and_layer_inputs(self) -> None:
        import anndata as ad

        counts, _labels, batch = simulate_low_rank_counts(
            n_cells=80,
            n_genes=140,
            n_states=2,
            markers_per_state=20,
            random_state=5,
        )
        adata = ad.AnnData(counts)
        adata.layers["counts"] = counts.copy()
        adata.obs["batch"] = batch if batch is not None else np.repeat(["a"], counts.shape[0])
        result = fit_anndata(
            adata,
            config=RMTGuardConfig(hvg_grid=(60, 120), max_pcs=15, batch_key="batch"),
            layer="counts",
        )
        self.assertEqual(adata.obsm["X_rmtguard"].shape[0], counts.shape[0])
        self.assertIn("rmtguard_leiden", adata.obs)
        self.assertIn("pc_diagnostics", adata.uns["rmtguard"])
        self.assertIn("embedding_diagnostics", adata.uns["rmtguard"])
        self.assertEqual(result.benchmark_metadata["batch_key"], "batch")


if __name__ == "__main__":
    unittest.main()
