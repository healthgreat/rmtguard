from __future__ import annotations

"""Build guarded manuscript draft artifacts for the RMTGuard submission route.

Author: RMTGuard development team
Date: 2026-04-29
Purpose: Convert the generated claim-evidence matrix into draft manuscript
text, a presubmission cover-letter draft, reviewer-risk tables, and a panel map.
Data source: Local benchmark outputs summarized by
scripts/build_manuscript_evidence_package.py.
Method notes: This script preserves random-matrix-noise-control claims as
bounded manuscript language. It does not create a submission-ready manuscript.
"""

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
OUT_DIR = ROOT / "results" / "manuscript"

CLAIM_MATRIX = OUT_DIR / "claim_evidence_matrix.tsv"
CHECKLIST = OUT_DIR / "nature_methods_submission_checklist.tsv"
GATE_REPORT = ROOT / "results" / "gates" / "gate_report.tsv"

PRESUBMISSION_DRAFT = MANUSCRIPT_DIR / "nature_methods_presubmission_draft.md"
ABSTRACT_DRAFT = MANUSCRIPT_DIR / "abstract_draft.md"
COVER_LETTER_DRAFT = MANUSCRIPT_DIR / "cover_letter_draft.md"
OBJECTION_MATRIX = OUT_DIR / "reviewer_objection_matrix.tsv"
STORYLINE_PANEL_MAP = OUT_DIR / "storyline_panel_map.tsv"
DRAFT_MANIFEST = OUT_DIR / "manuscript_draft_package_manifest.tsv"


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


def _claim_rows() -> list[dict[str, str]]:
    rows = _read_tsv(CLAIM_MATRIX)
    if not rows:
        raise FileNotFoundError(
            f"Missing claim-evidence matrix: {_rel(CLAIM_MATRIX)}. "
            "Run python scripts/build_manuscript_evidence_package.py first."
        )
    return rows


def _checklist_rows() -> list[dict[str, str]]:
    return _read_tsv(CHECKLIST)


def _recommendation() -> str:
    rows = _read_tsv(GATE_REPORT)
    for row in rows:
        if row.get("gate_id") == "recommendation":
            return row.get("status", "unknown")
    if GATE_REPORT.exists():
        for line in GATE_REPORT.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("recommendation\t"):
                return line.split("\t", 1)[1]
    return "unknown"


def _by_claim(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["claim_id"]: row for row in rows}


def _claim_line(row: dict[str, str]) -> str:
    return f"- `{row['claim_id']}` ({row['status']}): {row['allowed_wording']}"


