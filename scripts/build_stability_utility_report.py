from __future__ import annotations

"""Build a stability-versus-annotation utility audit for RMTGuard.

Author: RMTGuard development team
Date: 2026-04-30
Purpose: Quantify whether comparator methods are truly better than RMTGuard or
whether they trade higher clustering stability for weaker annotation recovery.
Data source: Phase 1 benchmark summary and subsampling stability summary.
Method notes: This is a pre-submission claim-control artifact. It does not
turn a failed stability gate into a pass and cannot guarantee journal
acceptance.
"""

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STABILITY_SUMMARY = ROOT / "results" / "stability_benchmarks" / "stability_summary.tsv"
PHASE1_SUMMARY = ROOT / "results" / "phase1_benchmarks" / "phase1_benchmark_summary.tsv"
STABILITY_DIAGNOSTICS = ROOT / "results" / "stability_benchmarks" / "stability_gate_diagnostics.tsv"
OUT_TSV = ROOT / "results" / "stability_benchmarks" / "stability_utility_tradeoff.tsv"
OUT_MD = ROOT / "docs" / "stability_utility_tradeoff.md"


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


def _float(value: str | None) -> float:
    try:
        return float(value) if value not in {None, ""} else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def _fmt(value: float) -> str:
    if value != value:
        return "nan"
    return f"{value:.6f}"


def _annotation_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str], float]:
    return {
        (row.get("dataset_id", ""), row.get("method", "")): _float(row.get("ari"))
        for row in rows
        if row.get("dataset_id") and row.get("method")
    }


def _diagnostic_lookup(rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        row.get("dataset_id", ""): row.get("status", "")
        for row in rows
        if row.get("dataset_id")
    }


def _relation(delta: float, margin: float) -> str:
    if delta != delta:
        return "not_available"
    if delta > margin:
        return "higher"
    if delta < -margin:
        return "lower"
    return "within_margin"


def _utility_relation(
    method: str,
    stability_delta: float,
    annotation_delta: float,
    annotation_available: bool,
    stability_margin: float,
    annotation_margin: float,
) -> str:
    if method == "rmtguard":
        return "rmtguard_reference"
    stability_relation = _relation(stability_delta, stability_margin)
    if not annotation_available:
        if stability_relation == "higher":
            return "unlabeled_comparator_higher_stability"
        if stability_relation == "lower":
            return "unlabeled_comparator_lower_stability"
        return "unlabeled_stability_within_margin"

    annotation_relation = _relation(annotation_delta, annotation_margin)
    if stability_relation == "higher" and annotation_relation == "higher":
        return "comparator_higher_stability_higher_annotation"
    if stability_relation == "higher" and annotation_relation == "lower":
        return "comparator_higher_stability_lower_annotation"
    if stability_relation == "lower" and annotation_relation == "higher":
        return "comparator_lower_stability_higher_annotation"
    if stability_relation == "lower" and annotation_relation == "lower":
        return "comparator_lower_stability_lower_annotation"
    if stability_relation == "higher":
        return "comparator_higher_stability_annotation_within_margin"
    if stability_relation == "lower":
        return "comparator_lower_stability_annotation_within_margin"
    if annotation_relation == "higher":
        return "stability_within_margin_comparator_higher_annotation"
    if annotation_relation == "lower":
        return "stability_within_margin_comparator_lower_annotation"
    return "both_within_margin"


def _dominance(
    method: str,
    stability_delta: float,
    annotation_delta: float,
    annotation_available: bool,
    stability_margin: float,
    annotation_margin: float,
) -> tuple[str, str]:
    if method == "rmtguard" or not annotation_available:
        return "no", "no"
    comparator_noninferior = stability_delta >= -stability_margin and annotation_delta >= -annotation_margin
    comparator_better = stability_delta > stability_margin or annotation_delta > annotation_margin
    rmtguard_noninferior = stability_delta <= stability_margin and annotation_delta <= annotation_margin
    rmtguard_better = stability_delta < -stability_margin or annotation_delta < -annotation_margin
    return (
        "yes" if comparator_noninferior and comparator_better else "no",
        "yes" if rmtguard_noninferior and rmtguard_better else "no",
    )


