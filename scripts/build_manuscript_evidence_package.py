from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "manuscript"
CLAIM_MATRIX = OUT_DIR / "claim_evidence_matrix.tsv"
CHECKLIST = OUT_DIR / "nature_methods_submission_checklist.tsv"
READINESS_MD = ROOT / "manuscript" / "submission_readiness.md"


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


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_tsv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _gate_map() -> dict[str, dict[str, str]]:
    rows = _read_tsv(ROOT / "results" / "gates" / "gate_evidence.tsv")
    return {row["gate_id"]: row for row in rows}


def _gate_status(gates: dict[str, dict[str, str]], gate_id: str) -> str:
    return gates.get(gate_id, {}).get("status", "pending")


def _gate_evidence(gates: dict[str, dict[str, str]], gate_id: str) -> str:
    row = gates.get(gate_id, {})
    return row.get("evidence_path", "") + (" | " + row.get("notes", "") if row.get("notes") else "")


def _metric_lookup() -> dict[str, str]:
    metrics: dict[str, str] = {}

    for row in _read_csv(ROOT / "results" / "synthetic_benchmarks" / "synthetic_benchmark_summary.csv"):
        if row.get("method") == "rmtguard" and row.get("scenario") == "pure_null":
            metrics["pure_null_signal_pcs"] = row.get("n_signal_pcs", "")
        if row.get("method") == "rmtguard" and row.get("scenario") == "rare_state":
            metrics["rare_state_ari"] = row.get("ari", "")

    no_call = _read_tsv(ROOT / "results" / "no_call_benchmarks" / "no_call_summary.tsv")
    if no_call:
        hard_rows = [row for row in no_call if row.get("expected_behavior") in {"diagnostic_no_call", "positive_call"}]
        metrics["no_call_hard_pass"] = str(sum(row.get("decision") == "pass" for row in hard_rows))
        metrics["no_call_hard_total"] = str(len(hard_rows))
        pure_null = next((row for row in no_call if row.get("scenario") == "pure_null"), None)
        if pure_null:
            metrics["pure_null_analysis_status"] = pure_null.get("analysis_status", "")
            metrics["pure_null_no_call_reason"] = pure_null.get("no_call_reason", "")

    stability = _read_tsv(ROOT / "results" / "stability_benchmarks" / "stability_summary.tsv")
    for row in stability:
        if row.get("dataset_id") == "pbmc3k_10x" and row.get("method") == "rmtguard":
            metrics["pbmc3k_rmtguard_stability"] = row.get("mean_pairwise_ari", "")
        if row.get("dataset_id") == "pbmc3k_10x" and row.get("method") == "scanpy_default_like":
            metrics["pbmc3k_scanpy_like_stability"] = row.get("mean_pairwise_ari", "")
        if row.get("dataset_id") == "pbmc3k_10x" and row.get("method") == "fixed_pcs_30":
            metrics["pbmc3k_fixed30_stability"] = row.get("mean_pairwise_ari", "")

    diagnostics = _read_tsv(ROOT / "results" / "stability_benchmarks" / "stability_gate_diagnostics.tsv")
    if diagnostics:
        metrics["stability_gate_diagnostics"] = "; ".join(
            (
                row.get("dataset_id", "")
                + ": "
                + row.get("status", "")
                + " RMTGuard="
                + row.get("rmtguard_mean_pairwise_ari", "")
                + " best="
                + row.get("best_baseline_method", "")
                + " "
                + row.get("best_baseline_mean_pairwise_ari", "")
            )
            for row in diagnostics
        )

    phase1 = _read_tsv(ROOT / "results" / "phase1_benchmarks" / "phase1_benchmark_summary.tsv")
    rmt_datasets = sorted({row.get("dataset_id", "") for row in phase1 if row.get("method") == "rmtguard"})
    metrics["real_dataset_count"] = str(len([x for x in rmt_datasets if x]))
    metrics["real_datasets"] = ", ".join(rmt_datasets)
    for dataset_id in ["kang_ifnb_pbmc", "baron_pancreas", "pbmc68k_zheng2017"]:
        rmt = next((row for row in phase1 if row.get("dataset_id") == dataset_id and row.get("method") == "rmtguard"), None)
        fixed = next((row for row in phase1 if row.get("dataset_id") == dataset_id and row.get("method") == "fixed_pcs_30"), None)
        if rmt:
            metrics[f"{dataset_id}_rmtguard_ari"] = rmt.get("ari", "")
        if fixed:
            metrics[f"{dataset_id}_fixed30_ari"] = fixed.get("ari", "")

    pdac = _read_tsv(ROOT / "results" / "pdac_tme" / "showcase_summary.tsv")
    validation = next((row for row in pdac if row.get("dataset_id") == "pdac_gse263733"), None)
    if validation:
        metrics["pdac_validation_ari"] = validation.get("label_ari", "")
        metrics["pdac_validation_nmi"] = validation.get("label_nmi", "")
        metrics["pdac_validation_signatures"] = validation.get("top_signatures", "")
    primary = next((row for row in pdac if row.get("dataset_id") == "pdac_gse154778"), None)
    if primary:
        metrics["pdac_primary_signatures"] = primary.get("top_signatures", "")

    return metrics


