from __future__ import annotations

import argparse
import csv
import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "submission"
GATEKEEPER_TSV = OUT_DIR / "presubmission_gatekeeper.tsv"
PACKAGE_MANIFEST = OUT_DIR / "nature_methods_presubmission_package_manifest.tsv"
PACKAGE_ZIP = OUT_DIR / "rmtguard_nature_methods_presubmission_package.zip"
REPORT_MD = OUT_DIR / "presubmission_gatekeeper.md"

GATE_EVIDENCE = ROOT / "results" / "gates" / "gate_evidence.tsv"
GATE_REPORT = ROOT / "results" / "gates" / "gate_report.tsv"
RELEASE_READINESS = ROOT / "results" / "release" / "release_readiness.tsv"
RELEASE_SUMMARY = ROOT / "results" / "release" / "release_audit_summary.txt"


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _status_map(rows: list[dict[str, str]], key: str) -> dict[str, str]:
    return {row.get(key, ""): row.get("status", "pending") for row in rows}


def evaluate_presubmission(
    gate_rows: list[dict[str, str]], release_rows: list[dict[str, str]]
) -> list[dict[str, str]]:
    gate_status = _status_map(gate_rows, "gate_id")
    release_status = _status_map(release_rows, "check_id")
    scientific_gates = [gate for gate in gate_status if gate != "software_release"]
    scientific_pass = bool(scientific_gates) and all(
        gate_status.get(gate) == "pass" for gate in scientific_gates
    )
    software_pass = gate_status.get("software_release") == "pass"
    external_release_pass = all(
        release_status.get(check_id) == "pass"
        for check_id in [
            "repository_url",
            "github_remote",
            "github_release_tag",
            "zenodo_doi",
        ]
    )
    nature_methods_ready = scientific_pass and software_pass and external_release_pass
    rows = [
        {
            "check_id": "scientific_gate_package",
            "status": "pass" if scientific_pass else "blocked",
            "evidence_path": _rel(GATE_EVIDENCE),
            "notes": (
                "All non-software gates pass."
                if scientific_pass
                else "One or more non-software gates are not pass."
            ),
        },
        {
            "check_id": "callability_boundary",
            "status": (
                "pass"
                if gate_status.get("stability_advantage") == "pass"
                else "blocked"
            ),
            "evidence_path": _rel(GATE_EVIDENCE),
            "notes": "Stability is pass only under callability-aware no-call wording; do not claim broad fixed-PC superiority.",
        },
        {
            "check_id": "software_release_gate",
            "status": "pass" if software_pass else "blocked",
            "evidence_path": _rel(RELEASE_READINESS),
            "notes": "GitHub Release and Zenodo DOI must be complete before submission.",
        },
        {
            "check_id": "external_release_objects",
            "status": "pass" if external_release_pass else "blocked",
            "evidence_path": _rel(RELEASE_READINESS),
            "notes": "Requires repository_url, github_remote, github_release_tag, and zenodo_doi to pass.",
        },
        {
            "check_id": "nature_methods_submission_ready",
            "status": "pass" if nature_methods_ready else "blocked",
            "evidence_path": _rel(GATE_REPORT),
            "notes": "Ready only when scientific gates, software_release, and external release objects are all pass.",
        },
    ]
    return rows


def package_files(tag: str) -> list[Path]:
    return [
        ROOT / "README.md",
        ROOT / "LICENSE",
        ROOT / "CITATION.cff",
        ROOT / "pyproject.toml",
        ROOT / "metadata" / "datasets.tsv",
        ROOT / "metadata" / "submission_gates.tsv",
        ROOT / "docs" / "publication_20_50_rescue_plan.md",
        ROOT / "docs" / "stability_gate_diagnostics.md",
        ROOT / "docs" / "no_call_benchmark.md",
        ROOT / "docs" / "method_risk_log.md",
        ROOT / "manuscript" / "submission_readiness.md",
        ROOT / "manuscript" / "nature_methods_presubmission_draft.md",
        ROOT / "manuscript" / "abstract_draft.md",
        ROOT / "manuscript" / "cover_letter_draft.md",
        ROOT / "results" / "gates" / "gate_evidence.tsv",
        ROOT / "results" / "gates" / "gate_report.tsv",
        ROOT / "results" / "stability_benchmarks" / "stability_gate_diagnostics.tsv",
        ROOT / "results" / "no_call_benchmarks" / "no_call_summary.tsv",
        ROOT / "results" / "manuscript" / "claim_evidence_matrix.tsv",
        ROOT / "results" / "manuscript" / "reviewer_objection_matrix.tsv",
        ROOT / "results" / "figures" / "figure_reproducibility.tsv",
        ROOT / "results" / "release" / "release_readiness.tsv",
        ROOT / "results" / "release" / "release_audit_summary.txt",
        ROOT / "results" / "submission" / "nature_methods_compliance_audit.tsv",
        ROOT / "results" / "submission" / "nature_methods_compliance_audit.md",
        ROOT / "results" / "submission" / "publication_execution_board.tsv",
        ROOT / "docs" / "publication_execution_board.md",
        ROOT / "results" / "submission" / "reporting_summary_draft.tsv",
        ROOT / "docs" / "nature_reporting_summary_draft.md",
        ROOT / "results" / "submission" / "editorial_risk_audit.tsv",
        ROOT / "docs" / "editorial_risk_audit.md",
        ROOT / "docs" / "top_paper_route_package.md",
        ROOT / "docs" / "editorial_presubmission_packet.md",
        ROOT / "docs" / "claim_boundary_lint.md",
        ROOT / "docs" / "claim_traceability.md",
        ROOT / "docs" / "submission_guard.md",
        ROOT / "manuscript" / "top_paper_claim_ladder.md",
        ROOT / "manuscript" / "nature_methods_presubmission_inquiry.md",
        ROOT / "manuscript" / "reviewer_response_playbook.md",
        ROOT / "manuscript" / "figure_claim_checklist.md",
        ROOT / "results" / "release" / "github_release_handoff_manifest.tsv",
        ROOT / "results" / "submission" / "claim_boundary_lint.tsv",
        ROOT / "results" / "submission" / "claim_traceability.tsv",
        ROOT / "results" / "submission" / "submission_guard.tsv",
        ROOT / "results" / "release" / "github_release_handoff.md",
        ROOT / "results" / "release" / f"rmtguard_{tag}_source.bundle",
    ]


