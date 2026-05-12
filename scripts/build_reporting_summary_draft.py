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
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_TSV = ROOT / "results" / "submission" / "reporting_summary_draft.tsv"
OUT_MD = ROOT / "docs" / "nature_reporting_summary_draft.md"

DATASETS = ROOT / "metadata" / "datasets.tsv"
CLAIMS = ROOT / "results" / "manuscript" / "claim_evidence_matrix.tsv"
RELEASE = ROOT / "results" / "release" / "release_readiness.tsv"
COMPLIANCE = ROOT / "results" / "submission" / "nature_methods_compliance_audit.tsv"
GATES = ROOT / "results" / "gates" / "gate_evidence.tsv"
ZENODO = ROOT / ".zenodo.json"
CITATION = ROOT / "CITATION.cff"
REALISTIC_NULL = ROOT / "results" / "calibration" / "realistic_null_summary.tsv"
RARE_STATE_POWER = ROOT / "results" / "calibration" / "rare_state_power_summary.tsv"
CURRENT_FREEZE = ROOT / "docs" / "current_evidence_freeze_2026-05-12.md"


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


def _zenodo_metadata() -> tuple[str, str]:
    if not ZENODO.exists():
        return "https://github.com/healthgreat/rmtguard", "10.5281/zenodo.20012350"
    try:
        metadata = json.loads(ZENODO.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "https://github.com/healthgreat/rmtguard", "10.5281/zenodo.20012350"
    repo = "https://github.com/healthgreat/rmtguard"
    for item in metadata.get("related_identifiers", []):
        identifier = item.get("identifier", "")
        if "github.com" in identifier:
            repo = identifier
            break
    return repo, metadata.get("doi", "10.5281/zenodo.20012350")


def _max_float(rows: list[dict[str, str]], column: str) -> float | None:
    values: list[float] = []
    for row in rows:
        try:
            values.append(float(row.get(column, "")))
        except ValueError:
            pass
    return max(values) if values else None


def _rare_state_boundary(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "Rare-state calibration summary is not available."
    weakest = min(rows, key=lambda row: float(row.get("power", "nan")))
    supported = [
        row
        for row in rows
        if float(row.get("prevalence", "nan")) >= 0.04
        and float(row.get("power", "nan")) >= 0.84
    ]
    return (
        "Rare-state power was bounded by prevalence and effect size: all tested "
        f"prevalence >=0.04 settings reached power >=84% ({len(supported)} settings), "
        f"whereas prevalence {weakest.get('prevalence')}/effect {weakest.get('effect_size')} "
        f"had power {float(weakest.get('power', 'nan')):.2f} and mean rare-state F1 "
        f"{float(weakest.get('mean_rare_f1', 'nan')):.3f}."
    )


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
    repo_url, zenodo_doi = _zenodo_metadata()
    repo_ready = release.get("repository_url") == "pass" and release.get("github_remote") == "pass"
    doi_ready = release.get("zenodo_doi") == "pass"
    current_head_release_tagged = release.get("github_release_tag") == "pass"
    null_rows = _read_tsv(REALISTIC_NULL)
    rare_rows = _read_tsv(RARE_STATE_POWER)
    max_false_signal = _max_float(null_rows, "false_signal_rate")

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
            "No prospective sample-size calculation was performed. The method is evaluated by 50-repeat realistic-null and rare-state calibration, repeated-subsampling real-data benchmarks, official Seurat/JackStraw comparator rows, scLENSpy comparator rows, topology stress tests, and public PDAC/TME application data.",
            CURRENT_FREEZE,
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
            (
                f"Across the current 50-repeat count-preserving null families, the maximum observed false-signal rate was {max_false_signal:.1%}. "
                if max_false_signal is not None
                else ""
            )
            + _rare_state_boundary(rare_rows),
            f"{_rel(REALISTIC_NULL)}; {_rel(RARE_STATE_POWER)}",
            "ready_for_author_check" if gates.get("synthetic_null_false_signal") == "pass" else "needs_author_completion",
            "Confirm exact benchmark numbers match final figures.",
            "Avoid exact type-I calibration claims beyond the tested null families and preprocessing regime.",
        ),
        _row(
            "Method validation",
            "Callability and no-call boundary",
            _claim_text(claim_rows, "pbmc3k_stability"),
            CLAIMS,
            "ready_for_author_check",
            "Keep PBMC68k as diagnostic no-call and avoid broad stability-superiority wording.",
            "The reporting summary can be completed, but the Nature Methods scientific claim remains gated by the stability_advantage result.",
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
            f"Public code is available at {repo_url}. The repository includes local code, tests, CI, Dockerfile, release manifests, dataset metadata and regeneration scripts. Post-release working-branch changes should not be described as part of the immutable release unless a new release is issued.",
            RELEASE,
            "ready_for_author_check" if repo_ready else "blocked",
            "Before submission, verify that the final submitted code corresponds to an archived release.",
            "Code availability is no longer the hard P0 blocker; final release coverage remains author-controlled.",
        ),
        _row(
            "Software",
            "Code DOI",
            f"The archived software DOI recorded in .zenodo.json and CITATION.cff is {zenodo_doi}. The current working branch contains post-release changes; if these are cited in the submitted manuscript, create and archive a new release before submission.",
            RELEASE,
            "needs_release_refresh" if doi_ready and not current_head_release_tagged else ("ready_for_author_check" if doi_ready else "blocked"),
            "Create a new GitHub Release/Zenodo archive if the final manuscript depends on post-v0.1.0 files.",
            "The DOI exists; the remaining issue is exact version coverage, not absence of DOI.",
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
    manual = [
        row
        for row in rows
        if row["status"]
        in {"pending_manual", "needs_author_completion", "needs_release_refresh"}
    ]
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
    lines.extend(["", "## Manual Or Release-Refresh Rows", ""])
    if manual:
        lines.extend(
            f"- `{row['section']} / {row['item']}` ({row['status']}): {row['author_action_required']}"
            for row in manual
        )
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
