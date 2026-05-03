#!/usr/bin/env python
"""Audit publication figure and table assets.

Author: RMTGuard development team
Date: 2026-05-01
Purpose: Verify that rendered figures and manuscript tables are complete,
nonblank, and packaged in publication-facing formats.
Data source: figures/manuscript/rendered_figure_manifest.tsv and
results/tables/manuscript/publication_table_manifest.tsv.
Method notes: This is a presentation/reproducibility audit only. It does not
change benchmark values or scientific claims.
"""

from __future__ import annotations

import csv
import zipfile
from pathlib import Path

import fitz
import pandas as pd
from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[1]
FIGURE_MANIFEST = ROOT / "figures" / "manuscript" / "rendered_figure_manifest.tsv"
SUPPLEMENTAL_FIGURE_MANIFESTS = [
    ROOT / "figures" / "manuscript" / "realdata_ablation_figure_manifest.tsv",
]
TABLE_MANIFEST = (
    ROOT / "results" / "tables" / "manuscript" / "publication_table_manifest.tsv"
)
SUPPLEMENTAL_TABLE_MANIFESTS = [
    ROOT
    / "results"
    / "tables"
    / "manuscript"
    / "realdata_ablation_table_manifest.tsv",
]
OUT_TSV = ROOT / "results" / "submission" / "publication_visual_asset_audit.tsv"
DOC = ROOT / "docs" / "publication_visual_asset_audit.md"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _atomic_write_tsv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, sep="\t", index=False, quoting=csv.QUOTE_MINIMAL)
    tmp.replace(path)


def _atomic_write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _audit_image(
    path: Path, min_width: int = 1800, min_height: int = 1200
) -> dict[str, object]:
    if not path.exists():
        return {"status": "fail", "detail": "missing", "width": "", "height": ""}
    with Image.open(path) as image:
        width, height = image.size
        stat = ImageStat.Stat(image.convert("L"))
    stddev = float(stat.stddev[0])
    failures: list[str] = []
    if width < min_width:
        failures.append(f"width<{min_width}")
    if height < min_height:
        failures.append(f"height<{min_height}")
    if stddev < 2.0:
        failures.append("near_blank")
    return {
        "status": "fail" if failures else "pass",
        "detail": ";".join(failures) if failures else "image readable and nonblank",
        "width": width,
        "height": height,
        "stddev": f"{stddev:.3f}",
    }


def _audit_pdf(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"status": "fail", "detail": "missing", "page_count": ""}
    with fitz.open(path) as pdf:
        page_count = pdf.page_count
    return {
        "status": "pass" if page_count >= 1 else "fail",
        "detail": "PDF readable" if page_count >= 1 else "empty PDF",
        "page_count": page_count,
    }


def _audit_docx(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"status": "fail", "detail": "missing"}
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile:
        return {"status": "fail", "detail": "invalid docx zip"}
    required = {"word/document.xml", "[Content_Types].xml"}
    missing = sorted(required - names)
    return {
        "status": "fail" if missing else "pass",
        "detail": (
            f"missing {','.join(missing)}" if missing else "DOCX package readable"
        ),
    }


def _audit_tsv(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"status": "fail", "detail": "missing", "rows": ""}
    try:
        df = pd.read_csv(path, sep="\t")
    except Exception as exc:  # pragma: no cover - diagnostic branch
        return {"status": "fail", "detail": f"unreadable TSV: {exc}", "rows": ""}
    return {
        "status": "pass" if len(df) > 0 else "fail",
        "detail": "TSV readable" if len(df) > 0 else "empty TSV",
        "rows": len(df),
    }


def audit_figures() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for manifest_path in [FIGURE_MANIFEST, *SUPPLEMENTAL_FIGURE_MANIFESTS]:
        if not manifest_path.exists():
            continue
        manifest = pd.read_csv(manifest_path, sep="\t")
        for _, item in manifest.iterrows():
            asset_id = item.get("figure_id", manifest_path.stem)
            for field, artifact_type in [
                ("png_path", "figure_png"),
                ("pdf_path", "figure_pdf"),
                ("tiff_path", "figure_tiff"),
            ]:
                path_text = str(item.get(field, "")).strip()
                if not path_text or path_text.lower() == "nan":
                    continue
                path = ROOT / path_text
                if artifact_type == "figure_pdf":
                    audit = _audit_pdf(path)
                else:
                    audit = _audit_image(path)
                rows.append(
                    {
                        "asset_group": "figures",
                        "asset_id": asset_id,
                        "asset_type": artifact_type,
                        "path": _rel(path),
                        **audit,
                    }
                )
    return rows


def audit_tables() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for manifest_path in [TABLE_MANIFEST, *SUPPLEMENTAL_TABLE_MANIFESTS]:
        if not manifest_path.exists():
            continue
        manifest = pd.read_csv(manifest_path, sep="\t")
        for _, item in manifest.iterrows():
            path_text = str(item.get("path", "")).strip()
            if not path_text or path_text.lower() == "nan":
                continue
            path = ROOT / path_text
            suffix = path.suffix.lower()
            if suffix == ".docx":
                audit = _audit_docx(path)
                asset_type = "table_docx"
            elif suffix == ".tsv":
                audit = _audit_tsv(path)
                asset_type = "table_tsv"
            else:
                audit = {"status": "fail", "detail": f"unexpected suffix {suffix}"}
                asset_type = "table_unknown"
            rows.append(
                {
                    "asset_group": "tables",
                    "asset_id": item.get("artifact", manifest_path.stem),
                    "asset_type": asset_type,
                    "path": _rel(path),
                    **audit,
                }
            )
    return rows


def build_doc(df: pd.DataFrame) -> str:
    failures = df[df["status"] != "pass"]
    lines = [
        "# Publication visual asset audit",
        "",
        "This audit checks that the manuscript figure and table artifacts exist and are readable in publication-facing formats.",
        "",
        f"- Total audited assets: {len(df)}",
        f"- Passing assets: {(df['status'] == 'pass').sum()}",
        f"- Failing assets: {len(failures)}",
        "",
        "## Audit Table",
        "",
        "| Asset group | Asset | Type | Status | Detail | Path |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in df.itertuples(index=False):
        lines.append(
            f"| {row.asset_group} | {row.asset_id} | {row.asset_type} | {row.status} | {row.detail} | `{row.path}` |"
        )
    return "\n".join(lines)


def main() -> int:
    rows = audit_figures() + audit_tables()
    df = pd.DataFrame(rows).fillna("")
    _atomic_write_tsv(df, OUT_TSV)
    _atomic_write_text(build_doc(df), DOC)
    print(_rel(OUT_TSV))
    print(_rel(DOC))
    failures = df[df["status"] != "pass"]
    if not failures.empty:
        print(f"failures\t{len(failures)}")
        return 1
    print("failures\t0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
