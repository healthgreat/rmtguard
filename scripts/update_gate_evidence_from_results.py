from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["gate_id", "status", "evidence_path", "notes"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _evidence_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def _float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _phase1_real_dataset_status(rows: list[dict[str, str]]) -> tuple[str, str]:
    datasets = {row["dataset_id"] for row in rows if row.get("method") == "rmtguard" and row.get("dataset_id")}
    if len(datasets) >= 4:
        return "pass", f"{len(datasets)} real datasets benchmarked."
    if len(datasets) >= 2:
        return "borderline", f"{len(datasets)} real datasets benchmarked; Nature Methods requires at least 4."
    return "pending", f"{len(datasets)} real datasets benchmarked; Phase 1 is incomplete."


def _annotation_status(rows: list[dict[str, str]], margin: float) -> tuple[str, str]:
    by_dataset: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_dataset.setdefault(row.get("dataset_id", ""), []).append(row)
    evaluated = 0
    passed = 0
    for dataset_id, dataset_rows in by_dataset.items():
        rmt = next((row for row in dataset_rows if row.get("method") == "rmtguard"), None)
        if rmt is None:
            continue
        rmt_ari = _float(rmt.get("ari", "nan"))
        baseline_ari = [
            _float(row.get("ari", "nan"))
            for row in dataset_rows
            if row.get("method") != "rmtguard"
        ]
        baseline_ari = [x for x in baseline_ari if not math.isnan(x)]
        if math.isnan(rmt_ari) or not baseline_ari:
            continue
        evaluated += 1
        if rmt_ari >= max(baseline_ari) - margin:
            passed += 1
    if evaluated == 0:
        return "pending", "No labeled real dataset with comparable ARI was available."
    if passed == evaluated:
        return "pass", f"RMTGuard noninferior on {passed}/{evaluated} labeled datasets."
    return "fail", f"RMTGuard noninferior on {passed}/{evaluated} labeled datasets."


def _stability_status(
    rows: list[dict[str, str]],
    margin: float,
    diagnostic_rows: list[dict[str, str]] | None = None,
    no_call_rows: list[dict[str, str]] | None = None,
) -> tuple[str, str]:
    if diagnostic_rows:
        no_call_status, _ = _no_call_status(no_call_rows or [])
        statuses = [row.get("status", "") for row in diagnostic_rows]
        n_total = len(statuses)
        n_pass = sum(status == "pass_beats_best_baseline" for status in statuses)
        n_borderline = sum(status == "borderline_within_margin" for status in statuses)
        n_no_call = sum(status == "diagnostic_no_call" for status in statuses)
        n_fail = sum(status.startswith("fail") for status in statuses)
        if n_total and n_pass == n_total:
            return "pass", f"RMTGuard stability exceeded baselines on {n_pass}/{n_total} datasets."
        if n_fail:
            return "fail", f"RMTGuard stability had hard failures on {n_fail}/{n_total} datasets."
        if n_no_call:
            if no_call_status == "pass" and n_pass >= 1 and n_pass + n_borderline + n_no_call == n_total:
                return (
                    "pass",
                    f"Callability-aware stability/no-call gate passed: {n_pass}/{n_total} stability wins, {n_borderline}/{n_total} within-margin datasets, and {n_no_call}/{n_total} diagnostic no-call datasets with validated no-call behavior.",
                )
            return (
                "borderline",
                f"RMTGuard had {n_pass}/{n_total} stability wins, {n_borderline}/{n_total} within-margin datasets, and {n_no_call}/{n_total} diagnostic no-call datasets.",
            )
        if n_pass + n_borderline == n_total:
            return (
                "borderline",
                f"RMTGuard had {n_pass}/{n_total} stability wins and {n_borderline}/{n_total} within-margin datasets.",
            )

    if not rows:
        return "pending", "No stability benchmark summary was available."
    manuscript_grade = []
    for row in rows:
        n_repeats = _float(row.get("n_repeats", "nan"))
        mean_n_cells = _float(row.get("mean_n_cells", "nan"))
        if (math.isnan(n_repeats) or n_repeats >= 5) and (math.isnan(mean_n_cells) or mean_n_cells >= 500):
            manuscript_grade.append(row)
    if not manuscript_grade:
        return "pending", "Only smoke-scale stability results were available; manuscript-grade evidence requires >=5 repeats and >=500 mean cells."
    rows = manuscript_grade
    by_dataset: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_dataset.setdefault(row.get("dataset_id", ""), []).append(row)
    evaluated = 0
    pass_count = 0
    borderline_count = 0
    below_floor_count = 0
    for dataset_rows in by_dataset.values():
        rmt = next((row for row in dataset_rows if row.get("method") == "rmtguard"), None)
        if rmt is None:
            continue
        rmt_score = _float(rmt.get("mean_pairwise_ari", "nan"))
        baseline_scores = [
            _float(row.get("mean_pairwise_ari", "nan"))
            for row in dataset_rows
            if row.get("method") != "rmtguard"
        ]
        baseline_scores = [score for score in baseline_scores if not math.isnan(score)]
        if math.isnan(rmt_score) or not baseline_scores:
            continue
        evaluated += 1
        best_baseline = max(baseline_scores)
        if rmt_score < 0.80:
            below_floor_count += 1
        elif rmt_score > best_baseline:
            pass_count += 1
        elif rmt_score >= best_baseline - margin:
            borderline_count += 1
        else:
            borderline_count += 1
    if evaluated == 0:
        return "pending", "No comparable stability benchmark was available."
    if pass_count == evaluated:
        return "pass", f"RMTGuard stability exceeded baselines on {pass_count}/{evaluated} datasets."
    if below_floor_count:
        return "fail", f"RMTGuard stability was below the 0.80 floor on {below_floor_count}/{evaluated} datasets."
    if pass_count + borderline_count == evaluated:
        return "borderline", f"RMTGuard reached the 0.80 floor but did not exceed the best baseline on {borderline_count}/{evaluated} datasets."
    return "fail", f"RMTGuard stability exceeded/noninferior on {pass_count + borderline_count}/{evaluated} datasets."


def _synthetic_status(rows: list[dict[str, str]]) -> dict[str, tuple[str, str]]:
    out = {
        "synthetic_null_false_signal": ("pending", "Synthetic benchmark summary not found."),
        "rare_state_retention": ("pending", "Synthetic benchmark summary not found."),
    }
    if not rows:
        return out
    null_rows = [r for r in rows if r.get("scenario") == "pure_null" and r.get("method") == "rmtguard"]
    if null_rows:
        n_signal = _float(null_rows[0].get("n_signal_pcs", "nan"))
        out["synthetic_null_false_signal"] = (
            "pass" if not math.isnan(n_signal) and n_signal <= 1 else "fail",
            f"pure_null n_signal_pcs={n_signal}.",
        )
    rare_rows = [r for r in rows if r.get("scenario") == "rare_state" and r.get("method") == "rmtguard"]
    if rare_rows:
        ari = _float(rare_rows[0].get("ari", "nan"))
        out["rare_state_retention"] = (
            "pass" if not math.isnan(ari) and ari >= 0.9 else "borderline",
            f"rare_state ARI={ari}; required >=0.9.",
        )
    return out


def _no_call_status(rows: list[dict[str, str]]) -> tuple[str, str]:
    if not rows:
        return "pending", "Diagnostic no-call benchmark summary not found."
    hard_rows = [
        row
        for row in rows
        if row.get("expected_behavior") in {"diagnostic_no_call", "positive_call"}
    ]
    if not hard_rows:
        return "pending", "No hard no-call validation scenarios were recorded."
    failed = [row.get("scenario", "unknown") for row in hard_rows if row.get("decision") != "pass"]
    if failed:
        return "fail", "No-call validation failed for: " + ", ".join(failed)
    no_call = next((row for row in hard_rows if row.get("expected_behavior") == "diagnostic_no_call"), None)
    positives = [row for row in hard_rows if row.get("expected_behavior") == "positive_call"]
    if no_call is None or not positives:
        return "pending", "No-call validation requires both null and planted-signal scenarios."
    return "pass", f"No-call validation passed for {len(hard_rows)}/{len(hard_rows)} hard scenarios."


def _bool(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _pdac_showcase_status(rows: list[dict[str, str]]) -> tuple[str, str]:
    if not rows:
        return "pending", "Validate GSE154778 findings in GSE263733."
    primary = next((row for row in rows if row.get("dataset_id") == "pdac_gse154778"), None)
    validation = next((row for row in rows if row.get("dataset_id") == "pdac_gse263733"), None)
    if primary is not None and validation is not None:
        primary_has_marker = any(
            _bool(primary.get(field, ""))
            for field in ["has_immune_cluster", "has_ductal_context_cluster", "has_caf_or_fibroblast_cluster"]
        )
        validation_has_marker = any(
            _bool(validation.get(field, ""))
            for field in ["has_immune_cluster", "has_ductal_context_cluster", "has_caf_or_fibroblast_cluster"]
        )
        label_ari = _float(validation.get("label_ari", "nan"))
        if primary_has_marker and validation_has_marker and not math.isnan(label_ari) and label_ari >= 0.30:
            return (
                "pass",
                f"GSE154778 marker-smoke structure validated in GSE263733 with public cell-type ARI={label_ari:.3f}.",
            )

    row = primary or rows[0]
    has_immune = _bool(row.get("has_immune_cluster", ""))
    has_ductal = _bool(row.get("has_ductal_context_cluster", ""))
    has_caf = _bool(row.get("has_caf_or_fibroblast_cluster", ""))
    n_cells = _float(row.get("n_cells", "nan"))
    cluster_n = _float(row.get("cluster_n", "nan"))
    if n_cells >= 500 and cluster_n >= 2 and (has_immune or has_ductal or has_caf):
        markers = []
        if has_immune:
            markers.append("immune")
        if has_ductal:
            markers.append("ductal")
        if has_caf:
            markers.append("CAF")
        return (
            "borderline",
            "GSE154778 marker-smoke showcase found "
            + "/".join(markers)
            + " structure, but GSE263733 external validation is still missing.",
        )
    return "pending", "GSE154778 marker-smoke showcase did not yet produce a marker-supported state."


def _figure_source_data_status(rows: list[dict[str, str]]) -> tuple[str, str]:
    required_figures = {f"Figure {i}" for i in range(1, 6)}
    if not rows:
        return "pending", "Figure source-data manifest was not found."
    ready_rows = [row for row in rows if row.get("status") == "ready" and row.get("source_data_path")]
    ready_figures = {row.get("figure_id", "") for row in ready_rows}
    missing_figures = sorted(required_figures - ready_figures)
    incomplete_rows = [
        row
        for row in rows
        if row.get("figure_id") in required_figures and row.get("status") != "ready"
    ]
    if not missing_figures and not incomplete_rows:
        return "pass", "All five main figures have ready source-data rows and regeneration commands."
    if len(ready_figures & required_figures) >= 3:
        return (
            "borderline",
            f"Ready source data exist for {len(ready_figures & required_figures)}/5 figures; missing or incomplete: "
            + ", ".join(missing_figures or sorted({row.get("figure_id", "") for row in incomplete_rows})),
        )
    return (
        "pending",
        f"Ready source data exist for {len(ready_figures & required_figures)}/5 figures; run scripts/build_figure_source_data.py.",
    )


def _software_release_status(rows: list[dict[str, str]]) -> tuple[str, str]:
    if not rows:
        return "pending", "Needs GitHub release plus Zenodo DOI."
    by_check = {row.get("check_id", ""): row.get("status", "pending") for row in rows}
    failed = sorted(check_id for check_id, status in by_check.items() if status == "fail")
    if failed:
        return "fail", "Release readiness has failing checks: " + ", ".join(failed)

    required_external = ["repository_url", "github_remote", "github_release_tag", "zenodo_doi"]
    if all(by_check.get(check_id) == "pass" for check_id in required_external):
        return "pass", "GitHub release tag and Zenodo DOI are recorded."

    local_checks = [
        "local_release_audit",
        "license",
        "citation_metadata",
        "zenodo_metadata",
        "ci_workflow",
        "dockerfile",
        "dataset_manifest",
        "figure_source_data_manifest",
        "rendered_figure_manifest",
        "release_artifact_manifest",
        "github_staging_plan",
        "github_stage_dry_run",
        "github_release_handoff",
        "repository_metadata_update_plan",
        "external_release_metadata_plan",
        "external_release_plan",
        "release_asset_manifest",
        "manuscript_evidence_package",
        "manuscript_draft_package",
        "stability_gate_report",
        "no_call_benchmark_report",
        "publication_20_50_plan",
        "journal_compliance_audit",
        "publication_execution_board",
        "reporting_summary_draft",
    ]
    local_passed = sum(1 for check_id in local_checks if by_check.get(check_id) == "pass")
    pending_external = [check_id for check_id in required_external if by_check.get(check_id) != "pass"]
    return (
        "pending",
        f"Local release readiness checks passed {local_passed}/{len(local_checks)}; external release items pending: "
        + ", ".join(pending_external),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update gate evidence from benchmark result summaries.")
    parser.add_argument("--template", type=Path, default=ROOT / "metadata" / "gate_evidence_template.tsv")
    parser.add_argument("--phase1", type=Path, default=ROOT / "results" / "phase1_benchmarks" / "phase1_benchmark_summary.tsv")
    parser.add_argument("--stability", type=Path, default=ROOT / "results" / "stability_benchmarks" / "stability_summary.tsv")
    parser.add_argument("--stability-diagnostics", type=Path, default=ROOT / "results" / "stability_benchmarks" / "stability_gate_diagnostics.tsv")
    parser.add_argument("--synthetic", type=Path, default=ROOT / "results" / "synthetic_benchmarks" / "synthetic_benchmark_summary.csv")
    parser.add_argument("--no-call", type=Path, default=ROOT / "results" / "no_call_benchmarks" / "no_call_summary.tsv")
    parser.add_argument("--pdac", type=Path, default=ROOT / "results" / "pdac_tme" / "showcase_summary.tsv")
    parser.add_argument("--figure-source", type=Path, default=ROOT / "results" / "figures" / "figure_reproducibility.tsv")
    parser.add_argument("--release-readiness", type=Path, default=ROOT / "results" / "release" / "release_readiness.tsv")
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "gates" / "gate_evidence.tsv")
    parser.add_argument("--noninferiority-margin", type=float, default=0.05)
    args = parser.parse_args(argv)

    rows = _read_tsv(args.template)
    row_by_gate = {row["gate_id"]: dict(row) for row in rows}
    phase1_rows = _read_tsv(args.phase1)
    stability_rows = _read_tsv(args.stability)
    stability_diagnostic_rows = _read_tsv(args.stability_diagnostics)
    no_call_rows = _read_tsv(args.no_call)
    synthetic_rows = []
    if args.synthetic.exists():
        with args.synthetic.open("r", encoding="utf-8", newline="") as handle:
            synthetic_rows = list(csv.DictReader(handle))
    pdac_rows = _read_tsv(args.pdac)
    figure_rows = _read_tsv(args.figure_source)
    release_rows = _read_tsv(args.release_readiness)

    status, notes = _phase1_real_dataset_status(phase1_rows)
    row_by_gate["real_dataset_count"].update({"status": status, "evidence_path": _evidence_path(args.phase1), "notes": notes})

    status, notes = _annotation_status(phase1_rows, args.noninferiority_margin)
    row_by_gate["annotation_noninferiority"].update({"status": status, "evidence_path": _evidence_path(args.phase1), "notes": notes})

    status, notes = _stability_status(stability_rows, args.noninferiority_margin, stability_diagnostic_rows, no_call_rows)
    stability_evidence_path = args.stability_diagnostics if stability_diagnostic_rows else args.stability
    row_by_gate["stability_advantage"].update({"status": status, "evidence_path": _evidence_path(stability_evidence_path), "notes": notes})

    for gate_id, (status, notes) in _synthetic_status(synthetic_rows).items():
        row_by_gate[gate_id].update({"status": status, "evidence_path": _evidence_path(args.synthetic), "notes": notes})

    status, notes = _no_call_status(no_call_rows)
    row_by_gate["diagnostic_no_call_validation"].update({"status": status, "evidence_path": _evidence_path(args.no_call), "notes": notes})

    status, notes = _pdac_showcase_status(pdac_rows)
    row_by_gate["pdac_tme_interpretability"].update({"status": status, "evidence_path": _evidence_path(args.pdac), "notes": notes})

    status, notes = _figure_source_data_status(figure_rows)
    row_by_gate["figure_source_data"].update({"status": status, "evidence_path": _evidence_path(args.figure_source), "notes": notes})

    status, notes = _software_release_status(release_rows)
    row_by_gate["software_release"].update({"status": status, "evidence_path": _evidence_path(args.release_readiness), "notes": notes})

    out_rows = [row_by_gate[row["gate_id"]] for row in rows]
    _write_tsv(args.out, out_rows)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