def build_storyline_panel_map(claims: list[dict[str, str]]) -> list[dict[str, str]]:
    claim_map = _by_claim(claims)

    def status(*claim_ids: str) -> str:
        statuses = [claim_map[claim_id]["status"] for claim_id in claim_ids if claim_id in claim_map]
        if any(item in {"fail", "blocked"} for item in statuses):
            return "blocked"
        if any(item == "pending" for item in statuses):
            return "pending"
        if any(item == "borderline" for item in statuses):
            return "borderline"
        if statuses and all(item == "pass" for item in statuses):
            return "pass"
        return "missing"

    rows = [
        {
            "figure": "Figure 1",
            "panel": "Algorithm overview and spectrum diagnostics",
            "storyline_role": "Define RMTGuard as a random-matrix noise-control framework, not an automatic tuning wrapper.",
            "source_artifact": "results/figures/source_data/figure1_algorithm_diagnostics.tsv",
            "linked_claim_ids": "noise_control_null;software_release",
            "status": status("noise_control_null", "software_release"),
            "manuscript_use": "Use as method overview with explicit diagnostic outputs.",
            "caveat": "Do not imply DOI-backed release until software_release is pass.",
        },
        {
            "figure": "Figure 2",
            "panel": "Synthetic null, rare state, batch, dropout, and overclustering stress tests",
            "storyline_role": "Show false-signal suppression while retaining planted low-rank or rare-state signal.",
            "source_artifact": "results/figures/source_data/figure2_synthetic_benchmark_summary.csv",
            "linked_claim_ids": "noise_control_null;rare_state_retention",
            "status": status("noise_control_null", "rare_state_retention"),
            "manuscript_use": "Use as the strongest current positive method evidence.",
            "caveat": "State synthetic assumptions and do not claim universal type-I calibration.",
        },
        {
            "figure": "Figure 3",
            "panel": "Public benchmark against Scanpy-like and fixed-PC baselines",
            "storyline_role": "Benchmark callability-aware reproducibility, diagnostic no-call behavior, and annotation recovery across PBMC, pancreas, and perturbation data.",
            "source_artifact": "results/figures/source_data/figure3_public_benchmark_summary.tsv",
            "linked_claim_ids": "public_benchmark_breadth;pbmc3k_stability;annotation_noninferiority",
            "status": status("public_benchmark_breadth", "pbmc3k_stability", "annotation_noninferiority"),
            "manuscript_use": "Use as callability-aware benchmark evidence, not as broad superiority over fixed-PC workflows.",
            "caveat": "Fixed n_pcs=30 remains slightly higher than RMTGuard on PBMC3k stability, and PBMC68k is a diagnostic no-call rather than a positive discovery.",
        },
        {
            "figure": "Figure 4",
            "panel": "PDAC/TME GSE154778 showcase and GSE263733 validation",
            "storyline_role": "Demonstrate a public biological use case with immune and ductal-context marker structure.",
            "source_artifact": "results/figures/source_data/figure4_pdac_tme_showcase_summary.tsv",
            "linked_claim_ids": "pdac_tme_showcase",
            "status": status("pdac_tme_showcase"),
            "manuscript_use": "Use as public application evidence.",
            "caveat": "Do not claim standalone CAF/fibroblast discovery from the current smoke run.",
        },
        {
            "figure": "Figure 5",
            "panel": "Runtime, ablation, reproducibility, and release audit",
            "storyline_role": "Document computational feasibility and release completeness.",
            "source_artifact": "results/figures/source_data/figure5_runtime_memory_summary.tsv",
            "linked_claim_ids": "figure_source_data;software_release",
            "status": status("figure_source_data", "software_release"),
            "manuscript_use": "Use as a readiness dashboard until external release exists.",
            "caveat": "Software release is pending until GitHub Release and Zenodo DOI are real.",
        },
    ]
    return rows


