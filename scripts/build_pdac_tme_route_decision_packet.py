#!/usr/bin/env python
"""Build a PDAC/TME route decision packet for the RMTGuard manuscript.

Author: RMTGuard development team
Date: 2026-05-04
Purpose: Convert the current PDAC/TME showcase audit into an author-facing
decision packet without falsely marking an author decision as completed.
Data source: docs/pdac_tme_showcase_depth.md and
results/pdac_tme/pdac_showcase_depth_audit.tsv.
Method notes: This script only writes planning and decision-support artifacts.
It does not create metadata/pdac_tme_route_decision.tsv because that file must
come from an explicit author decision.
"""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPTH_AUDIT_TSV = ROOT / "results" / "pdac_tme" / "pdac_showcase_depth_audit.tsv"
OUT_TSV = ROOT / "results" / "submission" / "pdac_tme_route_decision_packet.tsv"
OUT_MD = ROOT / "docs" / "pdac_tme_route_decision_packet.md"
AUTHOR_TEMPLATE = ROOT / "metadata" / "pdac_tme_route_decision_template.tsv"


FIELDNAMES = [
    "route_id",
    "recommendation",
    "manuscript_role",
    "current_evidence",
    "required_new_evidence",
    "minimum_pass_criterion",
    "stop_condition",
    "manual_author_reply",
    "downstream_codex_action",
]


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _read_depth_audit() -> list[dict[str, str]]:
    if not DEPTH_AUDIT_TSV.exists():
        return []
    with DEPTH_AUDIT_TSV.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_tsv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
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


