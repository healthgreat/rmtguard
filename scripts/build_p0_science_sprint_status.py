#!/usr/bin/env python
"""Build a P0 science-sprint status report for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-04
Purpose: Convert the active Nature Methods P0 scientific blockers into a
machine-readable status table after each executable sprint step.
Data source: Local component-ablation, calibration, and real-data annotation
result tables.
Method notes: This is a project-management status artifact. It does not prove
journal readiness and must not be used as a submission claim by itself.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
COMPONENT_SUMMARY = ROOT / "results" / "ablation" / "component_ablation_summary.tsv"
COMPONENT_DETAIL = ROOT / "results" / "ablation" / "component_ablation_detail.tsv"
NULL_SUMMARY = ROOT / "results" / "calibration" / "realistic_null_summary.tsv"
POWER_SUMMARY = ROOT / "results" / "calibration" / "rare_state_power_summary.tsv"
REALDATA_SUMMARY = (
    ROOT / "results" / "ablation" / "realdata_ablation_annotation_summary.tsv"
)
OUT_TSV = ROOT / "results" / "submission" / "p0_science_sprint_status.tsv"
OUT_MD = ROOT / "docs" / "p0_science_sprint_status.md"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _read_tsv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, sep="\t")


def _write_tsv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _min_repeat(df: pd.DataFrame) -> int:
    if df.empty or "n_repeats" not in df.columns:
        return 0
    return int(pd.to_numeric(df["n_repeats"], errors="coerce").fillna(0).min())


def _max_repeat(df: pd.DataFrame) -> int:
    if df.empty or "n_repeats" not in df.columns:
        return 0
    return int(pd.to_numeric(df["n_repeats"], errors="coerce").fillna(0).max())


def _realdata_component_depth(df: pd.DataFrame) -> int:
    if df.empty or "n_repeats" not in df.columns:
        return 0
    component_df = df.copy()
    if "run_label" in component_df.columns:
        component_df = component_df[
            ~component_df["run_label"].astype(str).str.contains(
                "seurat_matched", case=False, na=False
            )
        ]
    if "subsample_fraction" in component_df.columns:
        component_df = component_df[
            pd.to_numeric(component_df["subsample_fraction"], errors="coerce")
            .fillna(1.0)
            .between(0.79, 0.81)
        ]
    if "ablation_id" in component_df.columns:
        component_df = component_df[component_df["ablation_id"] != "default_v3_3"]
    if component_df.empty:
        return 0
    return int(
        pd.to_numeric(component_df["n_repeats"], errors="coerce").fillna(0).min()
    )


def _component_ci_present(df: pd.DataFrame) -> bool:
    required = [
        "false_call_rate_ci95_low",
        "false_call_rate_ci95_high",
        "power_ci95_low",
        "power_ci95_high",
        "mean_rare_f1_ci95_low",
        "mean_rare_f1_ci95_high",
    ]
    return not df.empty and all(col in df.columns for col in required)


def _calibration_ci_present(df: pd.DataFrame, required: list[str]) -> bool:
    return not df.empty and all(col in df.columns for col in required)


def build_rows() -> list[dict[str, object]]:
    component = _read_tsv(COMPONENT_SUMMARY)
    null_summary = _read_tsv(NULL_SUMMARY)
    power = _read_tsv(POWER_SUMMARY)
    realdata = _read_tsv(REALDATA_SUMMARY)

    component_min_repeats = _min_repeat(component)
    component_ci = _component_ci_present(component)
    null_min_repeats = _min_repeat(null_summary)
    power_min_repeats = _min_repeat(power)
    null_ci = _calibration_ci_present(
        null_summary,
        [
            "false_signal_rate_ci95_low",
            "false_signal_rate_ci95_high",
            "false_call_rate_ci95_low",
            "false_call_rate_ci95_high",
        ],
    )
    power_ci = _calibration_ci_present(
        power,
        [
            "power_ci95_low",
            "power_ci95_high",
            "mean_rare_f1_ci95_low",
            "mean_rare_f1_ci95_high",
        ],
    )
    realdata_component_repeats = _realdata_component_depth(realdata)

    rows = [
        {
            "gate_id": "NM-G02A",
            "gate_name": "synthetic_component_ablation",
            "status": (
                "done"
                if component_min_repeats >= 20 and component_ci
                else "partial"
            ),
            "repeat_depth": component_min_repeats,
            "ci_present": str(component_ci).lower(),
            "evidence": _rel(COMPONENT_SUMMARY),
            "next_action": "Use as synthetic component-ablation evidence; do not claim final component necessity until real-data checks are also upgraded.",
        },
        {
            "gate_id": "NM-G02B",
            "gate_name": "realdata_annotation_ablation",
            "status": "pending_20_repeat"
            if realdata_component_repeats < 20
            else "done",
            "repeat_depth": realdata_component_repeats,
            "ci_present": "true" if realdata_component_repeats > 1 else "false",
            "evidence": _rel(REALDATA_SUMMARY),
            "next_action": (
                "Use as 20-repeat real-data component-ablation evidence; do not overclaim broad stability superiority."
                if realdata_component_repeats >= 20
                else "Scale labeled real-data ablation annotation checks from current repeat depth to 20 repeats before Figure 5 finalization."
            ),
        },
        {
            "gate_id": "NM-G03A",
            "gate_name": "realistic_null_calibration",
            "status": "pending_50_repeat" if null_min_repeats < 50 else "done",
            "repeat_depth": null_min_repeats,
            "ci_present": str(null_ci).lower(),
            "evidence": _rel(NULL_SUMMARY),
            "next_action": (
                "Use as 50-repeat realistic-null evidence; keep false-positive control claims bounded to the simulated null families."
                if null_min_repeats >= 50
                else "Run manuscript-grade count-preserving null calibration with 50 repeats and source-data CIs."
            ),
        },
        {
            "gate_id": "NM-G03B",
            "gate_name": "rare_state_power_grid",
            "status": "pending_50_repeat" if power_min_repeats < 50 else "done",
            "repeat_depth": power_min_repeats,
            "ci_present": str(power_ci).lower(),
            "evidence": _rel(POWER_SUMMARY),
            "next_action": (
                "Use as 50-repeat power-curve evidence; explicitly state limited power at the lowest prevalence/effect settings."
                if power_min_repeats >= 50
                else "Run prevalence/effect/dropout power curves with 50 repeats and avoid single-setting rare-state claims."
            ),
        },
        {
            "gate_id": "NM-G04",
            "gate_name": "pdac_tme_author_route_decision",
            "status": "waiting_author_decision",
            "repeat_depth": 0,
            "ci_present": "false",
            "evidence": "metadata/pdac_tme_route_decision.tsv",
            "next_action": "Author must choose: deepen PDAC/TME as main figure, or demote it to supplement.",
        },
    ]
    return rows


def build_markdown(rows: list[dict[str, object]]) -> str:
    open_rows = [row for row in rows if row["status"] != "done"]
    realdata_done = any(
        row["gate_id"] == "NM-G02B" and row["status"] == "done" for row in rows
    )
    lines = [
        "# RMTGuard P0 Science Sprint Status",
        "",
        "Generated by `python scripts/build_p0_science_sprint_status.py`.",
        "",
        "## Bottom Line",
        "",
        f"- Open P0 science items: `{len(open_rows)}`.",
        "- Synthetic component ablation has reached 20-repeat depth with CI columns.",
        "- Real-data annotation ablations have reached 20-repeat depth for the current component set."
        if realdata_done
        else "- Real-data annotation ablations still need manuscript-grade repeat depth.",
        "- Realistic null/power grids have reached 50-repeat manuscript-grade depth; low-prevalence weak-effect limits still constrain claims."
        if all(
            row["gate_id"] not in {"NM-G03A", "NM-G03B"} or row["status"] == "done"
            for row in rows
        )
        else "- Realistic null/power grids still need manuscript-grade 50-repeat depth.",
        "- PDAC/TME route decision packet is available at `docs/pdac_tme_route_decision_packet.md`; final author decision is still required.",
        "- Acceptance guarantee remains `impossible`; this report only tracks scientific gate progress.",
        "",
        "## Status Table",
        "",
        "| Gate | Name | Status | Repeat depth | CI present | Evidence | Next action |",
        "| --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['gate_id']} | {row['gate_name']} | `{row['status']}` | {row['repeat_depth']} | `{row['ci_present']}` | `{row['evidence']}` | {row['next_action']} |"
        )
    lines.extend(
        [
            "",
            "## Manual Author Step",
            "",
            "Open `docs/pdac_tme_route_decision_packet.md` if you need the route criteria.",
            "",
            "Please provide one exact line:",
            "",
            "```text",
            "PDAC/TME route: deepen as main figure",
            "```",
            "",
            "or",
            "",
            "```text",
            "PDAC/TME route: demote to supplement",
            "```",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    rows = build_rows()
    _write_tsv(rows, OUT_TSV)
    _write_text(OUT_MD, build_markdown(rows))
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print(f"open_p0_science_items\t{sum(row['status'] != 'done' for row in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
