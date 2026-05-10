# RMTGuard

RMTGuard is a Random Matrix Theory guarded framework for reproducible
single-cell RNA-seq cell-state discovery. It is designed for a Nature
Methods-style methods manuscript: explicit high-dimensional noise control,
transparent diagnostics, public benchmarks, and reusable research software.

## Core Idea

After normalization and whitening, the null part of a high-dimensional
cell-by-gene matrix should have a covariance spectrum close to the
Marchenko-Pastur bulk. RMTGuard allows downstream analysis to use only structure
that exceeds this null model. The v3 implementation selects:

- HVG count by mean-binned normalized dispersion plus signal-plateau stability
  diagnostics
- signal PCs by MP edge plus Tracy-Widom proxy and optional permutation null
- adaptive near-edge embedding with RMT-gated PC admission
- kNN size by noise-PC perturbation stability
- cluster granularity by signal-adaptive graph modularity or stability
  diagnostics
- batch-aware spectra after simple batch mean residualization

## Quick Start

```bash
cd /path/to/RMTGuard
python -m pip install -e .
python examples/run_synthetic.py
python -m unittest discover -s tests
```

For figure rendering, install the optional plotting dependencies:

```bash
python -m pip install -e ".[figures]"
```

The demo writes:

```text
results/synthetic_rmtguard_summary.csv
```

## Minimal Python Use

```python
from rmtguard import RMTGuard, RMTGuardConfig

guard = RMTGuard(
    RMTGuardConfig(
        hvg_grid=(500, 1000, 2000),
        hvg_rule="spectral_stability",
        hvg_score="normalized_dispersion",
        embedding_rule="adaptive_near_edge",
        embedding_source="standard_pca",
        resolution_rule="graph_modularity",
        graph_resolution_grid=(1.0,),
        pc_rule="mp_tw",
        n_permutations=0,
        random_state=20260427,
    )
)
result = guard.fit(counts_matrix)

print(result.selected_hvg_n)
print(result.n_signal_pcs)
print(result.pc_diagnostics)
print(result.null_calibration)
```

## AnnData Use

```python
import scanpy as sc
from rmtguard import RMTGuardConfig
from rmtguard.scanpy_api import fit_anndata

adata = sc.read_h5ad("dataset.h5ad")
result = fit_anndata(
    adata,
    config=RMTGuardConfig(batch_key="sample_id", resolution_rule="graph_modularity"),
    layer="counts",
)

print(adata.obsm["X_rmtguard"].shape)
print(adata.obs["rmtguard_leiden"].head())
print(adata.uns["rmtguard"]["pc_diagnostics"])
```

If `leidenalg` is not installed, the Scanpy wrapper records a warning and keeps
KMeans fallback labels in `obs["rmtguard_leiden"]`.

## Benchmarks

```bash
python benchmarks/run_synthetic_benchmark.py
python scripts/prepare_phase1_datasets.py --dataset pbmc3k_10x --max-cells 1000
python scripts/prepare_phase1_datasets.py --dataset kang_ifnb_pbmc --max-cells 1000
python scripts/prepare_phase1_datasets.py --dataset baron_pancreas --max-cells 1000
python scripts/prepare_phase1_datasets.py --dataset pbmc68k_zheng2017 --max-cells 1000
python benchmarks/run_phase1_benchmark.py --datasets pbmc3k_10x kang_ifnb_pbmc baron_pancreas pbmc68k_zheng2017
python benchmarks/run_stability_benchmark.py --datasets pbmc3k_10x
python benchmarks/run_stability_benchmark.py --datasets pbmc3k_10x kang_ifnb_pbmc baron_pancreas pbmc68k_zheng2017 --methods rmtguard rmtguard_strict_signal scanpy_default_like fixed_pcs_30 fixed_pcs_50 elbow_rule parallel_analysis jackstraw_like
Rscript benchmarks/run_seurat_baseline.R --input data/processed/pbmc3k_10x.h5ad --dataset-id pbmc3k_10x
python scripts/prepare_pdac_datasets.py --dataset gse154778 --max-cells 1200
python scripts/prepare_pdac_datasets.py --dataset gse263733 --max-cells 1200
python benchmarks/run_pdac_showcase.py --h5ad data/processed/pdac_gse154778.h5ad --dataset-id pdac_gse154778
python benchmarks/run_pdac_showcase.py --h5ad data/processed/pdac_gse263733.h5ad --dataset-id pdac_gse263733
python scripts/build_pdac_showcase_depth_report.py
python scripts/run_pdac_tme_deep_validation.py
python scripts/run_pdac_tme_pathway_atlas_validation.py
python scripts/build_figure_source_data.py
python scripts/render_main_figures.py
python scripts/build_release_artifact_manifest.py
python scripts/build_release_asset_bundle.py
python scripts/build_external_release_plan.py
python scripts/build_github_staging_plan.py
python scripts/stage_github_release_files.py
python scripts/update_repository_metadata.py
python scripts/build_manuscript_evidence_package.py
python scripts/build_manuscript_draft_package.py
python scripts/build_publication_20_50_plan.py
python scripts/build_release_readiness.py
python benchmarks/run_h5ad_benchmark.py \
  --h5ad data/processed/example.h5ad \
  --dataset-id example \
  --batch-key sample_id
```