def build_rows(audit_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    current_evidence = "; ".join(
        f"{row.get('item_id')}: {row.get('status')} ({row.get('evidence')})"
        for row in audit_rows
    )
    if not current_evidence:
        current_evidence = "PDAC/TME depth audit not found; run build_pdac_showcase_depth_report.py first."

    return [
        {
            "route_id": "deepen_as_main_figure",
            "recommendation": "recommended_if_strict_Nature_Methods_remains_primary",
            "manuscript_role": "Main Figure 4 biological application, but not clinical mechanism discovery.",
            "current_evidence": current_evidence,
            "required_new_evidence": (
                "FDR-controlled differential expression; pathway/GSEA support; "
                "GSE263733 external signature validation; repeated-split stability; "
                "published PDAC atlas marker comparison; explicit no-clinical-claim boundary."
            ),
            "minimum_pass_criterion": (
                "At least one ductal/immune/myeloid state has stable clusters, coherent markers, "
                "FDR-controlled pathway support, and external validation without relying on private data."
            ),
            "stop_condition": (
                "Demote if evidence remains marker-smoke only, external validation stays modest, "
                "or no FDR-controlled state/pathway result survives."
            ),
            "manual_author_reply": "PDAC/TME route: deepen as main figure",
            "downstream_codex_action": (
                "Create and run a resumable PDAC/TME validation workflow for DE, GSEA, "
                "signature transfer, validation plots, and Figure 4 source data."
            ),
        },
        {
            "route_id": "demote_to_supplement",
            "recommendation": "recommended_if_prioritizing_fast_defensible_submission",
            "manuscript_role": "Supplementary public use case showing claim-bounded diagnostic behavior.",
            "current_evidence": current_evidence,
            "required_new_evidence": (
                "Short supplement table; no new disease claim; replacement application screen "
                "with stronger labels or orthogonal ground truth."
            ),
            "minimum_pass_criterion": (
                "PDAC/TME is presented as a bounded public showcase, while the main paper uses "
                "synthetic calibration, multi-dataset benchmarks, and callability/noise-control maps."
            ),
            "stop_condition": (
                "Stop using PDAC/TME in main text if it cannot add more than coarse marker structure."
            ),
            "manual_author_reply": "PDAC/TME route: demote to supplement",
            "downstream_codex_action": (
                "Move PDAC/TME to supplement and screen replacement applications with clearer "
                "annotation or perturbation ground truth."
            ),
        },
    ]


def build_template() -> list[dict[str, str]]:
    return [
        {
            "field": "selected_route",
            "value": "TO_CONFIRM: deepen_as_main_figure or demote_to_supplement",
            "notes": "Author-controlled. Do not auto-fill from Codex recommendation.",
        },
        {
            "field": "confirmed_by",
            "value": "TO_CONFIRM: Chongfa Chen / Yi Miao / Han Yan",
            "notes": "Name of author confirming the route.",
        },
        {
            "field": "confirmation_date",
            "value": "TO_CONFIRM: YYYY-MM-DD",
            "notes": "Date of explicit author decision.",
        },
        {
            "field": "allowed_claim_boundary",
            "value": "TO_CONFIRM: public-data, non-clinical, no disease-mechanism claim unless validated",
            "notes": "Keep this conservative unless authors approve deeper validation.",
        },
    ]


def build_markdown(rows: list[dict[str, str]]) -> str:
    deepen = rows[0]
    demote = rows[1]
    return f"""# PDAC/TME Route Decision Packet

Generated by `python scripts/build_pdac_tme_route_decision_packet.py`.

## Bottom Line

- Current author decision status: `waiting_author_decision`.
- Codex recommendation for the strict 20-50 JIF route: `{deepen['recommendation']}`.
- Conservative fallback recommendation: `{demote['recommendation']}`.
- This packet does not mark NM-G04 as complete; only an explicit author reply can do that.

## Why This Decision Matters

The current PDAC/TME evidence is useful but bounded. It supports coarse immune
and ductal-context marker structure in public data, with GSE263733 external
label support, but it does not yet support a new PDAC mechanism, clinical
translation claim, or standalone CAF-state discovery.

For a Nature Methods-facing manuscript, Figure 4 must show that the method
helps a real biological analysis in a reviewer-defensible way. If PDAC/TME
stays in the main figure, it needs formal validation. If it cannot be deepened,
it should move to supplement and the main application should be replaced by a
dataset with stronger ground truth.

## Option A: Deepen PDAC/TME As Main Figure

- Recommended when: strict Nature Methods route remains active.
- Manuscript role: {deepen['manuscript_role']}
- Required new evidence: {deepen['required_new_evidence']}
- Minimum pass criterion: {deepen['minimum_pass_criterion']}
- Stop condition: {deepen['stop_condition']}
- Exact author reply:

```text
{deepen['manual_author_reply']}
```

## Option B: Demote PDAC/TME To Supplement

- Recommended when: fast, defensible Genome Biology/Bioinformatics-style submission is prioritized.
- Manuscript role: {demote['manuscript_role']}
- Required new evidence: {demote['required_new_evidence']}
- Minimum pass criterion: {demote['minimum_pass_criterion']}
- Stop condition: {demote['stop_condition']}
- Exact author reply:

```text
{demote['manual_author_reply']}
```

## Manual Author Steps

1. Open the current PDAC depth audit:
   `{_rel(ROOT / 'docs' / 'pdac_tme_showcase_depth.md')}`.
2. Decide whether PDAC/TME should remain a main biological figure.
3. Reply in the chat with exactly one of the two lines above.
4. If choosing `deepen as main figure`, also confirm that only public datasets
   will be used unless a separate ethics/IRB route is approved.
5. If choosing `demote to supplement`, approve replacing Figure 4 with a
   stronger public application if one is found.

## Useful Links For Manual Review

- GSE154778 GEO page: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE154778
- GSE263733 GEO page: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE263733
- Nature Methods aims and scope: https://www.nature.com/nmeth/aims
- Nature Methods metrics: https://www.nature.com/nmeth/journal-impact
- Genome Biology aims and scope: https://link.springer.com/journal/13059/aims-and-scope

## Codex Next Action After Author Reply

- If Option A: build `scripts/run_pdac_tme_deep_validation.py` with checkpointed
  DE, GSEA, signature validation, repeated-split stability, and Figure 4 source
  data.
- If Option B: build `scripts/screen_replacement_biological_applications.py`
  and a supplementary PDAC/TME claim-bounded figure/table.

## Source Artifacts

- Route packet TSV: `{_rel(OUT_TSV)}`
- Author decision template: `{_rel(AUTHOR_TEMPLATE)}`
- Current PDAC/TME depth audit: `{_rel(ROOT / 'results' / 'pdac_tme' / 'pdac_showcase_depth_audit.tsv')}`
"""


def main() -> int:
    audit_rows = _read_depth_audit()
    rows = build_rows(audit_rows)
    _write_tsv(OUT_TSV, rows, FIELDNAMES)
    _write_tsv(AUTHOR_TEMPLATE, build_template(), ["field", "value", "notes"])
    _write_text(OUT_MD, build_markdown(rows))
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print(_rel(AUTHOR_TEMPLATE))
    print("author_decision_status\twaiting_author_decision")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