def build_rows(
    stability_rows: list[dict[str, str]],
    annotation_rows: list[dict[str, str]],
    diagnostic_rows: list[dict[str, str]] | None = None,
    stability_margin: float = 0.01,
    annotation_margin: float = 0.02,
) -> list[dict[str, str]]:
    annotations = _annotation_lookup(annotation_rows)
    diagnostics = _diagnostic_lookup(diagnostic_rows or [])
    by_dataset: dict[str, list[dict[str, str]]] = {}
    for row in stability_rows:
        dataset_id = row.get("dataset_id", "")
        if dataset_id:
            by_dataset.setdefault(dataset_id, []).append(row)

    out: list[dict[str, str]] = []
    for dataset_id in sorted(by_dataset):
        dataset_rows = by_dataset[dataset_id]
        rmt = next((row for row in dataset_rows if row.get("method") == "rmtguard"), None)
        if rmt is None:
            continue
        rmt_stability = _float(rmt.get("mean_pairwise_ari"))
        rmt_annotation = annotations.get((dataset_id, "rmtguard"), float("nan"))
        gate_status = diagnostics.get(dataset_id, "not_recorded")
        for row in sorted(dataset_rows, key=lambda item: item.get("method", "")):
            method = row.get("method", "")
            method_stability = _float(row.get("mean_pairwise_ari"))
            method_annotation = annotations.get((dataset_id, method), float("nan"))
            stability_delta = method_stability - rmt_stability
            annotation_delta = method_annotation - rmt_annotation
            annotation_available = (
                method_annotation == method_annotation
                and rmt_annotation == rmt_annotation
            )
            utility_relation = _utility_relation(
                method,
                stability_delta,
                annotation_delta,
                annotation_available,
                stability_margin,
                annotation_margin,
            )
            dominates, rmt_dominates = _dominance(
                method,
                stability_delta,
                annotation_delta,
                annotation_available,
                stability_margin,
                annotation_margin,
            )
            out.append(
                {
                    "dataset_id": dataset_id,
                    "method": method,
                    "gate_status": gate_status,
                    "mean_pairwise_ari": _fmt(method_stability),
                    "annotation_ari": _fmt(method_annotation),
                    "mean_cluster_n": _fmt(_float(row.get("mean_cluster_n"))),
                    "rmtguard_mean_pairwise_ari": _fmt(rmt_stability),
                    "rmtguard_annotation_ari": _fmt(rmt_annotation),
                    "delta_stability_vs_rmtguard": _fmt(stability_delta),
                    "delta_annotation_vs_rmtguard": _fmt(annotation_delta),
                    "stability_relation_vs_rmtguard": _relation(stability_delta, stability_margin),
                    "annotation_relation_vs_rmtguard": _relation(annotation_delta, annotation_margin),
                    "utility_relation_vs_rmtguard": utility_relation,
                    "comparator_dominates_rmtguard": dominates,
                    "rmtguard_dominates_comparator": rmt_dominates,
                    "annotation_available": "yes" if annotation_available else "no",
                    "interpretation": _interpretation(gate_status, utility_relation, dominates),
                }
            )
    return out


def _interpretation(gate_status: str, utility_relation: str, dominates: str) -> str:
    if gate_status == "diagnostic_no_call":
        return "diagnostic no-call context; do not use as a positive discovery claim"
    if utility_relation.startswith("unlabeled"):
        return "stability-only comparison because annotation labels are unavailable"
    if dominates == "yes":
        return "comparator is noninferior on both measured axes and better on at least one"
    if "higher_stability_lower_annotation" in utility_relation:
        return "comparator improves stability but loses annotation recovery"
    if "lower_stability_higher_annotation" in utility_relation:
        return "comparator loses stability but improves annotation recovery"
    if utility_relation == "rmtguard_reference":
        return "RMTGuard reference row"
    return "no strict utility dominance; keep claim scoped"


