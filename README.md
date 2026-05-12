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

The current high-impact competitor positioning memo is stored at
`docs/competitor_positioning_concord_sclens_2026-05-12.md`, with a
machine-readable matrix at `results/submission/competitor_positioning_matrix.tsv`.
It defines CONCORD as the recent high-impact SCI benchmark template and scLENS
as the closest random-matrix-like single-cell signal-detection competitor.
The resulting benchmark upgrade checklist is stored at
`docs/benchmark_upgrade_from_concord_sclens_2026-05-12.md`, with a
machine-readable action table at
`results/submission/benchmark_upgrade_from_concord_sclens.tsv`.
The first scLENS feasibility check is stored at
`docs/sclens_feasibility_check_2026-05-12.md`; the reproducible smoke runner is
`scripts/run_sclens_feasibility_smoke.py`, and its output table is
`results/submission/sclens_feasibility_smoke.tsv`. The h5ad adapter smoke test
is `benchmarks/run_sclens_h5ad_smoke.py`, with summary results at
`results/submission/sclens_h5ad_smoke_summary.tsv`. The 10-repeat scLENSpy
stability pilot is run by `benchmarks/run_sclens_stability_benchmark.py` and
reported in `docs/sclens_stability_pilot_2026-05-12.md`, with a direct
comparison table at `results/submission/sclens_vs_rmtguard_stability_pilot.tsv`.
The stronger `n_rand_matrix=20` direct comparator is reported in
`docs/sclens_stability_nrand20_2026-05-12.md`, with a machine-readable
comparison table at
`results/submission/sclens_vs_rmtguard_stability_nrand20.tsv`.
The CONCORD-style topology stress benchmark is run by
`benchmarks/run_topology_stress_benchmark.py` and reported at
`docs/topology_stress_benchmark_2026-05-12.md`, with source data at
`results/submission/topology_stress_summary.tsv` and figure drafts at
`figures/manuscript/figure_topology_stress.png`,
`figures/manuscript/figure_topology_stress.pdf`, and
`figures/manuscript/figure_topology_stress.tiff`.
The real public-data topology monitor is run by
`benchmarks/run_realdata_topology_benchmark.py` on Paul15 hematopoiesis and
reported at `docs/realdata_topology_benchmark_2026-05-12.md`, with source data
at `results/submission/realdata_topology_summary.tsv` and
`results/figures/source_data/figure_realdata_topology_source.tsv`, plus figure
assets at `figures/manuscript/figure_realdata_topology_benchmark.png`,
`figures/manuscript/figure_realdata_topology_benchmark.pdf`, and
`figures/manuscript/figure_realdata_topology_benchmark.tiff`. This monitor is
annotation-derived and must not be described as de novo trajectory discovery.
The current evidence-freeze checklist is generated by
`python scripts/build_current_evidence_freeze.py` and stored at
`docs/current_evidence_freeze_2026-05-12.md`, with a checksum manifest at
`results/submission/current_evidence_freeze_manifest.tsv`. It records which
figures, source-data tables, reports, claim boundaries, and remaining blockers
are currently safe to cite.
Freeze-aligned Results and figure-legend drafts are generated by
`python scripts/build_freeze_aligned_manuscript_text.py` and stored at
`manuscript/results_freeze_aligned_draft.md` and
`manuscript/figure_legends_freeze_aligned.md`, with a claim-control audit at
`results/submission/freeze_aligned_text_audit.tsv`.
The reviewer-facing Word handoff packet is generated by
`python scripts/build_external_review_docx.py` and stored at
`output/doc/RMTGuard_external_review_packet_2026-05-12.docx`.
The Nature Portfolio reporting-summary worksheet is generated by
`python scripts/build_reporting_summary_draft.py` and stored at
`docs/nature_reporting_summary_draft.md`, with a machine-readable table at
`results/submission/reporting_summary_draft.tsv`.
Figure-caption-source consistency is audited by
`python scripts/build_figure_caption_source_audit.py` and stored at
`docs/figure_caption_source_audit.md`, with a machine-readable table at
`results/submission/figure_caption_source_audit.tsv`.
Post-release DOI coverage is audited by
`python scripts/build_post_release_version_coverage_audit.py` and stored at
`docs/post_release_version_coverage_audit.md`, with machine-readable tables at
`results/submission/post_release_version_coverage_audit.tsv` and
`results/submission/post_release_changed_files.tsv`.
The future v0.1.1 release preflight is generated by
`python scripts/build_v0_1_1_release_preflight.py` and stored at
`docs/v0_1_1_release_preflight.md`, with a machine-readable table at
`results/submission/v0_1_1_release_preflight.tsv`. This is a no-action gate:
it does not create tags, GitHub Releases, or Zenodo records, and it should
continue to block release until author declarations, Figure 4 acknowledgement,
reporting-summary verification, claim integrity, final version coverage, and a
clean worktree are controlled.
The high-impact submission dashboard is generated by
`python scripts/build_high_impact_submission_dashboard.py` and stored at
`docs/high_impact_submission_dashboard.md`, with a machine-readable table at
`results/submission/high_impact_submission_dashboard.tsv`. It consolidates the
20-50 JIF gap assessment, author declaration packet, v0.1.1 preflight, Figure
audit, reporting-summary worksheet, claim lint/traceability, and Nature Methods
go/no-go status into one current mentor decision board.
The Figure 3 callability/no-call decision map is generated by
`make callability-decision-map`, reported at `docs/no_call_decision_map.md`,
stored as source data in `results/callability/no_call_decision_map.tsv` and
`results/figures/source_data/figure3_callability_decision_map.tsv`, and rendered
to `figures/manuscript/figure_no_call_decision_map.png`,
`figures/manuscript/figure_no_call_decision_map.pdf`, and
`figures/manuscript/figure_no_call_decision_map.tiff`.

