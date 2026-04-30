# Cover Letter Draft

Status: not submission-ready. Do not send this letter until `stability_advantage` and `software_release` are resolved.

Dear Editors,

We are preparing a Methods Article entitled "RMTGuard: random-matrix noise control for reproducible single-cell cell-state discovery". The manuscript presents a random-matrix-guided framework for reducing subjective choices in scRNA-seq cell-state analysis, including HVG selection, PC admission, graph construction, and clustering diagnostics.

The current evidence package supports the method's null-control and rare-state synthetic benchmarks, four public real-data benchmarks, and a PDAC/TME public showcase focused on immune and ductal-context marker structure. The software package includes a Scanpy/AnnData interface, benchmark runners, figure source-data generation, release manifests, CI tests, and draft reproducibility artifacts.

The strongest current synthetic claims are: Pure-null benchmark retained 1 signal PC(s), satisfying the pre-specified <=1 criterion. Rare-state synthetic ARI reached 0.9234648221808079.

Before this letter can be used for submission, the public GitHub Release and Zenodo DOI must be completed. The benchmark language must also remain callability-aware: PBMC68k is a diagnostic no-call and PBMC3k remains slightly below fixed `n_pcs=30`, so the manuscript should not claim broad superiority over fixed-PC baselines.

Sincerely,

[Corresponding author]
