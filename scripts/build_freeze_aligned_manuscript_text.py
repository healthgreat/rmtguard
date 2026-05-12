#!/usr/bin/env python
"""Build freeze-aligned Results text and figure legends for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-12
Purpose: Convert the current evidence-freeze assets into manuscript-facing
Results paragraphs, figure legends, and a claim-to-evidence audit.
Data source: results/submission/current_evidence_freeze_manifest.tsv and linked
benchmark/source-data tables.
Method notes: This script intentionally uses bounded wording. It should not be
edited to imply broad superiority, de novo trajectory inference, clinical
validation, or immutable DOI coverage for post-release working-branch changes.
"""

from __future__ import annotations

import csv
import math
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_RESULTS = ROOT / "manuscript" / "results_freeze_aligned_draft.md"
OUT_LEGENDS = ROOT / "manuscript" / "figure_legends_freeze_aligned.md"
OUT_AUDIT = ROOT / "results" / "submission" / "freeze_aligned_text_audit.tsv"


def _read_tsv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


def _fmt(value: Any, digits: int = 3) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "NA"
    if not math.isfinite(number):
        return "NA"
    return f"{number:.{digits}f}"


def _pct(value: Any, digits: int = 0) -> str:
    try:
        number = float(value) * 100.0
    except (TypeError, ValueError):
        return "NA"
    if not math.isfinite(number):
        return "NA"
    return f"{number:.{digits}f}%"


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _write_tsv_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else ["empty"]
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _row(df: pd.DataFrame, **criteria: Any) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for key, value in criteria.items():
        mask &= df[key].astype(str) == str(value)
    selected = df[mask]
    if selected.empty:
        raise KeyError(f"No row for {criteria}")
    return selected.iloc[0]


def _collect_values() -> dict[str, Any]:
    no_call = _read_tsv(ROOT / "results" / "callability" / "no_call_decision_map.tsv")
    realistic_null = _read_tsv(ROOT / "results" / "calibration" / "realistic_null_summary.tsv")
    rare_power = _read_tsv(ROOT / "results" / "calibration" / "rare_state_power_summary.tsv")
    sclens = _read_tsv(ROOT / "results" / "submission" / "sclens_vs_rmtguard_stability_nrand20.tsv")
    topology = _read_tsv(ROOT / "results" / "submission" / "topology_stress_summary.tsv")
    real_topology = _read_tsv(ROOT / "results" / "submission" / "realdata_topology_summary.tsv")
    freeze = _read_tsv(ROOT / "results" / "submission" / "current_evidence_freeze_manifest.tsv")

    decision_counts = no_call["decision"].value_counts().to_dict()
    pbmc68k = _row(no_call, unit_id="pbmc68k_zheng2017")
    pbmc3k = _row(no_call, unit_id="pbmc3k_10x")
    kang = _row(no_call, unit_id="kang_ifnb_pbmc")
    baron = _row(no_call, unit_id="baron_pancreas")

    max_false_signal = realistic_null["false_signal_rate"].astype(float).max()
    null_models = ", ".join(realistic_null["null_model"].astype(str).tolist())
    min_null_repeats = int(realistic_null["n_repeats"].astype(int).min())
    weak_rare = _row(rare_power, prevalence="0.02", effect_size="2.5")
    supported_rare = rare_power[rare_power["power"].astype(float) >= 0.80]
    supported_min_prev = float(supported_rare["prevalence"].astype(float).min())
    supported_min_effect = float(
        supported_rare[supported_rare["prevalence"].astype(float) == supported_min_prev][
            "effect_size"
        ].astype(float).min()
    )
    higher_prevalence_min = float(
        rare_power[rare_power["prevalence"].astype(float) >= 0.04]["power"].astype(float).min()
    )

    sclens_pbmc = {
        row["dataset_id"]: row for _, row in sclens.iterrows() if row["method"] == "scLENSpy_nrand20"
    }
    rmt_sclens_context = {
        row["dataset_id"]: row for _, row in sclens.iterrows() if row["method"] == "rmtguard"
    }

    rmt_topology = topology[topology["method"] == "rmtguard"].copy()
    rmt_topology["topology_knn_recall_mean"] = rmt_topology[
        "topology_knn_recall_mean"
    ].astype(float)
    rmt_topology["topology_trustworthiness_mean"] = rmt_topology[
        "topology_trustworthiness_mean"
    ].astype(float)
    rmt_topology["topology_continuity_mean"] = rmt_topology[
        "topology_continuity_mean"
    ].astype(float)
    rmt_topology["pairwise_distance_spearman_mean"] = rmt_topology[
        "pairwise_distance_spearman_mean"
    ].astype(float)

    rt_rmt = _row(real_topology, method="rmtguard")
    rt_fixed30 = _row(real_topology, method="fixed_pcs_30")
    rt_fixed50 = _row(real_topology, method="fixed_pcs_50")

    return {
        "freeze_item_n": int(len(freeze)),
        "freeze_missing_n": int((freeze["exists"].astype(str) != "True").sum()),
        "decision_counts": decision_counts,
        "pbmc68k": pbmc68k,
        "pbmc3k": pbmc3k,
        "kang": kang,
        "baron": baron,
        "max_false_signal": max_false_signal,
        "null_models": null_models,
        "min_null_repeats": min_null_repeats,
        "weak_rare": weak_rare,
        "supported_min_prev": supported_min_prev,
        "supported_min_effect": supported_min_effect,
        "higher_prevalence_min": higher_prevalence_min,
        "sclens_pbmc": sclens_pbmc,
        "rmt_sclens_context": rmt_sclens_context,
        "rmt_topology": rmt_topology,
        "rt_rmt": rt_rmt,
        "rt_fixed30": rt_fixed30,
        "rt_fixed50": rt_fixed50,
    }


