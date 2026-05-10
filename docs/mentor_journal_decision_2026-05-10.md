# Mentor Journal Decision For RMTGuard

Generated: 2026-05-10 22:08:00 +08:00

## Decision

The project should continue as a high-risk `Nature Methods` methods-paper route,
but only as a claim-bounded random-matrix noise-control and callability
framework. Do not submit a full manuscript yet.

The next submission action should be a tightly written Nature Methods
presubmission inquiry after Figure 4 wording and source-data tables are frozen.
If the editor is not interested, the paper should be reframed immediately for a
Genome Biology-style genomics workflow/software article.

## Primary Target

Primary target: `Nature Methods`.

Article framing:

> Random-matrix noise control makes single-cell cell-state discovery more
> transparent by separating supported structure from high-dimensional noise and
> reporting no-call boundaries.

Allowed claim:

- RMTGuard provides a reproducible, release-audited framework for
  random-matrix-guided signal detection, adaptive embedding, callability, and
  diagnostic reporting in scRNA-seq cell-state discovery.

Disallowed claim:

- RMTGuard broadly outperforms Seurat, Scanpy, fixed-PC, or elbow baselines on
  clustering stability or annotation recovery.

## Journal Routing

| Rank | Journal | Decision | Reason |
| --- | --- | --- | --- |
| 1 | Nature Methods | Primary high-risk target | It explicitly publishes novel methods, method comparisons, and tools with strong validation and biological application. Current package is closest to this scope but still needs final claim discipline. |
| 2 | Genome Biology | Most realistic fallback | Best fit if editors view the method as incremental but value open software, benchmark breadth, and reproducible genomics workflow. It is not a strict 20-50 JIF target by current local metrics. |
| 3 | Cell Genomics | Conditional backup | Use only if genomics/cancer single-cell application is strengthened and the method story is made more genomics-facing. |
| 4 | Nature Communications | Conditional transfer candidate | Use only if the biological use case becomes broader and clearer; current method-only story is weaker for this journal. |
| 5 | Bioinformatics / NAR Genomics and Bioinformatics | Safe fallback | Use if high-impact route fails or if reviewers consider the contribution a solid but incremental software/workflow tool. |

Do not target Nature Biotechnology now. Its impact range is attractive, but the
project does not yet provide a biotechnology platform, technology adoption
story, or translational engineering advance that would fit the journal better
than Nature Methods.

## Evidence Basis

Current local state:

- 20-50 JIF readiness score: `89/100`.
- Strict 20-50 route status: `not ready`.
- Public repository and release artifacts are controlled by the local
  release-readiness reports; code-availability wording must follow those
  reports exactly.
- Calibration and rare-state power evidence reached 50-repeat depth with
  limits.
- Component ablation reached current 20-repeat synthetic and labeled real-data
  layers.
- PDAC/TME now has FDR-controlled DE, rank-based Hallmark/Reactome pathway
  enrichment, atlas marker citation mapping, and Figure 4 pathway/atlas source
  data.

Active blockers:

- `stability_advantage`: the project still cannot honestly claim broad
  superiority over the strongest baselines.
- `PDAC_TME_author_route_confirmation_and_final_figure_wording`: Figure 4 is a
  bounded public-data use case, not a disease-mechanism discovery.
- `editorial_send_status` and `nature_methods_route`: final abstract, cover
  letter, reporting summary, source data, and go/no-go are not frozen.

## Final Strategic Rule

The paper should not fight the failed stability-superiority gate. The stronger
and more defensible story is:

> RMTGuard is a transparent statistical guardrail that tells analysts when the
> data support cell-state discovery and when they do not.

This is more publishable than claiming universal performance advantage.

## Two-Week Direction

1. Freeze PDAC/TME as bounded Figure 4 if authors agree.
2. Rewrite abstract, title, and Figure 3 legend around callability and
   noise-control, not superiority.
3. Build a callability map as the central real-data figure.
4. Generate final Figure 4 pathway/atlas panel using only
   manuscript-interpretable pathway hits.
5. Prepare a short Nature Methods presubmission inquiry.
6. If presubmission feedback is negative or no response is encouraging, switch
   to Genome Biology without reopening the entire benchmark layer.

## Stop Conditions

Stop the Nature Methods route if:

- Any draft sentence claims broad stability superiority.
- Figure 4 wording implies PDAC mechanism, prognosis, therapy response, or
  clinical validation.
- The presubmission inquiry receives a clear scope/novelty rejection.
- The team is unwilling to present no-call behavior as a feature rather than a
  failure.

## Sources Checked

- Nature Methods Aims & Scope: https://www.nature.com/nmeth/aims
- Nature Methods metrics: https://www.nature.com/nmeth/journal-impact
- Genome Biology About: https://genomebiology.biomedcentral.com/about
- Nature Communications journal information: https://www.nature.com/ncomms/ncomms/journal-information
- Nature Biotechnology Aims & Scope: https://www.nature.com/nbt/aims