def build_reviewer_objection_matrix(claims: list[dict[str, str]]) -> list[dict[str, str]]:
    claim_map = _by_claim(claims)

    def evidence(claim_id: str) -> str:
        row = claim_map.get(claim_id, {})
        return row.get("evidence", "")

    def status(claim_id: str) -> str:
        row = claim_map.get(claim_id, {})
        return row.get("status", "missing")

    rows = [
        {
            "objection_id": "stability_advantage",
            "likely_reviewer_concern": "The stability claim may be overstated because PBMC68k is below floor and PBMC3k/Baron do not clearly beat fixed-PC baselines.",
            "risk_level": "high",
            "linked_gate_or_claim": "pbmc3k_stability",
            "current_status": status("pbmc3k_stability"),
            "evidence": evidence("pbmc3k_stability"),
            "response_strategy": "Frame PBMC68k as a pre-specified diagnostic no-call and keep the benchmark claim callability-aware rather than broad superiority.",
            "required_before_submission": "Add final wording and reviewer response that separates positive cell-state discovery from diagnostic_no_call outputs.",
        },
        {
            "objection_id": "software_release",
            "likely_reviewer_concern": "The manuscript cannot be reviewed as reusable software without public release and DOI.",
            "risk_level": "blocking",
            "linked_gate_or_claim": "software_release",
            "current_status": status("software_release"),
            "evidence": evidence("software_release"),
            "response_strategy": "Complete GitHub repository, tagged release, GitHub Release, and Zenodo DOI before submission.",
            "required_before_submission": "Replace placeholder URLs, stage/commit approved files, create release tag, archive with Zenodo.",
        },
        {
            "objection_id": "method_novelty",
            "likely_reviewer_concern": "This may look like automatic parameter tuning around existing PCA and clustering.",
            "risk_level": "high",
            "linked_gate_or_claim": "noise_control_null",
            "current_status": status("noise_control_null"),
            "evidence": evidence("noise_control_null"),
            "response_strategy": "Center the paper on random-matrix null control, diagnostic contracts, and false-signal suppression.",
            "required_before_submission": "Strengthen ablation showing each RMT component changes decisions and reduces false discoveries.",
        },
        {
            "objection_id": "null_calibration_scope",
            "likely_reviewer_concern": "The MP/TW edge may not calibrate false positives under realistic scRNA-seq preprocessing.",
            "risk_level": "medium",
            "linked_gate_or_claim": "noise_control_null",
            "current_status": status("noise_control_null"),
            "evidence": evidence("noise_control_null"),
            "response_strategy": "State assumptions, include permutation calibration, and avoid exact type-I claims beyond tested settings.",
            "required_before_submission": "Run final permutation calibration and report false-positive rate by scenario.",
        },
        {
            "objection_id": "rare_state_loss",
            "likely_reviewer_concern": "Noise control could remove weak rare-cell-state structure.",
            "risk_level": "medium",
            "linked_gate_or_claim": "rare_state_retention",
            "current_status": status("rare_state_retention"),
            "evidence": evidence("rare_state_retention"),
            "response_strategy": "Use rare-state synthetic ARI as current support and add real rare-state sensitivity if feasible.",
            "required_before_submission": "Add rare-state sensitivity across prevalence and effect-size grids.",
        },
        {
            "objection_id": "benchmark_baselines",
            "likely_reviewer_concern": "Scanpy-like and fixed-PC baselines are not enough for a methods manuscript.",
            "risk_level": "medium",
            "linked_gate_or_claim": "public_benchmark_breadth",
            "current_status": status("public_benchmark_breadth"),
            "evidence": evidence("public_benchmark_breadth"),
            "response_strategy": "Keep current benchmark as Phase 1 and add Seurat, elbow, permutation PCA, and JackStraw-like baselines.",
            "required_before_submission": "Complete the planned baseline table or explicitly move to Genome Biology fallback.",
        },
        {
            "objection_id": "pbmc68k_label_quality",
            "likely_reviewer_concern": "PBMC68k has weak absolute ARI and may not support annotation-recovery claims.",
            "risk_level": "medium",
            "linked_gate_or_claim": "annotation_noninferiority",
            "current_status": status("annotation_noninferiority"),
            "evidence": evidence("annotation_noninferiority"),
            "response_strategy": "Frame PBMC68k as label-granularity stress evidence and rely on Kang and Baron for stronger annotation recovery.",
            "required_before_submission": "Add label-hierarchy sensitivity or remove PBMC68k from strong positive examples.",
        },
        {
            "objection_id": "pdac_biology_depth",
            "likely_reviewer_concern": "The PDAC/TME showcase may be too marker-smoke level for a top methods paper.",
            "risk_level": "medium",
            "linked_gate_or_claim": "pdac_tme_showcase",
            "current_status": status("pdac_tme_showcase"),
            "evidence": evidence("pdac_tme_showcase"),
            "response_strategy": "Use PDAC/TME as public workflow validation, not as disease-mechanism proof.",
            "required_before_submission": "Add pathway, marker, and external-validation tables for one stable immune or ductal-context state.",
        },
    ]
    return rows