def _build_results(values: dict[str, Any]) -> str:
    dc = values["decision_counts"]
    pbmc68k = values["pbmc68k"]
    pbmc3k = values["pbmc3k"]
    kang = values["kang"]
    baron = values["baron"]
    weak = values["weak_rare"]
    rt = values["rt_rmt"]
    f30 = values["rt_fixed30"]
    f50 = values["rt_fixed50"]
    topo = values["rmt_topology"]

    topo_sentence = "; ".join(
        [
            f"{row.scenario_id}: trustworthiness {_fmt(row.topology_trustworthiness_mean)}, continuity {_fmt(row.topology_continuity_mean)}, kNN recall {_fmt(row.topology_knn_recall_mean)}"
            for row in topo.itertuples(index=False)
        ]
    )

    pbmc_s = values["sclens_pbmc"]["pbmc3k_10x"]
    kang_s = values["sclens_pbmc"]["kang_ifnb_pbmc"]
    pbmc_r = values["rmt_sclens_context"]["pbmc3k_10x"]
    kang_r = values["rmt_sclens_context"]["kang_ifnb_pbmc"]

    return "\n\n".join(
        [
            "# Freeze-aligned Results draft",
            "",
            f"Generated: {date.today().isoformat()}",
            "",
            "Status: draft text for manuscript assembly; not a submission-ready final Results section.",
            "",
            "## RMTGuard implements a diagnostic random-matrix callability workflow",
            "",
            (
                "RMTGuard was evaluated as a callability-aware random-matrix workflow rather "
                "than as a universal replacement for fixed-parameter single-cell analysis. "
                f"The current evidence freeze contains {values['freeze_item_n']} manuscript-facing "
                f"items with {values['freeze_missing_n']} missing files, linking algorithm figures, "
                "source-data tables, release evidence, public benchmarks, topology monitors and "
                "manual author blockers. This freeze defines the Results boundary used below: "
                "supported structures may be reported, but diagnostic no-call and caveated-call "
                "outcomes are not relabelled as biological discoveries. "
                "[Evidence: docs/current_evidence_freeze_2026-05-12.md]"
            ),
            "",
            "## Null and rare-state calibration support bounded noise-control claims",
            "",
            (
                f"Across {values['min_null_repeats']}-repeat realistic null experiments covering "
                f"{values['null_models']}, the maximum observed false-signal rate was "
                f"{_pct(values['max_false_signal'])}. These results support a bounded "
                "false-signal-control claim under the tested count-preserving null families, "
                "not universal type-I-error calibration for every scRNA-seq preprocessing regime. "
                "[Evidence: results/calibration/realistic_null_summary.tsv]"
            ),
            (
                "Rare-state simulations also showed a clear operating boundary. Power was high "
                f"in the tested prevalence 0.02 setting only at effect size "
                f"{values['supported_min_effect']:.1f}, and all tested prevalence >=0.04 "
                f"settings had power at least {_pct(values['higher_prevalence_min'])}; the "
                f"weakest setting, prevalence 0.02 and effect size 2.5, had power "
                f"{_pct(weak.power)} and mean rare-state F1 {_fmt(weak.mean_rare_f1)}. "
                "The manuscript should therefore describe rare-state retention as supported "
                "for tested moderate settings and explicitly limited in the lowest-prevalence, "
                "weak-effect regime. [Evidence: results/calibration/rare_state_power_summary.tsv]"
            ),
            "",
            "## Public benchmarks support callability and caveat reporting, not broad superiority",
            "",
            (
                "The callability decision map classified the current benchmark rows as "
                f"{dc.get('diagnostic_no_call', 0)} diagnostic no-call rows, "
                f"{dc.get('callable_with_caveat', 0)} caveated real-data calls, "
                f"{dc.get('positive_control_pass', 0)} synthetic positive-control passes and "
                f"{dc.get('stress_monitor', 0)} stress-monitor rows. PBMC68k/Zheng 2017 was "
                f"kept as a diagnostic no-call with annotation ARI {_fmt(pbmc68k.annotation_ari)} "
                f"and stability gap {_fmt(pbmc68k.stability_gap_to_best)}, whereas PBMC3k, Kang "
                "IFN-beta PBMC and Baron pancreas were retained only as caveated benchmark "
                "contexts. [Evidence: results/callability/no_call_decision_map.tsv]"
            ),
            (
                f"Specifically, PBMC3k showed RMTGuard stability {_fmt(pbmc3k.stability_ari)} "
                f"with a gap of {_fmt(pbmc3k.stability_gap_to_best)} to the strongest comparator; "
                f"Kang IFN-beta PBMC showed annotation ARI {_fmt(kang.annotation_ari)} and "
                f"stability gap {_fmt(kang.stability_gap_to_best)}; Baron pancreas showed "
                f"annotation ARI {_fmt(baron.annotation_ari)} and stability gap "
                f"{_fmt(baron.stability_gap_to_best)}. These results support transparent "
                "reporting of when RMTGuard proceeds and when it refuses or caveats a result, "
                "but they do not support a statement that RMTGuard is always more stable than "
                "elbow or fixed-PC workflows. [Evidence: results/callability/no_call_decision_map.tsv]"
            ),
            (
                "A direct scLENSpy comparison reduced the risk that the work lacks an RMT-like "
                "comparator. In 10-repeat subsampling, RMTGuard mean pairwise ARI was "
                f"{_fmt(pbmc_r.mean_pairwise_ari)} on PBMC3k and {_fmt(kang_r.mean_pairwise_ari)} "
                f"on Kang IFN-beta PBMC, compared with scLENSpy n_rand_matrix=20 values of "
                f"{_fmt(pbmc_s.mean_pairwise_ari)} and {_fmt(kang_s.mean_pairwise_ari)}, respectively. "
                "This comparison is limited to the tested Python scLENSpy configuration and two "
                "datasets. [Evidence: results/submission/sclens_vs_rmtguard_stability_nrand20.tsv]"
            ),
            "",
            "## Topology benchmarks show monitored geometry preservation with real-data trade-offs",
            "",
            (
                "Synthetic CONCORD-style topology stress tests showed that RMTGuard preserved "
                f"line, branch and loop geometry under the tested simulations ({topo_sentence}). "
                "These simulations support topology monitoring as part of the benchmark arc, but "
                "they do not establish RMTGuard as a dedicated trajectory-inference method. "
                "[Evidence: results/submission/topology_stress_summary.tsv]"
            ),
            (
                "On Paul15 hematopoiesis, an annotation-derived real-data topology monitor showed "
                "a mixed trade-off. RMTGuard had higher annotation ARI "
                f"({_fmt(rt.annotation_ari_mean)}) than fixed 30 PCs ({_fmt(f30.annotation_ari_mean)}) "
                f"and fixed 50 PCs ({_fmt(f50.annotation_ari_mean)}), and lower neighbor tree "
                f"distance ({_fmt(rt.neighbor_tree_distance_mean)}) than fixed 30 PCs "
                f"({_fmt(f30.neighbor_tree_distance_mean)}) and fixed 50 PCs "
                f"({_fmt(f50.neighbor_tree_distance_mean)}). However, fixed-PC baselines had "
                f"higher centroid tree rho ({_fmt(f30.centroid_tree_spearman_mean)} and "
                f"{_fmt(f50.centroid_tree_spearman_mean)}) than RMTGuard "
                f"({_fmt(rt.centroid_tree_spearman_mean)}), and fixed 50 PCs had the highest "
                f"reference edge recall ({_fmt(f50.reference_edge_recall_mean)} versus "
                f"{_fmt(rt.reference_edge_recall_mean)} for RMTGuard). This figure should be "
                "presented as a real-data topology monitor with explicit trade-offs, not as "
                "broad topology superiority. [Evidence: results/submission/realdata_topology_summary.tsv]"
            ),
            "",
            "## PDAC/TME application and ablation evidence remain bounded",
            "",
            (
                "The PDAC/TME analysis is retained as a public-data application that connects "
                "RMTGuard-selected structures to marker, pathway and atlas-context evidence. "
                "It should be described as a bounded methods-paper showcase and not as a new "
                "PDAC mechanism, prognosis marker, therapy-response model, spatial validation "
                "or protein-level validation. [Evidence: docs/figure4_pdac_tme_wording_freeze.md; "
                "results/figures/source_data/figure4_pdac_tme_strengthened_source.tsv]"
            ),
            (
                "Component ablation and real-data annotation checks support discussion of the "
                "tested RMTGuard modules, but the manuscript should avoid universal component-"
                "necessity language. The correct wording is that MP/TW-style edge checks, "
                "near-edge stability, no-call logic and related safeguards contributed under "
                "the benchmark settings captured in the current source data. "
                "[Evidence: docs/component_ablation_benchmark.md; docs/realdata_ablation_annotation.md]"
            ),
        ]
    )


