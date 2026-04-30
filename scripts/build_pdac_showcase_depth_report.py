from __future__ import annotations

"""Build a claim-bounded PDAC/TME biological showcase depth audit.

Author: RMTGuard development team
Date: 2026-04-30
Purpose: Convert the public PDAC/TME marker showcase into reviewer-facing
evidence rows with explicit allowed and forbidden manuscript claims.
Data source: results/pdac_tme/showcase_summary.tsv and cluster marker summaries
generated from GSE154778 and GSE263733.
Method notes: Marker signatures are descriptive cluster-level summaries, not
gene-level differential expression tests. If final analyses add gene-level
marker or pathway p-values, apply multiple-testing correction.
"""

import ast
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_TSV = ROOT / "results" / "pdac_tme" / "pdac_showcase_depth_audit.tsv"
OUT_MD = ROOT / "docs" / "pdac_tme_showcase_depth.md"
SHOWCASE = ROOT / "results" / "pdac_tme" / "showcase_summary.tsv"
PRIMARY_MARKERS = ROOT / "results" / "pdac_tme" / "pdac_gse154778_cluster_marker_summary.tsv"
VALIDATION_MARKERS = ROOT / "results" / "pdac_tme" / "pdac_gse263733_cluster_marker_summary.tsv"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["item_id", "status", "evidence", "allowed_claim", "forbidden_claim", "notes"],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _as_bool(value: str) -> bool:
    return str(value).strip().lower() == "true"


def _as_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _as_signature_list(value: str) -> list[str]:
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return []
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return []


def _signature_clusters(rows: list[dict[str, str]], signature: str, min_cells: int = 20) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if row.get("top_signature") == signature and int(float(row.get("n_cells", "0") or 0)) >= min_cells
    ]


def build_rows(
    showcase_rows: list[dict[str, str]],
    primary_marker_rows: list[dict[str, str]],
    validation_marker_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    primary = next((row for row in showcase_rows if row.get("dataset_id") == "pdac_gse154778"), {})
    validation = next((row for row in showcase_rows if row.get("dataset_id") == "pdac_gse263733"), {})
    primary_signatures = set(_as_signature_list(primary.get("top_signatures", "")))
    validation_signatures = set(_as_signature_list(validation.get("top_signatures", "")))
    shared = sorted(primary_signatures & validation_signatures)
    validation_ari = _as_float(validation.get("label_ari", "nan"))
    validation_nmi = _as_float(validation.get("label_nmi", "nan"))
    ductal_clusters = _signature_clusters(validation_marker_rows, "ductal_malignant_context")
    immune_clusters = _signature_clusters(validation_marker_rows, "immune_myeloid")
    caf_present = _as_bool(primary.get("has_caf_or_fibroblast_cluster", "")) or _as_bool(validation.get("has_caf_or_fibroblast_cluster", ""))

    return [
        {
            "item_id": "primary_marker_structure",
            "status": "pass" if {"ductal_malignant_context", "immune_myeloid"}.issubset(primary_signatures) else "fail",
            "evidence": f"GSE154778 top signatures: {sorted(primary_signatures)}.",
            "allowed_claim": "GSE154778 shows coarse immune and ductal-context marker structure under RMTGuard.",
            "forbidden_claim": "Do not claim a new PDAC disease mechanism from GSE154778 alone.",
            "notes": primary.get("limitation", ""),
        },
        {
            "item_id": "external_label_validation",
            "status": "pass" if validation_ari >= 0.30 and validation_nmi >= 0.30 else "fail",
            "evidence": f"GSE263733 public-label validation ARI={validation_ari:.3f}, NMI={validation_nmi:.3f}.",
            "allowed_claim": "External public labels support the coarse marker structure in GSE263733.",
            "forbidden_claim": "Do not treat label validation as clinical validation.",
            "notes": validation.get("limitation", ""),
        },
        {
            "item_id": "cross_dataset_signature_concordance",
            "status": "pass" if {"ductal_malignant_context", "immune_myeloid"}.issubset(shared) else "fail",
            "evidence": f"Shared top signatures between GSE154778 and GSE263733: {shared}.",
            "allowed_claim": "Ductal-context and immune-myeloid signatures appear in both public datasets.",
            "forbidden_claim": "Do not claim cross-cohort patient-level reproducibility without harmonized clinical covariates.",
            "notes": "Concordance is signature-level, not gene-level differential expression concordance.",
        },
        {
            "item_id": "validation_cluster_support",
            "status": "pass" if ductal_clusters and immune_clusters else "fail",
            "evidence": f"Validation ductal clusters={len(ductal_clusters)}, immune-myeloid clusters={len(immune_clusters)} with >=20 cells.",
            "allowed_claim": "GSE263733 contains cluster-level support for ductal-context and immune-myeloid signatures.",
            "forbidden_claim": "Do not claim all rare or stromal states are resolved.",
            "notes": "Tiny clusters are excluded from this support count.",
        },
        {
            "item_id": "caf_fibroblast_boundary",
            "status": "controlled_no_claim" if not caf_present else "needs_review",
            "evidence": f"has_caf_or_fibroblast_cluster={caf_present}.",
            "allowed_claim": "CAF/fibroblast signals are not a primary claim in the current showcase.",
            "forbidden_claim": "Do not describe a standalone CAF or fibroblast-state discovery.",
            "notes": "This boundary prevents overclaiming from the current marker-smoke output.",
        },
        {
            "item_id": "multiple_testing_boundary",
            "status": "controlled_boundary",
            "evidence": "Current PDAC report uses descriptive signature scores, not gene-level p-values.",
            "allowed_claim": "Use descriptive marker-signature language unless formal DE/pathway tests are added.",
            "forbidden_claim": "Do not report marker/pathway significance without FDR-adjusted tests.",
            "notes": "If final manuscript adds gene-level tests, report correction method and test universe.",
        },
    ]


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    failed = [row for row in rows if row["status"] in {"fail", "needs_review"}]
    lines = [
        "# PDAC/TME Showcase Depth Audit",
        "",
        "This file is generated by `python scripts/build_pdac_showcase_depth_report.py`.",
        "",
        "## Decision",
        "",
        f"- Current status: `{'active_risk' if failed else 'controlled_public_use_case'}`.",
        "- Manuscript role: public biological use case, not a disease-mechanism discovery.",
        "- Claim boundary: immune and ductal-context marker structure only.",
        "",
        "## Evidence Rows",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"### {row['item_id']}",
                "",
                f"- Status: `{row['status']}`",
                f"- Evidence: {row['evidence']}",
                f"- Allowed claim: {row['allowed_claim']}",
                f"- Forbidden claim: {row['forbidden_claim']}",
                f"- Notes: {row['notes']}",
                "",
            ]
        )
    return lines


def build_outputs() -> list[dict[str, str]]:
    rows = build_rows(_read_tsv(SHOWCASE), _read_tsv(PRIMARY_MARKERS), _read_tsv(VALIDATION_MARKERS))
    _write_tsv(OUT_TSV, rows)
    _write_text(OUT_MD, build_markdown(rows))
    return rows


def main() -> int:
    rows = build_outputs()
    failed = [row for row in rows if row["status"] in {"fail", "needs_review"}]
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print(f"status\t{'active_risk' if failed else 'controlled_public_use_case'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
