from __future__ import annotations

"""Build editor-facing presubmission materials for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-01
Purpose: Produce evidence-bounded editor pitch, figure-claim checklist, and
reviewer-response playbook for the Nature Methods-first route.
Data source: Generated claim-evidence matrix, reviewer objection matrix,
storyline-panel map, top-paper route table, and public release blocker table.
Method notes: These outputs are controlled drafts. They do not assert journal
acceptance and must not be sent while release or scientific gates are blocked.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "submission"
MANUSCRIPT_DIR = ROOT / "manuscript"
DOCS_DIR = ROOT / "docs"

CLAIM_MATRIX = ROOT / "results" / "manuscript" / "claim_evidence_matrix.tsv"
OBJECTION_MATRIX = ROOT / "results" / "manuscript" / "reviewer_objection_matrix.tsv"
STORYLINE_PANEL_MAP = ROOT / "results" / "manuscript" / "storyline_panel_map.tsv"
TOP_ROUTE = OUT_DIR / "top_paper_route_decision.tsv"
PUBLIC_RELEASE_BLOCKERS = ROOT / "results" / "release" / "public_release_blockers.tsv"

PACKET_TSV = OUT_DIR / "editorial_presubmission_packet.tsv"
FIGURE_CHECKLIST_TSV = OUT_DIR / "figure_claim_checklist.tsv"
PACKET_MD = DOCS_DIR / "editorial_presubmission_packet.md"
INQUIRY_MD = MANUSCRIPT_DIR / "nature_methods_presubmission_inquiry.md"
RESPONSE_PLAYBOOK_MD = MANUSCRIPT_DIR / "reviewer_response_playbook.md"
FIGURE_CHECKLIST_MD = MANUSCRIPT_DIR / "figure_claim_checklist.md"


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


def _by_id(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    return {row.get(key, ""): row for row in rows if row.get(key)}


def _route(rows: list[dict[str, str]], route_id: str) -> dict[str, str]:
    for row in rows:
        if row.get("route_id") == route_id:
            return row
    return {}


def _release_blockers(rows: list[dict[str, str]]) -> list[str]:
    return [
        row.get("blocker_id", "")
        for row in rows
        if row.get("status", "").startswith("blocked") and row.get("blocker_id")
    ]


def build_packet_rows(
    claims: list[dict[str, str]],
    objections: list[dict[str, str]],
    route_rows: list[dict[str, str]],
    public_release_blockers: list[dict[str, str]],
) -> list[dict[str, str]]:
    claim_by_id = _by_id(claims, "claim_id")
    objection_by_id = _by_id(objections, "objection_id")
    nm_route = _route(route_rows, "nature_methods_first")
    gb_route = _route(route_rows, "genome_biology_fallback")
    blockers = _release_blockers(public_release_blockers)
    release_passed = not blockers
    return [
        {
            "item_id": "send_status",
            "target": "Nature Methods",
            "status": "do_not_send",
            "editor_facing_text": "The presubmission inquiry remains a controlled draft until the callability-aware scientific gate, Figure 4 author acknowledgement, and final go/no-go wording are resolved.",
            "evidence_path": _rel(TOP_ROUTE),
            "boundary": "Do not send while Nature Methods route remains gate-controlled.",
            "next_action": "Freeze final Nature Methods go/no-go wording and obtain corresponding-author acknowledgement for bounded Figure 4.",
        },
        {
            "item_id": "one_sentence_pitch",
            "target": "Nature Methods",
            "status": "draft_controlled",
            "editor_facing_text": "RMTGuard is a random-matrix noise-control framework that turns scRNA-seq embedding construction into an auditable call/no-call decision rather than a manually tuned PCA-and-clustering workflow.",
            "evidence_path": _rel(CLAIM_MATRIX),
            "boundary": "Pitch the random-matrix diagnostic contract, not automatic parameter tuning.",
            "next_action": "Use only if the callability-aware benchmark wording is preserved.",
        },
        {
            "item_id": "primary_positive_evidence",
            "target": "Nature Methods",
            "status": "usable_with_scope",
            "editor_facing_text": "The current evidence supports false-signal control in pure-null simulations, 3/3 diagnostic no-call validation scenarios, rare-state synthetic recovery (ARI 0.923), and four public real-data benchmarks.",
            "evidence_path": _rel(CLAIM_MATRIX),
            "boundary": "Do not convert positive synthetic and breadth evidence into broad fixed-PC superiority.",
            "next_action": "Keep Figure 2 and diagnostic no-call evidence prominent.",
        },
        {
            "item_id": "core_limitation_disclosure",
            "target": "Nature Methods",
            "status": "must_disclose",
            "editor_facing_text": claim_by_id.get("pbmc3k_stability", {}).get(
                "allowed_wording", ""
            ),
            "evidence_path": _rel(CLAIM_MATRIX),
            "boundary": claim_by_id.get("pbmc3k_stability", {}).get(
                "prohibited_wording", ""
            ),
            "next_action": objection_by_id.get("stability_advantage", {}).get(
                "response_strategy", ""
            ),
        },
        {
            "item_id": "software_release_disclosure",
            "target": "All journals",
            "status": "pass" if release_passed else "blocked",
            "editor_facing_text": (
                "Public repository, GitHub Release, and Zenodo DOI evidence are recorded for the archived v0.1.0 release."
                if release_passed
                else "Local release checks pass, but the public GitHub Release and Zenodo DOI are not complete."
            ),
            "evidence_path": _rel(PUBLIC_RELEASE_BLOCKERS),
            "boundary": "Do not imply that post-release working-branch changes are part of the immutable DOI snapshot.",
            "next_action": (
                "Keep v0.1.0 immutable; create a future version only after benchmark and metadata freeze."
                if release_passed
                else "Clear release blockers: " + ";".join(blockers)
            ),
        },
        {
            "item_id": "genome_biology_fallback_pitch",
            "target": "Genome Biology",
            "status": (
                "fallback_ready_after_scientific_reframe"
                if release_passed
                else gb_route.get("decision", "pending")
            ),
            "editor_facing_text": "RMTGuard can be reframed as an open, reproducible genomics workflow for callability-aware scRNA-seq noise control if Nature Methods editors judge the method advance too narrow.",
            "evidence_path": _rel(TOP_ROUTE),
            "boundary": "Do not describe Genome Biology as a strict 20-50 JIF route under current verified metrics.",
            "next_action": (
                "If Nature Methods presubmission is not encouraging, reframe immediately as a Genome Biology-style reproducible genomics workflow."
                if release_passed
                else gb_route.get("next_action", "")
            ),
        },
    ]


def build_figure_rows(
    storyline_rows: list[dict[str, str]], claims: list[dict[str, str]]
) -> list[dict[str, str]]:
    claim_by_id = _by_id(claims, "claim_id")
    rows: list[dict[str, str]] = []
    for row in storyline_rows:
        linked_claims = [
            item for item in row.get("linked_claim_ids", "").split(";") if item
        ]
        allowed = [
            claim_by_id.get(claim_id, {}).get("allowed_wording", "")
            for claim_id in linked_claims
        ]
        prohibited = [
            claim_by_id.get(claim_id, {}).get("prohibited_wording", "")
            for claim_id in linked_claims
        ]
        rows.append(
            {
                "figure": row.get("figure", ""),
                "status": row.get("status", ""),
                "allowed_caption_claim": " ".join(item for item in allowed if item),
                "prohibited_caption_claim": " ".join(
                    item for item in prohibited if item
                ),
                "must_show_caveat": row.get("caveat", ""),
                "source_artifact": row.get("source_artifact", ""),
                "editorial_use": row.get("manuscript_use", ""),
            }
        )
    return rows


def build_inquiry_markdown(packet_rows: list[dict[str, str]]) -> list[str]:
    by_item = _by_id(packet_rows, "item_id")
    return [
        "# Nature Methods Presubmission Inquiry Draft",
        "",
        "Status: do not send; internal author-review draft until Figure 4 author acknowledgement and final go/no-go wording are complete.",
        "Acceptance guarantee: `impossible`.",
        "",
        "Dear Editors,",
        "",
        'We are preparing a Methods Article entitled "RMTGuard: random-matrix noise control for reproducible single-cell cell-state discovery".',
        by_item["one_sentence_pitch"]["editor_facing_text"],
        "",
        "The manuscript's current evidence package supports three bounded claims.",
        by_item["primary_positive_evidence"]["editor_facing_text"],
        "",
        "We would present the real-data benchmark as callability-aware rather than as universal superiority over fixed-PC workflows.",
        "The current real-data benchmark does not show broad superiority over the strongest stability comparator on every dataset, and PBMC68k/Zheng 2017 is retained as a diagnostic no-call rather than a positive discovery.",
        "",
        "The biological application is a bounded public PDAC/TME use case supported by differential-marker, rank-based Hallmark/Reactome pathway, external-signature, and published-atlas-marker evidence; it is not presented as a standalone disease-mechanism or clinical-validation claim.",
        "",
        "The software-release evidence is recorded, but this inquiry remains an internal draft until the corresponding authors acknowledge the bounded Figure 4 route and the final Nature Methods go/no-go is completed.",
        by_item["software_release_disclosure"]["editor_facing_text"],
        "",
        "Sincerely,",
        "",
        "[Corresponding author]",
    ]


def build_playbook_markdown(objections: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Reviewer Response Playbook",
        "",
        "This file is generated by `python scripts/build_editorial_presubmission_packet.py`.",
        "Use it to draft responses without inventing new evidence.",
        "",
    ]
    for row in objections:
        lines.extend(
            [
                f"## {row.get('objection_id', '')}",
                "",
                f"- Risk level: `{row.get('risk_level', '')}`",
                f"- Current status: `{row.get('current_status', '')}`",
                f"- Likely concern: {row.get('likely_reviewer_concern', '')}",
                f"- Evidence: `{row.get('evidence', '')}`",
                f"- Response strategy: {row.get('response_strategy', '')}",
                f"- Required before submission: {row.get('required_before_submission', '')}",
                "",
                "Draft response:",
                "",
                f"We agree that this point requires explicit boundary control. In the current manuscript package, we address it by: {row.get('response_strategy', '')} The claim remains limited to the evidence listed above, and we do not use unsupported wording beyond the generated claim-evidence matrix.",
                "",
            ]
        )
    lines.extend(
        [
            "## Non-Negotiable Response Boundary",
            "",
            "Do not promise added experiments, DOI release, or stronger benchmark results unless those artifacts actually exist and the generated gate tables have been rerun.",
        ]
    )
    return lines


def build_figure_markdown(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Figure Claim Checklist",
        "",
        "This file is generated by `python scripts/build_editorial_presubmission_packet.py`.",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row.get('figure', '')}",
                "",
                f"- Status: `{row.get('status', '')}`",
                f"- Editorial use: {row.get('editorial_use', '')}",
                f"- Source artifact: `{row.get('source_artifact', '')}`",
                f"- Allowed caption claim: {row.get('allowed_caption_claim', '')}",
                f"- Prohibited caption claim: {row.get('prohibited_caption_claim', '')}",
                f"- Must-show caveat: {row.get('must_show_caveat', '')}",
                "",
            ]
        )
    return lines


def build_packet_markdown(packet_rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Editorial Presubmission Packet",
        "",
        "This file is generated by `python scripts/build_editorial_presubmission_packet.py`.",
        "",
        "Acceptance guarantee: `impossible`.",
        "This packet controls editor-facing language and does not replace the scientific gates.",
        "",
    ]
    for row in packet_rows:
        lines.extend(
            [
                f"## {row.get('item_id', '')}",
                "",
                f"- Target: `{row.get('target', '')}`",
                f"- Status: `{row.get('status', '')}`",
                f"- Evidence: `{row.get('evidence_path', '')}`",
                f"- Editor-facing text: {row.get('editor_facing_text', '')}",
                f"- Boundary: {row.get('boundary', '')}",
                f"- Next action: {row.get('next_action', '')}",
                "",
            ]
        )
    return lines


def main() -> int:
    claims = _read_tsv(CLAIM_MATRIX)
    objections = _read_tsv(OBJECTION_MATRIX)
    storyline_rows = _read_tsv(STORYLINE_PANEL_MAP)
    route_rows = _read_tsv(TOP_ROUTE)
    public_release_blockers = _read_tsv(PUBLIC_RELEASE_BLOCKERS)
    packet_rows = build_packet_rows(
        claims, objections, route_rows, public_release_blockers
    )
    figure_rows = build_figure_rows(storyline_rows, claims)
    _write_tsv(
        PACKET_TSV,
        packet_rows,
        [
            "item_id",
            "target",
            "status",
            "editor_facing_text",
            "evidence_path",
            "boundary",
            "next_action",
        ],
    )
    _write_tsv(
        FIGURE_CHECKLIST_TSV,
        figure_rows,
        [
            "figure",
            "status",
            "allowed_caption_claim",
            "prohibited_caption_claim",
            "must_show_caveat",
            "source_artifact",
            "editorial_use",
        ],
    )
    _write_text(PACKET_MD, build_packet_markdown(packet_rows))
    _write_text(INQUIRY_MD, build_inquiry_markdown(packet_rows))
    _write_text(RESPONSE_PLAYBOOK_MD, build_playbook_markdown(objections))
    _write_text(FIGURE_CHECKLIST_MD, build_figure_markdown(figure_rows))
    print(_rel(PACKET_TSV))
    print(_rel(FIGURE_CHECKLIST_TSV))
    print(_rel(PACKET_MD))
    print(_rel(INQUIRY_MD))
    print(_rel(RESPONSE_PLAYBOOK_MD))
    print(_rel(FIGURE_CHECKLIST_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
