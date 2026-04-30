from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    for path in ROOT.rglob("__pycache__"):
        shutil.rmtree(path, ignore_errors=True)
    for path in ROOT.rglob("*.egg-info"):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
    for path in ROOT.rglob(".pytest_cache"):
        shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    main()