def build_claim_rows() -> list[dict[str, str]]:
    gates = _gate_map()
    metrics = _metric_lookup()
    rows = [
        {
            "claim_id": "noise_control_null",
            "manuscript_claim": "RMTGuard controls false signal PCs under pure random-matrix null simulations.",
            "status": _gate_status(gates, "synthetic_null_false_signal"),
            "evidence": _gate_evidence(gates, "synthetic_null_false_signal"),
            "allowed_wording": f"Pure-null benchmark retained {metrics.get('pure_null_signal_pcs', 'NA')} signal PC(s), satisfying the pre-specified <=1 criterion.",
            "prohibited_wording": "Do not claim exact type-I error calibration across all scRNA-seq settings without final permutation calibration.",
        },
        {
            "claim_id": "diagnostic_no_call_validation",
            "manuscript_claim": "RMTGuard separates low-signal diagnostic no-calls from positive cell-state discovery calls.",
            "status": _gate_status(gates, "diagnostic_no_call_validation"),
            "evidence": _gate_evidence(gates, "diagnostic_no_call_validation"),
            "allowed_wording": (
                "Diagnostic no-call validation passed "
                + metrics.get("no_call_hard_pass", "0")
                + "/"
                + metrics.get("no_call_hard_total", "0")
                + " hard scenarios; pure-null status="
                + metrics.get("pure_null_analysis_status", "NA")
                + " reason="
                + metrics.get("pure_null_no_call_reason", "NA")
                + "."
            ),
            "prohibited_wording": "Do not present diagnostic_no_call outputs as biological clusters or discoveries.",
        },
        {
            "claim_id": "rare_state_retention",
            "manuscript_claim": "RMTGuard preserves planted rare cell states in synthetic stress tests.",
            "status": _gate_status(gates, "rare_state_retention"),
            "evidence": _gate_evidence(gates, "rare_state_retention"),
            "allowed_wording": f"Rare-state synthetic ARI reached {metrics.get('rare_state_ari', 'NA')}.",
            "prohibited_wording": "Do not imply all biological rare states are guaranteed to be retained.",
        },
        {
            "claim_id": "public_benchmark_breadth",
            "manuscript_claim": "RMTGuard has been benchmarked across four public real scRNA-seq datasets.",
            "status": _gate_status(gates, "real_dataset_count"),
            "evidence": _gate_evidence(gates, "real_dataset_count"),
            "allowed_wording": f"{metrics.get('real_dataset_count', '0')} real datasets are present: {metrics.get('real_datasets', '')}.",
            "prohibited_wording": "Do not describe Tabula Sapiens as completed unless it is added to the actual benchmark table.",
        },
        {
            "claim_id": "pbmc3k_stability",
            "manuscript_claim": "The multi-dataset gate is passed only as a callability-aware stability/no-call result; it is not broad fixed-PC superiority.",
            "status": _gate_status(gates, "stability_advantage"),
            "evidence": _gate_evidence(gates, "stability_advantage"),
            "allowed_wording": (
                "Callability-aware multi-dataset diagnostics: "
                + metrics.get("stability_gate_diagnostics", "")
                + ". PBMC3k mean pairwise ARI: RMTGuard="
                + metrics.get("pbmc3k_rmtguard_stability", "NA")
                + ", Scanpy-like="
                + metrics.get("pbmc3k_scanpy_like_stability", "NA")
                + ", fixed30="
                + metrics.get("pbmc3k_fixed30_stability", "NA")
                + "; PBMC68k is reported as a diagnostic no-call, not as a positive discovery."
            ),
            "prohibited_wording": "Do not claim RMTGuard outperforms fixed-PC baselines on every dataset or that PBMC68k yields a positive cell-state discovery.",
        },
        {
            "claim_id": "annotation_noninferiority",
            "manuscript_claim": "RMTGuard does not materially reduce labeled annotation recovery versus fixed-PC graph baselines.",
            "status": _gate_status(gates, "annotation_noninferiority"),
            "evidence": _gate_evidence(gates, "annotation_noninferiority"),
            "allowed_wording": (
                "Kang ARI RMTGuard="
                + metrics.get("kang_ifnb_pbmc_rmtguard_ari", "NA")
                + " vs fixed30="
                + metrics.get("kang_ifnb_pbmc_fixed30_ari", "NA")
                + "; Baron ARI RMTGuard="
                + metrics.get("baron_pancreas_rmtguard_ari", "NA")
                + " vs fixed30="
                + metrics.get("baron_pancreas_fixed30_ari", "NA")
                + "; PBMC68k absolute ARI remains weak."
            ),
            "prohibited_wording": "Do not frame PBMC68k as a strong positive annotation-recovery success.",
        },
        {
            "claim_id": "pdac_tme_showcase",
            "manuscript_claim": "The PDAC/TME showcase supports immune and ductal-context marker structure with external validation.",
            "status": _gate_status(gates, "pdac_tme_interpretability"),
            "evidence": _gate_evidence(gates, "pdac_tme_interpretability"),
            "allowed_wording": (
                "GSE154778 signatures: "
                + metrics.get("pdac_primary_signatures", "NA")
                + "; GSE263733 validation ARI="
                + metrics.get("pdac_validation_ari", "NA")
                + ", NMI="
                + metrics.get("pdac_validation_nmi", "NA")
                + "."
            ),
            "prohibited_wording": "Do not claim a standalone CAF/fibroblast discovery from the current smoke showcase.",
        },
        {
            "claim_id": "figure_source_data",
            "manuscript_claim": "All five planned main figures have ready source-data tables and draft renders.",
            "status": _gate_status(gates, "figure_source_data"),
            "evidence": _gate_evidence(gates, "figure_source_data"),
            "allowed_wording": "Figure source-data and draft render manifests exist for Figures 1-5.",
            "prohibited_wording": "Do not describe draft renders as final journal production artwork.",
        },
        {
            "claim_id": "software_release",
            "manuscript_claim": "The local release package is prepared, but public GitHub/Zenodo release is not complete.",
            "status": _gate_status(gates, "software_release"),
            "evidence": _gate_evidence(gates, "software_release"),
            "allowed_wording": "Local release checks pass, but GitHub release tag and Zenodo DOI are still pending.",
            "prohibited_wording": "Do not state that code is DOI-archived or fully released before the external release exists.",
        },
    ]
    return rows


