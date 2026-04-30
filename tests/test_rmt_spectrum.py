from __future__ import annotations

import unittest

import numpy as np

from rmtguard.rmt import spectrum_from_matrix


class RMTSpectrumTest(unittest.TestCase):
    def test_cell_gram_spectrum_matches_direct_svd_eigenvalues(self) -> None:
        rng = np.random.default_rng(20260429)
        x = rng.normal(size=(12, 30))
        centered = x - np.mean(x, axis=0, keepdims=True)
        singular_values = np.linalg.svd(centered, full_matrices=False, compute_uv=False)
        expected = (singular_values**2) / (x.shape[0] - 1)
        observed = spectrum_from_matrix(x).eigenvalues
        self.assertTrue(np.allclose(observed[: expected.size], expected, atol=1e-8))


if __name__ == "__main__":
    unittest.main()
