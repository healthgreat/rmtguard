#!/usr/bin/env python
"""Build the next-round Nature Methods science gate board.

Author: RMTGuard development team
Date: 2026-05-04
Purpose: Convert the remaining 20-50 JIF blockers into executable gates with
owners, inputs, outputs, pass criteria, and stop conditions.
Data source: Generated RMTGuard gap assessment, execution board, and current
release/manuscript artifacts.
Method notes: This is a planning and risk-control artifact. It is not an
acceptance prediction and must not be presented as proof of journal fit.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_TSV = ROOT / "results" / "submission" / "nature_methods_next_round_gate_board.tsv"
OUT_MD = ROOT / "docs" / "nature_methods_next_round_gate_board.md"


@dataclass(frozen=True)
class Gate:
    gate_id: str
    priority: str
    status: str
    owner: str
    blocker_target: str
    evidence_now: str
    next_action: str
    output_artifact: str
    pass_criterion: str
    stop_condition: str
    shared_reuse: str


GATES = [
    Gate(
        "NM-G01",
        "P0",
        "done",
        "Codex",
        "stability_advantage",
        "manuscript/claim_scope_final.md",
        "Keep the main claim frozen as callability-aware random-matrix noise control unless a new algorithm run beats the strongest comparator.",
        "manuscript/claim_scope_final.md",
        "No abstract, figure legend, or cover-letter sentence claims broad stability superiority over Seurat/Scanpy/fixed-PC baselines.",
        "Stop Nature Methods submission if any main-text claim implies universal superiority from the current benchmark.",
        "High-value claim-control template for all methods projects.",
    ),
    Gate(
        "NM-G02",
        "P0",
        "done",
        "Codex",
        "component_ablation",
        "docs/p0_science_sprint_status.md",
        "Use the current 20-repeat synthetic and real-data component-ablation layer as supporting evidence; keep component-necessity claims bounded by confidence intervals and real-data annotation checks.",
        "results/ablation/p0_component_ablation_20_50_repeat_summary.tsv",
        "Each current core component has effect estimate, CI, paired test where applicable, and a clear keep/drop interpretation.",
        "Stop claiming a component is necessary if its CI overlaps zero or if it only helps synthetic data while harming labeled real data.",
        "Reusable ablation protocol for algorithm papers.",
    ),
    Gate(
        "NM-G03",
        "P0",
        "done_with_limit",
        "Codex",
        "claim_boundary_controlled",
        "docs/rare_state_claim_boundary.md",
        "Use the 50-repeat realistic-null and rare-state power curves as limit-aware evidence; do not claim recovery in the lowest prevalence/effect regimes.",
        "results/calibration/rare_state_power_summary.tsv",
        "False signal rate remains near preset alpha under realistic nulls, and rare-state power is reported as a power curve rather than one positive setting.",
        "Stop Nature Methods rare-state superiority claims if weak-effect/low-prevalence regimes are central to the argument.",
        "Reusable null/power-calibration template for public-data method papers.",
    ),
    Gate(
        "NM-G04",
        "P0",
        "waiting_author_decision",
        "Chongfa Chen + corresponding authors",
        "PDAC_TME_depth_or_demotion",
        "docs/pdac_tme_showcase_depth.md",
        "Choose whether PDAC/TME remains a main figure or is demoted to supplement.",
        "metadata/pdac_tme_route_decision.tsv",
        "A written author decision exists: deepen as main figure, or demote to supplement and replace with stronger application.",
        "Stop using PDAC/TME as a main Figure 4 if no DE/GSEA/trajectory/external-validation plan is approved.",
        "Reusable disease-showcase decision template.",
    ),
    Gate(
        "NM-G05",
        "P1",
        "partial_done_supported_with_limits",
        "Codex",
        "biological_showcase",
        "results/pdac_tme/deep_validation",
        "Build on the completed first-pass PDAC/TME validation by adding full MSigDB/Reactome/Hallmark GSEA, literature-backed PDAC atlas marker mapping, and final author route confirmation.",
        "results/pdac_tme/deep_validation/pdac_deep_validation_summary.tsv",
        "PDAC/TME can remain a bounded main-figure candidate only if the current DE/signature-transfer evidence is upgraded with formal pathway and published-atlas support.",
        "Demote PDAC/TME if full pathway/atlas support is not convincing or if author route confirmation is not provided.",
        "Reusable public-disease showcase deepening checklist.",
    ),
    Gate(
        "NM-G06",
        "P1",
        "planned_alternative",
        "Codex",
        "biological_showcase",
        "docs/jif20_50_gap_assessment.md",
        "If PDAC/TME is demoted, select a stronger public application with clearer labels or external ground truth.",
        "results/submission/replacement_application_screen.tsv",
        "Replacement dataset has reliable labels/ground truth and shows a clear callability/noise-control use case.",
        "Stop adding datasets if they only expand breadth without improving the central claim.",
        "Reusable application-selection rule for other projects.",
    ),
    Gate(
        "NM-G07",
        "P1",
        "done",
        "Codex + author",
        "added_dataset_label_free_boundary",
        "docs/added_dataset_annotation_boundary.md",
        "Keep PBMC3k and PDAC GSE154778 as label-free stability/runtime evidence unless reliable annotations are later documented.",
        "results/submission/added_dataset_annotation_boundary.tsv",
        "Every dataset is explicitly typed as labeled annotation evidence or label-free stability/runtime evidence.",
        "Stop reporting annotation ARI for PBMC3k/PDAC GSE154778 unless labels are documented and defensible.",
        "Reusable annotation-boundary table for benchmark papers.",
    ),
    Gate(
        "NM-G08",
        "P1",
        "planned_after_freeze",
        "Codex",
        "final_source_data_and_reporting",
        "figures/manuscript/rendered_figure_manifest.tsv",
        "After benchmark freeze, regenerate all figure source data, captions, reporting summary draft, and cover-letter claim language.",
        "results/submission/final_source_data_caption_audit.tsv",
        "Every number in the abstract/main figures has a source table row and passes claim-boundary lint.",
        "Stop submission if source-data tables cannot reproduce a quoted number.",
        "Reusable final-figure audit template.",
    ),
    Gate(
        "NM-G09",
        "P0",
        "planned_after_p0",
        "Corresponding authors + Codex",
        "nature_methods_route",
        "docs/publication_execution_board.md",
        "Run a formal Nature Methods go/no-go after NM-G01 to NM-G04 are resolved.",
        "results/submission/nature_methods_go_no_go_final.tsv",
        "Nature Methods is attempted only if scientific P0 gates are resolved and claims remain reviewer-defensible.",
        "Route directly to Genome Biology/Bioinformatics-style manuscript if novelty and benchmark strength remain incremental.",
        "Reusable go/no-go rule for high-impact routes.",
    ),
]


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _write_tsv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "gate_id",
                "priority",
                "status",
                "owner",
                "blocker_target",
                "evidence_now",
                "next_action",
                "output_artifact",
                "pass_criterion",
                "stop_condition",
                "shared_reuse",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def build_rows() -> list[dict[str, str]]:
    return [gate.__dict__.copy() for gate in GATES]


def build_markdown(rows: list[dict[str, str]]) -> str:
    p0_open = [
        row
        for row in rows
        if row["priority"] == "P0"
        and row["status"] not in {"pass", "done"}
        and not row["status"].startswith("done_")
    ]
    waiting = [row for row in rows if row["status"].startswith("waiting")]
    lines = [
        "# Nature Methods Next-Round Science Gate Board",
        "",
        "Generated by `python scripts/build_nature_methods_next_round_gate_board.py`.",
        "",
        "## Bottom Line",
        "",
        "- Acceptance guarantee: `impossible`.",
        "- Strict 20-50 JIF route remains `not ready`.",
        "- Public release is no longer a P0 blocker; the active blockers are scientific and author-confirmation gates.",
        f"- Open P0 gates: `{len(p0_open)}`.",
        f"- Waiting author decisions: `{len(waiting)}`.",
        "",
        "## Immediate 48-Hour Actions",
        "",
        "1. Obtain the author decision on PDAC/TME using `docs/pdac_tme_route_decision_packet.md`: deepen as main figure or demote to supplement.",
        "2. Treat `docs/pdac_tme_deep_validation.md` as first-pass support, not final disease biology proof.",
        "3. Add full MSigDB/Reactome/Hallmark GSEA and literature-backed PDAC atlas marker mapping before final Figure 4 wording.",
        "4. Keep the rare-state claim boundary locked: power is strong for moderate prevalence/effect settings, but weak at the lowest prevalence/effect setting.",
        "5. Keep PBMC3k and PDAC GSE154778 label-free unless reliable labels are documented.",
        "6. Use `docs/p0_science_sprint_status.md` as the sprint control file.",
        "7. Run the formal Nature Methods go/no-go only after NM-G04 is resolved.",
        "",
        "## Two-Week Science Sprint",
        "",
        "- NM-G05 has first-pass support from FDR-controlled DE, marker-set enrichment, external signature transfer, and Figure 4 source data; full pathway GSEA and atlas citation mapping remain before high-impact wording.",
        "- Otherwise execute NM-G06 and screen replacement applications with stronger ground truth using the supplement-demotion runbook.",
        "- Rebuild Figure 3/5 source data only after the benchmark freeze.",
        "",
        "## Gate Table",
        "",
        "| Gate | Priority | Status | Owner | Blocker | Next Action | Pass Criterion | Stop Condition |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {gate_id} | {priority} | `{status}` | {owner} | `{blocker_target}` | {next_action} | {pass_criterion} | {stop_condition} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Manual Author Inputs",
            "",
            "Decision criteria are summarized in `docs/pdac_tme_route_decision_packet.md`.",
            "",
            "Please send these exact replies when available:",
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
            "",
            "Also still needed:",
            "",
            "```text",
            "Use postal code <FINAL_POSTAL_CODE> for both Yi Miao and Han Yan correspondence addresses.",
            "Funding statement confirmed: <TEXT>",
            "Competing interests confirmed: <TEXT>",
            "Ethics/public-data-use statement confirmed: <TEXT>",
            "CRediT roles confirmed / revised as follows: <TEXT>",
            "```",
            "",
            "## Evidence Boundary",
            "",
            "This board is a planning artifact based on current local reports. It does not prove Nature Methods acceptance, and it must be regenerated after any benchmark freeze or claim rewrite.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    rows = build_rows()
    _write_tsv(rows, OUT_TSV)
    _write_text(build_markdown(rows), OUT_MD)
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    p0_open = sum(
        1
        for row in rows
        if row["priority"] == "P0"
        and row["status"] not in {"pass", "done"}
        and not row["status"].startswith("done_")
    )
    print(f"open_p0_gates\t{p0_open}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
