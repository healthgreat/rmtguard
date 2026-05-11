# Nature Methods Presubmission Inquiry Draft

Status: do not send; internal author-review draft until Figure 4 author acknowledgement and final go/no-go wording are complete.
Acceptance guarantee: `impossible`.
Figure 4 source: `manuscript/figure4_caption_strengthened_draft.md`; `results/submission/figure4_strengthened_text_audit.tsv`.

Dear Editors,

We are preparing a Methods Article entitled "RMTGuard: random-matrix noise control for reproducible single-cell cell-state discovery".
RMTGuard is a random-matrix noise-control framework that turns scRNA-seq embedding construction into an auditable call/no-call decision rather than a manually tuned PCA-and-clustering workflow.

The manuscript's current evidence package supports three bounded claims.
The current evidence supports false-signal control in pure-null simulations, 3/3 diagnostic no-call validation scenarios, rare-state synthetic recovery (ARI 0.923), and four public real-data benchmarks.

We would present the real-data benchmark as callability-aware rather than as universal superiority over fixed-PC workflows.
The current real-data benchmark does not show broad superiority over the strongest stability comparator on every dataset, and PBMC68k/Zheng 2017 is retained as a diagnostic no-call rather than a positive discovery.

The biological application is a bounded public PDAC/TME use case built around a strengthened Figure 4 evidence board. The current package includes 9802 positive cluster-marker rows at BH-FDR <=0.05 (3 tiny clusters skipped by the pre-specified rule), external-signature support for 5 public-label matches and 4 validation RMTGuard-cluster matches, shared marker families (ductal/malignant-context, immune-myeloid), 189 Hallmark and 1466 Reactome BH-FDR-significant pathway rows, 215 retained manuscript-interpretable pathway rows, and 7 published-atlas-marker overlap rows.
This PDAC/TME panel is not presented as a standalone disease-mechanism or clinical-validation claim. GSE154778 RMTGuard ARI=0.619 vs best baseline scanpy_default_like=0.793; GSE263733 RMTGuard ARI=0.704 vs best baseline scanpy_default_like=0.785.

The software-release evidence is recorded, but this inquiry remains an internal draft until the corresponding authors acknowledge the bounded Figure 4 route and the final Nature Methods go/no-go is completed.
Public repository, GitHub Release, and Zenodo DOI evidence are recorded for the archived v0.1.0 release.

Internal control files for the author-review draft include the strengthened Figure 4 Results draft and text audit:
- `manuscript/results_figure4_strengthened_draft.md`
- `results/submission/figure4_strengthened_text_audit.tsv`

Sincerely,

[Corresponding author]