def build_presubmission_draft(claims: list[dict[str, str]], checklist: list[dict[str, str]]) -> list[str]:
    pass_claims = [row for row in claims if row["status"] == "pass"]
    caution_claims = [row for row in claims if row["status"] != "pass"]
    blockers = [row for row in checklist if row.get("status") in {"pending", "borderline", "blocked", "fail"}]

    lines = [
        "# Nature Methods Presubmission Draft",
        "",
        "Status: not submission-ready. This draft is generated from local benchmark evidence and must not be submitted until the software-release blockers are resolved.",
        "",
        "## Working Title",
        "",
        "RMTGuard: random-matrix noise control for reproducible single-cell cell-state discovery",
        "",
        "## Current Decision",
        "",
        f"- Gate recommendation: `{_recommendation()}`",
        "- Nature Methods route: `not ready`",
        "- Genome Biology fallback: `not ready until software_release is complete`",
        "",
        "## Central Claim",
        "",
        "Random-matrix noise control can reduce subjective parameter choices in scRNA-seq cell-state discovery while preserving interpretable biological structure.",
        "",
        "This claim is currently supported only within the benchmark scope listed below. It should be written as callability-aware noise control, not broad superiority over every fixed-PC workflow.",
        "",
        "## Evidence That Can Be Used",
        "",
    ]
    lines.extend(_claim_line(row) for row in pass_claims)
    lines.extend(
        [
            "",
            "## Claims That Must Stay Guarded",
            "",
        ]
    )
    lines.extend(f"- `{row['claim_id']}` ({row['status']}): {row['prohibited_wording']}" for row in caution_claims)
    lines.extend(["", "## Blocking Items", ""])
    lines.extend(f"- `{row['item']}` ({row['status']}): {row['next_action']}" for row in blockers)
    lines.extend(
        [
            "",
            "## Draft Results Narrative",
            "",
            "### 1. RMTGuard defines a noise-control contract for scRNA-seq embeddings",
            "",
            "The method estimates a random-matrix null spectrum after preprocessing and uses the MP edge, finite-sample edge checks, permutation calibration where enabled, HVG spectral plateau diagnostics, and near-edge PC stability to decide which structure is allowed into downstream embedding and graph construction.",
            "",
            "### 2. Synthetic stress tests support false-signal control and rare-state retention",
            "",
            "The current synthetic benchmark passes the pure-null false-signal criterion and retains the planted rare-state signal. The text should state the simulated assumptions and avoid claiming exact calibration outside the tested settings.",
            "",
            "### 3. Public benchmarks support a callability-aware stability/no-call claim",
            "",
            "Four public real datasets are present in Phase 1. RMTGuard exceeds all non-RMTGuard baselines on Kang IFN-beta PBMC, is close to fixed `n_pcs=30` on Baron pancreas and PBMC3k, and returns diagnostic no-call on PBMC68k/Zheng 2017 where the strongest stable comparator also has weak annotation recovery. This should be presented as callability-aware noise control, not as a claim that RMTGuard beats fixed-PC baselines on every dataset.",
            "",
            "### 4. PDAC/TME is a public biological use case, not a disease-mechanism claim",
            "",
            "GSE154778 and GSE263733 currently support immune and ductal-context marker structure with external validation. The manuscript must not describe this as a standalone CAF or fibroblast-state discovery without stronger evidence.",
            "",
            "### 5. Software release is the remaining hard external blocker",
            "",
            "Local release manifests, checksums, staging plans, and figure source data exist. A local release tag exists, but the software-release gate remains pending until a real GitHub repository, GitHub Release, and Zenodo DOI exist.",
            "",
            "## Manuscript Decision Boundary",
            "",
            "Use this draft for internal manuscript assembly only. Nature Methods submission should wait until `software_release` is pass and the final text preserves the callability-aware stability/no-call boundary. If reviewers reject the no-call framing as insufficient methodological advance, reframe to Genome Biology or lower.",
        ]
    )
    return lines


def build_abstract_draft(claims: list[dict[str, str]]) -> list[str]:
    claim_map = _by_claim(claims)
    null_claim = claim_map.get("noise_control_null", {}).get("allowed_wording", "")
    rare_claim = claim_map.get("rare_state_retention", {}).get("allowed_wording", "")
    stability_claim = claim_map.get("pbmc3k_stability", {}).get("allowed_wording", "")
    pdac_claim = claim_map.get("pdac_tme_showcase", {}).get("allowed_wording", "")
    return [
        "# Abstract Draft",
        "",
        "Status: not submission-ready. This is a guarded working abstract, not a final Nature Methods abstract.",
        "",
        "Single-cell RNA-seq cell-state discovery often depends on user-selected highly variable genes, principal components, graph neighborhoods, and clustering resolution. RMTGuard addresses this problem by adding a random-matrix noise-control layer to the standard analysis workflow. The method estimates spectral noise boundaries, separates strict signal PCs from stable near-edge embedding PCs, and records diagnostic outputs for HVG selection, PC admission, graph construction, and clustering.",
        "",
        f"In the current benchmark snapshot, {null_claim} {rare_claim} Public benchmarks cover PBMC, perturbation, pancreas, and large immune data, but the stability gate remains blocked: {stability_claim} The PDAC/TME showcase currently supports a public immune and ductal-context use case: {pdac_claim}",
        "",
        "These results support continued development of RMTGuard as a reproducible genomics-methods workflow. They do not yet support a submission-ready claim of broad superiority over fixed-PC baselines, and the software-release DOI is still pending.",
    ]


