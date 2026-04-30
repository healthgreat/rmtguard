from __future__ import annotations

"""Build a draft Nature Portfolio reporting-summary worksheet.

Author: RMTGuard development team
Date: 2026-04-30
Purpose: Pre-fill reporting-summary content from local RMTGuard evidence for
manual author verification during Nature Methods submission.
Data source: Dataset manifest, claim-evidence matrix, release readiness, and
compliance audit tables.
Method notes: This is not the official Nature Portfolio form. It is a
traceable worksheet to reduce manual omission risk.
"""

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_TSV = ROOT / "results" / "submission" / "reporting_summary_draft.tsv"
OUT_MD = ROOT / "docs" / "nature_reporting_summary_draft.md"

DATASETS = ROOT / "metadata" / "datasets.tsv"
CLAIMS = ROOT / "results" / "manuscript" / "claim_evidence_matrix.tsv"
RELEASE = ROOT / "results" / "release" / "release_readiness.tsv"
COMPLIANCE = ROOT / "results" / "submission" / "nature_methods_compliance_audit.tsv"
GATES = ROOT / "results" / "gates" / "gate_evidence.tsv"


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


def _write_tsv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _status_map(rows: list[dict[str, str]], key: str) -> dict[str, str]:
    return {row.get(key, ""): row.get("status", "pending") for row in rows if row.get(key)}


def _dataset_ids(rows: list[dict[str, str]]) -> str:
    return ", ".join(row.get("dataset_id", "") for row in rows if row.get("dataset_id"))


def _accessions(rows: list[dict[str, str]]) -> str:
    values = []
    for row in rows:
        accession = row.get("accession", "")
        if accession and accession != "NA":
            values.append(accession)
    return ", ".join(values)


def _claim_text(rows: list[dict[str, str]], claim_id: str) -> str:
    row = next((item for item in rows if item.get("claim_id") == claim_id), {})
    return row.get("allowed_wording", "")


def _row(
    section: str,
    item: str,
    draft_response: str,
    evidence_path: Path | str,
    status: str,
    author_action_required: str,
    notes: str,
) -> dict[str, str]:
    evidence = _rel(evidence_path) if isinstance(evidence_path, Path) else evidence_path
    return {
        "section": section,
        "item": item,
        "draft_response": draft_response,
        "evidence_path": evidence,
        "status": status,
        "author_action_required": author_action_required,
        "notes": notes,
    }


