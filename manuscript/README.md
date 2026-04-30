# Manuscript Working Notes

## Proposed title

RMTGuard: random-matrix noise control for reproducible single-cell cell-state
discovery

## Main figures

The fixed five-figure plan is in `manuscript/figure_plan.md`.

1. Algorithm overview and MP/TW/permutation decision rule.
2. Synthetic null, rare state, batch, dropout, trajectory, and overclustering.
3. Public benchmark against Scanpy, Seurat, fixed PCs, elbow, and permutation PCA.
4. PDAC/TME showcase using GSE154778 and GSE263733.
5. Runtime, memory, ablation, reproducibility, and release audit.

## Journal route

Prepare the Nature Methods version first. If strict submission gates are not all
passed but software and benchmark evidence are complete, use
`manuscript/genome_biology_fallback_outline.md`.

## Required before submission

- Freeze dataset manifest.
- Archive manuscript code release with DOI.
- Archive processed benchmark outputs and figure source data with DOI.
- Complete data/code availability statements.
- Add an ethics/privacy statement for any human clinical metadata.
- Mark all Nature Methods gates in `metadata/submission_gates.tsv` as `pass`.

## Current readiness note

Regenerate the manuscript claim boundary with:

```bash
python scripts/build_manuscript_evidence_package.py
```

The human-readable status is written to `manuscript/submission_readiness.md`.

Regenerate the guarded manuscript draft package with:

```bash
python scripts/build_manuscript_draft_package.py
```

This writes `manuscript/nature_methods_presubmission_draft.md`,
`manuscript/abstract_draft.md`, `manuscript/cover_letter_draft.md`,
`results/manuscript/reviewer_objection_matrix.tsv`, and
`results/manuscript/storyline_panel_map.tsv`. These are working drafts and
risk-control tables; they are explicitly not submission-ready while PBMC3k
stability is borderline and the public GitHub/Zenodo release is pending.
