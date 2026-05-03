#!/usr/bin/env python
"""Build the RMTGuard callability/no-call decision map.

Author: RMTGuard development team
Date: 2026-05-01
Purpose: Convert synthetic no-call checks and real public benchmark diagnostics
into an auditable decision table for Figure 3 and manuscript review.
Data source: results/no_call_benchmarks/no_call_summary.tsv,
results/figures/source_data/figure3_public_benchmark_summary.tsv, and
results/figures/source_data/figure3_pbmc3k_stability_summary.tsv.
Method notes: This script does not reclassify biological findings by hand. It
applies explicit thresholds to existing diagnostics and preserves weak datasets
as caveated or no-call contexts.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
NO_CALL_SUMMARY = ROOT / "results" / "no_call_benchmarks" / "no_call_summary.tsv"
PUBLIC_BENCHMARK = (
    ROOT
    / "results"
    / "figures"
    / "source_data"
    / "figure3_public_benchmark_summary.tsv"
)
STABILITY = (
    ROOT
    / "results"
    / "figures"
    / "source_data"
    / "figure3_pbmc3k_stability_summary.tsv"
)

OUT_DIR = ROOT / "results" / "callability"
OUT_TSV = OUT_DIR / "no_call_decision_map.tsv"
FIG3_SOURCE = (
    ROOT
    / "results"
    / "figures"
    / "source_data"
    / "figure3_callability_decision_map.tsv"
)
DOC = ROOT / "docs" / "no_call_decision_map.md"

DATASET_LABELS = {
    "pbmc3k_10x": "PBMC3k",
    "kang_ifnb_pbmc": "Kang IFN-beta PBMC",
    "baron_pancreas": "Baron pancreas",
    "pbmc68k_zheng2017": "PBMC68k",
}

SCENARIO_LABELS = {
    "pure_null": "pure null",
    "planted_low_rank": "planted low-rank",
    "rare_state": "rare state",
    "batch_effect": "batch effect",
    "dropout_stress": "dropout stress",
    "continuous_trajectory": "continuous trajectory",
    "overclustering_stress": "overclustering stress",
}

DECISION_SCORE = {
    "positive_control_pass": 1.0,
    "callable_bounded": 0.85,
    "callable_with_caveat": 0.55,
    "stress_monitor": 0.50,
    "diagnostic_no_call": 0.10,
}


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


def _num(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return math.nan
    if math.isnan(number):
        return math.nan
    return number


def _fmt(value: object, digits: int = 3) -> str:
    number = _num(value)
    if math.isnan(number):
        return "-"
    return f"{number:.{digits}f}"


def _label_unit(unit_id: str, unit_type: str) -> str:
    if unit_type == "synthetic":
        return SCENARIO_LABELS.get(unit_id, unit_id.replace("_", " "))
    return DATASET_LABELS.get(unit_id, unit_id.replace("_", " "))


def _claim_for_decision(decision: str) -> str:
    if decision == "diagnostic_no_call":
        return "Do not report as biological discovery; describe as diagnostic no-call or low-confidence context."
    if decision == "callable_with_caveat":
        return "Report only as bounded benchmark evidence with explicit caveats."
    if decision == "stress_monitor":
        return "Use for stress-test interpretation only, not as a hard manuscript success gate."
    return "Callable within current evidence boundary."


def _synthetic_rows() -> list[dict[str, object]]:
    df = pd.read_csv(NO_CALL_SUMMARY, sep="\t")
    rows: list[dict[str, object]] = []
    for row in df.itertuples(index=False):
        unit_id = str(row.scenario)
        expected = str(row.expected_behavior)
        decision_raw = str(row.decision)
        if (
            expected in {"diagnostic_no_call", "positive_call"}
            and decision_raw == "pass"
        ):
            decision = (
                "diagnostic_no_call"
                if expected == "diagnostic_no_call"
                else "positive_control_pass"
            )
        else:
            decision = "stress_monitor"
        flags = []
        if expected == "diagnostic_no_call":
            flags.append("expected_no_call_control")
        if expected == "positive_call":
            flags.append("expected_positive_control")
        if expected == "stress_monitor":
            flags.append("stress_monitor_not_hard_gate")
        rows.append(
            {
                "unit_type": "synthetic",
                "unit_id": unit_id,
                "unit_label": _label_unit(unit_id, "synthetic"),
                "decision": decision,
                "decision_score": DECISION_SCORE[decision],
                "analysis_status": row.analysis_status,
                "primary_reason": (
                    str(row.no_call_reason).replace("_", " ")
                    if isinstance(row.no_call_reason, str) and row.no_call_reason
                    else str(row.notes)
                ),
                "flags": ";".join(flags),
                "n_signal_pcs": _fmt(row.n_signal_pcs, 1),
                "accepted_embedding_pcs": _fmt(row.accepted_embedding_pcs, 1),
                "cluster_n": _fmt(row.cluster_n, 1),
                "annotation_ari": _fmt(row.ari, 3),
                "stability_ari": "-",
                "best_baseline_stability_ari": "-",
                "stability_gap_to_best": "-",
                "recommended_claim": _claim_for_decision(decision),
            }
        )
    return rows


def _real_rows() -> list[dict[str, object]]:
    public = pd.read_csv(PUBLIC_BENCHMARK, sep="\t")
    stability = pd.read_csv(STABILITY, sep="\t")
    rmt = public[public["method"] == "rmtguard"].copy()
    rmt_stab = stability[stability["method"] == "rmtguard"][
        ["dataset_id", "mean_pairwise_ari", "mean_cluster_n"]
    ].rename(
        columns={
            "mean_pairwise_ari": "rmtguard_stability_ari",
            "mean_cluster_n": "rmtguard_mean_cluster_n",
        }
    )
    best_stab = (
        stability[stability["method"] != "rmtguard"]
        .groupby("dataset_id")["mean_pairwise_ari"]
        .max()
        .rename("best_baseline_stability_ari")
        .reset_index()
    )
    merged = rmt.merge(rmt_stab, on="dataset_id", how="left").merge(
        best_stab, on="dataset_id", how="left"
    )

    rows: list[dict[str, object]] = []
    for row in merged.itertuples(index=False):
        unit_id = str(row.dataset_id)
        ari = _num(row.ari)
        stability_ari = _num(row.rmtguard_stability_ari)
        best = _num(row.best_baseline_stability_ari)
        cluster_n = _num(row.cluster_n)
        mean_cluster_n = _num(row.rmtguard_mean_cluster_n)
        n_signal = _num(row.n_signal_pcs)
        accepted = _num(row.accepted_embedding_pcs)
        gap = (
            best - stability_ari
            if not math.isnan(best) and not math.isnan(stability_ari)
            else math.nan
        )

        flags: list[str] = []
        if not math.isnan(n_signal) and n_signal <= 1:
            flags.append("insufficient_signal_pcs")
        if not math.isnan(accepted) and accepted <= 1:
            flags.append("insufficient_embedding_pcs")
        if not math.isnan(mean_cluster_n) and mean_cluster_n < 2:
            flags.append("low_subsampling_cluster_count")
        if not math.isnan(cluster_n) and cluster_n <= 3:
            flags.append("low_cluster_count")
        if not math.isnan(ari) and ari < 0.20:
            flags.append("weak_annotation_recovery")
        if not math.isnan(gap) and gap > 0.05:
            flags.append("below_best_stability_baseline")
        if math.isnan(ari):
            flags.append("no_public_annotation_ari")

        if {
            "weak_annotation_recovery",
            "low_subsampling_cluster_count",
        }.issubset(flags) or {
            "insufficient_signal_pcs",
            "insufficient_embedding_pcs",
        }.intersection(
            flags
        ):
            decision = "diagnostic_no_call"
        elif any(
            flag in flags
            for flag in ["below_best_stability_baseline", "low_cluster_count"]
        ):
            decision = "callable_with_caveat"
        else:
            decision = "callable_bounded"

        reason = _reason_from_flags(flags)
        rows.append(
            {
                "unit_type": "real_public",
                "unit_id": unit_id,
                "unit_label": _label_unit(unit_id, "real_public"),
                "decision": decision,
                "decision_score": DECISION_SCORE[decision],
                "analysis_status": row.analysis_status,
                "primary_reason": reason,
                "flags": ";".join(flags) if flags else "none",
                "n_signal_pcs": _fmt(n_signal, 1),
                "accepted_embedding_pcs": _fmt(accepted, 1),
                "cluster_n": _fmt(cluster_n, 1),
                "annotation_ari": _fmt(ari, 3),
                "stability_ari": _fmt(stability_ari, 3),
                "best_baseline_stability_ari": _fmt(best, 3),
                "stability_gap_to_best": _fmt(gap, 3),
                "recommended_claim": _claim_for_decision(decision),
            }
        )
    return rows


def _reason_from_flags(flags: list[str]) -> str:
    if not flags:
        return "No automatic callability caveat triggered by current thresholds."
    text = {
        "insufficient_signal_pcs": "insufficient signal PCs",
        "insufficient_embedding_pcs": "insufficient embedding PCs",
        "low_subsampling_cluster_count": "low cluster count across subsampling",
        "low_cluster_count": "low cluster count in the full run",
        "weak_annotation_recovery": "weak annotation recovery",
        "below_best_stability_baseline": "below strongest stability baseline",
        "no_public_annotation_ari": "no public annotation ARI available",
    }
    return "; ".join(text.get(flag, flag.replace("_", " ")) for flag in flags)


def build_decision_map() -> pd.DataFrame:
    rows = _synthetic_rows() + _real_rows()
    order = {
        "synthetic": 0,
        "real_public": 1,
    }
    df = pd.DataFrame(rows)
    df["_order"] = df["unit_type"].map(order).fillna(99)
    df = df.sort_values(["_order", "unit_id"]).drop(columns=["_order"])
    return df


def build_doc(df: pd.DataFrame) -> str:
    counts = df["decision"].value_counts().to_dict()
    lines = [
        "# RMTGuard callability and no-call decision map",
        "",
        "This report turns RMTGuard's diagnostic boundary into an auditable table for Figure 3 and manuscript review.",
        "",
        "## Decision Rules",
        "",
        "- `diagnostic_no_call`: insufficient signal/embedding PCs, or weak annotation recovery combined with unstable low cluster count.",
        "- `callable_with_caveat`: callable run with a clear benchmark caveat, such as lower stability than the strongest comparator or low cluster count.",
        "- `callable_bounded`: callable within the current evidence boundary.",
        "- `positive_control_pass`: synthetic positive-control scenario passed.",
        "- `stress_monitor`: synthetic stress test recorded for interpretation, not as a hard success gate.",
        "",
        "## Decision Counts",
        "",
    ]
    for key in sorted(counts):
        lines.append(f"- `{key}`: {counts[key]}")
    lines.extend(
        [
            "",
            "## Decision Map",
            "",
            "| Unit type | Unit | Decision | Score | Main reason | Recommended claim |",
            "| --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for row in df.itertuples(index=False):
        lines.append(
            f"| {row.unit_type} | {row.unit_label} | {row.decision} | {row.decision_score:.2f} | {row.primary_reason} | {row.recommended_claim} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "A no-call or caveated call is not a failed hidden result to relabel as a discovery. It is a manuscript-facing guardrail that limits the claim to what the data support.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    df = build_decision_map()
    _atomic_write_tsv(df, OUT_TSV)
    _atomic_write_tsv(df, FIG3_SOURCE)
    _atomic_write_text(build_doc(df), DOC)
    print(_rel(OUT_TSV))
    print(_rel(FIG3_SOURCE))
    print(_rel(DOC))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
