from __future__ import annotations

"""Summarize algorithm rescue probes without promoting failed changes.

Author: RMTGuard development team
Date: 2026-04-30
Purpose: Record local rescue attempts for the stability gate so failed or
dataset-specific tweaks are not silently promoted into manuscript claims.
Data source: Stability probe directories under results/.
Method notes: This report is a gate-control artifact. It does not guarantee
journal acceptance and does not change the official benchmark gate.
"""

import csv
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "rescue"
OUT_TSV = OUT_DIR / "algorithm_rescue_probe_summary.tsv"
OUT_MD = ROOT / "docs" / "algorithm_rescue_probe_report.md"

PROBES = [
    {
        "probe_id": "resolution_path_0p6_2p5",
        "path": ROOT / "results" / "stability_benchmarks_resolution_path_probe" / "stability_summary.tsv",
        "tested_change": "graph modularity resolution path 0.6-2.5 with low/high signal overrides disabled",
        "decision_rule": "Promote only if PBMC3k improves and PBMC68k no-call or underclustering also improves without hurting labeled datasets.",
    },
    {
        "probe_id": "resolution_path_0p6_2p5_kang_baron_partial",
        "path": ROOT / "results" / "stability_benchmarks_resolution_path_probe_kang_baron" / "kang_ifnb_pbmc_stability_summary.tsv",
        "tested_change": "same resolution path on Kang/Baron; run timed out after Kang checkpoint",
        "decision_rule": "Reject if Kang stability drops below current RMTGuard baseline.",
    },
    {
        "probe_id": "resolution_path_min0p8",
        "path": ROOT / "results" / "stability_benchmarks_resolution_path_min08_probe" / "stability_summary.tsv",
        "tested_change": "conservative graph modularity resolution path 0.8-2.0",
        "decision_rule": "Promote only if PBMC3k improves without harming Kang stability.",
    },
    {
        "probe_id": "pbmc68k_near_edge_window_2p0",
        "path": ROOT / "results" / "stability_benchmarks_low_signal_near2_probe" / "stability_summary.tsv",
        "tested_change": "increase near-edge window to 2.0 for low-signal PBMC68k probe",
        "decision_rule": "Promote only if PBMC68k leaves collapse/no-call behavior without forcing fixed PCs.",
    },
    {
        "probe_id": "pbmc68k_mp_edge",
        "path": ROOT / "results" / "stability_benchmarks_pbmc68k_mp_probe2" / "stability_summary.tsv",
        "tested_change": "use MP edge without Tracy-Widom proxy for PBMC68k",
        "decision_rule": "Promote only if PBMC68k stability and cluster count improve while null control remains plausible.",
    },
    {
        "probe_id": "pbmc68k_stable_low_signal_embedding",
        "path": ROOT / "results" / "stability_benchmarks_low_signal_rescue_probe" / "stability_summary.tsv",
        "tested_change": "optional stable low-signal PC rescue with pure-null guard",
        "decision_rule": "Promote only if PBMC68k improves over current RMTGuard while synthetic pure-null remains diagnostic_no_call.",
    },
    {
        "probe_id": "pbmc68k_null_calibrated_low_signal_embedding",
        "path": ROOT / "results" / "stability_benchmarks_null_calibrated_rescue_probe" / "stability_summary.tsv",
        "tested_change": "null-calibrated stable low-signal PC rescue with near-edge eigenvalue-ratio guard",
        "decision_rule": "Promote only if synthetic pure-null remains diagnostic_no_call and PBMC68k improves over current RMTGuard without fixed-PC forcing.",
    },
    {
        "probe_id": "pbmc68k_coarse_to_fine_elbow",
        "path": ROOT / "results" / "stability_benchmarks_coarse_to_fine_probe" / "stability_summary.tsv",
        "run_path": ROOT / "results" / "stability_benchmarks_coarse_to_fine_probe" / "pbmc68k_zheng2017_stability_runs.tsv",
        "tested_change": "experimental label-free coarse PCA compartments followed by within-compartment RMTGuard",
        "decision_rule": "Reject as an RMTGuard rescue if no coarse compartments receive a guarded fine split or if performance simply matches the coarse PC-rule baseline.",
    },
    {
        "probe_id": "pbmc68k_coarse_to_fine_parallel",
        "path": ROOT / "results" / "stability_benchmarks_coarse_to_fine_parallel_probe" / "stability_summary.tsv",
        "run_path": ROOT / "results" / "stability_benchmarks_coarse_to_fine_parallel_probe" / "pbmc68k_zheng2017_stability_runs.tsv",
        "tested_change": "experimental coarse-to-fine workflow using parallel-analysis coarse PCs",
        "decision_rule": "Reject if the guarded fine layer never activates or stability falls below the fixed-PC comparator.",
    },
]

