"""Audit figure assets, source data, and caption claim boundaries.

Author: RMTGuard contributors
Date: 2026-05-12
Purpose: Build a submission-facing audit that maps each intended display item
to rendered figure files, machine-readable source data, frozen captions, and
remaining claim-boundary actions.
Data sources: figures/manuscript, results/figures/source_data,
manuscript/figure_legends_freeze_aligned.md, and submission benchmark tables.
Method notes: This is a consistency audit only. It does not alter plotted
values, figure panels, or manuscript claims.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_TSV = ROOT / "results" / "submission" / "figure_caption_source_audit.tsv"
OUT_MD = ROOT / "docs" / "figure_caption_source_audit.md"

LEGENDS = ROOT / "manuscript" / "figure_legends_freeze_aligned.md"


@dataclass(frozen=True)
class DisplayItem:
    display_id: str
    intended_role: str
    assets: tuple[Path, ...]
    source_data: tuple[Path, ...]
    legend_required_phrase: str
    claim_boundary: str
    status_if_present: str
    required_action: str


DISPLAY_ITEMS = [
    DisplayItem(
        "Figure 1",
        "Algorithm overview and random-matrix callability diagnostics",
        (
            ROOT / "figures" / "manuscript" / "figure1_rmtguard_algorithm_diagnostics.png",
            ROOT / "figures" / "manuscript" / "figure1_rmtguard_algorithm_diagnostics.pdf",
            ROOT / "figures" / "manuscript" / "figure1_rmtguard_algorithm_diagnostics.tiff",
        ),
        (
            ROOT / "results" / "figures" / "source_data" / "figure1_algorithm_diagnostics.tsv",
            ROOT / "results" / "figures" / "source_data" / "figure1_embedding_pc_records.tsv",
        ),
        "Figure 1. RMTGuard random-matrix callability workflow.",
        "Workflow and diagnostic overview only; do not claim new random-matrix theory.",
        "ready_with_boundary",
        "Verify final panel labels match both source-data tables before submission.",
    ),
    DisplayItem(
        "Figure 2",
        "Synthetic false-signal, no-call and rare-state calibration",
        (
            ROOT / "figures" / "manuscript" / "figure2_synthetic_benchmarks.png",
            ROOT / "figures" / "manuscript" / "figure2_synthetic_benchmarks.pdf",
            ROOT / "figures" / "manuscript" / "figure2_synthetic_benchmarks.tiff",
        ),
        (
            ROOT / "results" / "figures" / "source_data" / "figure2_synthetic_benchmark_summary.csv",
            ROOT / "results" / "figures" / "source_data" / "figure2_no_call_summary.tsv",
            ROOT / "results" / "calibration" / "realistic_null_summary.tsv",
            ROOT / "results" / "calibration" / "rare_state_power_summary.tsv",
        ),
        "Figure 2. Synthetic calibration of false-signal and rare-state behavior.",
        "Supports tested null and rare-state regimes only; lowest-prevalence weak-effect limitation must remain visible.",
        "ready_with_boundary",
        "Final caption must keep the prevalence 0.02/effect 2.5 limitation.",
    ),
    DisplayItem(
        "Figure 3",
        "Public benchmark, callability map and comparator evidence",
        (
            ROOT / "figures" / "manuscript" / "figure3_public_benchmarks.png",
            ROOT / "figures" / "manuscript" / "figure3_public_benchmarks.pdf",
            ROOT / "figures" / "manuscript" / "figure3_public_benchmarks.tiff",
            ROOT / "figures" / "manuscript" / "figure_no_call_decision_map.png",
            ROOT / "figures" / "manuscript" / "figure_no_call_decision_map.pdf",
            ROOT / "figures" / "manuscript" / "figure3_official_seurat_paired_label_delta.pdf",
        ),
        (
            ROOT / "results" / "figures" / "source_data" / "figure3_public_benchmark_summary.tsv",
            ROOT / "results" / "figures" / "source_data" / "figure3_callability_decision_map.tsv",
            ROOT / "results" / "figures" / "source_data" / "figure3_official_seurat_paired_label_delta.tsv",
            ROOT / "results" / "submission" / "sclens_vs_rmtguard_stability_nrand20.tsv",
        ),
        "Figure 3. Public benchmark callability, caveats and no-call decisions.",
        "Does not support broad superiority over every fixed-PC or elbow baseline.",
        "ready_with_boundary",
        "Decide whether no-call and Seurat paired panels are integrated into main Figure 3 or moved to Extended Data.",
    ),
    DisplayItem(
        "Figure 4",
        "Bounded PDAC/TME public-data application",
        (
            ROOT / "figures" / "manuscript" / "figure4_pdac_tme_strengthened.png",
            ROOT / "figures" / "manuscript" / "figure4_pdac_tme_strengthened.pdf",
            ROOT / "figures" / "manuscript" / "figure4_pdac_tme_strengthened.tiff",
        ),
        (
            ROOT / "results" / "figures" / "source_data" / "figure4_pdac_tme_strengthened_source.tsv",
            ROOT / "results" / "figures" / "source_data" / "figure4_pdac_tme_pathway_atlas_source.tsv",
        ),
        "Figure 4. Bounded PDAC/TME public-data application.",
        "Methods-paper public-data use case only; no new mechanism, prognosis, therapy-response, spatial or protein-validation claim.",
        "ready_pending_author_ack",
        "Obtain corresponding-author acknowledgement of bounded wording before external submission.",
    ),
    DisplayItem(
        "Figure 5",
        "Ablation, release readiness, runtime and reproducibility",
        (
            ROOT / "figures" / "manuscript" / "figure5_reproducibility_release_audit.png",
            ROOT / "figures" / "manuscript" / "figure5_reproducibility_release_audit.pdf",
            ROOT / "figures" / "manuscript" / "figure5_reproducibility_release_audit.tiff",
        ),
        (
            ROOT / "results" / "figures" / "source_data" / "figure5_runtime_memory_summary.tsv",
            ROOT / "results" / "figures" / "source_data" / "figure5_gate_evidence.tsv",
            ROOT / "results" / "figures" / "source_data" / "figure5_ablation_stability_summary.tsv",
            ROOT / "results" / "release" / "release_readiness.tsv",
        ),
        "Figure 5. Ablation, reproducibility and release readiness.",
        "Component contribution only under tested datasets/repeats; post-release working branch requires a new DOI archive if cited.",
        "ready_with_boundary",
        "Use this as the main Figure 5; keep the larger real-data ablation forest as Extended Data.",
    ),
    DisplayItem(
        "Extended Data - real-data ablation",
        "Real-data annotation and batch ablation forest plot",
        (
            ROOT / "figures" / "manuscript" / "figure5_realdata_ablation_forest.png",
            ROOT / "figures" / "manuscript" / "figure5_realdata_ablation_forest.pdf",
            ROOT / "figures" / "manuscript" / "figure5_realdata_ablation_forest.tiff",
        ),
        (
            ROOT / "results" / "figures" / "source_data" / "figure5_realdata_ablation_delta_summary.tsv",
        ),
        "Extended Data Figure. Real-data ablation annotation monitor.",
        "Supports component-sensitivity discussion under tested labeled datasets and repeats only.",
        "ready_with_boundary",
        "Label as Extended Data or Supplementary Figure; do not use as universal component-necessity proof.",
    ),
    DisplayItem(
        "Extended Data - topology",
        "Synthetic topology stress and Paul15 real-data topology monitor",
        (
            ROOT / "figures" / "manuscript" / "figure_topology_stress.png",
            ROOT / "figures" / "manuscript" / "figure_topology_stress.pdf",
            ROOT / "figures" / "manuscript" / "figure_realdata_topology_benchmark.png",
            ROOT / "figures" / "manuscript" / "figure_realdata_topology_benchmark.pdf",
        ),
        (
            ROOT / "results" / "submission" / "topology_stress_summary.tsv",
            ROOT / "results" / "submission" / "realdata_topology_summary.tsv",
            ROOT / "results" / "figures" / "source_data" / "figure_realdata_topology_source.tsv",
        ),
        "Extended Data Figure. Topology stress and Paul15 real-data topology monitor.",
        "Topology monitoring with trade-offs only; not trajectory-method superiority.",
        "ready_with_boundary",
        "Keep annotation-derived Paul15 limitation in the final legend.",
    ),
]


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def _exists(paths: tuple[Path, ...]) -> tuple[bool, list[str], list[str]]:
    present = [_rel(path) for path in paths if path.exists()]
    missing = [_rel(path) for path in paths if not path.exists()]
    return not missing, present, missing


def _legend_contains(phrase: str) -> bool:
    if not LEGENDS.exists():
        return False
    return phrase in LEGENDS.read_text(encoding="utf-8")


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in DISPLAY_ITEMS:
        assets_ok, present_assets, missing_assets = _exists(item.assets)
        source_ok, present_sources, missing_sources = _exists(item.source_data)
        legend_ok = _legend_contains(item.legend_required_phrase)
        if not assets_ok or not source_ok or not legend_ok:
            status = "blocked_missing_asset_or_legend"
        else:
            status = item.status_if_present
        rows.append(
            {
                "display_id": item.display_id,
                "intended_role": item.intended_role,
                "audit_status": status,
                "assets_ok": str(assets_ok),
                "source_data_ok": str(source_ok),
                "legend_ok": str(legend_ok),
                "present_assets": ";".join(present_assets),
                "missing_assets": ";".join(missing_assets) or "none",
                "present_source_data": ";".join(present_sources),
                "missing_source_data": ";".join(missing_sources) or "none",
                "legend_required_phrase": item.legend_required_phrase,
                "claim_boundary": item.claim_boundary,
                "required_action": item.required_action,
            }
        )
    return rows


def write_tsv(rows: list[dict[str, str]]) -> None:
    OUT_TSV.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_TSV.with_suffix(OUT_TSV.suffix + ".tmp")
    fieldnames = [
        "display_id",
        "intended_role",
        "audit_status",
        "assets_ok",
        "source_data_ok",
        "legend_ok",
        "present_assets",
        "missing_assets",
        "present_source_data",
        "missing_source_data",
        "legend_required_phrase",
        "claim_boundary",
        "required_action",
    ]
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(OUT_TSV)


def write_markdown(rows: list[dict[str, str]]) -> None:
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["audit_status"]] = status_counts.get(row["audit_status"], 0) + 1
    blocked = [row for row in rows if row["audit_status"].startswith("blocked")]
    action_rows = [
        row
        for row in rows
        if row["audit_status"]
        in {"ready_pending_author_ack", "needs_layout_decision"}
    ]
    lines = [
        "# Figure-caption-source audit",
        "",
        "Generated by `python scripts/build_figure_caption_source_audit.py`.",
        "",
        "## Boundary",
        "",
        "This audit checks consistency among rendered figure files, machine-readable source data, and freeze-aligned legends. It does not certify journal acceptance and does not change any scientific result.",
        "",
        "## Status",
        "",
        f"- Display items checked: `{len(rows)}`.",
        f"- Blocked missing-asset/legend rows: `{len(blocked)}`.",
        "- Status counts: "
        + ", ".join(f"`{key}`={value}" for key, value in sorted(status_counts.items())),
        "",
        "## Remaining Actions",
        "",
    ]
    if action_rows:
        lines.extend(
            f"- `{row['display_id']}` ({row['audit_status']}): {row['required_action']}"
            for row in action_rows
        )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Audit Table",
            "",
            "| Display item | Status | Assets | Source data | Legend | Claim boundary | Required action |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            "| {display_id} | {audit_status} | {assets_ok} | {source_data_ok} | {legend_ok} | {claim_boundary} | {required_action} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `ready_with_boundary` means the assets, source data and frozen legend exist, but the claim boundary must still be preserved during final journal formatting.",
            "- `ready_pending_author_ack` means Codex can package the figure, but corresponding-author acknowledgement is still needed before external submission.",
            "- `needs_layout_decision` means all key evidence exists, but the final main/supplement figure layout has not been frozen.",
        ]
    )
    tmp = OUT_MD.with_suffix(OUT_MD.suffix + ".tmp")
    tmp.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    tmp.replace(OUT_MD)


def main() -> int:
    rows = build_rows()
    write_tsv(rows)
    write_markdown(rows)
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print("blocked\t" + str(sum(row["audit_status"].startswith("blocked") for row in rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
