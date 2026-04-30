from __future__ import annotations

"""Build per-dataset diagnostics for the RMTGuard stability gate."""

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STABILITY_SUMMARY = ROOT / "results" / "stability_benchmarks" / "stability_summary.tsv"
STABILITY_RUNS = ROOT / "results" / "stability_benchmarks" / "stability_runs.tsv"
PHASE1_SUMMARY = ROOT / "results" / "phase1_benchmarks" / "phase1_benchmark_summary.tsv"
OUT_TSV = ROOT / "results" / "stability_benchmarks" / "stability_gate_diagnostics.tsv"
OUT_MD = ROOT / "docs" / "stability_gate_diagnostics.md"


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


def _float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _fmt(value: float) -> str:
    if value != value:
        return "nan"
    return f"{value:.6f}"


def _annotation_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str], float]:
    return {
        (row.get("dataset_id", ""), row.get("method", "")): _float(row.get("ari", "nan"))
        for row in rows
    }


def _no_call_lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    by_dataset: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if row.get("method") == "rmtguard":
            by_dataset.setdefault(row.get("dataset_id", ""), []).append(row)
    out: dict[str, dict[str, str]] = {}
    for dataset_id, dataset_rows in by_dataset.items():
        total = len(dataset_rows)
        no_call_rows = [row for row in dataset_rows if row.get("analysis_status") == "diagnostic_no_call"]
        reasons = sorted({row.get("no_call_reason", "") for row in no_call_rows if row.get("no_call_reason")})
        out[dataset_id] = {
            "no_call_count": str(len(no_call_rows)),
            "total_runs": str(total),
            "no_call_fraction": _fmt(len(no_call_rows) / total) if total else "nan",
            "no_call_reasons": ";".join(reasons),
        }
    return out


