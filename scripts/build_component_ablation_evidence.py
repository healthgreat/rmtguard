#!/usr/bin/env python
"""Build the current component-ablation evidence matrix for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-02
Purpose: Convert existing stability, calibration, rescue-probe, and draft
ablation outputs into an explicit component-level evidence and gap report.
Data source: Generated local TSVs under results/.
Method notes: This is an evidence-control artifact, not a replacement for
final manuscript-grade component ablation experiments.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
STABILITY_STATS = (
    ROOT
    / "results"
    / "manuscript_stability_benchmarks"
    / "manuscript_stability_statistics.tsv"
)
REALISTIC_NULL = ROOT / "results" / "calibration" / "realistic_null_summary.tsv"
RARE_POWER = ROOT / "results" / "calibration" / "rare_state_power_summary.tsv"
COMPONENT_ABLATION_SUMMARY = ROOT / "results" / "ablation" / "component_ablation_summary.tsv"
REALDATA_ABLATION_SUMMARY = (
    ROOT / "results" / "ablation" / "realdata_ablation_annotation_summary.tsv"
)
DRAFT_ABLATION = (
    ROOT / "results" / "figures" / "source_data" / "figure5_ablation_stability_summary.tsv"
)
RESCUE_PROBES = ROOT / "results" / "rescue" / "algorithm_rescue_probe_summary.tsv"
NO_CALL_MAP = ROOT / "results" / "callability" / "no_call_decision_map.tsv"

OUT_DIR = ROOT / "results" / "ablation"
OUT_EVIDENCE = OUT_DIR / "component_ablation_evidence.tsv"
OUT_GAP = OUT_DIR / "component_ablation_gap_matrix.tsv"
OUT_MD = ROOT / "docs" / "component_ablation_evidence.md"


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


def _write_tsv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _float(value: str, default: float = math.nan) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format(value: float, digits: int = 3) -> str:
    if math.isnan(value):
        return "NA"
    return f"{value:.{digits}f}"


def _evidence_path(*paths: Path) -> str:
    existing = [_rel(path) for path in paths if path.exists()]
    return ";".join(existing) if existing else "missing"


def _adaptive_embedding_summary(
    stability_rows: list[dict[str, str]]
) -> tuple[str, str, str]:
    by_key = {
        (row.get("dataset_id", ""), row.get("method", "")): row
        for row in stability_rows
    }
    deltas: list[float] = []
    snippets: list[str] = []
    for dataset_id in sorted({row.get("dataset_id", "") for row in stability_rows}):
        adaptive = by_key.get((dataset_id, "rmtguard"))
        strict = by_key.get((dataset_id, "rmtguard_strict_signal"))
        if not adaptive or not strict:
            continue
        delta = _float(adaptive.get("mean_pairwise_ari", "")) - _float(
            strict.get("mean_pairwise_ari", "")
        )
        deltas.append(delta)
        snippets.append(f"{dataset_id}:{_format(delta)}")
    if not deltas:
        return "missing", "No direct adaptive-vs-strict comparison table found.", "NA"
    positives = sum(delta > 0 for delta in deltas)
    status = "partial_mixed" if positives < len(deltas) else "supported_partial"
    summary = (
        "Adaptive embedding delta versus strict-signal embedding across "
        f"{len(deltas)} datasets: " + ", ".join(snippets) + "."
    )
    quantitative = (
        f"mean_delta={_format(mean(deltas))};min_delta={_format(min(deltas))};"
        f"positive_datasets={positives}/{len(deltas)}"
    )
    return status, summary, quantitative


def _null_summary(null_rows: list[dict[str, str]]) -> tuple[str, str, str]:
    if not null_rows:
        return "missing", "No realistic-null summary found.", "NA"
    max_false_signal = max(_float(row.get("false_signal_rate", "")) for row in null_rows)
    max_false_call = max(_float(row.get("false_call_rate", "")) for row in null_rows)
    min_no_call = min(_float(row.get("no_call_rate", "")) for row in null_rows)
    models = ",".join(row.get("null_model", "") for row in null_rows)
    status = "supported_partial" if max_false_call <= 0.05 else "risk_high"
    summary = (
        f"Count-preserving realistic nulls ({models}) show max false-call "
        f"rate {_format(max_false_call)} and minimum no-call rate {_format(min_no_call)}."
    )
    quantitative = (
        f"max_false_signal={_format(max_false_signal)};"
        f"max_false_call={_format(max_false_call)};"
        f"min_no_call={_format(min_no_call)}"
    )
    return status, summary, quantitative


def _rare_power_summary(power_rows: list[dict[str, str]]) -> tuple[str, str, str]:
    if not power_rows:
        return "missing", "No rare-state power summary found.", "NA"
    powers = [_float(row.get("power", "")) for row in power_rows]
    guard_rates = [_float(row.get("rare_state_guard_selection_rate", "")) for row in power_rows]
    high_power = sum(power >= 0.80 for power in powers)
    status = "supported_partial" if high_power >= len(powers) / 2 else "partial_weak"
    summary = (
        f"Rare-state guard power is >=0.80 in {high_power}/{len(powers)} grid "
        f"settings, but the weakest low-prevalence/effect settings remain below target."
    )
    quantitative = (
        f"min_power={_format(min(powers))};median_power={_format(sorted(powers)[len(powers)//2])};"
        f"high_power_settings={high_power}/{len(powers)};"
        f"mean_guard_selection={_format(mean(guard_rates))}"
    )
    return status, summary, quantitative


def _draft_ablation_summary(
    draft_rows: list[dict[str, str]], ablation_id: str
) -> tuple[str, str, str]:
    rows = [row for row in draft_rows if row.get("ablation_id") == ablation_id]
    if not rows:
        return "missing_experiment", f"No draft row found for {ablation_id}.", "NA"
    values = [
        _float(row.get("mean_pairwise_ari", ""))
        for row in rows
        if row.get("method") == "rmtguard"
    ]
    if not values:
        values = [_float(row.get("mean_pairwise_ari", "")) for row in rows]
    datasets = sorted({row.get("dataset_id", "") for row in rows})
    summary = (
        f"Draft ablation {ablation_id} has {len(rows)} row(s) on "
        f"{','.join(datasets)}; not final cross-dataset evidence."
    )
    quantitative = f"mean_pairwise_ari={_format(mean(values))}" if values else "NA"
    return "single_dataset_draft", summary, quantitative


def _rescue_summary(rescue_rows: list[dict[str, str]]) -> tuple[str, str, str]:
    if not rescue_rows:
        return "missing", "No rejected rescue-probe table found.", "NA"
    rejected = [
        row
        for row in rescue_rows
        if str(row.get("decision", "")).startswith("reject")
        or "reject" in str(row.get("decision", ""))
    ]
    comparator = [
        row for row in rescue_rows if row.get("decision", "") == "comparator_context"
    ]
    summary = (
        f"{len(rejected)} rescue-probe row(s) are explicitly rejected and "
        f"{len(comparator)} comparator-context row(s) are preserved."
    )
    quantitative = f"rejected_probe_rows={len(rejected)};comparator_rows={len(comparator)}"
    return "negative_probe_preserved", summary, quantitative


def _ablation_row(
    rows: list[dict[str, str]], ablation_id: str, scenario: str
) -> dict[str, str]:
    return next(
        (
            row
            for row in rows
            if row.get("ablation_id") == ablation_id
            and row.get("scenario") == scenario
        ),
        {},
    )


def _ablation_float(
    rows: list[dict[str, str]], ablation_id: str, scenario: str, field: str
) -> float:
    return _float(_ablation_row(rows, ablation_id, scenario).get(field, ""))


def _draft_component_summary(
    rows: list[dict[str, str]], ablation_id: str, component: str
) -> tuple[str, str, str]:
    null_row = _ablation_row(rows, ablation_id, "realistic_null")
    rare_row = _ablation_row(rows, ablation_id, "rare_state_power")
    if not null_row and not rare_row:
        return "missing_experiment", f"No draft component row found for {component}.", "NA"
    null_false_call = _float(null_row.get("false_call_rate", "")) if null_row else math.nan
    rare_power = _float(rare_row.get("power", "")) if rare_row else math.nan
    rare_f1 = _float(rare_row.get("mean_rare_f1", "")) if rare_row else math.nan
    n_rows = int(_float(null_row.get("n_rows", "0"), 0)) + int(
        _float(rare_row.get("n_rows", "0"), 0)
    )
    summary = (
        f"Draft component screen has {n_rows} row(s) for {component}; "
        f"null false-call={_format(null_false_call)}, rare power={_format(rare_power)}, "
        f"rare F1={_format(rare_f1)}."
    )
    quantitative = (
        f"draft_null_false_call={_format(null_false_call)};"
        f"draft_rare_power={_format(rare_power)};"
        f"draft_rare_f1={_format(rare_f1)}"
    )
    return "draft_screen_present", summary, quantitative


def _rare_guard_on_off_summary(
    rows: list[dict[str, str]],
) -> tuple[str, str, str]:
    default_power = _ablation_float(
        rows, "default_v3_3", "rare_state_power", "power"
    )
    off_power = _ablation_float(
        rows, "rare_state_guard_off", "rare_state_power", "power"
    )
    default_f1 = _ablation_float(
        rows, "default_v3_3", "rare_state_power", "mean_rare_f1"
    )
    off_f1 = _ablation_float(
        rows, "rare_state_guard_off", "rare_state_power", "mean_rare_f1"
    )
    if math.isnan(default_power) or math.isnan(off_power):
        return "missing_experiment", "No rare-state guard on/off draft screen found.", "NA"
    status = "draft_screen_positive" if default_power > off_power else "draft_screen_mixed"
    summary = (
        "Draft rare-state guard screen shows default guard versus guard-off "
        f"power {_format(default_power)} vs {_format(off_power)} and rare F1 "
        f"{_format(default_f1)} vs {_format(off_f1)}."
    )
    quantitative = (
        f"guard_on_power={_format(default_power)};"
        f"guard_off_power={_format(off_power)};"
        f"guard_on_rare_f1={_format(default_f1)};"
        f"guard_off_rare_f1={_format(off_f1)}"
    )
    return status, summary, quantitative


def _no_call_forcing_summary(rows: list[dict[str, str]]) -> tuple[str, str, str]:
    default_false_call = _ablation_float(
        rows, "default_v3_3", "realistic_null", "false_call_rate"
    )
    forced_false_call = _ablation_float(
        rows, "force_min_embedding_pcs_10", "realistic_null", "false_call_rate"
    )
    forced_power = _ablation_float(
        rows, "force_min_embedding_pcs_10", "rare_state_power", "power"
    )
    forced_f1 = _ablation_float(
        rows, "force_min_embedding_pcs_10", "rare_state_power", "mean_rare_f1"
    )
    forced_batch_ari = _ablation_float(
        rows, "force_min_embedding_pcs_10", "batch_effect", "mean_batch_ari"
    )
    forced_label_ari = _ablation_float(
        rows, "force_min_embedding_pcs_10", "batch_effect", "mean_ari"
    )
    if math.isnan(default_false_call) or math.isnan(forced_false_call):
        return "missing_experiment", "No forced-min-PC no-call draft screen found.", "NA"
    status = (
        "draft_screen_positive_negative_control"
        if forced_false_call > default_false_call
        else "draft_screen_mixed"
    )
    summary = (
        "Draft no-call negative control shows forced minimum 10 PCs raises "
        f"null false-call from {_format(default_false_call)} to "
        f"{_format(forced_false_call)} and leaves rare-state power "
        f"{_format(forced_power)}. In the draft batch-effect screen, forced PCs "
        f"show batch ARI {_format(forced_batch_ari)} and label ARI "
        f"{_format(forced_label_ari)}."
    )
    quantitative = (
        f"default_null_false_call={_format(default_false_call)};"
        f"forced_null_false_call={_format(forced_false_call)};"
        f"forced_rare_power={_format(forced_power)};"
        f"forced_rare_f1={_format(forced_f1)};"
        f"forced_batch_ari={_format(forced_batch_ari)};"
        f"forced_label_ari={_format(forced_label_ari)}"
    )
    return status, summary, quantitative


def _biwhiten_summary(rows: list[dict[str, str]]) -> tuple[str, str, str]:
    default_false_call = _ablation_float(
        rows, "default_v3_3", "realistic_null", "false_call_rate"
    )
    zscore_false_call = _ablation_float(
        rows, "whiten_zscore", "realistic_null", "false_call_rate"
    )
    zscore_power = _ablation_float(rows, "whiten_zscore", "rare_state_power", "power")
    default_batch_ari = _ablation_float(
        rows, "default_v3_3", "batch_effect", "mean_batch_ari"
    )
    default_label_ari = _ablation_float(
        rows, "default_v3_3", "batch_effect", "mean_ari"
    )
    zscore_batch_ari = _ablation_float(
        rows, "whiten_zscore", "batch_effect", "mean_batch_ari"
    )
    zscore_label_ari = _ablation_float(
        rows, "whiten_zscore", "batch_effect", "mean_ari"
    )
    residualized_batch_ari = _ablation_float(
        rows, "batch_residualized", "batch_effect", "mean_batch_ari"
    )
    residualized_label_ari = _ablation_float(
        rows, "batch_residualized", "batch_effect", "mean_ari"
    )
    if math.isnan(default_false_call) or math.isnan(zscore_false_call):
        return "missing_experiment", "No biwhitening versus z-score draft screen found.", "NA"
    status = (
        "draft_screen_positive_batch_present"
        if zscore_false_call > default_false_call and not math.isnan(default_batch_ari)
        else "draft_screen_mixed"
    )
    summary = (
        "Draft whitening screen shows z-score whitening increases null "
        f"false-call from {_format(default_false_call)} to "
        f"{_format(zscore_false_call)} while rare-state power is "
        f"{_format(zscore_power)}. In the batch-effect screen, default "
        f"biwhitening has label ARI {_format(default_label_ari)} and batch ARI "
        f"{_format(default_batch_ari)}, z-score has label ARI "
        f"{_format(zscore_label_ari)} and batch ARI {_format(zscore_batch_ari)}, "
        f"and batch residualization has label ARI {_format(residualized_label_ari)} "
        f"and batch ARI {_format(residualized_batch_ari)}."
    )
    quantitative = (
        f"biwhiten_null_false_call={_format(default_false_call)};"
        f"zscore_null_false_call={_format(zscore_false_call)};"
        f"zscore_rare_power={_format(zscore_power)};"
        f"default_batch_ari={_format(default_batch_ari)};"
        f"default_label_ari={_format(default_label_ari)};"
        f"zscore_batch_ari={_format(zscore_batch_ari)};"
        f"zscore_label_ari={_format(zscore_label_ari)};"
        f"batch_residualized_batch_ari={_format(residualized_batch_ari)};"
        f"batch_residualized_label_ari={_format(residualized_label_ari)}"
    )
    return status, summary, quantitative


def _realdata_summary(rows: list[dict[str, str]]) -> tuple[str, str, str]:
    if not rows:
        return "missing_realdata_annotation", "No real-data annotation ablation summary found.", "NA"
    default = [row for row in rows if row.get("ablation_id") == "default_v3_3"]
    forced = [
        row for row in rows if row.get("ablation_id") == "force_min_embedding_pcs_10"
    ]
    batch_res = [
        row for row in rows if row.get("ablation_id") == "batch_residualized"
    ]
    datasets = sorted({row.get("dataset_id", "") for row in rows})
    run_labels = sorted(
        {row.get("run_label", "default") or "default" for row in rows}
    )
    repeat_depths = [
        int(float(row.get("n_repeats", "0")))
        for row in rows
        if row.get("n_repeats", "")
    ]
    max_repeats = max(repeat_depths) if repeat_depths else 0
    default_ari = mean([_float(row.get("mean_label_ari", "")) for row in default])
    forced_ari = mean([_float(row.get("mean_label_ari", "")) for row in forced])
    batch_res_ari = mean([_float(row.get("mean_label_ari", "")) for row in batch_res])
    finite_batch = [
        _float(row.get("mean_batch_ari", ""))
        for row in rows
        if math.isfinite(_float(row.get("mean_batch_ari", "")))
    ]
    max_batch_ari = max(finite_batch) if finite_batch else math.nan
    status = "draft_realdata_annotation_present"
    if max_repeats >= 3:
        status = "repeated_split_pilot_present"
    if max_repeats >= 10:
        status = "ten_repeat_realdata_annotation_pilot_present"
    summary = (
        f"Draft real-data annotation check covers {len(datasets)} dataset(s): "
        f"{','.join(datasets)} across run label(s) {','.join(run_labels)}. "
        f"Maximum repeat depth is {max_repeats}. Mean label ARI is {_format(default_ari)} for "
        f"default RMTGuard, {_format(forced_ari)} for forced minimum PCs, and "
        f"{_format(batch_res_ari)} for batch-residualized fitting."
    )
    quantitative = (
        f"realdata_dataset_count={len(datasets)};"
        f"realdata_max_repeats={max_repeats};"
        f"realdata_run_labels={','.join(run_labels)};"
        f"default_realdata_label_ari={_format(default_ari)};"
        f"forced_realdata_label_ari={_format(forced_ari)};"
        f"batch_residualized_realdata_label_ari={_format(batch_res_ari)};"
        f"max_finite_realdata_batch_ari={_format(max_batch_ari)}"
    )
    return status, summary, quantitative


def build_component_rows() -> list[dict[str, object]]:
    stability = _read_tsv(STABILITY_STATS)
    null_rows = _read_tsv(REALISTIC_NULL)
    power_rows = _read_tsv(RARE_POWER)
    ablation_summary_rows = _read_tsv(COMPONENT_ABLATION_SUMMARY)
    realdata_ablation_rows = _read_tsv(REALDATA_ABLATION_SUMMARY)
    draft_rows = _read_tsv(DRAFT_ABLATION)
    rescue_rows = _read_tsv(RESCUE_PROBES)
    no_call_rows = _read_tsv(NO_CALL_MAP)

    adaptive_status, adaptive_summary, adaptive_quant = _adaptive_embedding_summary(stability)
    null_status, null_summary, null_quant = _null_summary(null_rows)
    rare_status, rare_summary, rare_quant = _rare_power_summary(power_rows)
    pc_perm_status, pc_perm_summary, pc_perm_quant = _draft_component_summary(
        ablation_summary_rows,
        "pc_rule_mp_tw_permutation",
        "MP+TW+permutation calibration",
    )
    hvg_plateau_status, hvg_plateau_summary, hvg_plateau_quant = (
        _draft_component_summary(
            ablation_summary_rows,
            "hvg_rule_spectral_plateau",
            "spectral plateau HVG",
        )
    )
    rare_guard_status, rare_guard_summary, rare_guard_quant = (
        _rare_guard_on_off_summary(ablation_summary_rows)
    )
    no_call_force_status, no_call_force_summary, no_call_force_quant = (
        _no_call_forcing_summary(ablation_summary_rows)
    )
    biwhiten_status, biwhiten_summary, biwhiten_quant = _biwhiten_summary(
        ablation_summary_rows
    )
    realdata_status, realdata_summary, realdata_quant = _realdata_summary(
        realdata_ablation_rows
    )
    min_pc_status, min_pc_summary, min_pc_quant = _draft_ablation_summary(
        draft_rows, "min_embedding_pcs_10"
    )
    consensus_status, consensus_summary, consensus_quant = _draft_ablation_summary(
        draft_rows, "consensus_clustering"
    )
    rescue_status, rescue_summary, rescue_quant = _rescue_summary(rescue_rows)

    no_call_status = "supported_partial" if no_call_rows else "missing"
    no_call_summary = (
        f"No-call decision map has {len(no_call_rows)} row(s) and is exposed as a "
        "machine-readable decision artifact."
        if no_call_rows
        else "No no-call decision-map artifact found."
    )

    rows = [
        {
            "component_id": "mp_tw_noise_edge",
            "component_label": "MP/TW noise edge",
            "current_evidence_status": null_status,
            "claim_role": "Controls false signal PCs under high-dimensional nulls.",
            "direct_evidence_summary": null_summary,
            "quantitative_signal": null_quant,
            "reviewer_risk": "Draft separated PC-rule screen exists, but repeat count is low and not manuscript-grade.",
            "manuscript_use": "Use for null-control claim only; do not claim broad real-data superiority from this row.",
            "next_required_experiment": "Run MP-only, MP+TW, and MP+TW+permutation variants on realistic nulls and rare-state grids with 20-50 repeats.",
            "evidence_paths": _evidence_path(REALISTIC_NULL, COMPONENT_ABLATION_SUMMARY),
        },
        {
            "component_id": "permutation_calibration",
            "component_label": "Permutation calibration",
            "current_evidence_status": pc_perm_status,
            "claim_role": "Finite-sample correction and reviewer-facing type-I error calibration.",
            "direct_evidence_summary": pc_perm_summary,
            "quantitative_signal": pc_perm_quant,
            "reviewer_risk": "Moderate-high; this is now runnable and screened, but only with three permutations and draft repeats.",
            "manuscript_use": "Mention as draft ablation evidence; final claim still requires higher permutations/repeats and confidence intervals.",
            "next_required_experiment": "Compare no permutation versus 20/50/100 permutations on count-preserving nulls and planted rare-state matrices.",
            "evidence_paths": _evidence_path(COMPONENT_ABLATION_SUMMARY, REALISTIC_NULL, RARE_POWER),
        },
        {
            "component_id": "hvg_spectral_plateau",
            "component_label": "HVG spectral plateau",
            "current_evidence_status": hvg_plateau_status,
            "claim_role": "Reduces subjective HVG choice by using spectral stability rather than a fixed HVG count.",
            "direct_evidence_summary": hvg_plateau_summary,
            "quantitative_signal": hvg_plateau_quant,
            "reviewer_risk": "Moderate-high; draft screen exists but does not yet cover real datasets or confidence intervals.",
            "manuscript_use": "Use as draft sensitivity evidence only.",
            "next_required_experiment": "Run fixed 1k/2k/3k HVG and spectral-plateau HVG variants on stability, annotation, null, and rare-state grids.",
            "evidence_paths": _evidence_path(COMPONENT_ABLATION_SUMMARY),
        },
        {
            "component_id": "adaptive_near_edge_embedding",
            "component_label": "Adaptive near-edge embedding",
            "current_evidence_status": adaptive_status,
            "claim_role": "Allows stable near-edge PCs into downstream embedding while preserving strict signal-PC accounting.",
            "direct_evidence_summary": adaptive_summary,
            "quantitative_signal": adaptive_quant,
            "reviewer_risk": "Mixed; it improves some datasets but hurts Baron relative to strict-signal embedding.",
            "manuscript_use": "Use as a bounded engineering improvement, not as universal stability rescue.",
            "next_required_experiment": "Rerun adaptive versus strict embedding with final Seurat/JackStraw baselines and annotation-recovery tests.",
            "evidence_paths": _evidence_path(STABILITY_STATS),
        },
        {
            "component_id": "rare_state_guard",
            "component_label": "Rare-state guard",
            "current_evidence_status": rare_guard_status,
            "claim_role": "Prevents conservative no-call behavior from discarding coherent rare states.",
            "direct_evidence_summary": rare_summary + " " + rare_guard_summary,
            "quantitative_signal": rare_quant + ";" + rare_guard_quant,
            "reviewer_risk": "Moderate; guard-on/off draft screen is positive, but current repeats are draft scale.",
            "manuscript_use": "Use as promising internal evidence; keep manuscript language provisional until repeat count increases.",
            "next_required_experiment": "Add rare-state guard on/off comparison with confidence intervals across prevalence/effect-size grid.",
            "evidence_paths": _evidence_path(RARE_POWER, COMPONENT_ABLATION_SUMMARY),
        },
        {
            "component_id": "no_call_contract",
            "component_label": "Diagnostic no-call contract",
            "current_evidence_status": no_call_force_status,
            "claim_role": "Turns insufficient signal into an explicit diagnostic output instead of forced clustering.",
            "direct_evidence_summary": no_call_summary + " " + no_call_force_summary,
            "quantitative_signal": f"decision_rows={len(no_call_rows)};{no_call_force_quant};{realdata_quant}",
            "reviewer_risk": "Moderate; draft evidence is strong, but no-call must be positioned as a transparent diagnostic boundary, not as a hidden failure.",
            "manuscript_use": "Central defensible claim for Genome Biology-style workflow paper.",
            "next_required_experiment": "Render a no-call decision tree/heatmap in Figure 3 and scale real-data annotation checks to 10-50 splits.",
            "evidence_paths": _evidence_path(NO_CALL_MAP, COMPONENT_ABLATION_SUMMARY, REALDATA_ABLATION_SUMMARY),
        },
        {
            "component_id": "resolution_path_stability",
            "component_label": "Resolution path stability",
            "current_evidence_status": rescue_status,
            "claim_role": "Avoids promoting unstable graph-resolution tweaks after local improvements.",
            "direct_evidence_summary": rescue_summary,
            "quantitative_signal": rescue_quant,
            "reviewer_risk": "Low for transparency, high for performance rescue; probes are mostly negative.",
            "manuscript_use": "Use as evidence of disciplined stop rules, not as a positive performance figure.",
            "next_required_experiment": "Summarize graph-resolution rescue probes in supplementary table and keep rejected probes visible.",
            "evidence_paths": _evidence_path(RESCUE_PROBES),
        },
        {
            "component_id": "min_embedding_pcs_forcing",
            "component_label": "Fixed minimum embedding PCs",
            "current_evidence_status": no_call_force_status,
            "claim_role": "Negative-control check against forcing fixed PCs to pass the PBMC3k stability gate.",
            "direct_evidence_summary": min_pc_summary + " " + no_call_force_summary,
            "quantitative_signal": min_pc_quant + ";" + no_call_force_quant + ";" + realdata_quant,
            "reviewer_risk": "Low if kept as negative control; high if used as algorithm default.",
            "manuscript_use": "Keep as ablation/negative control only.",
            "next_required_experiment": "Repeat fixed-min-PC forcing across all four datasets and null grids before any claim.",
            "evidence_paths": _evidence_path(DRAFT_ABLATION, COMPONENT_ABLATION_SUMMARY, REALDATA_ABLATION_SUMMARY),
        },
        {
            "component_id": "consensus_clustering",
            "component_label": "Consensus clustering only",
            "current_evidence_status": consensus_status,
            "claim_role": "Negative-control check showing consensus clustering alone does not solve the gate.",
            "direct_evidence_summary": consensus_summary,
            "quantitative_signal": consensus_quant,
            "reviewer_risk": "Low if reported as rejected fallback.",
            "manuscript_use": "Supplementary negative ablation only.",
            "next_required_experiment": "No default promotion unless cross-dataset stability and annotation recovery improve.",
            "evidence_paths": _evidence_path(DRAFT_ABLATION),
        },
        {
            "component_id": "biwhitening_batch_residualization",
            "component_label": "Biwhitening and batch residualization",
            "current_evidence_status": biwhiten_status,
            "claim_role": "Separates biological signal from library-size, batch, or covariance scaling artifacts.",
            "direct_evidence_summary": biwhiten_summary + " Draft public real-data annotation checks now include a repeated-split pilot, but repeat count remains below manuscript grade.",
            "quantitative_signal": biwhiten_quant + ";" + realdata_quant,
            "reviewer_risk": "Moderate-high; synthetic and draft real-data screens exist, but repeat count is low and matched Seurat/JackStraw baselines remain missing.",
            "manuscript_use": "Use as draft whitening, synthetic batch-effect, and real-data annotation evidence only; do not claim broad batch robustness until repeated real-data runs finish.",
            "next_required_experiment": "Scale synthetic batch grid and real-data Kang/Baron/PBMC68k annotation checks to 10-50 repeats with confidence intervals.",
            "evidence_paths": _evidence_path(COMPONENT_ABLATION_SUMMARY, REALDATA_ABLATION_SUMMARY),
        },
        {
            "component_id": "realdata_annotation_recovery",
            "component_label": "Real-data annotation recovery",
            "current_evidence_status": realdata_status,
            "claim_role": "Checks whether component variants preserve public cell-type annotation recovery on real datasets.",
            "direct_evidence_summary": realdata_summary,
            "quantitative_signal": realdata_quant,
            "reviewer_risk": "Moderate-high; 10-repeat real-data CI pilot now covers Kang, Baron, PBMC68k, and PDAC external validation, but 20-50 repeats and matched Seurat/JackStraw baselines remain missing.",
            "manuscript_use": "Use as draft annotation sensitivity evidence only.",
            "next_required_experiment": "Run 20-50 repeated splits and add matched Seurat v5, JackStraw, and PC-rule baselines.",
            "evidence_paths": _evidence_path(REALDATA_ABLATION_SUMMARY),
        },
    ]
    return rows


def build_gap_rows() -> list[dict[str, object]]:
    realdata_status, _, _ = _realdata_summary(_read_tsv(REALDATA_ABLATION_SUMMARY))
    return [
        {
            "ablation_question": "Does MP edge alone control false signal under realistic count nulls?",
            "manuscript_importance": "critical",
            "current_status": "draft_screen_present",
            "minimum_next_run": "MP-only versus MP+TW versus MP+TW+permutation; 20-50 repeats; three null models.",
            "pass_condition": "False-call rate near preset alpha without rare-state power collapse.",
            "priority": "P0",
            "evidence_path": f"{_rel(REALISTIC_NULL)};{_rel(COMPONENT_ABLATION_SUMMARY)}",
        },
        {
            "ablation_question": "Does permutation calibration improve finite-sample type-I error control?",
            "manuscript_importance": "critical",
            "current_status": "draft_screen_present",
            "minimum_next_run": "0, 20, 50, and 100 permutations on null and rare-state grids.",
            "pass_condition": "Lower or calibrated false-signal rate with acceptable runtime.",
            "priority": "P0",
            "evidence_path": _rel(COMPONENT_ABLATION_SUMMARY),
        },
        {
            "ablation_question": "Does HVG spectral plateau outperform fixed-HVG choices?",
            "manuscript_importance": "high",
            "current_status": "draft_screen_present",
            "minimum_next_run": "Compare spectral plateau to fixed 1k/2k/3k HVG on four public datasets plus simulations.",
            "pass_condition": "Comparable annotation recovery and improved or clearly bounded stability/no-call behavior.",
            "priority": "P1",
            "evidence_path": _rel(COMPONENT_ABLATION_SUMMARY),
        },
        {
            "ablation_question": "Does adaptive near-edge embedding improve over strict signal PCs?",
            "manuscript_importance": "critical",
            "current_status": "partial_mixed",
            "minimum_next_run": "Adaptive versus strict embedding on final benchmark split and annotation metrics.",
            "pass_condition": "Improves stability without reducing annotation recovery or increasing null false calls.",
            "priority": "P0",
            "evidence_path": _rel(STABILITY_STATS),
        },
        {
            "ablation_question": "Does the rare-state guard preserve rare coherent states?",
            "manuscript_importance": "critical",
            "current_status": "draft_screen_positive",
            "minimum_next_run": "Rare-state guard on/off power grid with confidence intervals.",
            "pass_condition": "Improves rare F1/ARI power while preserving null no-call.",
            "priority": "P0",
            "evidence_path": f"{_rel(RARE_POWER)};{_rel(COMPONENT_ABLATION_SUMMARY)}",
        },
        {
            "ablation_question": "Does no-call prevent overclustering when signal is insufficient?",
            "manuscript_importance": "critical",
            "current_status": "draft_screen_positive_negative_control",
            "minimum_next_run": "No-call on/off and forced clustering comparison on realistic nulls and PBMC68k stress test.",
            "pass_condition": "Lower false call/overclustering with explicit no-call reason retained.",
            "priority": "P0",
            "evidence_path": f"{_rel(NO_CALL_MAP)};{_rel(COMPONENT_ABLATION_SUMMARY)}",
        },
        {
            "ablation_question": "Does biwhitening or residualization prevent batch-driven PCs?",
            "manuscript_importance": "high",
            "current_status": "draft_screen_present_synthetic_batch",
            "minimum_next_run": "Scale synthetic batch grid to 20-50 repeats plus Kang IFN-beta with and without residualization.",
            "pass_condition": "Reduced batch-aligned PCs without erasing biological IFN response structure.",
            "priority": "P1",
            "evidence_path": _rel(COMPONENT_ABLATION_SUMMARY),
        },
        {
            "ablation_question": "Do fixed minimum PCs or consensus clustering simply tune around the gate?",
            "manuscript_importance": "high",
            "current_status": "draft_screen_positive_negative_control",
            "minimum_next_run": "Repeat rejected fallback controls on all Phase 1 datasets and realistic nulls.",
            "pass_condition": "No forced-PC fallback is promoted unless null and annotation gates remain controlled.",
            "priority": "P1",
            "evidence_path": f"{_rel(DRAFT_ABLATION)};{_rel(COMPONENT_ABLATION_SUMMARY)}",
        },
        {
            "ablation_question": "Do component choices preserve real-data cell-type annotation recovery?",
            "manuscript_importance": "critical",
            "current_status": realdata_status,
            "minimum_next_run": "Repeat Kang, Baron, PBMC68k, and one external validation dataset across 20-50 seeds/splits with matched baselines.",
            "pass_condition": "No major annotation recovery loss versus default and no increase in batch alignment.",
            "priority": "P0",
            "evidence_path": _rel(REALDATA_ABLATION_SUMMARY),
        },
    ]


def build_markdown(
    component_rows: list[dict[str, object]], gap_rows: list[dict[str, object]]
) -> str:
    status_counts: dict[str, int] = {}
    for row in component_rows:
        status = str(row["current_evidence_status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    status_text = ", ".join(f"{key}={value}" for key, value in sorted(status_counts.items()))
    lines = [
        "# RMTGuard Component Ablation Evidence",
        "",
        "Generated by `python scripts/build_component_ablation_evidence.py`.",
        "",
        "## Bottom Line",
        "",
        "- This file is a component-level evidence control matrix, not a final ablation manuscript result.",
        "- A resumable draft component-ablation benchmark now exists for PC calibration, HVG rule, adaptive embedding, rare-state guard, no-call forcing, whitening, synthetic batch effects, and real-data annotation checks.",
        "- The strongest current evidence is realistic-null no-call control, rare-state guard on/off improvement, no-call forcing negative control, and biwhitening/batch draft protection against null or batch-driven false calls.",
        "- The highest-risk remaining experiments are manuscript-grade repeats, confidence intervals, real-data annotation checks, and Kang/real-data batch-residualization ablation.",
        f"- Component evidence status counts: `{status_text}`.",
        "",
        "## Component Evidence Matrix",
        "",
        "| Component | Status | Quantitative signal | Reviewer risk | Next required experiment |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in component_rows:
        lines.append(
            f"| {row['component_label']} | {row['current_evidence_status']} | {row['quantitative_signal']} | {row['reviewer_risk']} | {row['next_required_experiment']} |"
        )
    lines.extend(
        [
            "",
            "## Required Ablation Gap Matrix",
            "",
            "| Question | Importance | Current status | Priority | Minimum next run | Pass condition |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in gap_rows:
        lines.append(
            f"| {row['ablation_question']} | {row['manuscript_importance']} | {row['current_status']} | {row['priority']} | {row['minimum_next_run']} | {row['pass_condition']} |"
        )
    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            "- Direct evidence: rows are built from local TSV artifacts listed in `evidence_paths`.",
            "- Reasonable inference: missing experiments are prioritized by likely reviewer objections and the current failed stability-superiority gate.",
            "- Do not claim that full component ablation is complete until all P0 gap rows have generated final cross-dataset, confidence-interval-backed results.",
            "",
            "## Output Files",
            "",
            f"- Component evidence TSV: `{_rel(OUT_EVIDENCE)}`",
            f"- Gap matrix TSV: `{_rel(OUT_GAP)}`",
            f"- Draft ablation benchmark summary: `{_rel(COMPONENT_ABLATION_SUMMARY)}`",
            f"- Real-data annotation ablation summary: `{_rel(REALDATA_ABLATION_SUMMARY)}`",
            f"- Markdown report: `{_rel(OUT_MD)}`",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    component_rows = build_component_rows()
    gap_rows = build_gap_rows()
    _write_tsv(
        OUT_EVIDENCE,
        component_rows,
        [
            "component_id",
            "component_label",
            "current_evidence_status",
            "claim_role",
            "direct_evidence_summary",
            "quantitative_signal",
            "reviewer_risk",
            "manuscript_use",
            "next_required_experiment",
            "evidence_paths",
        ],
    )
    _write_tsv(
        OUT_GAP,
        gap_rows,
        [
            "ablation_question",
            "manuscript_importance",
            "current_status",
            "minimum_next_run",
            "pass_condition",
            "priority",
            "evidence_path",
        ],
    )
    _write_text(OUT_MD, build_markdown(component_rows, gap_rows))
    print(_rel(OUT_EVIDENCE))
    print(_rel(OUT_GAP))
    print(_rel(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