The current bounded PDAC/TME Figure 4 wording freeze is stored at
`docs/figure4_pdac_tme_wording_freeze.md`, with the manuscript caption draft in
`manuscript/figure4_caption_bounded_draft.md`.

The strengthened PDAC/TME Figure 4 evidence board is stored at
`docs/pdac_tme_figure4_strengthening_board.md`, with a machine-readable table at
`results/submission/pdac_tme_figure4_strengthening_board.tsv` and panel
blueprint at `manuscript/figure4_strengthened_panel_blueprint.md`. It separates
what currently supports a bounded methods-paper biological application from
what would still be required for a PDAC mechanism, clinical, prognosis,
therapy-response, spatial, or protein-validation claim.
The strengthened source-data-driven Figure 4 draft is rendered by
`python scripts/render_figure4_strengthened.py` and written to
`figures/manuscript/figure4_pdac_tme_strengthened.png`,
`figures/manuscript/figure4_pdac_tme_strengthened.pdf`, and
`figures/manuscript/figure4_pdac_tme_strengthened.tiff`, with source data at
`results/figures/source_data/figure4_pdac_tme_strengthened_source.tsv`.
As of 2026-05-11, panel A uses compact labels and a separate bounded-claim note
so the public-data/no-mechanism limitation remains visible without behaving
like a crowded legend entry; panel F carries the no-superiority boundary through
its title and manuscript wording rather than an in-plot warning label.
The synchronized strengthened Figure 4 caption, Results draft, and claim audit
are generated by `python scripts/build_figure4_strengthened_text.py` and stored
at `manuscript/figure4_caption_strengthened_draft.md`,
`manuscript/results_figure4_strengthened_draft.md`, and
`docs/figure4_strengthened_text_audit.md`. These strengthened text drafts are
the current source for corresponding-author sign-off; the older bounded caption
draft is retained as provenance.

The current Nature Methods route-control decision is stored at
`docs/nature_methods_go_no_go_final.md`. Full submission is no-go; a
presubmission inquiry is conditionally allowed only after corresponding-author
acknowledgement of the bounded Figure 4 route.

