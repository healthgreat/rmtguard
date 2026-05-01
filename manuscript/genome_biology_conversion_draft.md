# Genome Biology Conversion Draft

Status: not submission-ready until the public GitHub/Zenodo release is complete.
This is a fallback manuscript scaffold, not a downgrade of the scientific standards.

## Working Title

RMTGuard: a callability-aware random-matrix workflow for reproducible single-cell RNA-seq state discovery

## Target Positioning

- Current route decision: `activate_after_software_release`
- Article frame: genomics software, reproducible benchmark, public workflow, and transparent no-call boundaries.
- Do not present Genome Biology as a strict 20-50 JIF target under the current verified metric table.

## Evidence-Bounded Abstract Draft

Single-cell RNA-seq workflows often require subjective choices of highly variable genes, principal components, graph neighborhoods and clustering resolution. RMTGuard addresses this reproducibility problem by treating embedding construction as a random-matrix noise-control decision rather than a purely manual tuning step. The workflow estimates spectral noise boundaries, calibrates signal-PC calls, records diagnostic no-call states when low-signal data should not be forced into clusters, and exports reproducible AnnData-compatible embeddings and diagnostics. In synthetic stress tests, the pure-null benchmark retained one or fewer signal PCs and the rare-state benchmark reached ARI=0.9234648221808079. Across four public real datasets, the current benchmark supports breadth and annotation noninferiority, but it also preserves an explicit limitation: RMTGuard does not beat the strongest stability comparator on every dataset and PBMC68k/Zheng 2017 is reported as a diagnostic no-call rather than a positive discovery. As a public biological use case, the PDAC/TME workflow recovered immune and ductal-context marker structure with external validation in GSE263733. RMTGuard is therefore best framed as a reproducible, evidence-bounded genomics workflow for noise-controlled cell-state analysis, not as a universal clustering-superiority claim.

## Results Skeleton

1. RMTGuard defines a random-matrix noise-control contract for scRNA-seq embeddings.
2. Synthetic benchmarks support false-signal control and planted rare-state retention.
3. Public benchmarks establish callability-aware behavior, annotation noninferiority, and transparent diagnostic no-calls.
4. PDAC/TME public datasets provide a bounded immune/ductal-context application.
5. The reproducibility package, release audit, source data, Docker, CI, and DOI archive define the software-resource contribution.

## Figure Adaptation

- Figure 1: workflow and diagnostic contract.
- Figure 2: synthetic false-signal and rare-state tests.
- Figure 3: public benchmark with callability/no-call labels and all comparator caveats.
- Figure 4: PDAC/TME public use case.
- Figure 5: release audit, runtime, memory, and reproducibility manifest.

## Required Edits Before Use

- Complete public GitHub Release and Zenodo DOI.
- Replace any Nature Methods-only breakthrough language with reproducible genomics workflow language.
- Keep PBMC68k as a diagnostic no-call stress case.
- Keep PDAC/TME as a public use case, not a disease-mechanism discovery.
- Regenerate claim-evidence and compliance artifacts after release metadata is real.