CURRENT_BASELINES = {
    ("pbmc3k_10x", "rmtguard"): 0.8913076392119752,
    ("kang_ifnb_pbmc", "rmtguard"): 0.8260682072984193,
    ("pbmc68k_zheng2017", "rmtguard"): 0.6000000000000000,
}


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


def _mean_fine_callable(run_path: Path, dataset_id: str, method: str) -> float:
    rows = [
        row
        for row in _read_tsv(run_path)
        if row.get("dataset_id") == dataset_id and row.get("method") == method and row.get("fine_callable_compartments", "") != ""
    ]
    if not rows:
        return float("nan")
    return float(np.mean([_float(row.get("fine_callable_compartments")) for row in rows]))


def _decision(
    probe_id: str,
    dataset_id: str,
    method: str | float,
    mean_pairwise_ari: float,
    mean_cluster_n: float | None = None,
    mean_fine_callable: float = float("nan"),
) -> str:
    if not isinstance(method, str):
        old_mean_pairwise_ari = float(method)
        old_mean_cluster_n = float(mean_pairwise_ari)
        method = "rmtguard"
        mean_pairwise_ari = old_mean_pairwise_ari
        mean_cluster_n = old_mean_cluster_n
    if mean_cluster_n is None:
        mean_cluster_n = float("nan")
    if probe_id.startswith("pbmc68k_null_calibrated") and method != "rmtguard":
        return "comparator_context"
    if probe_id.startswith("pbmc68k_coarse_to_fine") and method != "rmtguard_coarse_to_fine":
        return "comparator_context"
    if probe_id.startswith("pbmc68k_coarse_to_fine") and mean_fine_callable == mean_fine_callable and mean_fine_callable <= 0:
        return "reject_reduces_to_coarse_baseline"
    current = CURRENT_BASELINES.get((dataset_id, "rmtguard"), float("nan"))
    delta = mean_pairwise_ari - current if current == current else float("nan")
    if probe_id.startswith("resolution_path") and dataset_id == "pbmc3k_10x" and delta > 0.02:
        return "local_improvement_not_sufficient_for_default"
    if probe_id.startswith("resolution_path") and dataset_id == "kang_ifnb_pbmc" and delta < -0.02:
        return "reject_hurts_kang_stability"
    if dataset_id == "pbmc68k_zheng2017" and (mean_pairwise_ari <= 0.60 or mean_cluster_n < 2.0):
        return "reject_does_not_rescue_pbmc68k"
    if delta == delta and delta > 0.02:
        return "candidate_requires_full_four_dataset_rerun"
    if delta == delta and delta < -0.02:
        return "reject_hurts_current_baseline"
    return "no_material_improvement"


