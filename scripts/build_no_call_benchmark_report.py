from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SYNTHETIC = ROOT / "results" / "synthetic_benchmarks" / "synthetic_benchmark_summary.csv"
OUT_DIR = ROOT / "results" / "no_call_benchmarks"
SUMMARY_TSV = OUT_DIR / "no_call_summary.tsv"
DOC_MD = ROOT / "docs" / "no_call_benchmark.md"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "scenario",
        "expected_behavior",
        "analysis_status",
        "no_call_reason",
        "n_signal_pcs",
        "accepted_embedding_pcs",
        "cluster_n",
        "ari",
        "decision",
        "notes",
    ]
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _float(value: str | None) -> float:
    try:
        return float(value) if value not in {None, ""} else float("nan")
    except ValueError:
        return float("nan")


def _fmt(value: float) -> str:
    return "nan" if math.isnan(value) else f"{value:.6f}"


def _rmtguard_rows(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {
        row.get("scenario", ""): row
        for row in rows
        if row.get("method") == "rmtguard" and row.get("scenario")
    }


def classify_no_call(row: dict[str, str] | None, scenario: str) -> dict[str, str]:
    if row is None:
        return {
            "scenario": scenario,
            "expected_behavior": _expected_behavior(scenario),
            "analysis_status": "missing",
            "no_call_reason": "",
            "n_signal_pcs": "nan",
            "accepted_embedding_pcs": "nan",
            "cluster_n": "nan",
            "ari": "nan",
            "decision": "fail",
            "notes": "Scenario missing from synthetic benchmark summary.",
        }

    analysis_status = row.get("analysis_status", "")
    no_call_reason = row.get("no_call_reason", "")
    n_signal = _float(row.get("n_signal_pcs"))
    accepted = _float(row.get("accepted_embedding_pcs"))
    cluster_n = _float(row.get("cluster_n"))
    ari = _float(row.get("ari"))
    expected = _expected_behavior(scenario)

    if scenario == "pure_null":
        passed = analysis_status == "diagnostic_no_call" and n_signal <= 1
        decision = "pass" if passed else "fail"
        notes = (
            "Null matrix correctly returned diagnostic_no_call with <=1 signal PC."
            if passed
            else "Pure-null data should not produce a positive cell-state call."
        )
    elif scenario == "planted_low_rank":
        passed = analysis_status == "ok" and ari >= 0.80 and accepted >= max(1.0, n_signal)
        decision = "pass" if passed else "fail"
        notes = (
            "Strong planted signal remained callable and recoverable."
            if passed
            else "Strong planted signal should remain callable with high ARI."
        )
    elif scenario == "rare_state":
        passed = analysis_status == "ok" and ari >= 0.90
        decision = "pass" if passed else "fail"
        notes = (
            "Rare-state recovery passed the pre-specified ARI >=0.90 floor."
            if passed
            else "Rare-state benchmark did not meet the ARI >=0.90 floor."
        )
    else:
        if analysis_status in {"ok", "diagnostic_no_call"}:
            decision = "monitor"
            notes = "Stress scenario recorded for interpretation, not used as a hard no-call gate."
        else:
            decision = "fail"
            notes = "RMTGuard did not report a recognized analysis_status."

    return {
        "scenario": scenario,
        "expected_behavior": expected,
        "analysis_status": analysis_status or "not_recorded",
        "no_call_reason": no_call_reason,
        "n_signal_pcs": _fmt(n_signal),
        "accepted_embedding_pcs": _fmt(accepted),
        "cluster_n": _fmt(cluster_n),
        "ari": _fmt(ari),
        "decision": decision,
        "notes": notes,
    }


def _expected_behavior(scenario: str) -> str:
    if scenario == "pure_null":
        return "diagnostic_no_call"
    if scenario in {"planted_low_rank", "rare_state"}:
        return "positive_call"
    return "stress_monitor"


def build_rows(synthetic_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_scenario = _rmtguard_rows(synthetic_rows)
    ordered = [
        "pure_null",
        "planted_low_rank",
        "rare_state",
        "batch_effect",
        "dropout_stress",
        "continuous_trajectory",
        "overclustering_stress",
    ]
    return [classify_no_call(by_scenario.get(scenario), scenario) for scenario in ordered]


def build_markdown(rows: list[dict[str, str]], synthetic_path: Path, summary_path: Path) -> str:
    hard_rows = [row for row in rows if row["expected_behavior"] in {"diagnostic_no_call", "positive_call"}]
    hard_pass = sum(row["decision"] == "pass" for row in hard_rows)
    hard_total = len(hard_rows)
    lines = [
        "# RMTGuard diagnostic no-call benchmark",
        "",
        "This report validates that RMTGuard can distinguish a guarded diagnostic no-call from a positive cell-state discovery claim.",
        "",
        "## Inputs",
        "",
        f"- Synthetic benchmark summary: `{_rel(synthetic_path)}`",
        f"- No-call summary table: `{_rel(summary_path)}`",
        "",
        "## Hard-gate summary",
        "",
        f"- Required no-call/positive-call checks passed: {hard_pass}/{hard_total}",
        "- Pure-null matrices are expected to return `diagnostic_no_call` and <=1 signal PC.",
        "- Planted low-rank and rare-state matrices are expected to remain positive calls.",
        "",
        "## Scenario decisions",
        "",
        "| Scenario | Expected | Status | Reason | n_signal_pcs | accepted_embedding_pcs | ARI | Decision |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {scenario} | {expected_behavior} | {analysis_status} | {no_call_reason} | {n_signal_pcs} | {accepted_embedding_pcs} | {ari} | {decision} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "A `diagnostic_no_call` is not reported as a biological discovery. It is a guarded output indicating that the random-matrix noise-control layer found insufficient stable signal for downstream cell-state claims.",
            "",
        ]
    )
    return "\n".join(lines)


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the RMTGuard diagnostic no-call benchmark report.")
    parser.add_argument("--synthetic", type=Path, default=DEFAULT_SYNTHETIC)
    parser.add_argument("--out", type=Path, default=SUMMARY_TSV)
    parser.add_argument("--doc", type=Path, default=DOC_MD)
    args = parser.parse_args(argv)

    rows = build_rows(_read_csv(args.synthetic))
    _write_tsv(args.out, rows)
    _write_text(args.doc, build_markdown(rows, args.synthetic, args.out))
    print(_rel(args.out))
    print(_rel(args.doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
