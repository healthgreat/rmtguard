from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from prepare_phase1_datasets import _download


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "metadata" / "datasets.tsv"
RAW_DIR = ROOT / "data" / "raw"


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            dataset_id = row["dataset_id"]
            url = row["url"].strip()
            if not url.startswith("http"):
                print(f"skip {dataset_id}: accession-only or manual download")
                continue

            out = RAW_DIR / f"{dataset_id}{Path(url).suffix or '.download'}"
            if out.exists():
                print(f"exists {dataset_id}: {out}")
            else:
                print(f"download {dataset_id}: {url}")
                _download(url, out)

            observed = sha256sum(out)
            expected = row.get("sha256", "").strip()
            if expected and expected.lower() != observed.lower():
                raise RuntimeError(f"checksum mismatch for {dataset_id}: {observed} != {expected}")
            print(f"sha256 {dataset_id}: {observed}")


if __name__ == "__main__":
    main()
