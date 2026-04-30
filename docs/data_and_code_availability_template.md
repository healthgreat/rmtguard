# Data and Code Availability Template

## Data Availability

All public datasets analyzed in this study are listed in
`metadata/datasets.tsv` with accessions, URLs, benchmark roles, and download
instructions. Raw data are obtained from the original public repositories. Large
processed benchmark outputs and figure source data will be archived with a DOI
through Zenodo, Figshare, GEO, CELLxGENE, or GitHub Releases when license and
size permit.

No private clinical data are used in the planned Nature Methods submission. If
controlled-access human data are added later, only accessions, approved access
procedures, and non-identifying aggregate outputs should be shared.

## Code Availability

The RMTGuard source code, benchmark scripts, environment files, tests, and
documentation are available at:

```text
https://github.com/your-lab/rmtguard
```

The exact manuscript version will be tagged as a GitHub Release and archived in
Zenodo to obtain a DOI. The release will include installation instructions, test
data, expected demo outputs, and commands needed to reproduce all benchmark
tables and figures.

## Reproducibility Commands

```bash
python -m pip install -e ".[scanpy,dev]"
python -m unittest discover -s tests
python examples/run_synthetic.py
python benchmarks/run_synthetic_benchmark.py
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
python scripts/build_release_readiness.py
python scripts/release_audit.py
```
