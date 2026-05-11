# Genome Biology Abstract v2

Status: `working draft`; do not submit until exact-code archive and final author checks are complete.

Single-cell RNA-seq cell-state discovery depends on feature-selection,
dimensionality, neighborhood, and clustering decisions that are often difficult
to compare across analyses. RMTGuard addresses this problem by reframing
embedding construction as a callability decision: principal components and
downstream graph structure are admitted only when they pass random-matrix
noise-control diagnostics, and low-confidence cases are reported as diagnostic
no-calls rather than forced into biological clusters.

RMTGuard implements spectral noise diagnostics, calibrated signal-PC admission,
adaptive near-edge embedding, stability summaries, AnnData-compatible outputs,
and machine-readable audit tables for feature, PC, graph, and cluster decisions.
In realistic null simulations, false-call rates remained 0 across three
50-repeat null models. In the rare-state grid, power was high in several
prevalence/effect-size settings but explicitly limited at the lowest
prevalence and effect sizes. Across four public real datasets, the benchmark
supports a callability-aware workflow but does not support universal stability
superiority over the strongest comparator; PBMC68k/Zheng 2017 is therefore
reported as a diagnostic no-call stress case.

A bounded PDAC/TME public-data application illustrates how callable clusters can
be connected to marker, external-signature, pathway, and atlas-marker evidence
without making a clinical or disease-mechanism claim. The current package
includes 9802 BH-FDR marker rows; external signature support 5 public-label matches and 4 RMTGuard-cluster matches; 189 Hallmark, 1466 Reactome, and 7 atlas-overlap rows. RMTGuard is thus positioned as an open,
evidence-bounded genomics workflow for transparent scRNA-seq callability
diagnostics.
