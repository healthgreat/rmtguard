# GitHub Release Checklist

## Before creating the public repository

- Confirm this repository contains only RMTGuard files, not unrelated projects
  such as `SheafSignal/`.
- Run `python scripts/clean_artifacts.py`.
- Run `python scripts/build_figure_source_data.py` after benchmark and gate
  tables are current.
- Run `python scripts/render_main_figures.py` to regenerate draft PNG/PDF
  figures from the source-data tables.
- Run `python scripts/build_release_artifact_manifest.py` to separate GitHub
  files, accession-only data, DOI-archived results, and local-only probe
  outputs.
- Run `python scripts/build_release_asset_bundle.py` to write the release asset
  checksum manifest. Use `--execute` only when creating the local zip for
  GitHub Release or Zenodo upload.
- Run `python scripts/build_external_release_plan.py` to create the command
  level external GitHub/Zenodo release plan.
- Run `python scripts/build_github_staging_plan.py` to generate the initial
  commit include/exclude plan before any `git add`.
- Run `python scripts/stage_github_release_files.py` for a dry-run of the exact
  files that would be staged. Use `--execute` only after reviewing
  `docs/github_staging_plan.md`.
- Run `python scripts/update_repository_metadata.py` to write the repository
  URL replacement plan. Use `--repo-url https://github.com/healthgreat/rmtguard
  --execute` for the current public repository.
- Run `python scripts/build_manuscript_evidence_package.py` to refresh the
  claim-evidence matrix and submission readiness note.
- Run `python scripts/build_release_readiness.py` to write the local release
  readiness summary and confirm that external GitHub/Zenodo items remain
  explicit.
- Run `python scripts/release_audit.py`.
- Confirm no raw private or controlled-access clinical data are present.
- Confirm `metadata/datasets.tsv` lists every benchmark dataset and its access
  conditions.

## First GitHub push

```bash
git init
git add .
git commit -m "Initial RMTGuard research software release"
git branch -M main
git remote add origin https://github.com/healthgreat/rmtguard.git
git push -u origin main
```

## Release for manuscript submission

```bash
git tag -a v0.1.0 -m "RMTGuard manuscript analysis release"
git push origin v0.1.0
```

After pushing the tag, create a GitHub Release and archive the release with
Zenodo to obtain a DOI. Put the DOI in the manuscript Code Availability
statement.

## Data release

- Small fixture data can stay in GitHub.
- Large public benchmark data should be downloaded from public accessions using
  scripts and checksums.
- Processed figure source data should be archived with a persistent DOI.
- Never upload identifiable patient-level data to GitHub.
