# Nature Methods Publication Strategy

## Target

Primary target: **Nature Methods**. Most likely final home if Nature Methods
judges the method-breakthrough claim insufficient: **Genome Biology**.

RMTGuard should be framed as a method for random-matrix noise control in
single-cell cell-state discovery, not as a convenience wrapper around Scanpy.
The central claim is:

> RMTGuard reduces analyst-controlled degrees of freedom in scRNA-seq workflows
> by selecting HVGs, signal PCs, neighborhood size, and cluster granularity under
> an explicit high-dimensional noise model.

Nature Methods' 2024 Journal Impact Factor is 32.1 and its 5-year Journal Impact
Factor is 51.7. The submission should emphasize methodological breadth,
software usability, reproducibility, and cross-dataset validation rather than a
single clinical discovery.

## Required Manuscript Package

1. Algorithm statement: MP bulk fit, Tracy-Widom proxy, optional permutation
   calibration, HVG spectral plateau, noise-PC stability guard, and batch-aware
   residualization.
2. Open software: GitHub source, MIT license, CI, Docker, test data, CLI, example
   runtime, and Zenodo DOI before submission.
3. Synthetic stress tests: pure null, planted low-rank signal, rare state, batch
   effect, dropout, continuous trajectory, and overclustering.
4. Public benchmark: PBMC3k, PBMC68k/Zheng 2017, Kang IFN-beta PBMC, Baron
   pancreas, selected Tabula Sapiens tissues.
5. PDAC/TME showcase: GSE154778 as the main public example and GSE263733 as
   external validation.
6. Comparisons: Scanpy default, Seurat default, fixed PC counts, elbow,
   permutation/parallel analysis, JackStraw-like baseline when feasible, and
   optional scVI supplement.

## Editorial Risk

The main risk is not software packaging; it is whether the MP null model remains
diagnostic under scRNA-seq count structure, dropout, ambient RNA, cell-cycle
programs, batch effects, and continuous biological gradients. The paper must
show both where RMTGuard works and where its diagnostics warn users not to
overinterpret the output.

## Go/No-Go Rule

Do not submit to Nature Methods until all gates in `metadata/submission_gates.tsv`
are marked `pass` in the evidence table. The strict gates protect the project
from a premature desk reject caused by incomplete real-data benchmark evidence.

If the software/reproducibility gates pass but the broad method-breakthrough or
PDAC/TME showcase gates are borderline, reframe the manuscript for Genome
Biology as a reproducible genomics workflow and benchmark paper.

## Fallback Journals

If Nature Methods rejects after review, the preferred fallback is Genome
Biology. Further fallback options are Cell Genomics, Nature Communications, Cell
Systems, Briefings in Bioinformatics, NAR Genomics and Bioinformatics, or
Bioinformatics, depending on whether the strongest evidence is biological
breadth, software utility, or statistical benchmarking.