def build_diagnostics(
    rows: list[dict[str, str]],
    annotation_rows: list[dict[str, str]] | None = None,
    run_rows: list[dict[str, str]] | None = None,
    floor: float = 0.80,
    margin: float = 0.05,
    weak_annotation_threshold: float = 0.20,
) -> list[dict[str, str]]:
    annotation = _annotation_lookup(annotation_rows or [])
    no_calls = _no_call_lookup(run_rows or [])
    by_dataset: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_dataset.setdefault(row.get("dataset_id", ""), []).append(row)

    out: list[dict[str, str]] = []
    for dataset_id in sorted(dataset for dataset in by_dataset if dataset):
        dataset_rows = by_dataset[dataset_id]
        rmt = next((row for row in dataset_rows if row.get("method") == "rmtguard"), None)
        if rmt is None:
            continue

        baseline_rows = [row for row in dataset_rows if not row.get("method", "").startswith("rmtguard")]
        best = max(baseline_rows, key=lambda row: _float(row.get("mean_pairwise_ari", "nan")))
        method_to_score = {
            row.get("method", ""): _float(row.get("mean_pairwise_ari", "nan"))
            for row in dataset_rows
        }
        method_to_cluster_n = {
            row.get("method", ""): _float(row.get("mean_cluster_n", "nan"))
            for row in dataset_rows
        }
        rmt_score = _float(rmt.get("mean_pairwise_ari", "nan"))
        best_score = _float(best.get("mean_pairwise_ari", "nan"))
        best_annotation_ari = annotation.get((dataset_id, best.get("method", "")), float("nan"))
        rmt_annotation_ari = annotation.get((dataset_id, "rmtguard"), float("nan"))
        no_call_info = no_calls.get(dataset_id, {})
        no_call_fraction = _float(no_call_info.get("no_call_fraction", "nan"))
        delta_best = rmt_score - best_score

        low_signal_collapse = (
            rmt_score < floor
            and method_to_cluster_n.get("rmtguard", 0.0) < 2.0
            and no_call_fraction == no_call_fraction
            and no_call_fraction >= 0.50
        )
        weak_best_annotation = best_annotation_ari == best_annotation_ari and best_annotation_ari < weak_annotation_threshold
        if low_signal_collapse and weak_best_annotation:
            status = "diagnostic_no_call"
        elif rmt_score < floor:
            status = "fail_below_floor"
        elif rmt_score > best_score:
            status = "pass_beats_best_baseline"
        elif rmt_score >= best_score - margin:
            status = "borderline_within_margin"
        else:
            status = "fail_below_best_baseline"

        notes = []
        if status == "fail_below_floor":
            notes.append(f"RMTGuard stability is below the pre-specified {floor:.2f} floor.")
        if method_to_cluster_n.get("rmtguard", 0.0) < 2.0:
            notes.append("RMTGuard collapses to fewer than two clusters on average.")
        if status == "diagnostic_no_call":
            notes.append(f"Best stable comparator has weak annotation ARI={best_annotation_ari:.3f}, supporting low-confidence no-call rather than a positive discovery claim.")
            notes.append("RMTGuard no-call reasons: " + (no_call_info.get("no_call_reasons") or "not_recorded") + ".")
        if best.get("method") == "fixed_pcs_30" and delta_best < 0:
            notes.append("Fixed n_pcs=30 remains the strongest comparator.")
        if rmt_score > best_score:
            notes.append("RMTGuard exceeds all non-RMTGuard baselines.")
        if not notes:
            notes.append("RMTGuard is close to the best baseline but not a clear win.")

        out.append(
            {
                "dataset_id": dataset_id,
                "status": status,
                "rmtguard_mean_pairwise_ari": _fmt(rmt_score),
                "best_baseline_method": best.get("method", ""),
                "best_baseline_mean_pairwise_ari": _fmt(best_score),
                "delta_vs_best_baseline": _fmt(delta_best),
                "delta_vs_scanpy_like": _fmt(rmt_score - method_to_score.get("scanpy_default_like", float("nan"))),
                "delta_vs_fixed30": _fmt(rmt_score - method_to_score.get("fixed_pcs_30", float("nan"))),
                "rmtguard_mean_cluster_n": _fmt(method_to_cluster_n.get("rmtguard", float("nan"))),
                "fixed30_mean_cluster_n": _fmt(method_to_cluster_n.get("fixed_pcs_30", float("nan"))),
                "rmtguard_annotation_ari": _fmt(rmt_annotation_ari),
                "best_baseline_annotation_ari": _fmt(best_annotation_ari),
                "rmtguard_no_call_fraction": no_call_info.get("no_call_fraction", "nan"),
                "rmtguard_no_call_reasons": no_call_info.get("no_call_reasons", ""),
                "n_repeats": rmt.get("n_repeats", ""),
                "sample_fraction": rmt.get("sample_fraction", ""),
                "notes": " ".join(notes),
            }
        )
    return out


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# Stability Gate Diagnostics",
        "",
        "This file is generated by `python scripts/build_stability_gate_report.py`.",
        "",
        "## Current Interpretation",
        "",
        "- The multi-dataset evidence supports a callability-aware stability/no-call interpretation, not broad superiority over every fixed-PC baseline.",
        "- RMTGuard is strong on Kang IFN-beta PBMC and close on Baron pancreas.",
        "- PBMC3k remains slightly below fixed `n_pcs=30`.",
        "- PBMC68k/Zheng 2017 is a low-confidence diagnostic no-call: RMTGuard falls below the 0.80 stability floor and collapses to very few clusters, but the strongest stable comparator also has weak annotation recovery.",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend(["", "## Per-Dataset Diagnostics", ""])
    for row in rows:
        lines.append(
            "- `{dataset_id}`: {status}; RMTGuard={rmtguard_mean_pairwise_ari}, "
            "best={best_baseline_method} {best_baseline_mean_pairwise_ari}, "
            "delta={delta_vs_best_baseline}; {notes}".format(**row)
        )
    lines.extend(
        [
            "",
            "## Source",
            "",
            f"- Stability summary: `{_rel(STABILITY_SUMMARY)}`",
            f"- Diagnostics table: `{_rel(OUT_TSV)}`",
        ]
    )
    return lines


def main() -> int:
    rows = _read_tsv(STABILITY_SUMMARY)
    annotation_rows = _read_tsv(PHASE1_SUMMARY)
    run_rows = _read_tsv(STABILITY_RUNS)
    diagnostics = build_diagnostics(rows, annotation_rows, run_rows)
    _write_tsv(
        OUT_TSV,
        diagnostics,
        [
            "dataset_id",
            "status",
            "rmtguard_mean_pairwise_ari",
            "best_baseline_method",
            "best_baseline_mean_pairwise_ari",
            "delta_vs_best_baseline",
            "delta_vs_scanpy_like",
            "delta_vs_fixed30",
            "rmtguard_mean_cluster_n",
            "fixed30_mean_cluster_n",
            "rmtguard_annotation_ari",
            "best_baseline_annotation_ari",
            "rmtguard_no_call_fraction",
            "rmtguard_no_call_reasons",
            "n_repeats",
            "sample_fraction",
            "notes",
        ],
    )
    _write_text(OUT_MD, build_markdown(diagnostics))
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
