# Data Layout

This repository should not commit large raw scRNA-seq matrices directly to git.

## Tracked in GitHub

- `metadata/datasets.tsv`: dataset identifiers, accessions, URLs, checksums, and benchmark roles.
- `scripts/download_public_datasets.py`: deterministic download helper for URL-based public datasets.
- Tiny synthetic or fixture data only when needed for tests.

## Not Tracked Directly

- `data/raw/`: downloaded public raw data.
- `data/processed/`: normalized or converted matrices.
- `data/external/`: manually obtained public data.

For publication, large processed benchmark matrices should be archived in
Zenodo/Figshare/GEO/CELLxGENE or GitHub Releases/Git LFS when license and size
permit. The manuscript must cite accessions and persistent DOIs.