The current Genome Biology fallback package is generated by
`python scripts/build_genome_biology_fallback_v2.py` and stored at
`docs/genome_biology_fallback_v2_packet.md`, with a machine-readable checklist
at `results/submission/genome_biology_fallback_v2_checklist.tsv`, abstract draft
at `manuscript/genome_biology_abstract_v2.md`, and cover-letter draft at
`manuscript/genome_biology_cover_letter_v2.md`. This route is a high-quality
fallback only; it is not a strict 20-50 JIF route under the current official
Genome Biology metrics.

The gated Nature Methods presubmission send packet is stored at
`manuscript/nature_methods_presubmission_send_packet.md`, with a machine-readable
gate table at `results/submission/nature_methods_presubmission_send_packet.tsv`,
a runbook at `docs/nature_methods_presubmission_send_runbook.md`, and a local
HOLD `.eml` draft at
`output/email/RMTGuard_nature_methods_presubmission_inquiry_HOLD.eml`. This
draft must not be sent while the packet reports a `hold_*` status, and the
official Nature Methods presubmission/submission route must be verified
immediately before any editor-facing send.
The presubmission inquiry itself is generated by
`python scripts/build_editorial_presubmission_packet.py` and now includes the
strengthened Figure 4 evidence details and source-file audit links while
preserving the `do not send` author-acknowledgement gate.

The official-source route verification checklist is stored at
`docs/nature_methods_official_route_verification.md`, with a machine-readable
copy at `results/submission/nature_methods_official_route_verification.tsv`.
It records the current official Nature Methods presubmission route, Article
fit, data/code availability, ethics, and AI-use checks, but still requires a
fresh manual website check immediately before sending.

The corresponding-author sign-off packet is stored at
`manuscript/corresponding_author_signoff_packet.md`, with a Word handoff copy
at `output/doc/RMTGuard_corresponding_author_signoff_packet.docx`.

The broader author-declaration confirmation packet is generated by
`python scripts/build_author_declaration_confirmation_packet.py` and stored at
`docs/author_declaration_confirmation_packet.md`, with a machine-readable
checklist at
`results/submission/author_declaration_confirmation_checklist.tsv` and a Word
handoff copy at
`output/doc/RMTGuard_author_declaration_confirmation_packet.docx`. It covers
postal code, CRediT roles, funding, competing interests, ethics/public-data
wording, Figure 4 bounded wording acknowledgement, reporting-summary
verification, and title-page metadata. It does not certify author approval;
written replies must still be saved under `metadata/author_reply_evidence/`.
The author-declaration email and chat drafts are generated by
`python scripts/build_author_declaration_email_packet.py` and stored at
`manuscript/author_declaration_confirmation_email_draft.md`,
`manuscript/author_declaration_confirmation_wechat_draft.md`,
`output/email/RMTGuard_author_declaration_confirmation_email.eml`, and
`docs/author_declaration_reply_intake_runbook.md`. These drafts are not sent by
the script and do not mark any author item as confirmed.

The email-ready sign-off draft is stored at
`manuscript/corresponding_author_signoff_email_draft.md`, with a local `.eml`
draft at `output/email/RMTGuard_corresponding_author_signoff_email.eml` and a
confirmation tracker at `metadata/corresponding_author_signoff_tracker.tsv`.
The current author status is recorded as an internal
`proxy_authorized_working_assumption` in
`docs/corresponding_author_proxy_assumption.md`; this permits drafting work but
does not unlock editor-facing submission.
After receiving replies, use
`scripts/record_corresponding_author_signoff.py`; the exact intake workflow is
documented in `docs/corresponding_author_reply_intake_runbook.md`.

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
non-clinical, hypothesis-generating use case. Bounded Figure 4 wording is
frozen in `docs/figure4_pdac_tme_wording_freeze.md`; formal corresponding-
author acknowledgement is still required before external presubmission use.

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
`results/release/release_audit_summary.txt`. The archived v0.1.0 public
release evidence is recorded; post-release working-branch changes should not
be treated as part of the immutable DOI snapshot unless a new release is made.

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
borderline. Public GitHub/Zenodo release evidence is present, but scientific
submission readiness remains gated separately.

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