def build_checklist_rows() -> list[dict[str, str]]:
    gates = _gate_map()
    rows = [
        ("Nature Methods gate decision", "blocked", "At least one required gate is not pass.", "Resolve software_release pending before submission."),
        ("Synthetic null control", _gate_status(gates, "synthetic_null_false_signal"), _gate_evidence(gates, "synthetic_null_false_signal"), "Keep final null calibration explicit."),
        ("Diagnostic no-call validation", _gate_status(gates, "diagnostic_no_call_validation"), _gate_evidence(gates, "diagnostic_no_call_validation"), "Keep no-call outputs separate from discovery claims."),
        ("Rare-state retention", _gate_status(gates, "rare_state_retention"), _gate_evidence(gates, "rare_state_retention"), "Keep synthetic limitation wording."),
        ("Public real benchmark breadth", _gate_status(gates, "real_dataset_count"), _gate_evidence(gates, "real_dataset_count"), "Add Tabula Sapiens only if results are strong and reproducible."),
        ("Callability-aware stability/no-call", _gate_status(gates, "stability_advantage"), _gate_evidence(gates, "stability_advantage"), "Keep wording callability-aware and do not claim broad fixed-PC superiority."),
        ("Annotation noninferiority", _gate_status(gates, "annotation_noninferiority"), _gate_evidence(gates, "annotation_noninferiority"), "Discuss PBMC68k weak absolute ARI as caveat."),
        ("PDAC/TME interpretability", _gate_status(gates, "pdac_tme_interpretability"), _gate_evidence(gates, "pdac_tme_interpretability"), "Keep claim immune/ductal-context, not CAF discovery."),
        ("Software release", _gate_status(gates, "software_release"), _gate_evidence(gates, "software_release"), "Requires real GitHub Release and Zenodo DOI."),
        ("Figure source data", _gate_status(gates, "figure_source_data"), _gate_evidence(gates, "figure_source_data"), "Design-polish final figures separately."),
    ]
    return [
        {"item": item, "status": status, "evidence": evidence, "next_action": next_action}
        for item, status, evidence, next_action in rows
    ]


