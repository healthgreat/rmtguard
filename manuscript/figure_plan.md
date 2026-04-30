# Main Figure Plan

Current scripted artifacts:

- Source-data manifest: `results/figures/figure_reproducibility.tsv`
- Draft render manifest: `figures/manuscript/rendered_figure_manifest.tsv`
- Source-data command: `python scripts/build_figure_source_data.py`
- Draft rendering command: `python scripts/render_main_figures.py`

These are reproducibility drafts. Final submission figures still need panel
labeling, design polish, and journal-format checks.

## Figure 1

RMTGuard algorithm overview and MP/TW/permutation decision rule. Show the
cell-by-gene matrix, preprocessing, spectrum, selected signal PCs, noise PCs,
neighbor stability, and clustering guard.

## Figure 2

Synthetic benchmark across pure null, rare state, batch effect, dropout stress,
continuous trajectory, and overclustering stress. Main message: RMTGuard keeps
true low-rank structure while controlling noise-driven PCs.

## Figure 3

Public benchmark against Scanpy default, Seurat default, fixed `n_pcs=30`,
fixed `n_pcs=50`, elbow, permutation/parallel PCA, and RMTGuard ablations.
Main message: improved stability without sacrificing annotation recovery.

## Figure 4

PDAC/TME showcase using GSE154778 and external validation in GSE263733. Main
message: stable immune or malignant-ductal-context states are retained while
unstable overclustered states are suppressed. The current smoke run does not
support a standalone CAF/fibroblast main claim.

## Figure 5

Runtime, memory, ablation, reproducibility, and release audit. Main message:
RMTGuard is practical on a single workstation and the manuscript package is
fully reproducible from public data.
