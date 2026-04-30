from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "figures"
SOURCE_DIR = OUT_DIR / "source_data"
MANIFEST = OUT_DIR / "figure_reproducibility.tsv"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _atomic_replace(tmp_path: Path, final_path: Path) -> None:
    final_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.replace(final_path)


def _copy_atomic(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    shutil.copyfile(src, tmp)
    _atomic_replace(tmp, dst)


def _read_delimited(path: Path, delimiter: str) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def _write_delimited(path: Path, rows: Iterable[dict[str, object]], delimiter: str = "\t") -> None:
    rows = [dict(row) for row in rows]
    if not rows:
        raise ValueError(f"No rows to write for {path}")
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _stringify(row.get(key, "")) for key in fieldnames})
    _atomic_replace(tmp, path)


def _stringify(value: object) -> str:
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _details_to_rows(path: Path, dataset_id: str) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    with path.open("r", encoding="utf-8") as handle:
        details = json.load(handle)

    diagnostics: list[dict[str, object]] = []
    for group in ["pc_diagnostics", "hvg_diagnostics", "embedding_diagnostics"]:
        values = details.get(group, {})
        if not isinstance(values, dict):
            continue
        for metric, value in values.items():
            if metric == "pc_records":
                continue
            diagnostics.append(
                {
                    "dataset_id": dataset_id,
                    "diagnostic_group": group,
                    "metric": metric,
                    "value": value,
                }
            )

    pc_records = []
    embedding = details.get("embedding_diagnostics", {})
    for record in embedding.get("pc_records", []):
        pc_records.append({"dataset_id": dataset_id, **record})
    return diagnostics, pc_records