def _build_legends(values: dict[str, Any]) -> str:
    pbmc68k = values["pbmc68k"]
    rt = values["rt_rmt"]
    f30 = values["rt_fixed30"]
    f50 = values["rt_fixed50"]
    topo = values["rmt_topology"]
    topo_short = "; ".join(
        [
            f"{row.scenario_id}, trustworthiness {_fmt(row.topology_trustworthiness_mean)}"
            for row in topo.itertuples(index=False)
        ]
    )
    return "\n\n".join(
        [
            "# Freeze-aligned figure legends draft",
            "",
            f"Generated: {date.today().isoformat()}",
            "",
            "Status: draft legends for manuscript assembly; not final journal artwork captions.",
            "",
            "## Figure 1. RMTGuard random-matrix callability workflow.",
            (
                "Schematic and diagnostic outputs for the RMTGuard workflow. The method uses "
                "random-matrix spectral diagnostics, adaptive embedding decisions and explicit "
                "callability outputs to separate supported signal from high-dimensional noise. "
                "This figure should be read as a workflow and diagnostic overview, not as a claim "
                "of new random-matrix theory. Source data: "
                "`results/figures/source_data/figure1_algorithm_diagnostics.tsv`."
            ),
            "",
            "## Figure 2. Synthetic calibration of false-signal and rare-state behavior.",
            (
                "Synthetic null, planted-signal and rare-state scenarios evaluate whether the "
                "workflow controls false signal under tested null families while retaining "
                "detectable rare states. Realistic null simulations covered gene-permutation, "
                "library-multinomial and library-stratified gene nulls; the maximum observed "
                f"false-signal rate in the current 50-repeat summary was {_pct(values['max_false_signal'])}. "
                "Rare-state power is claim-bounded: moderate prevalence/effect regimes are "
                "supported, whereas prevalence 0.02/effect size 2.5 remains weak. Source data: "
                "`results/calibration/realistic_null_summary.tsv` and "
                "`results/calibration/rare_state_power_summary.tsv`."
            ),
            "",
            "## Figure 3. Public benchmark callability, caveats and no-call decisions.",
            (
                "Public benchmark panels report RMTGuard performance alongside fixed-PC, elbow, "
                "Scanpy-like, Seurat and scLENSpy comparators where available. The callability "
                f"map includes PBMC68k/Zheng 2017 as a diagnostic no-call (annotation ARI "
                f"{_fmt(pbmc68k.annotation_ari)}), not a biological discovery. PBMC3k, Kang "
                "IFN-beta PBMC and Baron pancreas are retained as caveated benchmark contexts. "
                "The legend must not state that RMTGuard outperforms all fixed-PC or elbow "
                "baselines. Source data: `results/callability/no_call_decision_map.tsv`, "
                "`results/submission/sclens_vs_rmtguard_stability_nrand20.tsv` and related "
                "Figure 3 source-data tables."
            ),
            "",
            "## Figure 4. Bounded PDAC/TME public-data application.",
            (
                "RMTGuard is applied to public PDAC/TME datasets to illustrate marker, pathway "
                "and atlas-context interpretation under the current callability framework. The "
                "figure supports a methods-paper use case only. It does not establish a new PDAC "
                "mechanism, clinical biomarker, prognosis model, therapy-response predictor, "
                "spatial validation or protein-level validation. Source data: "
                "`results/figures/source_data/figure4_pdac_tme_strengthened_source.tsv`."
            ),
            "",
            "## Figure 5. Ablation, reproducibility and release readiness.",
            (
                "Ablation and reproducibility panels summarize the tested contributions of "
                "RMTGuard components, runtime/memory reporting and release artifacts. The public "
                "repository, GitHub Release and Zenodo DOI support code availability for the "
                "archived release, while post-release working-branch changes should not be "
                "described as part of the immutable DOI snapshot unless a new release is issued. "
                "Source data: `results/figures/source_data/figure5_realdata_ablation_delta_summary.tsv` "
                "and release manifests."
            ),
            "",
            "## Extended Data Figure. Topology stress and Paul15 real-data topology monitor.",
            (
                "Synthetic topology stress tests evaluate line, branch and loop geometry "
                f"({topo_short}). The Paul15 hematopoiesis monitor uses an annotation-derived "
                "cluster graph rather than experimentally measured pseudotime. RMTGuard had "
                f"higher annotation ARI ({_fmt(rt.annotation_ari_mean)}) and lower neighbor tree "
                f"distance ({_fmt(rt.neighbor_tree_distance_mean)}) than fixed 30 PCs "
                f"({_fmt(f30.neighbor_tree_distance_mean)}) and fixed 50 PCs "
                f"({_fmt(f50.neighbor_tree_distance_mean)}), but fixed-PC baselines had higher "
                "centroid tree rho/reference edge recall. This extended figure should therefore "
                "be described as topology monitoring with trade-offs, not as trajectory-method "
                "superiority. Source data: `results/submission/topology_stress_summary.tsv` and "
                "`results/submission/realdata_topology_summary.tsv`."
            ),
        ]
    )