On Windows machines whose user path contains non-ASCII characters, set
`BASILISK_EXTERNAL_DIR` to an ASCII-only directory before running the optional
Seurat h5ad baseline, for example:

```bash
BASILISK_EXTERNAL_DIR=/mnt/d/BioSoft/basilisk-cache Rscript benchmarks/run_seurat_baseline.R --input data/processed/pbmc3k_10x.h5ad --dataset-id pbmc3k_10x
```

The planned public datasets are listed in:

```text
metadata/datasets.tsv
```

Large scRNA-seq matrices should not be committed directly to GitHub. GitHub
tracks source code, workflows, metadata, checksums, small fixtures, and download
scripts. Large raw/processed data should be referenced through GEO, CELLxGENE,
Zenodo, Figshare, GitHub Releases, or Git LFS when size and license permit.

## Current Journal Strategy

As of 2026-05-10, the high-impact route is claim-bounded:

> Random-matrix noise control makes single-cell cell-state discovery more
> transparent by separating supported structure from high-dimensional noise and
> reporting no-call boundaries.

Primary target remains `Nature Methods`, but the project should not claim broad
superiority over Seurat, Scanpy, fixed-PC, or elbow-rule baselines. If editors
view the contribution as incremental methods/software, the planned fallback is
Genome Biology-style genomics workflow/software framing.

The current mentor decision memo is stored at
`docs/mentor_journal_decision_2026-05-10.md`.

The Nature Methods package must include algorithm details, open-source code,
installation instructions, demo runtime, test data, public benchmarks, ablation
studies, release-readiness checks, and source-data tables. PDAC/TME public
datasets GSE154778 and GSE263733 are reserved as a bounded biological showcase
and external validation, not as a clinical mechanism claim.

## Submission Route

The project follows a strict journal decision route:

```text
Nature Methods first -> Genome Biology fallback -> Cell Genomics / Nature Communications / Bioinformatics
```

Nature Methods submission requires all gates in:

```text
metadata/submission_gates.tsv
```

to be marked as `pass` in a gate evidence table. Evaluate the current state with:

```bash
python scripts/evaluate_submission_gates.py
```

Use the fallback outline if software and benchmark evidence are complete but the
method-breakthrough or PDAC/TME showcase gates are only borderline.

After running benchmarks, create a working evidence table with:

```bash
python scripts/update_gate_evidence_from_results.py
python scripts/evaluate_submission_gates.py --evidence results/gates/gate_evidence.tsv
```

Current multi-dataset stability evidence is `fail`: v3.2 reaches the
predefined 0.80 floor on PBMC3k and exceeds Scanpy-like stability, wins on
Kang IFN-beta PBMC, and is close to fixed `n_pcs=30` on Baron pancreas, but
PBMC68k/Zheng 2017 falls below the 0.80 stability floor and underclusters.
Kang IFN-beta, Baron pancreas, and PBMC68k/Zheng 2017 cell-type recovery are
currently within the annotation noninferiority margin after using unsupervised
graph baselines, although PBMC68k remains weak in absolute ARI and is now
treated as both a label-granularity caveat and a stability failure mode. See
`docs/method_risk_log.md` and `docs/stability_gate_diagnostics.md`.

For manuscript-grade stability evidence across all Phase 1 public datasets,
run:

```bash
make stability-phase1
python scripts/build_stability_gate_report.py
```

The benchmark runner writes per-dataset checkpoint TSVs under
`results/stability_benchmarks/` and reuses completed checkpoints unless
`--force` is provided.

