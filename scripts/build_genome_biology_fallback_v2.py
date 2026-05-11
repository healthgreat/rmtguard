from __future__ import annotations

"""Build the current Genome Biology fallback package for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-11
Purpose: Convert the Nature Methods-first RMTGuard package into a bounded
Genome Biology fallback route while preserving claim limits and release gates.
Data source: Local benchmark, release, claim-boundary, and Figure 4 artifacts.
Method notes: This script prepares fallback materials only. It does not claim
journal acceptance, strict 20-50 JIF eligibility, or broad clustering
superiority.
"""

import csv
import json
import subprocess
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

STABILITY = ROOT / "results" / "stability_benchmarks" / "stability_gate_diagnostics.tsv"
REALISTIC_NULL = ROOT / "results" / "calibration" / "realistic_null_summary.tsv"
RARE_POWER = ROOT / "results" / "calibration" / "rare_state_power_summary.tsv"
PDAC_DEEP = ROOT / "results" / "pdac_tme" / "deep_validation" / "pdac_deep_validation_summary.tsv"
PDAC_PATHWAY = (
    ROOT
    / "results"
    / "pdac_tme"
    / "pathway_atlas_validation"
    / "pdac_pathway_atlas_validation_summary.tsv"
)
PDAC_BOARD = ROOT / "results" / "submission" / "pdac_tme_figure4_strengthening_board.tsv"
CLAIM_SCOPE = ROOT / "results" / "submission" / "claim_scope_final_audit.tsv"
GO_NO_GO = ROOT / "results" / "submission" / "nature_methods_go_no_go_final.tsv"
RELEASE_READINESS = ROOT / "results" / "release" / "release_readiness.tsv"
PYPROJECT = ROOT / "pyproject.toml"
ZENODO = ROOT / ".zenodo.json"

OUT_TSV = ROOT / "results" / "submission" / "genome_biology_fallback_v2_checklist.tsv"
OUT_MD = ROOT / "docs" / "genome_biology_fallback_v2_packet.md"
OUT_ABSTRACT = ROOT / "manuscript" / "genome_biology_abstract_v2.md"
OUT_COVER = ROOT / "manuscript" / "genome_biology_cover_letter_v2.md"

OFFICIAL_SOURCES = {
    "aims_scope": "https://link.springer.com/journal/13059/aims-and-scope",
    "journal_home_metrics": "https://link.springer.com/journal/13059",
    "source_code_policy": "https://link.springer.com/article/10.1186/s13059-016-1040-y",
}


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


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "item_id",
        "status",
        "evidence_path",
        "current_value",
        "required_action",
        "allowed_wording",
        "forbidden_wording",
        "notes",
    ]
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


def _summary_value(path: Path, summary_id: str, default: str = "not_available") -> str:
    for row in _read_tsv(path):
        if row.get("summary_id") == summary_id:
            return row.get("value", default)
    return default


def _release_status(check_id: str, default: str = "missing") -> str:
    for row in _read_tsv(RELEASE_READINESS):
        if row.get("check_id") == check_id:
            return row.get("status", default)
    return default