def _dataset_summaries(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_dataset: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_dataset.setdefault(row["dataset_id"], []).append(row)

    summaries: list[dict[str, str]] = []
    for dataset_id in sorted(by_dataset):
        dataset_rows = [row for row in by_dataset[dataset_id] if row["method"] != "rmtguard"]
        gate_status = by_dataset[dataset_id][0]["gate_status"]
        higher_stability = [row for row in dataset_rows if row["stability_relation_vs_rmtguard"] == "higher"]
        lower_annotation = [row for row in higher_stability if row["annotation_relation_vs_rmtguard"] == "lower"]
        dominating = [row for row in dataset_rows if row["comparator_dominates_rmtguard"] == "yes"]
        unlabeled = all(row["annotation_available"] == "no" for row in by_dataset[dataset_id])
        if gate_status == "diagnostic_no_call":
            decision = "diagnostic_no_call_context"
        elif unlabeled and higher_stability:
            decision = "unlabeled_stability_deficit"
        elif dominating:
            decision = "rmtguard_dominated_on_measured_axes"
        elif higher_stability and len(lower_annotation) == len(higher_stability):
            decision = "stability_annotation_tradeoff"
        elif not higher_stability:
            decision = "rmtguard_not_stability_deficient"
        else:
            decision = "mixed_tradeoff"
        summaries.append(
            {
                "dataset_id": dataset_id,
                "decision": decision,
                "gate_status": gate_status,
                "higher_stability_methods": ";".join(row["method"] for row in higher_stability) or "none",
                "dominating_methods": ";".join(row["method"] for row in dominating) or "none",
                "notes": _summary_notes(decision),
            }
        )
    return summaries


def _summary_notes(decision: str) -> str:
    notes = {
        "diagnostic_no_call_context": "Treat as no-call stress evidence, not positive cell-state discovery.",
        "unlabeled_stability_deficit": "RMTGuard loses on stability-only evidence; no annotation utility axis is available.",
        "rmtguard_dominated_on_measured_axes": "At least one comparator is better or noninferior on both stability and annotation.",
        "stability_annotation_tradeoff": "Higher-stability comparators lose annotation recovery.",
        "rmtguard_not_stability_deficient": "No comparator is materially more stable than RMTGuard.",
        "mixed_tradeoff": "Comparators show mixed stability and annotation tradeoffs.",
    }
    return notes.get(decision, "Review manually.")


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    summaries = _dataset_summaries(rows)
    lines = [
        "# Stability-Utility Tradeoff Audit",
        "",
        "This file is generated by `python scripts/build_stability_utility_report.py`.",
        "",
        "## Current Decision",
        "",
        "- This audit does not rescue the failed `stability_advantage` gate.",
        "- It separates pure clustering reproducibility from annotation recovery so the manuscript cannot overclaim broad fixed-PC superiority.",
        "- The current evidence supports only a scoped, callability-aware benchmark claim unless the algorithm is improved or the claim is narrowed.",
        "",
        "## Dataset-Level Interpretation",
        "",
    ]
    for row in summaries:
        lines.append(
            "- `{dataset_id}`: `{decision}`; higher-stability methods: `{higher_stability_methods}`; "
            "dominating methods: `{dominating_methods}`. {notes}".format(**row)
        )
    lines.extend(["", "## Rows Requiring Claim Control", ""])
    flagged = [
        row
        for row in rows
        if row["comparator_dominates_rmtguard"] == "yes"
        or row["utility_relation_vs_rmtguard"] in {
            "unlabeled_comparator_higher_stability",
            "comparator_higher_stability_lower_annotation",
        }
    ]
    if flagged:
        for row in flagged:
            lines.append(
                "- `{dataset_id}` / `{method}`: {utility_relation_vs_rmtguard}; "
                "delta stability={delta_stability_vs_rmtguard}, delta annotation={delta_annotation_vs_rmtguard}; "
                "{interpretation}".format(**row)
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Source Tables",
            "",
            f"- Stability summary: `{_rel(STABILITY_SUMMARY)}`",
            f"- Phase 1 summary: `{_rel(PHASE1_SUMMARY)}`",
            f"- Stability diagnostics: `{_rel(STABILITY_DIAGNOSTICS)}`",
            f"- Utility tradeoff TSV: `{_rel(OUT_TSV)}`",
        ]
    )
    return lines


FIELDNAMES = [
    "dataset_id",
    "method",
    "gate_status",
    "mean_pairwise_ari",
    "annotation_ari",
    "mean_cluster_n",
    "rmtguard_mean_pairwise_ari",
    "rmtguard_annotation_ari",
    "delta_stability_vs_rmtguard",
    "delta_annotation_vs_rmtguard",
    "stability_relation_vs_rmtguard",
    "annotation_relation_vs_rmtguard",
    "utility_relation_vs_rmtguard",
    "comparator_dominates_rmtguard",
    "rmtguard_dominates_comparator",
    "annotation_available",
    "interpretation",
]


def main() -> int:
    rows = build_rows(_read_tsv(STABILITY_SUMMARY), _read_tsv(PHASE1_SUMMARY), _read_tsv(STABILITY_DIAGNOSTICS))
    _write_tsv(OUT_TSV, rows, FIELDNAMES)
    _write_text(OUT_MD, build_markdown(rows))
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
