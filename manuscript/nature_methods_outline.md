# Nature Methods Outline

## Title

RMTGuard: random-matrix noise control for reproducible single-cell cell-state
discovery

## Central Claim

Random-matrix noise control reduces subjective parameter choices and improves
reproducibility in scRNA-seq cell-state discovery.

## Article Structure

1. Introduction: subjective parameters in scRNA-seq workflows and the risk of
   noise-driven overclustering.
2. Method: MP bulk fit, Tracy-Widom proxy, optional permutation calibration,
   HVG spectral plateau, noise-PC stability, and batch-aware residualization.
3. Synthetic benchmarks: false signal control, rare-state retention, batch and
   dropout stress.
4. Public benchmarks: PBMC, perturbation, pancreas, atlas-scale or large immune
   datasets.
5. PDAC/TME application: GSE154778 primary showcase and GSE263733 validation.
6. Software and reproducibility: GitHub, Docker, CI, Zenodo DOI, source data.

## Submission Gate

Submit to Nature Methods only if all required gates in
`metadata/submission_gates.tsv` are marked `pass` in the evidence table.