def _recommendation() -> str:
    report = ROOT / "results" / "gates" / "gate_report.tsv"
    text = report.read_text(encoding="utf-8", errors="replace") if report.exists() else ""
    for line in text.splitlines():
        if line.startswith("recommendation\t"):
            return line.split("\t", 1)[1]
    return "unknown"


def write_readiness_md(claim_rows: list[dict[str, str]], checklist_rows: list[dict[str, str]]) -> None:
    blocked = [row for row in checklist_rows if row["status"] in {"pending", "borderline", "blocked", "fail"}]
    pass_claims = [row for row in claim_rows if row["status"] == "pass"]
    caution_claims = [row for row in claim_rows if row["status"] != "pass"]
    lines = [
        "# Submission Readiness",
        "",
        "This file is generated by `python scripts/build_manuscript_evidence_package.py`.",
        "",
        f"- Current recommendation: `{_recommendation()}`",
        "- Nature Methods status: `not ready`",
        "- Genome Biology fallback status: `not ready until software_release is complete`",
        "",
        "## Blocking Items",
        "",
    ]
    lines.extend(f"- `{row['item']}`: {row['status']} - {row['next_action']}" for row in blocked)
    lines.extend(["", "## Manuscript-safe Claims", ""])
    lines.extend(f"- `{row['claim_id']}`: {row['allowed_wording']}" for row in pass_claims)
    lines.extend(["", "## Caution Or Prohibited Claims", ""])
    lines.extend(
        f"- `{row['claim_id']}` ({row['status']}): {row['prohibited_wording']}"
        for row in caution_claims
    )
    lines.extend(
        [
            "",
            "## Source Tables",
            "",
            f"- Claim-evidence matrix: `{_rel(CLAIM_MATRIX)}`",
            f"- Submission checklist: `{_rel(CHECKLIST)}`",
        ]
    )
    tmp = READINESS_MD.with_suffix(READINESS_MD.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(READINESS_MD)


def main() -> int:
    claim_rows = build_claim_rows()
    checklist_rows = build_checklist_rows()
    _write_tsv(
        CLAIM_MATRIX,
        claim_rows,
        ["claim_id", "manuscript_claim", "status", "evidence", "allowed_wording", "prohibited_wording"],
    )
    _write_tsv(CHECKLIST, checklist_rows, ["item", "status", "evidence", "next_action"])
    write_readiness_md(claim_rows, checklist_rows)
    print(_rel(CLAIM_MATRIX))
    print(_rel(CHECKLIST))
    print(_rel(READINESS_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
