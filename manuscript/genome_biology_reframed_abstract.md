# Genome Biology Reframed Abstract

Status: working draft; do not submit until public GitHub and Zenodo release gates pass.

Single-cell RNA-seq cell-state discovery depends on analyst choices about feature selection, dimensionality, neighborhood graphs and clustering resolution. Rather than claiming to remove these choices, RMTGuard exposes one specific source of uncertainty: whether principal components and downstream graph structure exceed a random-matrix noise boundary sufficiently to support a cell-state call.

RMTGuard implements a callability-aware workflow that combines random-matrix spectral diagnostics, strict signal-PC admission, near-edge embedding diagnostics, stability summaries and explicit no-call reporting for low-confidence matrices. The software exports AnnData-compatible embeddings and audit tables for feature, PC and clustering decisions so that analysts can distinguish callable structure from noise-controlled no-calls.

Current synthetic benchmarks support pure-null false-signal control and planted rare-state retention, while public real-data benchmarks show useful annotation recovery but do not support broad stability superiority over the strongest baseline on all datasets. The PBMC68k/Zheng 2017 stress case is therefore reported as a diagnostic no-call rather than a positive discovery. A PDAC/TME public-data showcase is retained as a bounded use case, not a standalone cancer-mechanism claim.

These results position RMTGuard as an evidence-bounded genomics workflow for transparent scRNA-seq callability diagnostics. External public-release placeholders must be replaced before any submission.