def _build_audit_rows() -> list[dict[str, str]]:
    rows = [
        {
            "text_item": "Results section 1",
            "claim_type": "workflow_boundary",
            "evidence_path": "docs/current_evidence_freeze_2026-05-12.md",
            "allowed_wording": "callability-aware random-matrix workflow",
            "forbidden_wording": "universal replacement for Seurat/Scanpy/fixed-PC workflows",
            "status": "controlled",
        },
        {
            "text_item": "Results section 2",
            "claim_type": "null_and_rare_state",
            "evidence_path": "results/calibration/realistic_null_summary.tsv;results/calibration/rare_state_power_summary.tsv",
            "allowed_wording": "supported under tested null and rare-state settings",
            "forbidden_wording": "exact type-I control or guaranteed rare-state retention in all scRNA-seq datasets",
            "status": "controlled",
        },
        {
            "text_item": "Results section 3",
            "claim_type": "public_benchmark",
            "evidence_path": "results/callability/no_call_decision_map.tsv;results/submission/sclens_vs_rmtguard_stability_nrand20.tsv",
            "allowed_wording": "callability and caveat reporting",
            "forbidden_wording": "broad stability superiority over all strongest baselines",
            "status": "controlled",
        },
        {
            "text_item": "Results section 4",
            "claim_type": "topology",
            "evidence_path": "results/submission/topology_stress_summary.tsv;results/submission/realdata_topology_summary.tsv",
            "allowed_wording": "topology monitor with real-data trade-offs",
            "forbidden_wording": "de novo trajectory inference or topology superiority",
            "status": "controlled",
        },
        {
            "text_item": "Results section 5",
            "claim_type": "pdac_and_ablation",
            "evidence_path": "docs/figure4_pdac_tme_wording_freeze.md;docs/component_ablation_benchmark.md;docs/realdata_ablation_annotation.md",
            "allowed_wording": "bounded public-data use case and tested ablation findings",
            "forbidden_wording": "new PDAC mechanism, clinical validation, or universal component necessity",
            "status": "controlled",
        },
        {
            "text_item": "Figure legends",
            "claim_type": "caption_boundary",
            "evidence_path": "manuscript/figure_legends_freeze_aligned.md",
            "allowed_wording": "explicit source data and caveats in every legend",
            "forbidden_wording": "caption-level upgrade of caveated or no-call results",
            "status": "controlled",
        },
    ]
    return rows


def main() -> int:
    values = _collect_values()
    _write_text_atomic(OUT_RESULTS, _build_results(values))
    _write_text_atomic(OUT_LEGENDS, _build_legends(values))
    _write_tsv_atomic(OUT_AUDIT, _build_audit_rows())
    print(OUT_RESULTS.relative_to(ROOT).as_posix())
    print(OUT_LEGENDS.relative_to(ROOT).as_posix())
    print(OUT_AUDIT.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