def build_rows(
    dataset_rows: list[dict[str, str]],
    claim_rows: list[dict[str, str]],
    release_rows: list[dict[str, str]],
    compliance_rows: list[dict[str, str]],
    gate_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    release = _status_map(release_rows, "check_id")
    compliance = _status_map(compliance_rows, "check_id")
    gates = _status_map(gate_rows, "gate_id")
    public_data = bool(dataset_rows)
    repo_pending = release.get("repository_url") != "pass"
    doi_pending = release.get("zenodo_doi") != "pass"

    rows = [
        _row(
            "Data",
            "Public dataset sources",
            f"All datasets are public scRNA-seq datasets listed in metadata/datasets.tsv: {_dataset_ids(dataset_rows)}.",
            DATASETS,
            "ready_for_author_check" if public_data else "blocked",
            "Verify every accession and URL before submission.",
            f"Accessions listed: {_accessions(dataset_rows) or 'some sources use URLs rather than accession IDs'}.",
        ),
        _row(
            "Data",
            "Human data privacy and ethics",
            "No private clinical data are used in the current manuscript package; all main evidence is derived from public datasets.",
            DATASETS,
            "ready_for_author_check",
            "Confirm no controlled-access or identifiable patient-level data were added outside this repository.",
            "This is an analysis/privacy statement, not an IRB determination.",
        ),
        _row(
            "Data",
            "Data exclusion and preprocessing",
            "Large raw and processed matrices are excluded from GitHub; datasets are regenerated from public accessions and scripts. QC/filtering, normalization, HVG selection, RMT spectrum diagnostics, and benchmark outputs are recorded in scripts and result manifests.",
            "scripts/prepare_phase1_datasets.py; benchmarks/run_phase1_benchmark.py; metadata/datasets.tsv",
            "ready_for_author_check",
            "Confirm the Methods section lists final QC thresholds and any dataset-specific exclusions.",
            "Do not leave QC decisions implicit in the reporting summary.",
        ),
        _row(
            "Statistics",
            "Randomization and blinding",
            "This is a computational methods study using public datasets and simulations. Experimental randomization/blinding is not applicable; computational randomness is controlled with explicit random_state values and repeated subsampling benchmarks.",
            GATES,
            "ready_for_author_check",
            "Confirm this wording fits the official form's available options.",
            "For benchmark comparisons, report seed/repeat settings rather than experimental blinding.",
        ),
        _row(
            "Statistics",
            "Sample size and replication",
            "No prospective sample-size calculation was performed. The method is evaluated by simulations, repeated subsampling stability, four Phase 1 public real datasets, and a PDAC/TME external validation dataset.",
            GATES,
            "ready_for_author_check",
            "Confirm final manuscript still uses the same benchmark set.",
            "This supports computational reproducibility, not prospective clinical power.",
        ),
        _row(
            "Statistics",
            "Multiple testing and uncertainty",
            "The primary benchmarks use pre-specified gate thresholds for false signal PCs, rare-state ARI, stability/no-call behavior, annotation noninferiority, and PDAC/TME interpretability. If gene-level marker or pathway tests are added to the final manuscript, report the p-value adjustment method explicitly.",
            CLAIMS,
            "needs_author_completion",
            "Add final marker/pathway multiple-testing details if those analyses enter the main text.",
            "Current method gates are threshold-based; marker/pathway testing may need FDR control.",
        ),
        _row(
            "Method validation",
            "Noise-control and rare-state claims",
            _claim_text(claim_rows, "noise_control_null") + " " + _claim_text(claim_rows, "rare_state_retention"),
            CLAIMS,
            "ready_for_author_check" if gates.get("synthetic_null_false_signal") == "pass" else "blocked",
            "Confirm exact benchmark numbers match final figures.",
            "Avoid exact type-I calibration claims beyond tested simulations.",
        ),
        _row(
            "Method validation",
            "Callability and no-call boundary",
            _claim_text(claim_rows, "pbmc3k_stability"),
            CLAIMS,
            "ready_for_author_check" if gates.get("stability_advantage") == "pass" else "blocked",
            "Keep PBMC68k as diagnostic no-call in text and reviewer responses.",
            "This is the key overclaim-control statement.",
        ),
        _row(
            "Biological application",
            "PDAC/TME public showcase",
            _claim_text(claim_rows, "pdac_tme_showcase"),
            CLAIMS,
            "ready_for_author_check" if gates.get("pdac_tme_interpretability") == "pass" else "blocked",
            "Confirm final text does not claim standalone CAF/fibroblast discovery.",
            "Use as public application evidence, not clinical decision support.",
        ),
        _row(
            "Software",
            "Code availability",
            "Local code, tests, CI, Dockerfile, release manifests, and source bundle are prepared. Public GitHub repository and GitHub Release are still pending until a real repository URL is provided.",
            RELEASE,
            "blocked" if repo_pending else "ready_for_author_check",
            "Create public GitHub repository, push tag, and replace placeholder URLs.",
            "Do not mark this complete before repository_url and github_remote pass.",
        ),
        _row(
            "Software",
            "Code DOI",
            "Zenodo DOI is pending until the GitHub Release is archived and the DOI is recorded in .zenodo.json, CITATION.cff, and Code Availability text.",
            RELEASE,
            "blocked" if doi_pending else "ready_for_author_check",
            "Archive the GitHub Release with Zenodo and run finalize_submission_release.py.",
            "This remains the hard Nature Portfolio code-release blocker.",
        ),
        _row(
            "Reporting summary",
            "Official form status",
            "This draft pre-fills reporting-summary content, but the official Nature Portfolio reporting summary must be completed and verified by the corresponding author.",
            COMPLIANCE,
            "pending_manual" if compliance.get("reporting_summary") == "pending_manual" else "ready_for_author_check",
            "Transfer verified answers into the official submission system.",
            "Codex can assist but cannot truthfully certify the official form without author review.",
        ),
    ]
    return rows


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    blocked = [row for row in rows if row["status"] == "blocked"]
    manual = [row for row in rows if row["status"] in {"pending_manual", "needs_author_completion"}]
    lines = [
        "# Nature Reporting Summary Draft",
        "",
        "This file is generated by `python scripts/build_reporting_summary_draft.py`.",
        "",
        "## Boundary",
        "",
        "This is a draft worksheet, not the official Nature Portfolio reporting summary form. The corresponding author must verify and transfer the final answers during submission.",
        "",
        "## Status",
        "",
        f"- Blocked rows: `{len(blocked)}`.",
        f"- Manual/author-completion rows: `{len(manual)}`.",
        "- Acceptance guarantee: `impossible`; this worksheet only reduces reporting omission risk.",
        "",
        "## Blocked Rows",
        "",
    ]
    if blocked:
        lines.extend(f"- `{row['section']} / {row['item']}`: {row['author_action_required']}" for row in blocked)
    else:
        lines.append("- none")
    lines.extend(["", "## Draft Responses", ""])
    for row in rows:
        lines.extend(
            [
                f"### {row['section']} - {row['item']}",
                "",
                f"- Status: `{row['status']}`",
                f"- Draft response: {row['draft_response']}",
                f"- Evidence: `{row['evidence_path']}`",
                f"- Author action required: {row['author_action_required']}",
                f"- Notes: {row['notes']}",
                "",
            ]
        )
    return lines


def build_outputs() -> list[dict[str, str]]:
    rows = build_rows(_read_tsv(DATASETS), _read_tsv(CLAIMS), _read_tsv(RELEASE), _read_tsv(COMPLIANCE), _read_tsv(GATES))
    _write_tsv(
        OUT_TSV,
        rows,
        ["section", "item", "draft_response", "evidence_path", "status", "author_action_required", "notes"],
    )
    _write_text(OUT_MD, build_markdown(rows))
    return rows


def main() -> int:
    rows = build_outputs()
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print(f"blocked\t{sum(row['status'] == 'blocked' for row in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