def build_cover_letter_draft(claims: list[dict[str, str]]) -> list[str]:
    claim_map = _by_claim(claims)
    return [
        "# Cover Letter Draft",
        "",
        "Status: not submission-ready. Do not send this letter until `stability_advantage` and `software_release` are resolved.",
        "",
        "Dear Editors,",
        "",
        "We are preparing a Methods Article entitled \"RMTGuard: random-matrix noise control for reproducible single-cell cell-state discovery\". The manuscript presents a random-matrix-guided framework for reducing subjective choices in scRNA-seq cell-state analysis, including HVG selection, PC admission, graph construction, and clustering diagnostics.",
        "",
        "The current evidence package supports the method's null-control and rare-state synthetic benchmarks, four public real-data benchmarks, and a PDAC/TME public showcase focused on immune and ductal-context marker structure. The software package includes a Scanpy/AnnData interface, benchmark runners, figure source-data generation, release manifests, CI tests, and draft reproducibility artifacts.",
        "",
        f"The strongest current synthetic claims are: {claim_map.get('noise_control_null', {}).get('allowed_wording', '')} {claim_map.get('rare_state_retention', {}).get('allowed_wording', '')}",
        "",
        "Before this letter can be used for submission, the public GitHub Release and Zenodo DOI must be completed. The benchmark language must also remain callability-aware: PBMC68k is a diagnostic no-call and PBMC3k remains slightly below fixed `n_pcs=30`, so the manuscript should not claim broad superiority over fixed-PC baselines.",
        "",
        "Sincerely,",
        "",
        "[Corresponding author]",
    ]


def build_manifest() -> list[dict[str, str]]:
    outputs = [
        (PRESUBMISSION_DRAFT, "markdown_draft", "not_submission_ready"),
        (ABSTRACT_DRAFT, "markdown_draft", "not_submission_ready"),
        (COVER_LETTER_DRAFT, "markdown_draft", "not_submission_ready"),
        (OBJECTION_MATRIX, "risk_table", "active"),
        (STORYLINE_PANEL_MAP, "storyline_table", "active"),
        (DRAFT_MANIFEST, "manifest", "active"),
    ]
    return [
        {
            "path": _rel(path),
            "artifact_type": artifact_type,
            "status": status,
            "source": _rel(CLAIM_MATRIX),
            "notes": "Generated by scripts/build_manuscript_draft_package.py.",
        }
        for path, artifact_type, status in outputs
    ]


def main() -> int:
    claims = _claim_rows()
    checklist = _checklist_rows()
    storyline_rows = build_storyline_panel_map(claims)
    objection_rows = build_reviewer_objection_matrix(claims)

    _write_text(PRESUBMISSION_DRAFT, build_presubmission_draft(claims, checklist))
    _write_text(ABSTRACT_DRAFT, build_abstract_draft(claims))
    _write_text(COVER_LETTER_DRAFT, build_cover_letter_draft(claims))
    _write_tsv(
        STORYLINE_PANEL_MAP,
        storyline_rows,
        [
            "figure",
            "panel",
            "storyline_role",
            "source_artifact",
            "linked_claim_ids",
            "status",
            "manuscript_use",
            "caveat",
        ],
    )
    _write_tsv(
        OBJECTION_MATRIX,
        objection_rows,
        [
            "objection_id",
            "likely_reviewer_concern",
            "risk_level",
            "linked_gate_or_claim",
            "current_status",
            "evidence",
            "response_strategy",
            "required_before_submission",
        ],
    )
    _write_tsv(
        DRAFT_MANIFEST,
        build_manifest(),
        ["path", "artifact_type", "status", "source", "notes"],
    )
    print(_rel(PRESUBMISSION_DRAFT))
    print(_rel(ABSTRACT_DRAFT))
    print(_rel(COVER_LETTER_DRAFT))
    print(_rel(STORYLINE_PANEL_MAP))
    print(_rel(OBJECTION_MATRIX))
    print(_rel(DRAFT_MANIFEST))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
