#!/usr/bin/env python
"""Build a current evidence-freeze manifest for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-12
Purpose: Freeze the current manuscript-facing evidence assets so figures,
source data, claims, and remaining blockers can be audited before external
review or journal routing.
Data source: Local generated reports, figures, and source-data tables.
Method notes: This script records file existence, size, SHA256, claim boundary,
and next action. It does not certify that the manuscript is submission-ready.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_TSV = ROOT / "results" / "submission" / "current_evidence_freeze_manifest.tsv"
OUT_DOC = ROOT / "docs" / "current_evidence_freeze_2026-05-12.md"


@dataclass(frozen=True)
class FreezeItem:
    item_id: str
    category: str
    path: Path
    role: str
    claim_boundary: str
    next_action: str


ITEMS = [
    FreezeItem(
        "release_github_zenodo",
        "release",
        ROOT / "docs" / "public_release_blocker_report.md",
        "Public code/release evidence",
        "Supports code availability only; does not prove scientific acceptance.",
        "Re-check repository, release, and DOI immediately before submission.",
    ),
    FreezeItem(
        "nature_go_no_go",
        "journal_route",
        ROOT / "docs" / "nature_methods_go_no_go_final.md",
        "Nature Methods go/no-go control packet",
        "Presubmission may be considered; full submission remains gated.",
        "Update after final author acknowledgement and figure freeze.",
    ),
    FreezeItem(
        "genome_biology_fallback",
        "journal_route",
        ROOT / "docs" / "genome_biology_fallback_v2_packet.md",
        "Genome Biology fallback packet",
        "Fallback route if Nature Methods novelty/stability bar is not met.",
        "Refresh after any editorial feedback.",
    ),
    FreezeItem(
        "figure1_algorithm",
        "figure",
        ROOT / "figures" / "manuscript" / "figure1_rmtguard_algorithm_diagnostics.pdf",
        "Figure 1 algorithm diagnostics PDF",
        "Algorithm overview and diagnostic logic; avoid claiming mathematical novelty beyond RMT-guarded workflow.",
        "Regenerate after final algorithm text freeze.",
    ),
    FreezeItem(
        "figure1_source",
        "source_data",
        ROOT / "results" / "figures" / "source_data" / "figure1_algorithm_diagnostics.tsv",
        "Figure 1 source data",
        "Supports plotted diagnostic examples only.",
        "Verify exact panel mapping before submission.",
    ),
    FreezeItem(
        "figure2_synthetic",
        "figure",
        ROOT / "figures" / "manuscript" / "figure2_synthetic_benchmarks.pdf",
        "Figure 2 synthetic benchmark PDF",
        "Supports null/rare-state and synthetic behavior claims under tested settings.",
        "Cross-check against 50-repeat calibration before final text.",
    ),
    FreezeItem(
        "realistic_null_calibration",
        "statistics",
        ROOT / "docs" / "realistic_null_power_calibration.md",
        "50-repeat realistic null and rare-state calibration report",
        "Supports controlled false-signal behavior in tested null families; weak rare-state setting remains a limitation.",
        "Keep low-prevalence weak-effect limitation visible.",
    ),
    FreezeItem(
        "figure3_public_benchmark",
        "figure",
        ROOT / "figures" / "manuscript" / "figure3_public_benchmarks.pdf",
        "Figure 3 public benchmark PDF",
        "Does not support broad stability superiority against all baselines.",
        "Use bounded language and include no-call decision map.",
    ),
    FreezeItem(
        "figure3_seurat_paired",
        "figure",
        ROOT / "figures" / "manuscript" / "figure3_official_seurat_paired_label_delta.pdf",
        "Official Seurat paired comparison forest plot",
        "Supports paired comparison reporting; not a universal RMTGuard win.",
        "Ensure comparator methods and paired-test assumptions are stated.",
    ),
    FreezeItem(
        "no_call_decision_map",
        "figure",
        ROOT / "figures" / "manuscript" / "figure_no_call_decision_map.pdf",
        "Figure 3 callability/no-call decision map",
        "Supports transparent no-call/caveat behavior; no-call rows cannot be converted into discovery claims.",
        "Keep in main or supplement depending on final Figure 3 layout.",
    ),
    FreezeItem(
        "no_call_source",
        "source_data",
        ROOT / "results" / "figures" / "source_data" / "figure3_callability_decision_map.tsv",
        "Figure 3 no-call source data",
        "Machine-readable basis for no-call/caveat decisions.",
        "Verify thresholds remain consistent with Methods.",
    ),
    FreezeItem(
        "topology_stress",
        "figure",
        ROOT / "figures" / "manuscript" / "figure_topology_stress.pdf",
        "Synthetic topology stress benchmark PDF",
        "Supports synthetic topology preservation monitor; not proof of real trajectory correctness.",
        "Keep together with real-data topology monitor.",
    ),
    FreezeItem(
        "topology_stress_source",
        "source_data",
        ROOT / "results" / "submission" / "topology_stress_summary.tsv",
        "Synthetic topology stress summary",
        "20-repeat synthetic line/branch/loop evidence.",
        "Mention CONCORD-style inspiration without claiming CONCORD reimplementation.",
    ),
    FreezeItem(
        "realdata_topology",
        "figure",
        ROOT / "figures" / "manuscript" / "figure_realdata_topology_benchmark.pdf",
        "Paul15 real-data topology monitor PDF",
        "Mixed trade-off evidence; supports topology monitoring, not broad topology superiority.",
        "Optional: add second real trajectory/perturbation dataset if targeting Nature Methods.",
    ),
    FreezeItem(
        "realdata_topology_source",
        "source_data",
        ROOT / "results" / "figures" / "source_data" / "figure_realdata_topology_source.tsv",
        "Paul15 real-data topology source data",
        "Annotation-derived topology metrics only; not experimentally measured pseudotime.",
        "Keep limitation in legend and Results.",
    ),
    FreezeItem(
        "sclens_direct_comparator",
        "competitor",
        ROOT / "docs" / "sclens_stability_nrand20_2026-05-12.md",
        "Direct scLENSpy n_rand_matrix=20 comparator report",
        "Supports direct competitor coverage on PBMC3k/Kang only.",
        "Avoid claiming all scLENS variants or all datasets are covered.",
    ),
    FreezeItem(
        "figure4_strengthened",
        "figure",
        ROOT / "figures" / "manuscript" / "figure4_pdac_tme_strengthened.pdf",
        "Strengthened PDAC/TME Figure 4 PDF",
        "Bounded public-data application; no mechanism, prognosis, therapy-response, spatial, or protein-validation claim.",
        "Needs corresponding-author acknowledgement before external use.",
    ),
    FreezeItem(
        "figure4_source",
        "source_data",
        ROOT / "results" / "figures" / "source_data" / "figure4_pdac_tme_strengthened_source.tsv",
        "Strengthened Figure 4 source data",
        "Supports marker/pathway/atlas-use-case panels only.",
        "Confirm caption wording with authors.",
    ),
    FreezeItem(
        "figure5_ablation",
        "figure",
        ROOT / "figures" / "manuscript" / "figure5_realdata_ablation_forest.pdf",
        "Real-data ablation forest plot",
        "Supports component contribution discussion with tested datasets and repeats only.",
        "Avoid universal component-necessity wording.",
    ),
    FreezeItem(
        "component_ablation_report",
        "statistics",
        ROOT / "docs" / "component_ablation_benchmark.md",
        "20-repeat synthetic component ablation report",
        "Supports marginal component discussion for tested synthetic settings.",
        "Pair with real-data ablation annotation report.",
    ),
    FreezeItem(
        "realdata_ablation_report",
        "statistics",
        ROOT / "docs" / "realdata_ablation_annotation.md",
        "Real-data ablation annotation report",
        "Supports annotation/batch ablation checks on included labeled datasets.",
        "Keep dataset coverage explicit.",
    ),
    FreezeItem(
        "gantt",
        "project_management",
        ROOT / "figures" / "project_management" / "rmtguard_project_gantt.pdf",
        "Current project Gantt chart",
        "Project-management status only; not scientific evidence.",
        "Refresh after each major benchmark addition.",
    ),
    FreezeItem(
        "manual_author_actions",
        "manual_blocker",
        ROOT / "docs" / "manual_next_actions_20_50.md",
        "Manual author action checklist",
        "Tracks actions Codex cannot certify alone.",
        "Authors must verify funding, COI, ethics, and Figure 4 acknowledgement.",
    ),
]


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_tsv_atomic(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else ["empty"]
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def build_manifest() -> pd.DataFrame:
    rows = []
    today = date.today().isoformat()
    for item in ITEMS:
        exists = item.path.exists()
        rows.append(
            {
                "freeze_date": today,
                "item_id": item.item_id,
                "category": item.category,
                "path": _rel(item.path),
                "exists": exists,
                "size_bytes": item.path.stat().st_size if exists else "",
                "sha256": _sha256(item.path) if exists else "",
                "role": item.role,
                "claim_boundary": item.claim_boundary,
                "next_action": item.next_action,
            }
        )
    return pd.DataFrame(rows)


def build_doc(df: pd.DataFrame) -> str:
    missing = df[~df["exists"]]
    category_counts = df.groupby("category")["item_id"].count().to_dict()
    lines = [
        "# RMTGuard current evidence freeze",
        "",
        f"Date: {date.today().isoformat()}",
        "Project: RMTGuard",
        "",
        "## Purpose",
        "",
        "This freeze records the current manuscript-facing evidence assets, their",
        "source files, checksums, claim boundaries, and next actions. It is a",
        "quality-control artifact, not a statement that the manuscript is ready for",
        "submission.",
        "",
        "## Freeze Status",
        "",
        f"- Items checked: `{len(df)}`",
        f"- Missing items: `{len(missing)}`",
        f"- Manifest: `{_rel(OUT_TSV)}`",
        "",
        "## Category Counts",
        "",
    ]
    for category, count in sorted(category_counts.items()):
        lines.append(f"- `{category}`: {count}")
    lines.extend(
        [
            "",
            "## Current 20-50 JIF Distance",
            "",
            "- Stronger than the earlier state: public code/DOI, scLENSpy comparator,",
            "  realistic null/power calibration, synthetic topology stress, real-data",
            "  topology monitor, no-call decision map, and strengthened Figure 4 assets",
            "  are now present.",
            "- Still not a guaranteed Nature Methods package: the strongest defensible",
            "  claim is diagnostic random-matrix callability with transparent",
            "  trade-offs, not broad superiority over all fixed-PC or elbow baselines.",
            "- Remaining high-impact risks: final source-data/figure freeze after all",
            "  benchmark decisions, corresponding-author Figure 4 acknowledgement,",
            "  and optional second real trajectory/perturbation topology dataset if",
            "  Nature Methods remains the preferred route.",
            "",
            "## Frozen Items",
            "",
            "| ID | Category | Exists | Role | Claim boundary | Next action |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in df.itertuples(index=False):
        lines.append(
            f"| {row.item_id} | {row.category} | {row.exists} | {row.role} | {row.claim_boundary} | {row.next_action} |"
        )
    if not missing.empty:
        lines.extend(["", "## Missing Items", ""])
        for row in missing.itertuples(index=False):
            lines.append(f"- `{row.item_id}`: `{row.path}`")
    lines.extend(
        [
            "",
            "## Use In Manuscript Planning",
            "",
            "Use this file as the source-of-truth checklist before drafting Results,",
            "figure legends, cover letter claims, and response-to-reviewer language.",
            "Any claim not represented here should be treated as unsupported until a",
            "new evidence item is added and this freeze is regenerated.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    df = build_manifest()
    _write_tsv_atomic(OUT_TSV, df.to_dict(orient="records"))
    _write_text_atomic(OUT_DOC, build_doc(df))
    print(_rel(OUT_TSV))
    print(_rel(OUT_DOC))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