def _zenodo_doi() -> str:
    if not ZENODO.exists():
        return "not_available"
    try:
        data = json.loads(ZENODO.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "not_available"
    return str(data.get("doi", "not_available"))


def _repository_url() -> str:
    if not PYPROJECT.exists():
        return "not_available"
    for line in PYPROJECT.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("Repository"):
            return stripped.split("=", 1)[1].strip().strip('"')
    return "not_available"


def _git_describe() -> str:
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "git_unavailable"
    return result.stdout.strip()


def _release_current_status() -> tuple[str, str]:
    describe = _git_describe()
    repo_status = _release_status("repository_url")
    remote_status = _release_status("github_remote")
    doi_status = _release_status("zenodo_doi")
    if describe.startswith("v0.1.0") and describe != "v0.1.0":
        return (
            "release_refresh_required",
            f"Current commit is {describe}, after archived v0.1.0; make a new GitHub/Zenodo archive for the submitted version.",
        )
    if repo_status == "pass" and remote_status == "pass" and doi_status == "pass":
        return (
            "archived_release_available",
            "Public repository and Zenodo DOI are recorded for the tagged release.",
        )
    return (
        "release_incomplete",
        f"repository_url={repo_status}; github_remote={remote_status}; zenodo_doi={doi_status}.",
    )


def _stability_summary() -> str:
    rows = _read_tsv(STABILITY)
    n_datasets = len(rows)
    no_calls = [row["dataset_id"] for row in rows if row.get("status") == "diagnostic_no_call"]
    below_best = [
        row["dataset_id"]
        for row in rows
        if row.get("status") == "fail_below_best_baseline"
    ]
    return (
        f"{n_datasets} public datasets; diagnostic no-call datasets="
        f"{','.join(no_calls) or 'none'}; below strongest stability baseline="
        f"{','.join(below_best) or 'none'}."
    )


def _null_summary() -> str:
    rows = _read_tsv(REALISTIC_NULL)
    parts = []
    for row in rows:
        parts.append(
            f"{row.get('null_model')} false_call_rate={row.get('false_call_rate')}"
        )
    return "; ".join(parts) if parts else "not_available"


def _rare_summary() -> str:
    rows = _read_tsv(RARE_POWER)
    if not rows:
        return "not_available"
    high_power = [
        row
        for row in rows
        if float(row.get("power", "0") or 0) >= 0.8
    ]
    low_power = [
        row
        for row in rows
        if float(row.get("power", "0") or 0) < 0.8
    ]
    return (
        f"50-repeat rare-state grid; {len(high_power)} settings power>=0.8, "
        f"{len(low_power)} settings power<0.8; low-prevalence/effect-size limits retained."
    )


def _pdac_summary() -> str:
    de = _summary_value(PDAC_DEEP, "significant_de_marker_rows")
    public_sig = _summary_value(PDAC_DEEP, "external_label_supported_primary_signatures")
    cluster_sig = _summary_value(
        PDAC_DEEP, "external_cluster_signature_supported_primary_signatures"
    )
    hallmark = _summary_value(PDAC_PATHWAY, "significant_hallmark_pathways")
    reactome = _summary_value(PDAC_PATHWAY, "significant_reactome_pathways")
    atlas = _summary_value(PDAC_PATHWAY, "atlas_supported_cluster_signature_rows")
    return (
        f"{de} BH-FDR marker rows; external signature support {public_sig} public-label "
        f"matches and {cluster_sig} RMTGuard-cluster matches; {hallmark} Hallmark, "
        f"{reactome} Reactome, and {atlas} atlas-overlap rows."
    )


def _pdac_stability_boundary() -> str:
    for row in _read_tsv(PDAC_BOARD):
        if row.get("evidence_layer") == "subsampling_stability_context":
            return row.get("key_result", "not_available")
    return "not_available"


def build_rows() -> list[dict[str, str]]:
    release_status, release_note = _release_current_status()
    repo = _repository_url()
    doi = _zenodo_doi()
    return [
        {
            "item_id": "journal_fit",
            "status": "fallback_fit_not_strict_20_50",
            "evidence_path": OFFICIAL_SOURCES["aims_scope"],
            "current_value": "Genome Biology scope covers genomics/post-genomics, new methods, software tools, and bioinformatics.",
            "required_action": "Use only as high-quality fallback, not as strict 20-50 JIF route.",
            "allowed_wording": "Genome Biology is a realistic genomics methods/software fallback.",
            "forbidden_wording": "Do not describe Genome Biology as satisfying the 20-50 JIF target.",
            "notes": "Official 2024 JIF=9.4; 5-year JIF=16.3 from journal home page checked 2026-05-11.",
        },
        {
            "item_id": "article_type_frame",
            "status": "software_methodology_candidate",
            "evidence_path": OFFICIAL_SOURCES["aims_scope"],
            "current_value": "RMTGuard is best framed as an open callability-aware scRNA-seq workflow with software, diagnostics, and benchmarks.",
            "required_action": "Prefer Software/Methodology framing after checking current submission forms.",
            "allowed_wording": "Open reproducible software/workflow for random-matrix callability diagnostics.",
            "forbidden_wording": "Do not frame as a broad Nature Methods-style conceptual breakthrough.",
            "notes": "Final article type must be selected in the current submission system.",
        },
        {
            "item_id": "code_release",
            "status": release_status,
            "evidence_path": _rel(RELEASE_READINESS),
            "current_value": f"repository={repo}; zenodo_doi={doi}; git={_git_describe()}",
            "required_action": "Before submission, archive the exact submitted commit if it differs from v0.1.0.",
            "allowed_wording": "A public repository and DOI archive exist for v0.1.0; exact submitted-version archiving must be current.",
            "forbidden_wording": "Do not imply the post-v0.1.0 working branch is the immutable archived manuscript version.",
            "notes": release_note,
        },
        {
            "item_id": "source_code_policy",
            "status": "compatible_if_current_archive_refreshes",
            "evidence_path": OFFICIAL_SOURCES["source_code_policy"],
            "current_value": "MIT license, public GitHub URL, Zenodo DOI metadata, Docker/CI/test package present.",
            "required_action": "Keep OSI-compatible license and DOI-assigning archive for the manuscript version.",
            "allowed_wording": "RMTGuard is released under the MIT License with repository and archival metadata.",
            "forbidden_wording": "Do not use non-commercial or restricted-use language.",
            "notes": "Genome Biology source-code policy emphasizes public repository, DOI archive, and open-source licensing.",
        },
        {
            "item_id": "central_claim",
            "status": "claim_bounded",
            "evidence_path": _rel(CLAIM_SCOPE),
            "current_value": "Callability-aware random-matrix noise-control workflow for scRNA-seq cell-state discovery.",
            "required_action": "Keep no-call and comparator limitations in abstract, Figure 3, and Discussion.",
            "allowed_wording": "RMTGuard exposes when structure is callable versus noise-controlled no-call.",
            "forbidden_wording": "Do not claim universal clustering superiority or automatic optimization of all scRNA-seq parameters.",
            "notes": "This frame is stronger for Genome Biology than Nature Methods breakthrough language.",
        },
        {
            "item_id": "synthetic_calibration",
            "status": "usable_with_grid_limits",
            "evidence_path": _rel(REALISTIC_NULL) + ";" + _rel(RARE_POWER),
            "current_value": _null_summary() + " | " + _rare_summary(),
            "required_action": "Report null and rare-state limits with CI rather than only positive examples.",
            "allowed_wording": "False-call control and rare-state power are supported in the tested simulation grid.",
            "forbidden_wording": "Do not generalize rare-state power beyond the tested prevalence/effect-size grid.",
            "notes": "Use this as Figure 2 and Supplementary benchmark evidence.",
        },
        {
            "item_id": "real_data_benchmark",
            "status": "callability_map_not_superiority",
            "evidence_path": _rel(STABILITY),
            "current_value": _stability_summary(),
            "required_action": "Reframe Figure 3 as callability/no-call and benchmark trade-off map.",
            "allowed_wording": "Real data show callability trade-offs and diagnostic no-call behavior across public datasets.",
            "forbidden_wording": "Do not claim RMTGuard beats the strongest comparator on every real dataset.",
            "notes": "PBMC68k/Zheng 2017 remains a diagnostic no-call, not a positive discovery.",
        },
        {
            "item_id": "pdac_tme_use_case",
            "status": "bounded_main_or_supplement",
            "evidence_path": _rel(PDAC_DEEP) + ";" + _rel(PDAC_PATHWAY) + ";" + _rel(PDAC_BOARD),
            "current_value": _pdac_summary() + " Stability boundary: " + _pdac_stability_boundary(),
            "required_action": "Keep as public-data application; demote to supplement if editors want a more general workflow paper.",
            "allowed_wording": "Bounded public PDAC/TME application with marker, pathway, external-signature, and atlas-marker support.",
            "forbidden_wording": "Do not claim a new PDAC mechanism, clinical validation, prognosis, therapy response, spatial validation, or protein validation.",
            "notes": "Current Figure 4 text audit should travel with the fallback package.",
        },
        {
            "item_id": "submission_status",
            "status": "prepare_not_send",
            "evidence_path": _rel(GO_NO_GO),
            "current_value": "Nature Methods full submission is no-go; Genome Biology fallback can be prepared but not sent until current archive and final author checks are complete.",
            "required_action": "Refresh exact release archive, confirm author sign-off, verify current Genome Biology submission instructions, then rerun gates.",
            "allowed_wording": "Fallback package prepared for possible transfer or direct Genome Biology submission.",
            "forbidden_wording": "Do not call the fallback submission-ready today.",
            "notes": "Use after Nature Methods presubmission is negative or abandoned.",
        },
    ]


def build_packet(rows: list[dict[str, str]]) -> str:
    lines = [
        "# Genome Biology Fallback v2 Packet",
        "",
        "Generated by `python scripts/build_genome_biology_fallback_v2.py`.",
        f"Verified/source refresh date: {date.today().isoformat()}.",
        "",
        "## Bottom Line",
        "",
        "- Route: `Genome Biology fallback`, not the strict 20-50 JIF target.",
        "- Current status: `prepare_not_send`.",
        "- Recommended frame: open callability-aware scRNA-seq software/workflow.",
        "- Acceptance guarantee: `impossible`.",
        "- Critical requirement: archive the exact submitted code version if it differs from `v0.1.0`.",
        "",
        "## Official Source Profile",
        "",
        f"- Aims and scope: {OFFICIAL_SOURCES['aims_scope']}",
        f"- Journal home and metrics: {OFFICIAL_SOURCES['journal_home_metrics']}",
        f"- Source-code policy/editorial: {OFFICIAL_SOURCES['source_code_policy']}",
        "- Officially checked values used here: 2024 JIF 9.4; 2024 5-year JIF 16.3.",
        "- CAS zone and warning-list status still require institutional manual verification.",
        "",
        "## Checklist",
        "",
        "| Item | Status | Evidence | Current Value | Required Action |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            + row["item_id"]
            + " | `"
            + row["status"]
            + "` | `"
            + row["evidence_path"]
            + "` | "
            + row["current_value"].replace("|", ";")
            + " | "
            + row["required_action"].replace("|", ";")
            + " |"
        )
    lines.extend(
        [
            "",
            "## Manuscript Reframe",
            "",
            "Use this route if Nature Methods presubmission is not encouraging or if "
            "we decide not to spend more time pursuing a strict 20-50 JIF route. "
            "The Genome Biology version should lead with reproducible genomics "
            "software, open source code, source data, no-call diagnostics, and "
            "transparent benchmark limitations.",
            "",
            "## Figure Plan",
            "",
            "1. Figure 1: RMTGuard workflow and random-matrix callability contract.",
            "2. Figure 2: realistic null and rare-state power calibration with CIs.",
            "3. Figure 3: public real-data callability map, not superiority table.",
            "4. Figure 4: bounded PDAC/TME public-data application or supplement.",
            "5. Figure 5: software release, runtime, memory, CI, Docker, source data.",
            "",
            "## Hard Stop Rules",
            "",
            "- Do not call this strict 20-50 JIF.",
            "- Do not submit until the exact manuscript code version is archived.",
            "- Do not hide PBMC68k diagnostic no-call behavior.",
            "- Do not claim a new PDAC mechanism or clinical validation.",
            "- Do not claim acceptance or editor interest.",
        ]
    )
    return "\n".join(lines)


def build_abstract() -> str:
    return f"""# Genome Biology Abstract v2

Status: `working draft`; do not submit until exact-code archive and final author checks are complete.

Single-cell RNA-seq cell-state discovery depends on feature-selection,
dimensionality, neighborhood, and clustering decisions that are often difficult
to compare across analyses. RMTGuard addresses this problem by reframing
embedding construction as a callability decision: principal components and
downstream graph structure are admitted only when they pass random-matrix
noise-control diagnostics, and low-confidence cases are reported as diagnostic
no-calls rather than forced into biological clusters.

RMTGuard implements spectral noise diagnostics, calibrated signal-PC admission,
adaptive near-edge embedding, stability summaries, AnnData-compatible outputs,
and machine-readable audit tables for feature, PC, graph, and cluster decisions.
In realistic null simulations, false-call rates remained 0 across three
50-repeat null models. In the rare-state grid, power was high in several
prevalence/effect-size settings but explicitly limited at the lowest
prevalence and effect sizes. Across four public real datasets, the benchmark
supports a callability-aware workflow but does not support universal stability
superiority over the strongest comparator; PBMC68k/Zheng 2017 is therefore
reported as a diagnostic no-call stress case.

A bounded PDAC/TME public-data application illustrates how callable clusters can
be connected to marker, external-signature, pathway, and atlas-marker evidence
without making a clinical or disease-mechanism claim. The current package
includes {_pdac_summary()} RMTGuard is thus positioned as an open,
evidence-bounded genomics workflow for transparent scRNA-seq callability
diagnostics.
"""


def build_cover_letter(rows: list[dict[str, str]]) -> str:
    release_status, release_note = _release_current_status()
    repo = _repository_url()
    doi = _zenodo_doi()
    return f"""# Genome Biology Cover Letter v2

Status: `prepare_not_send`.

Dear Editors,

We are preparing RMTGuard, an open callability-aware random-matrix workflow for
single-cell RNA-seq state discovery, for possible consideration by Genome
Biology as a genomics software/methodology manuscript.

RMTGuard addresses a practical reproducibility problem in single-cell analysis:
the distinction between structure that exceeds high-dimensional noise and
low-confidence structure that should not be forced into a biological
cell-state call. The software combines random-matrix spectral diagnostics,
signal-PC admission, adaptive embedding, no-call reporting, AnnData-compatible
outputs, and machine-readable audit tables.

The manuscript is intentionally evidence-bounded. Synthetic calibration
supports false-call control under tested null models and rare-state retention
within a pre-specified prevalence/effect-size grid. Public real-data benchmarks
are presented as callability and no-call diagnostics, not as universal
superiority over every fixed-PC or elbow-rule comparator. PBMC68k/Zheng 2017 is
reported as a diagnostic no-call stress case. A public PDAC/TME application is
included only as a bounded marker, pathway, external-signature, and atlas-marker
showcase, without a new disease-mechanism or clinical-validation claim.

Code and reproducibility materials are maintained at:

{repo}

Archive identifier metadata currently records {doi}, but the exact submitted commit
must be archived again if it differs from the currently archived tagged
release. Current release check: `{release_status}` ({release_note}).

We believe this controlled framing will be useful to Genome Biology readers who
need transparent single-cell workflows that report supported structure,
diagnostic no-calls, and benchmark limitations in a reusable software package.

Sincerely,

[TO CONFIRM: corresponding author]
"""


def main() -> int:
    rows = build_rows()
    _write_tsv(OUT_TSV, rows)
    _write_text(OUT_MD, build_packet(rows))
    _write_text(OUT_ABSTRACT, build_abstract())
    _write_text(OUT_COVER, build_cover_letter(rows))
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    print(_rel(OUT_ABSTRACT))
    print(_rel(OUT_COVER))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
