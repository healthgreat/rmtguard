# Nature Methods Presubmission Inquiry Draft

Status: do not send until public GitHub/Zenodo release and gate wording are complete.
Acceptance guarantee: `impossible`.

Dear Editors,

We are preparing a Methods Article entitled "RMTGuard: random-matrix noise control for reproducible single-cell cell-state discovery".
RMTGuard is a random-matrix noise-control framework that turns scRNA-seq embedding construction into an auditable call/no-call decision rather than a manually tuned PCA-and-clustering workflow.

The manuscript's current evidence package supports three bounded claims.
The current evidence supports false-signal control in pure-null simulations, 3/3 diagnostic no-call validation scenarios, rare-state synthetic recovery (ARI 0.923), and four public real-data benchmarks.

We would present the real-data benchmark as callability-aware rather than as universal superiority over fixed-PC workflows.
The current real-data benchmark does not show broad superiority over the strongest stability comparator on every dataset, and PBMC68k/Zheng 2017 is retained as a diagnostic no-call rather than a positive discovery.

The biological application is a public PDAC/TME use case focused on immune and ductal-context marker structure, not a standalone disease-mechanism claim.

This inquiry draft is currently not ready to send because the public software release is incomplete.
Local release checks pass, but the public GitHub Release and Zenodo DOI are not complete.

Sincerely,

[Corresponding author]