The current PDAC/TME showcase gate is
`pathway_atlas_supported_with_limits`: GSE154778 and GSE263733 now have
FDR-controlled marker DE, marker-set enrichment, external signature transfer,
rank-based MSigDB Hallmark/Reactome pathway enrichment, atlas marker citation
mapping, and Figure 4 source data in `docs/pdac_tme_deep_validation.md` and
`docs/pdac_tme_pathway_atlas_validation.md`. This remains a public-data,
non-clinical, hypothesis-generating use case. Final author route confirmation
and bounded Figure 4 wording/source-data freeze are still required before final
Nature Methods-style wording.

The current figure source-data gate is `pass`: `scripts/build_figure_source_data.py`
creates `results/figures/figure_reproducibility.tsv` and source-data tables for
Figures 1-5 under `results/figures/source_data/`. This is source-data readiness,
not completed journal-quality figure rendering.

Draft main figures can be regenerated with `scripts/render_main_figures.py`.
The script writes PNG/PDF drafts and a render manifest under
`figures/manuscript/`. These drafts are for manuscript assembly and design
review; they are not final Nature Methods production artwork.

Local release readiness can be summarized with
`scripts/build_release_readiness.py`, which writes
`results/release/release_readiness.tsv` and
`results/release/release_audit_summary.txt`. The software-release gate remains
`pending` until a real GitHub Release and Zenodo DOI exist.

Release file destinations can be audited with
`scripts/build_release_artifact_manifest.py`. It writes
`results/release/release_artifact_manifest.tsv`, separating GitHub repository
files from public accession downloads, processed matrices, DOI-archived result
tables, draft figures, and local-only development probes.

Release/Zenodo asset checksums can be generated with
`scripts/build_release_asset_bundle.py`. The default mode writes
`results/release/release_asset_manifest.tsv` and
`results/release/release_asset_summary.tsv`; use `--execute` only when you want
to create the local zip asset.

The GitHub initial-commit staging plan can be regenerated with
`scripts/build_github_staging_plan.py`. It writes
`results/release/github_staging_manifest.tsv`,
`results/release/github_staging_summary.tsv`, and the human-readable
`docs/github_staging_plan.md`; it does not run `git add`.
Run `scripts/stage_github_release_files.py` for a dry-run of the approved
staging set. Only `scripts/stage_github_release_files.py --execute` runs
`git add`.

Repository URLs can be previewed or updated with
`scripts/update_repository_metadata.py`. By default it only writes
`results/release/repository_metadata_update_plan.tsv`. Use
`--repo-url https://github.com/<owner>/rmtguard --execute` only after the real
GitHub repository exists.

The remaining external GitHub/Zenodo actions are summarized by
`scripts/build_external_release_plan.py`, which writes
`results/release/external_release_plan.tsv` and
`docs/external_release_plan.md`. It does not create remotes, commits, tags,
GitHub releases, or Zenodo records.

Manuscript claims and limitations can be regenerated with
`scripts/build_manuscript_evidence_package.py`. It writes
`results/manuscript/claim_evidence_matrix.tsv`,
`results/manuscript/nature_methods_submission_checklist.tsv`, and
`manuscript/submission_readiness.md`.

Guarded manuscript working drafts can be regenerated with
`scripts/build_manuscript_draft_package.py`. It writes
`manuscript/nature_methods_presubmission_draft.md`,
`manuscript/abstract_draft.md`, `manuscript/cover_letter_draft.md`,
`results/manuscript/reviewer_objection_matrix.tsv`, and
`results/manuscript/storyline_panel_map.tsv`. These files are explicitly not
submission-ready while the multi-dataset stability/no-call gate remains
borderline and the public GitHub/Zenodo release is pending.

The strict 20-50 JIF publication route can be regenerated with
`scripts/build_publication_20_50_plan.py`. It writes
`results/gates/publication_20_50_decision.tsv` and
`docs/publication_20_50_rescue_plan.md`. This file records the current boundary:
Nature Methods remains the realistic 20-50 target if gates pass; Genome Biology
is a fallback only if the strict 20-50 JIF requirement is relaxed.

## Statistical Assumptions

RMTGuard assumes that, after normalization and whitening or residualization, the
technical noise component is sufficiently close to a random-matrix null for the
MP bulk and finite-sample edge diagnostics to be informative. These diagnostics
are guardrails for exploratory analysis, not clinical decision tools. For real
patient-derived data, respect privacy, ethics, repository terms, and IRB
requirements.