def _combined_marker_rows(paths: list[tuple[str, Path]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for dataset_id, path in paths:
        for row in _read_delimited(path, "\t"):
            rows.append({"dataset_id": dataset_id, **row})
    return rows


def _runtime_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    synthetic = ROOT / "results" / "synthetic_benchmarks" / "synthetic_benchmark_summary.csv"
    phase1 = ROOT / "results" / "phase1_benchmarks" / "phase1_benchmark_summary.tsv"
    for source, benchmark, delimiter, id_col in [
        (synthetic, "synthetic", ",", "scenario"),
        (phase1, "public_real", "\t", "dataset_id"),
    ]:
        if not source.exists():
            continue
        for row in _read_delimited(source, delimiter):
            if row.get("method") != "rmtguard":
                continue
            rows.append(
                {
                    "benchmark": benchmark,
                    "unit_id": row.get(id_col, ""),
                    "method": row.get("method", ""),
                    "runtime_seconds": row.get("runtime_seconds", ""),
                    "peak_memory_mb": row.get("peak_memory_mb", ""),
                    "selected_hvg_n": row.get("selected_hvg_n", ""),
                    "n_signal_pcs": row.get("n_signal_pcs", ""),
                    "accepted_embedding_pcs": row.get("accepted_embedding_pcs", ""),
                    "cluster_n": row.get("cluster_n", ""),
                }
            )
    return rows


def _ablation_rows(paths: list[tuple[str, Path]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for ablation_id, path in paths:
        if not path.exists():
            continue
        for row in _read_delimited(path, "\t"):
            rows.append({"ablation_id": ablation_id, **row})
    return rows


def _ready(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def _manifest_row(
    figure_id: str,
    panel: str,
    source_data_path: Path,
    input_paths: list[Path],
    notes: str,
) -> dict[str, str]:
    missing = [path for path in input_paths if not path.exists()]
    status = "ready" if not missing and _ready(source_data_path) else "missing"
    if missing:
        notes = notes + " Missing inputs: " + "; ".join(_rel(path) for path in missing)
    return {
        "figure_id": figure_id,
        "panel": panel,
        "source_data_path": _rel(source_data_path),
        "input_paths": ";".join(_rel(path) for path in input_paths),
        "regeneration_command": "python scripts/build_figure_source_data.py",
        "status": status,
        "notes": notes,
    }


def build_source_data() -> list[dict[str, str]]:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    synthetic_summary = ROOT / "results" / "synthetic_benchmarks" / "synthetic_benchmark_summary.csv"
    no_call_summary = ROOT / "results" / "no_call_benchmarks" / "no_call_summary.tsv"
    phase1_summary = ROOT / "results" / "phase1_benchmarks" / "phase1_benchmark_summary.tsv"
    stability_summary = ROOT / "results" / "stability_benchmarks" / "stability_summary.tsv"
    pdac_summary = ROOT / "results" / "pdac_tme" / "showcase_summary.tsv"
    gate_evidence = ROOT / "results" / "gates" / "gate_evidence.tsv"
    gate_report = ROOT / "results" / "gates" / "gate_report.tsv"
    pdac_details = ROOT / "results" / "pdac_tme" / "pdac_gse154778_rmtguard_details.json"
    pdac_primary_markers = ROOT / "results" / "pdac_tme" / "pdac_gse154778_cluster_marker_summary.tsv"
    pdac_validation_markers = ROOT / "results" / "pdac_tme" / "pdac_gse263733_cluster_marker_summary.tsv"

    manifest: list[dict[str, str]] = []

    fig1_diagnostics = SOURCE_DIR / "figure1_algorithm_diagnostics.tsv"
    fig1_pc_records = SOURCE_DIR / "figure1_embedding_pc_records.tsv"
    diagnostics, pc_records = _details_to_rows(pdac_details, "pdac_gse154778")
    _write_delimited(fig1_diagnostics, diagnostics)
    _write_delimited(fig1_pc_records, pc_records)
    manifest.append(
        _manifest_row(
            "Figure 1",
            "algorithm diagnostics",
            fig1_diagnostics,
            [pdac_details],
            "MP/TW edge, HVG plateau, and adaptive embedding diagnostics from the PDAC main run.",
        )
    )
    manifest.append(
        _manifest_row(
            "Figure 1",
            "embedding PC records",
            fig1_pc_records,
            [pdac_details],
            "Per-PC strict-signal, near-edge, stability, and acceptance records.",
        )
    )

    fig2 = SOURCE_DIR / "figure2_synthetic_benchmark_summary.csv"
    fig2_no_call = SOURCE_DIR / "figure2_no_call_summary.tsv"
    _copy_atomic(synthetic_summary, fig2)
    _copy_atomic(no_call_summary, fig2_no_call)
    manifest.append(
        _manifest_row(
            "Figure 2",
            "synthetic benchmarks",
            fig2,
            [synthetic_summary],
            "Pure-null, rare-state, batch, dropout, trajectory, and overclustering stress results.",
        )
    )
    manifest.append(
        _manifest_row(
            "Figure 2",
            "diagnostic no-call validation",
            fig2_no_call,
            [no_call_summary],
            "Pure-null no-call and positive-call checks for planted low-rank and rare-state simulations.",
        )
    )

    fig3_public = SOURCE_DIR / "figure3_public_benchmark_summary.tsv"
    fig3_stability = SOURCE_DIR / "figure3_pbmc3k_stability_summary.tsv"
    _copy_atomic(phase1_summary, fig3_public)
    _copy_atomic(stability_summary, fig3_stability)
    manifest.append(
        _manifest_row(
            "Figure 3",
            "public benchmark",
            fig3_public,
            [phase1_summary],
            "PBMC3k, Kang IFN-beta PBMC, Baron pancreas, and PBMC68k/Zheng public benchmark table.",
        )
    )
    manifest.append(
        _manifest_row(
            "Figure 3",
            "PBMC3k stability",
            fig3_stability,
            [stability_summary],
            "Five-repeat PBMC3k subsampling stability comparison against Scanpy-like and fixed-PC baselines.",
        )
    )

    fig4_summary = SOURCE_DIR / "figure4_pdac_tme_showcase_summary.tsv"
    fig4_markers = SOURCE_DIR / "figure4_pdac_tme_cluster_marker_summary.tsv"
    _copy_atomic(pdac_summary, fig4_summary)
    _write_delimited(
        fig4_markers,
        _combined_marker_rows(
            [
                ("pdac_gse154778", pdac_primary_markers),
                ("pdac_gse263733", pdac_validation_markers),
            ]
        ),
    )
    manifest.append(
        _manifest_row(
            "Figure 4",
            "PDAC/TME showcase summary",
            fig4_summary,
            [pdac_summary],
            "GSE154778 marker-smoke showcase and GSE263733 external label validation summary.",
        )
    )
    manifest.append(
        _manifest_row(
            "Figure 4",
            "PDAC/TME cluster markers",
            fig4_markers,
            [pdac_primary_markers, pdac_validation_markers],
            "Cluster-level coarse marker signatures; intended claims are immune and ductal-context only.",
        )
    )

    fig5_runtime = SOURCE_DIR / "figure5_runtime_memory_summary.tsv"
    fig5_gates = SOURCE_DIR / "figure5_gate_evidence.tsv"
    fig5_ablation = SOURCE_DIR / "figure5_ablation_stability_summary.tsv"
    _write_delimited(fig5_runtime, _runtime_rows())
    _copy_atomic(gate_evidence, fig5_gates)
    _write_delimited(
        fig5_ablation,
        _ablation_rows(
            [
                ("min_embedding_pcs_10", ROOT / "results" / "stability_benchmarks_v3_minpc10_ablation" / "stability_summary.tsv"),
                ("consensus_clustering", ROOT / "results" / "stability_benchmarks_v3_consensus_ablation" / "stability_summary.tsv"),
                ("strict_signal_embedding", stability_summary),
            ]
        ),
    )
    manifest.append(
        _manifest_row(
            "Figure 5",
            "runtime and memory",
            fig5_runtime,
            [synthetic_summary, phase1_summary],
            "Runtime and peak-memory summaries from RMTGuard synthetic and public real-data runs.",
        )
    )
    manifest.append(
        _manifest_row(
            "Figure 5",
            "gate status",
            fig5_gates,
            [gate_evidence, gate_report],
            "Current submission-gate evidence; software release remains a separate GitHub/Zenodo gate.",
        )
    )
    manifest.append(
        _manifest_row(
            "Figure 5",
            "ablation stability",
            fig5_ablation,
            [
                ROOT / "results" / "stability_benchmarks_v3_minpc10_ablation" / "stability_summary.tsv",
                ROOT / "results" / "stability_benchmarks_v3_consensus_ablation" / "stability_summary.tsv",
                stability_summary,
            ],
            "PBMC3k stability ablations, including strict-signal rows from the official stability summary.",
        )
    )

    _write_delimited(MANIFEST, manifest)
    return manifest


def main() -> int:
    manifest = build_source_data()
    missing = [row for row in manifest if row["status"] != "ready"]
    print(_rel(MANIFEST))
    if missing:
        for row in missing:
            print(f"missing: {row['figure_id']} {row['panel']} -> {row['notes']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
