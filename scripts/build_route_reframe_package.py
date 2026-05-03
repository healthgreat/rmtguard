from __future__ import annotations

"""Build the post-SuperGrok route reframe package for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-01
Purpose: Freeze Nature Methods-facing submission language and create a bounded
Genome Biology working frame after external pre-review identified active P0
blockers.
Data source: External-review triage, route gates, claim-evidence matrix,
release readiness, and scientific gate reports.
Method notes: This package changes manuscript routing and wording boundaries
only. It does not resolve public release, benchmark, novelty, or acceptance
blockers.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "submission"
DOCS_DIR = ROOT / "docs"
MANUSCRIPT_DIR = ROOT / "manuscript"

TRIAGE = OUT_DIR / "external_review_feedback_triage.tsv"
POST_FEEDBACK_ROUTE = OUT_DIR / "post_feedback_journal_route_gate.tsv"
CLAIM_MATRIX = ROOT / "results" / "manuscript" / "claim_evidence_matrix.tsv"
GATE_REPORT = ROOT / "results" / "gates" / "gate_report.tsv"
RELEASE_READINESS = ROOT / "results" / "release" / "release_readiness.tsv"

OUT_TSV = OUT_DIR / "route_reframe_decision.tsv"
OUT_MD = DOCS_DIR / "route_reframe_package.md"
GB_ABSTRACT = MANUSCRIPT_DIR / "genome_biology_reframed_abstract.md"
NM_HOLD = MANUSCRIPT_DIR / "nature_methods_hold_statement.md"

FIELDNAMES = [
    "item_id",
    "status",
    "evidence_path",
    "current_problem",
    "required_wording",
    "forbidden_wording",
    "next_action",
]


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


def _read_tsv_from_header(path: Path, required_field: str) -> list[dict[str, str]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines):
        if required_field in line.split("\t"):
            return list(csv.DictReader(lines[idx:], delimiter="\t"))
    return []


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _by(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    return {row.get(key, ""): row for row in rows}


def _active_p0_ids(triage_rows: list[dict[str, str]]) -> list[str]:
    return [
        row.get("feedback_id", "")
        for row in triage_rows
        if row.get("priority") == "P0" and row.get("status") == "open"
    ]


def _claim(claims: dict[str, dict[str, str]], claim_id: str, field: str) -> str:
    return claims.get(claim_id, {}).get(field, "")


def build_rows(
    triage_rows: list[dict[str, str]],
    route_rows: list[dict[str, str]],
    claim_rows: list[dict[str, str]],
    gate_rows: list[dict[str, str]],
    release_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    route = _by(route_rows, "decision_id")
    claims = _by(claim_rows, "claim_id")
    gates = _by(gate_rows, "gate_id")
    release = _by(release_rows, "check_id")
    active_p0 = _active_p0_ids(triage_rows)
    release_blocked = any(
        release.get(check, {}).get("status") != "pass"
        for check in ["repository_url", "github_remote", "zenodo_doi"]
    )
    stability_failed = gates.get("stability_advantage", {}).get("status") != "pass"

    rows = [
        {
            "item_id": "nature_methods_presubmission",
            "status": "frozen_no_go",
            "evidence_path": _rel(POST_FEEDBACK_ROUTE),
            "current_problem": "External pre-review and generated gates identify Nature Methods as no-go while public release, stability, and novelty blockers remain active.",
            "required_wording": "Nature Methods is held; use only as a future stretch route if P0/P1 evidence changes.",
            "forbidden_wording": "Do not send presubmission inquiry or describe the package as Nature Methods-ready.",
            "next_action": "Keep Nature Methods materials archived as internal scaffolding, not editor-facing text.",
        },
        {
            "item_id": "genome_biology_working_route",
            "status": "conditional_after_release",
            "evidence_path": _rel(POST_FEEDBACK_ROUTE),
            "current_problem": "Genome Biology is the realistic route only after public release and reframe; active P0/P1 feedback still blocks submission.",
            "required_wording": "RMTGuard is a callability-aware reproducible genomics workflow with explicit no-call diagnostics.",
            "forbidden_wording": "Do not claim Genome Biology acceptance, strict IF20-50 guarantee, or universal clustering superiority.",
            "next_action": "Use the reframed abstract and cover letter only after GitHub/Zenodo release and gate regeneration.",
        },
        {
            "item_id": "central_claim",
            "status": "downgraded",
            "evidence_path": _rel(CLAIM_MATRIX),
            "current_problem": "The old subjective-parameter-reduction claim is too broad because RMTGuard still has configurable thresholds and stability settings.",
            "required_wording": "RMTGuard exposes random-matrix signal admission and diagnostic no-call boundaries for scRNA-seq workflows.",
            "forbidden_wording": "Do not claim the method removes subjective choices or automatically optimizes all scRNA-seq parameters.",
            "next_action": "Use callability/no-call language in abstract, cover letter, and Figure 3 captions.",
        },
        {
            "item_id": "stability_claim",
            "status": "failed_disclosed",
            "evidence_path": _rel(GATE_REPORT),
            "current_problem": _claim(claims, "pbmc3k_stability", "allowed_wording"),
            "required_wording": "Stability benchmarks reveal callability trade-offs and failed superiority versus the strongest elbow baseline on several datasets.",
            "forbidden_wording": _claim(claims, "pbmc3k_stability", "prohibited_wording"),
            "next_action": "Do not upgrade stability language until manuscript-grade benchmark reruns change the evidence.",
        },
        {
            "item_id": "software_release_claim",
            "status": "blocked_external" if release_blocked else "pass",
            "evidence_path": _rel(RELEASE_READINESS),
            "current_problem": "External public-release identifiers remain incomplete.",
            "required_wording": _claim(claims, "software_release", "allowed_wording"),
            "forbidden_wording": _claim(claims, "software_release", "prohibited_wording"),
            "next_action": "Complete external public-release evidence before any submission.",
        },
        {
            "item_id": "pdac_tme_showcase",
            "status": "bounded_or_supplementary",
            "evidence_path": _rel(CLAIM_MATRIX),
            "current_problem": "Current PDAC/TME evidence is marker-smoke/public-use-case depth, not a standalone cancer mechanism discovery.",
            "required_wording": _claim(claims, "pdac_tme_showcase", "allowed_wording"),
            "forbidden_wording": _claim(claims, "pdac_tme_showcase", "prohibited_wording"),
            "next_action": "Deepen with DE/pathway/trajectory validation or demote to supplementary.",
        },
    ]

    local_reframe_complete = (
        route.get("overall_post_feedback_route", {}).get("decision")
        == "pause_for_p0_feedback"
        and rows[0]["status"] == "frozen_no_go"
        and rows[1]["status"] == "conditional_after_release"
        and rows[2]["status"] == "downgraded"
    )
    rows.append(
        {
            "item_id": "overall_route_reframe",
            "status": (
                "local_reframe_complete"
                if local_reframe_complete
                else "incomplete"
            ),
            "evidence_path": _rel(OUT_TSV),
            "current_problem": ";".join(active_p0) or "none",
            "required_wording": "Nature Methods held; Genome Biology conditional after release; callability-aware diagnostic workflow.",
            "forbidden_wording": "Do not claim submission-ready status, public DOI release, or broad stability superiority.",
            "next_action": (
                "Clear public release and benchmark/statistical P1 actions before route upgrade."
                if stability_failed or release_blocked or active_p0
                else "Rerun route gates for candidate status."
            ),
        }
    )
    return rows


def build_markdown(rows: list[dict[str, str]]) -> list[str]:
    overall = next((row for row in rows if row["item_id"] == "overall_route_reframe"), {})
    lines = [
        "# Route Reframe Package",
        "",
        "This file is generated by `python scripts/build_route_reframe_package.py`.",
        "",
        "Acceptance guarantee: `impossible`.",
        "This package implements the external pre-review route correction: Nature Methods is held, while Genome Biology becomes a conditional reproducible-workflow route after public release and evidence reframe.",
        "",
        "## Overall Reframe",
        "",
        f"- Status: `{overall.get('status', 'missing')}`",
        f"- Active P0 feedback: `{overall.get('current_problem', 'missing')}`",
        f"- Required wording: {overall.get('required_wording', 'missing')}",
        f"- Forbidden wording: {overall.get('forbidden_wording', 'missing')}",
        f"- Next action: {overall.get('next_action', 'missing')}",
        "",
        "## Decision Rows",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"### {row['item_id']}",
                "",
                f"- Status: `{row['status']}`",
                f"- Evidence: `{row['evidence_path']}`",
                f"- Current problem: {row['current_problem']}",
                f"- Required wording: {row['required_wording']}",
                f"- Forbidden wording: {row['forbidden_wording']}",
                f"- Next action: {row['next_action']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Route Rule",
            "",
            "Use Nature Methods documents only as internal scaffolding while this package is active.",
            "Use Genome Biology-facing wording only after public release evidence exists and the external review action plan no longer has unresolved P0 blockers.",
        ]
    )
    return lines


def build_genome_biology_abstract(rows: list[dict[str, str]]) -> list[str]:
    return [
        "# Genome Biology Reframed Abstract",
        "",
        "Status: working draft; do not submit until public GitHub and Zenodo release gates pass.",
        "",
        "Single-cell RNA-seq cell-state discovery depends on analyst choices about feature selection, dimensionality, neighborhood graphs and clustering resolution. Rather than claiming to remove these choices, RMTGuard exposes one specific source of uncertainty: whether principal components and downstream graph structure exceed a random-matrix noise boundary sufficiently to support a cell-state call.",
        "",
        "RMTGuard implements a callability-aware workflow that combines random-matrix spectral diagnostics, strict signal-PC admission, near-edge embedding diagnostics, stability summaries and explicit no-call reporting for low-confidence matrices. The software exports AnnData-compatible embeddings and audit tables for feature, PC and clustering decisions so that analysts can distinguish callable structure from noise-controlled no-calls.",
        "",
        "Current synthetic benchmarks support pure-null false-signal control and planted rare-state retention, while public real-data benchmarks show useful annotation recovery but do not support broad stability superiority over the strongest baseline on all datasets. The PBMC68k/Zheng 2017 stress case is therefore reported as a diagnostic no-call rather than a positive discovery. A PDAC/TME public-data showcase is retained as a bounded use case, not a standalone cancer-mechanism claim.",
        "",
        "These results position RMTGuard as an evidence-bounded genomics workflow for transparent scRNA-seq callability diagnostics. External public-release placeholders must be replaced before any submission.",
    ]


def build_nature_methods_hold(rows: list[dict[str, str]]) -> list[str]:
    overall = next((row for row in rows if row["item_id"] == "overall_route_reframe"), {})
    return [
        "# Nature Methods Hold Statement",
        "",
        "Status: hold / no-go in the current evidence state.",
        "",
        "Nature Methods presubmission should not be sent while the active P0 blockers remain unresolved. The current package lacks public GitHub/Zenodo release evidence, fails the strict real-data stability advantage gate, and has an external-review novelty objection that cannot be answered by wording alone.",
        "",
        f"Current route reframe status: `{overall.get('status', 'missing')}`.",
        "",
        "The Nature Methods materials may remain useful as internal scaffolding for figure planning and methods rigor, but they must not be used as editor-facing text until new benchmark evidence, stronger novelty framing, and public release artifacts exist.",
    ]


def main() -> int:
    rows = build_rows(
        _read_tsv(TRIAGE),
        _read_tsv(POST_FEEDBACK_ROUTE),
        _read_tsv(CLAIM_MATRIX),
        _read_tsv_from_header(GATE_REPORT, "gate_id"),
        _read_tsv(RELEASE_READINESS),
    )
    _write_tsv(OUT_TSV, rows)
    _write_text(OUT_MD, build_markdown(rows))
    _write_text(GB_ABSTRACT, build_genome_biology_abstract(rows))
    _write_text(NM_HOLD, build_nature_methods_hold(rows))
    overall = next(row for row in rows if row["item_id"] == "overall_route_reframe")
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print(_rel(GB_ABSTRACT))
    print(_rel(NM_HOLD))
    print(f"overall\t{overall['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