def build_rows(probes: list[dict[str, object]] = PROBES) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for probe in probes:
        path = Path(probe["path"])
        source_rows = _read_tsv(path)
        if not source_rows:
            rows.append(
                {
                    "probe_id": str(probe["probe_id"]),
                    "dataset_id": "not_available",
                    "method": "not_available",
                    "tested_change": str(probe["tested_change"]),
                    "mean_pairwise_ari": "nan",
                    "mean_cluster_n": "nan",
                    "mean_fine_callable_compartments": "nan",
                    "delta_vs_current_rmtguard": "nan",
                    "decision": "incomplete_or_missing_probe",
                    "decision_rule": str(probe["decision_rule"]),
                    "evidence_path": _rel(path),
                }
            )
            continue
        for row in source_rows:
            dataset_id = row.get("dataset_id", "")
            method = row.get("method", "")
            mean_pairwise_ari = _float(row.get("mean_pairwise_ari"))
            mean_cluster_n = _float(row.get("mean_cluster_n"))
            current = CURRENT_BASELINES.get((dataset_id, "rmtguard"), float("nan"))
            delta = mean_pairwise_ari - current if current == current else float("nan")
            mean_fine_callable = _mean_fine_callable(
                Path(probe.get("run_path", "")),
                dataset_id,
                method,
            ) if probe.get("run_path") else float("nan")
            rows.append(
                {
                    "probe_id": str(probe["probe_id"]),
                    "dataset_id": dataset_id,
                    "method": method,
                    "tested_change": str(probe["tested_change"]),
                    "mean_pairwise_ari": _fmt(mean_pairwise_ari),
                    "mean_cluster_n": _fmt(mean_cluster_n),
                    "mean_fine_callable_compartments": _fmt(mean_fine_callable),
                    "delta_vs_current_rmtguard": _fmt(delta),
                    "decision": _decision(str(probe["probe_id"]), dataset_id, method, mean_pairwise_ari, mean_cluster_n, mean_fine_callable),
                    "decision_rule": str(probe["decision_rule"]),
                    "evidence_path": _rel(path),
                }
            )
    return rows


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Algorithm Rescue Probe Report",
        "",
        "This file is generated by `python scripts/build_algorithm_rescue_probe_report.py`.",
        "",
        "## Current Decision",
        "",
        "- None of the current local rescue probes should be promoted to the default RMTGuard algorithm.",
        "- Resolution-path clustering improves PBMC3k stability locally but hurts Kang IFN-beta PBMC stability.",
        "- Low-signal PBMC68k probes do not resolve the collapse/no-call failure without forcing PCs.",
        "- The optional stable low-signal PC rescue keeps synthetic pure-null guarded but worsens PBMC68k stability.",
        "- The null-calibrated low-signal rescue restores synthetic pure-null no-call in smoke testing but does not improve PBMC68k stability.",
        "- Coarse-to-fine probes improve only when they reduce to the coarse PC-rule baseline; no guarded fine layer activates on PBMC68k.",
        "- The `stability_advantage` gate therefore remains `fail`.",
        "",
        "## Probe Rows",
        "",
    ]
    for row in rows:
        lines.append(
            "- `{probe_id}` / `{dataset_id}` / `{method}`: `{decision}`; stability={mean_pairwise_ari}, "
            "cluster_n={mean_cluster_n}, fine_callable={mean_fine_callable_compartments}, "
            "delta={delta_vs_current_rmtguard}. {tested_change}".format(**row)
        )
    lines.extend(
        [
            "",
            "## Next Algorithmic Direction",
            "",
            "1. Do not use fixed `min_embedding_pcs` or manual cluster counts to pass the gate.",
            "2. Target a principled low-signal embedding diagnostic for PBMC68k-like immune data.",
            "3. Preserve the Kang annotation recovery advantage while improving PBMC3k stability.",
            "4. Promote a rescue only after a full four-dataset rerun against elbow, fixed-PC, permutation PCA, and JackStraw-like baselines.",
            "",
            "## Output",
            "",
            f"- Probe summary TSV: `{_rel(OUT_TSV)}`",
        ]
    )
    return lines


FIELDNAMES = [
    "probe_id",
    "dataset_id",
    "method",
    "tested_change",
    "mean_pairwise_ari",
    "mean_cluster_n",
    "mean_fine_callable_compartments",
    "delta_vs_current_rmtguard",
    "decision",
    "decision_rule",
    "evidence_path",
]


def main() -> int:
    rows = build_rows()
    _write_tsv(OUT_TSV, rows, FIELDNAMES)
    _write_text(OUT_MD, build_markdown(rows))
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
