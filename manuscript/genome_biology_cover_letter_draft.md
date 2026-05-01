# Genome Biology Cover Letter Draft

Status: `prepare_after_release`; public release status: `blocked_external`.
Do not send this draft until all placeholders are replaced and the current journal instructions are verified.

Dear Editors,

We submit RMTGuard, a callability-aware random-matrix workflow for reproducible single-cell RNA-seq state discovery, for consideration as a genomics software and benchmark manuscript.

Single-cell RNA-seq analyses often depend on subjective choices of highly variable genes, principal components, graph neighborhoods and clustering resolution. RMTGuard addresses this reproducibility problem by exposing the spectral noise boundary as an explicit analysis decision, reporting diagnostic no-call states when low-signal data should not be forced into biological clusters, and exporting AnnData-compatible embeddings, diagnostics and benchmark metadata.

The manuscript is intentionally evidence-bounded. Synthetic benchmarks support false-signal control under pure-null simulations and rare-state retention, while public real-data benchmarks show annotation noninferiority and transparent callability limits rather than universal superiority over fixed-PC baselines. PBMC68k/Zheng 2017 is reported as a diagnostic no-call stress case, not as a positive cell-state discovery. A public PDAC/TME showcase provides a bounded immune and ductal-context application with external validation, without claiming a standalone clinical or disease-mechanism discovery.

The accompanying reproducibility package includes source code, tests, public data-accession workflow scripts, figure source data and release manifests. Public repository and archive information should be inserted here before submission: [TO CONFIRM: public GitHub URL]; [TO CONFIRM: Zenodo DOI].

We believe this evidence-bounded framing is appropriate for readers who need reproducible single-cell workflows that distinguish robust signal, low-confidence no-calls and overstated clustering claims.

Sincerely,

[TO CONFIRM: corresponding author name and affiliation]
