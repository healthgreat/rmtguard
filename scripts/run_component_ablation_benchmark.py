#!/usr/bin/env python
"""Run draft component ablations for the RMTGuard methods package.

Author: RMTGuard development team
Date: 2026-05-02
Purpose: Generate a resumable, local P0/P1 component-ablation pilot covering
PC calibration, HVG rule, adaptive embedding, rare-state guard, no-call
forcing, and whitening choices.
Data source: Synthetic scRNA-seq-like count nulls and planted rare-state
matrices generated locally with fixed random seeds.
Method notes: Defaults are deliberately lightweight. Treat these outputs as a
draft failure-mode screen, not final manuscript-grade component ablation.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rmtguard import RMTGuard, RMTGuardConfig
from rmtguard.simulate import simulate_low_rank_counts
from scripts.run_realistic_null_power_calibration import (
    _best_rare_cluster_f1,
    _empirical_like_counts,
    _gene_permutation_null,
    _library_stratified_gene_null,
    _multinomial_library_null,
    _rare_state_counts,
)

OUT_DIR = ROOT / "results" / "ablation"
DETAIL = OUT_DIR / "component_ablation_detail.tsv"
SUMMARY = OUT_DIR / "component_ablation_summary.tsv"
DOC = ROOT / "docs" / "component_ablation_benchmark.md"


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


def _read_existing(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, sep="\t")


def _key(row: dict[str, Any]) -> tuple[str, str, str, str, int]:
    return (
        str(row["ablation_id"]),
        str(row["component_family"]),
        str(row["scenario"]),
        str(row["setting_id"]),
        int(row["repeat"]),
    )


def _planned_variants(args: argparse.Namespace) -> list[dict[str, Any]]:
    base = RMTGuardConfig(
        hvg_grid=tuple(args.hvg_grid),
        max_pcs=args.max_pcs,
        whiten="biwhiten",
        pc_rule="mp_tw",
        hvg_rule="spectral_stability",
        hvg_score="normalized_dispersion",
        embedding_rule="adaptive_near_edge",
        embedding_source="standard_pca",
        near_edge_window=1.25,
        embedding_stability_repeats=args.embedding_stability_repeats,
        embedding_stability_threshold=0.75,
        resolution_rule="graph_modularity",
        graph_resolution_grid=(1.0,),
        rare_state_guard="adaptive_binary_split",
        rare_state_min_fraction=0.015,
        rare_state_max_fraction=0.15,
        rare_state_min_cells=4,
        rare_state_min_separation=3.0,
        rare_state_min_silhouette=0.35,
        n_permutations=0,
        tw_alpha=0.01,
        random_state=args.random_state,
        cluster_grid=tuple(range(2, args.max_clusters + 1)),
    )
    variants = [
        {
            "ablation_id": "default_v3_3",
            "component_family": "reference",
            "variant_label": "default RMTGuard v3.3",
            "config": base,
        },
        {
            "ablation_id": "pc_rule_mp_only",
            "component_family": "pc_calibration",
            "variant_label": "MP edge only",
            "config": replace(base, pc_rule="mp"),
        },
        {
            "ablation_id": "pc_rule_mp_tw_permutation",
            "component_family": "pc_calibration",
            "variant_label": "MP + TW + permutation",
            "config": replace(
                base,
                pc_rule="mp_tw_permutation",
                n_permutations=args.n_permutations,
                tw_alpha=0.1,
            ),
        },
        {
            "ablation_id": "hvg_rule_dispersion",
            "component_family": "hvg_selection",
            "variant_label": "dispersion HVG",
            "config": replace(base, hvg_rule="dispersion"),
        },
        {
            "ablation_id": "hvg_rule_spectral_plateau",
            "component_family": "hvg_selection",
            "variant_label": "spectral plateau HVG",
            "config": replace(base, hvg_rule="spectral_plateau"),
        },
        {
            "ablation_id": "embedding_strict_signal",
            "component_family": "adaptive_embedding",
            "variant_label": "strict signal embedding",
            "config": replace(base, embedding_rule="strict_signal"),
        },
        {
            "ablation_id": "rare_state_guard_off",
            "component_family": "rare_state_guard",
            "variant_label": "rare-state guard off",
            "config": replace(base, rare_state_guard="off"),
        },
        {
            "ablation_id": "force_min_embedding_pcs_10",
            "component_family": "no_call_contract",
            "variant_label": "force minimum 10 embedding PCs",
            "config": replace(base, min_embedding_pcs=10),
        },
        {
            "ablation_id": "whiten_zscore",
            "component_family": "biwhitening",
            "variant_label": "z-score whitening",
            "config": replace(base, whiten="zscore"),
        },
        {
            "ablation_id": "batch_residualized",
            "component_family": "batch_residualization",
            "variant_label": "batch residualized fit",
            "config": base,
            "batch_only": True,
            "use_batches": True,
        },
    ]
    return variants


def _null_matrices(
    base_counts: np.ndarray, rng: np.random.Generator
) -> list[tuple[str, np.ndarray]]:
    return [
        ("library_multinomial_null", _multinomial_library_null(base_counts, rng)),
        ("gene_permutation_null", _gene_permutation_null(base_counts, rng)),
        (
            "library_stratified_gene_null",
            _library_stratified_gene_null(base_counts, rng),
        ),
    ]


def _fit_variant(
    counts: np.ndarray,
    config: RMTGuardConfig,
    seed: int,
    batches: np.ndarray | None = None,
) -> tuple[Any, dict[str, Any]]:
    result = RMTGuard(replace(config, random_state=seed)).fit(counts, batches=batches)
    embedding_diag = result.embedding_diagnostics
    metadata = {
        "analysis_status": result.analysis_status,
        "no_call_reason": result.no_call_reason,
        "n_signal_pcs": int(result.n_signal_pcs),
        "n_embedding_pcs": int(result.n_embedding_pcs),
        "cluster_n": int(result.cluster_n) if result.cluster_n is not None else 0,
        "selected_hvg_n": int(result.selected_hvg_n),
        "strict_signal_pcs": int(
            embedding_diag.get("strict_signal_pcs", result.n_signal_pcs)
        ),
        "accepted_embedding_pcs": int(
            embedding_diag.get("accepted_embedding_pcs", result.n_embedding_pcs)
        ),
        "near_edge_candidate_pcs": int(
            embedding_diag.get("near_edge_candidate_pcs", 0)
        ),
        "embedding_pc_stability_min": embedding_diag.get(
            "embedding_pc_stability_min", math.nan
        ),
        "embedding_pc_stability_median": embedding_diag.get(
            "embedding_pc_stability_median", math.nan
        ),
        "null_false_positive_rate": result.null_calibration[
            "null_false_positive_rate"
        ],
        "selected_edge": result.pc_diagnostics["selected_edge"],
        "mp_edge": result.pc_diagnostics["mp_edge"],
        "tw_edge": result.pc_diagnostics["tw_edge"],
        "runtime_seconds": result.benchmark_metadata["runtime_seconds"],
        "peak_memory_mb": result.benchmark_metadata["peak_memory_mb"],
        "batch_aware": result.benchmark_metadata["batch_aware"],
    }
    return result, metadata


def _config_columns(config: RMTGuardConfig) -> dict[str, Any]:
    config_dict = asdict(config)
    keep = [
        "whiten",
        "pc_rule",
        "hvg_rule",
        "embedding_rule",
        "rare_state_guard",
        "min_embedding_pcs",
        "n_permutations",
        "tw_alpha",
    ]
    return {f"config_{key}": config_dict[key] for key in keep}


def _append_row(rows: list[dict[str, Any]], row: dict[str, Any]) -> None:
    rows.append(row)
    _atomic_write_tsv(pd.DataFrame(rows), DETAIL)


def run_detail(args: argparse.Namespace) -> pd.DataFrame:
    variants = _planned_variants(args)
    existing_df = pd.DataFrame() if args.force else _read_existing(DETAIL)
    rows: list[dict[str, Any]] = (
        existing_df.to_dict(orient="records") if not existing_df.empty else []
    )
    completed = {_key(row) for row in rows} if rows else set()

    for repeat in range(args.n_repeats):
        rng = np.random.default_rng(args.random_state + repeat)
        base = _empirical_like_counts(args.n_cells, args.n_genes, rng)
        for setting_id, counts in _null_matrices(base, rng):
            for variant in variants:
                if variant.get("batch_only"):
                    continue
                plan_row = {
                    "ablation_id": variant["ablation_id"],
                    "component_family": variant["component_family"],
                    "scenario": "realistic_null",
                    "setting_id": setting_id,
                    "repeat": repeat,
                }
                if _key(plan_row) in completed:
                    continue
                seed = args.random_state + 1000 + repeat * 101 + len(rows)
                result, metrics = _fit_variant(counts, variant["config"], seed)
                false_signal = int(result.n_signal_pcs > args.false_signal_pc_floor)
                false_call = int(result.analysis_status != "diagnostic_no_call")
                row = {
                    **plan_row,
                    "variant_label": variant["variant_label"],
                    "n_cells": args.n_cells,
                    "n_genes": args.n_genes,
                    "false_signal": false_signal,
                    "false_call": false_call,
                    "ari": math.nan,
                    "nmi": math.nan,
                    "rare_f1": math.nan,
                    "rare_precision": math.nan,
                    "rare_recall": math.nan,
                    "power_pass": math.nan,
                    **_config_columns(variant["config"]),
                    **metrics,
                }
                _append_row(rows, row)
                completed.add(_key(row))

        for prevalence, effect_size in args.rare_settings:
            setting_id = f"prevalence_{prevalence:.3f}_effect_{effect_size:.2f}"
            counts, labels = _rare_state_counts(
                args.n_cells,
                args.n_genes,
                prevalence=prevalence,
                effect_size=effect_size,
                rng=rng,
            )
            for variant in variants:
                if variant.get("batch_only"):
                    continue
                plan_row = {
                    "ablation_id": variant["ablation_id"],
                    "component_family": variant["component_family"],
                    "scenario": "rare_state_power",
                    "setting_id": setting_id,
                    "repeat": repeat,
                }
                if _key(plan_row) in completed:
                    continue
                seed = args.random_state + 2000 + repeat * 101 + len(rows)
                result, metrics = _fit_variant(counts, variant["config"], seed)
                rare_metrics = _best_rare_cluster_f1(labels, result.cluster_labels)
                ari = float(adjusted_rand_score(labels, result.cluster_labels))
                nmi = float(normalized_mutual_info_score(labels, result.cluster_labels))
                power_pass = int(
                    ari >= args.rare_ari_floor
                    or rare_metrics["rare_f1"] >= args.rare_f1_floor
                )
                row = {
                    **plan_row,
                    "variant_label": variant["variant_label"],
                    "n_cells": args.n_cells,
                    "n_genes": args.n_genes,
                    "prevalence": prevalence,
                    "effect_size": effect_size,
                    "false_signal": math.nan,
                    "false_call": math.nan,
                    "ari": ari,
                    "nmi": nmi,
                    "power_pass": power_pass,
                    **rare_metrics,
                    **_config_columns(variant["config"]),
                    **metrics,
                }
                _append_row(rows, row)
                completed.add(_key(row))

        counts, labels, batches = simulate_low_rank_counts(
            n_cells=args.n_cells,
            n_genes=args.n_genes,
            n_states=args.batch_states,
            markers_per_state=args.batch_markers_per_state,
            batch_effect=True,
            dropout_rate=args.batch_dropout_rate,
            random_state=args.random_state + 30000 + repeat,
        )
        setting_id = "planted_states_with_batch_effect"
        for variant in variants:
            plan_row = {
                "ablation_id": variant["ablation_id"],
                "component_family": variant["component_family"],
                "scenario": "batch_effect",
                "setting_id": setting_id,
                "repeat": repeat,
            }
            if _key(plan_row) in completed:
                continue
            seed = args.random_state + 3000 + repeat * 101 + len(rows)
            fit_batches = batches if variant.get("use_batches") else None
            result, metrics = _fit_variant(
                counts,
                variant["config"],
                seed,
                batches=fit_batches,
            )
            label_ari = float(adjusted_rand_score(labels, result.cluster_labels))
            label_nmi = float(normalized_mutual_info_score(labels, result.cluster_labels))
            batch_ari = float(adjusted_rand_score(batches, result.cluster_labels))
            batch_nmi = float(normalized_mutual_info_score(batches, result.cluster_labels))
            row = {
                **plan_row,
                "variant_label": variant["variant_label"],
                "n_cells": args.n_cells,
                "n_genes": args.n_genes,
                "batch_states": args.batch_states,
                "batch_markers_per_state": args.batch_markers_per_state,
                "batch_dropout_rate": args.batch_dropout_rate,
                "false_signal": math.nan,
                "false_call": math.nan,
                "ari": label_ari,
                "nmi": label_nmi,
                "batch_ari": batch_ari,
                "batch_nmi": batch_nmi,
                "rare_f1": math.nan,
                "rare_precision": math.nan,
                "rare_recall": math.nan,
                "power_pass": math.nan,
                **_config_columns(variant["config"]),
                **metrics,
            }
            _append_row(rows, row)
            completed.add(_key(row))
    return pd.DataFrame(rows)


def summarize(detail: pd.DataFrame) -> pd.DataFrame:
    if detail.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for keys, group in detail.groupby(
        ["component_family", "ablation_id", "variant_label", "scenario"],
        dropna=False,
    ):
        component_family, ablation_id, variant_label, scenario = keys
        summary: dict[str, Any] = {
            "component_family": component_family,
            "ablation_id": ablation_id,
            "variant_label": variant_label,
            "scenario": scenario,
            "n_rows": int(len(group)),
            "n_repeats": int(group["repeat"].nunique()),
            "mean_signal_pcs": float(group["n_signal_pcs"].mean()),
            "mean_embedding_pcs": float(group["n_embedding_pcs"].mean()),
            "mean_cluster_n": float(group["cluster_n"].mean()),
            "mean_runtime_seconds": float(group["runtime_seconds"].mean()),
            "mean_batch_ari": (
                float(group["batch_ari"].mean())
                if "batch_ari" in group and group["batch_ari"].notna().any()
                else math.nan
            ),
            "mean_batch_nmi": (
                float(group["batch_nmi"].mean())
                if "batch_nmi" in group and group["batch_nmi"].notna().any()
                else math.nan
            ),
        }
        if scenario == "realistic_null":
            summary.update(
                {
                    "false_signal_rate": float(group["false_signal"].mean()),
                    "false_call_rate": float(group["false_call"].mean()),
                    "no_call_rate": float(
                        (group["analysis_status"] == "diagnostic_no_call").mean()
                    ),
                    "mean_ari": math.nan,
                    "mean_rare_f1": math.nan,
                    "power": math.nan,
                }
            )
        elif scenario == "rare_state_power":
            summary.update(
                {
                    "false_signal_rate": math.nan,
                    "false_call_rate": math.nan,
                    "no_call_rate": float(
                        (group["analysis_status"] == "diagnostic_no_call").mean()
                    ),
                    "mean_ari": float(group["ari"].mean()),
                    "mean_rare_f1": float(group["rare_f1"].mean()),
                    "power": float(group["power_pass"].mean()),
                }
            )
        elif scenario == "batch_effect":
            summary.update(
                {
                    "false_signal_rate": math.nan,
                    "false_call_rate": math.nan,
                    "no_call_rate": float(
                        (group["analysis_status"] == "diagnostic_no_call").mean()
                    ),
                    "mean_ari": float(group["ari"].mean()),
                    "mean_rare_f1": math.nan,
                    "power": math.nan,
                }
            )
        else:
            raise ValueError(f"Unknown ablation scenario: {scenario}")
        rows.append(summary)
    return pd.DataFrame(rows).sort_values(
        ["component_family", "scenario", "ablation_id"]
    )


def build_doc(summary: pd.DataFrame, args: argparse.Namespace) -> str:
    if summary.empty:
        status_line = "No component ablation rows were generated."
    else:
        null_rows = summary[summary["scenario"] == "realistic_null"]
        rare_rows = summary[summary["scenario"] == "rare_state_power"]
        batch_rows = summary[summary["scenario"] == "batch_effect"]
        max_false_call = (
            float(null_rows["false_call_rate"].max()) if not null_rows.empty else math.nan
        )
        min_power = float(rare_rows["power"].min()) if not rare_rows.empty else math.nan
        max_batch_ari = (
            float(batch_rows["mean_batch_ari"].max()) if not batch_rows.empty else math.nan
        )
        status_line = (
            f"Draft run contains {int(summary['n_rows'].sum())} detail rows; "
            f"maximum null false-call rate is {max_false_call:.3f}; "
            f"minimum rare-state power across variants is {min_power:.3f}; "
            f"maximum batch-alignment ARI across variants is {max_batch_ari:.3f}."
        )
    lines = [
        "# RMTGuard component ablation benchmark",
        "",
        "Generated by `python scripts/run_component_ablation_benchmark.py`.",
        "",
        "## Scope",
        "",
        f"- Cells per matrix: {args.n_cells}",
        f"- Genes per matrix: {args.n_genes}",
        f"- Repeats per setting: {args.n_repeats}",
        f"- Rare-state settings: {', '.join(f'{p:.3f}/{e:.2f}' for p, e in args.rare_settings)}",
        f"- Batch-effect scenario: {args.batch_states} states, {args.batch_markers_per_state} marker genes per state, dropout {args.batch_dropout_rate}",
        f"- Permutations for permutation-calibrated variant: {args.n_permutations}",
        "- Status: draft local screen; not final manuscript-grade ablation.",
        "",
        "## Bottom Line",
        "",
        f"- {status_line}",
        "- Use this output to prioritize final P0 ablations; do not use it as a final superiority claim.",
        "",
        "## Summary Table",
        "",
        "| Component | Variant | Scenario | Rows | False call | Power | Rare F1 | Label ARI | Batch ARI | Mean signal PCs | Runtime seconds |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary.itertuples(index=False):
        false_call = (
            "NA" if math.isnan(float(row.false_call_rate)) else f"{row.false_call_rate:.3f}"
        )
        power = "NA" if math.isnan(float(row.power)) else f"{row.power:.3f}"
        rare_f1 = "NA" if math.isnan(float(row.mean_rare_f1)) else f"{row.mean_rare_f1:.3f}"
        label_ari = "NA" if math.isnan(float(row.mean_ari)) else f"{row.mean_ari:.3f}"
        batch_ari = (
            "NA"
            if math.isnan(float(row.mean_batch_ari))
            else f"{row.mean_batch_ari:.3f}"
        )
        lines.append(
            f"| {row.component_family} | {row.variant_label} | {row.scenario} | {int(row.n_rows)} | {false_call} | {power} | {rare_f1} | {label_ari} | {batch_ari} | {row.mean_signal_pcs:.2f} | {row.mean_runtime_seconds:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            "- Direct evidence: synthetic count nulls, planted rare-state matrices, and planted-state batch-effect matrices generated during this run.",
            "- Current limitation: low repeat count and small matrices; final manuscript claims require 20-50 repeats, confidence intervals, and real-data/annotation checks.",
            "- Reviewer-facing use: this is now a reproducible ablation runner and draft screen, not the final Figure 5 ablation table.",
            "",
            "## Output Files",
            "",
            f"- Detail table: `{_rel(DETAIL)}`",
            f"- Summary table: `{_rel(SUMMARY)}`",
            f"- Report: `{_rel(DOC)}`",
        ]
    )
    return "\n".join(lines)


def _parse_rare_settings(values: list[str]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for value in values:
        if "/" not in value:
            raise argparse.ArgumentTypeError(
                "rare settings must use prevalence/effect syntax, e.g. 0.04/4.0"
            )
        prevalence, effect = value.split("/", 1)
        out.append((float(prevalence), float(effect)))
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-cells", type=int, default=180)
    parser.add_argument("--n-genes", type=int, default=360)
    parser.add_argument("--n-repeats", type=int, default=3)
    parser.add_argument("--hvg-grid", type=int, nargs="+", default=[120, 240, 360])
    parser.add_argument("--max-pcs", type=int, default=24)
    parser.add_argument("--max-clusters", type=int, default=8)
    parser.add_argument("--embedding-stability-repeats", type=int, default=2)
    parser.add_argument("--n-permutations", type=int, default=3)
    parser.add_argument("--false-signal-pc-floor", type=int, default=1)
    parser.add_argument("--rare-ari-floor", type=float, default=0.80)
    parser.add_argument("--rare-f1-floor", type=float, default=0.70)
    parser.add_argument("--batch-states", type=int, default=3)
    parser.add_argument("--batch-markers-per-state", type=int, default=12)
    parser.add_argument("--batch-dropout-rate", type=float, default=0.10)
    parser.add_argument(
        "--rare-setting",
        action="append",
        default=["0.02/6.0", "0.04/4.0"],
        help="Rare-state setting as prevalence/effect. Can be repeated.",
    )
    parser.add_argument("--random-state", type=int, default=20260502)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    args.rare_settings = _parse_rare_settings(args.rare_setting)
    return args


def main() -> int:
    args = parse_args()
    if args.force and DETAIL.exists():
        DETAIL.unlink()
    detail = run_detail(args)
    summary = summarize(detail)
    _atomic_write_tsv(summary, SUMMARY)
    _atomic_write_text(build_doc(summary, args), DOC)
    print(_rel(DETAIL))
    print(_rel(SUMMARY))
    print(_rel(DOC))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