def build_manifest(paths: list[Path]) -> list[dict[str, str]]:
    rows = []
    for path in paths:
        if path.exists() and path.is_file():
            rows.append(
                {
                    "path": _rel(path),
                    "package_status": "included",
                    "size_bytes": str(path.stat().st_size),
                    "sha256": _sha256(path),
                    "notes": "Included in local presubmission package.",
                }
            )
        else:
            rows.append(
                {
                    "path": _rel(path),
                    "package_status": "missing",
                    "size_bytes": "0",
                    "sha256": "",
                    "notes": "Expected artifact is missing; regenerate before submission.",
                }
            )
    return rows


def write_package(zip_path: Path, manifest_rows: list[dict[str, str]]) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = zip_path.with_suffix(zip_path.suffix + ".tmp")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for row in manifest_rows:
            if row["package_status"] != "included":
                continue
            source = ROOT / row["path"]
            archive.write(source, row["path"])
    tmp.replace(zip_path)


def build_report(
    gatekeeper_rows: list[dict[str, str]],
    manifest_rows: list[dict[str, str]],
    package_zip: Path,
) -> list[str]:
    blocked = [row for row in gatekeeper_rows if row["status"] != "pass"]
    missing = [row for row in manifest_rows if row["package_status"] != "included"]
    lines = [
        "# RMTGuard Presubmission Gatekeeper",
        "",
        "This file is generated by `python scripts/build_presubmission_package.py`.",
        "",
        "## Decision",
        "",
        "- Target journal route: `Nature Methods` within the 20-50 JIF target band.",
        (
            "- Current status: `not_submission_ready`."
            if blocked
            else "- Current status: `submission_ready_for_editorial_review`."
        ),
        "- Acceptance guarantee: `not possible`; this package enforces evidence and release gates.",
        "- Journal compliance audit: `results/submission/nature_methods_compliance_audit.tsv`.",
        "- Publication execution board: `results/submission/publication_execution_board.tsv`.",
        "- Reporting-summary draft: `results/submission/reporting_summary_draft.tsv`.",
        "- Editorial risk audit: `results/submission/editorial_risk_audit.tsv`.",
        f"- Package zip: `{_rel(package_zip)}`",
        "",
        "## Blocking Items",
        "",
    ]
    if blocked:
        lines.extend(f"- `{row['check_id']}`: {row['notes']}" for row in blocked)
    else:
        lines.append("- none")
    lines.extend(["", "## Missing Package Artifacts", ""])
    if missing:
        lines.extend(f"- `{row['path']}`" for row in missing)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "The stability result is valid only as a callability-aware stability/no-call result. PBMC68k is a diagnostic no-call, not a positive cell-state discovery. Do not claim broad superiority over fixed-PC baselines.",
            "Editor-facing drafts are controlled outputs and must not be sent until the public release and scientific gate boundaries are current.",
            "",
        ]
    )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the local Nature Methods presubmission package and gatekeeper report."
    )
    parser.add_argument("--tag", default="v0.1.0-rc6")
    parser.add_argument("--zip", type=Path, default=PACKAGE_ZIP)
    args = parser.parse_args(argv)

    gatekeeper_rows = evaluate_presubmission(
        _read_tsv(GATE_EVIDENCE), _read_tsv(RELEASE_READINESS)
    )
    manifest_rows = build_manifest(package_files(args.tag))
    _write_tsv(
        GATEKEEPER_TSV,
        gatekeeper_rows,
        ["check_id", "status", "evidence_path", "notes"],
    )
    _write_tsv(
        PACKAGE_MANIFEST,
        manifest_rows,
        ["path", "package_status", "size_bytes", "sha256", "notes"],
    )
    write_package(args.zip, manifest_rows)
    _write_text(REPORT_MD, build_report(gatekeeper_rows, manifest_rows, args.zip))
    print(_rel(GATEKEEPER_TSV))
    print(_rel(PACKAGE_MANIFEST))
    print(_rel(REPORT_MD))
    print(_rel(args.zip))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
