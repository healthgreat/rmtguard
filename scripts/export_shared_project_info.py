#!/usr/bin/env python
"""Export reusable RMTGuard publication artifacts to a shared D-drive folder.

Author: RMTGuard development team
Date: 2026-05-04
Purpose: Copy release, journal-routing, Gantt, manual-action, and next-sprint
artifacts into a cross-project shared information folder for reuse by other
manuscript projects.
Data source: Local generated reports under docs/, results/, figures/, and
manuscript/.
Method notes: This script does not copy raw data, processed matrices, tokens,
or secrets. Existing destination files are overwritten atomically only for the
named shared artifacts.
"""

from __future__ import annotations

import argparse
import csv
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHARED_ROOT = Path(r"D:\99、共用信息")
PACKAGE_DIRNAME = "RMTGuard_20_50投稿资料包"
MANIFEST_TSV = ROOT / "results" / "shared_info" / "rmtguard_shared_export_manifest.tsv"
MANIFEST_MD = ROOT / "docs" / "shared_info_export_manifest.md"


@dataclass(frozen=True)
class CopyItem:
    source: Path
    destination_subdir: str
    destination_name: str
    role: str


COPY_ITEMS = [
    CopyItem(
        ROOT / "docs" / "jif20_50_gap_assessment.md",
        "01_project_status",
        "RMTGuard_JIF20_50_GAP_ASSESSMENT.md",
        "20-50 JIF gap assessment",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "jif20_50_gap_assessment.tsv",
        "01_project_status",
        "RMTGuard_JIF20_50_GAP_ASSESSMENT.tsv",
        "machine-readable gap assessment",
    ),
    CopyItem(
        ROOT / "docs" / "publication_execution_board.md",
        "01_project_status",
        "RMTGuard_PUBLICATION_EXECUTION_BOARD.md",
        "submission execution board",
    ),
    CopyItem(
        ROOT / "docs" / "nature_methods_next_round_gate_board.md",
        "01_project_status",
        "RMTGuard_NATURE_METHODS_NEXT_ROUND_GATE_BOARD.md",
        "Nature Methods next-round science gate board",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "nature_methods_next_round_gate_board.tsv",
        "01_project_status",
        "RMTGuard_NATURE_METHODS_NEXT_ROUND_GATE_BOARD.tsv",
        "machine-readable Nature Methods next-round gate board",
    ),
    CopyItem(
        ROOT / "results" / "project_management" / "rmtguard_project_gantt.md",
        "01_project_status",
        "RMTGuard_PROJECT_GANTT.md",
        "Gantt chart markdown",
    ),
    CopyItem(
        ROOT / "figures" / "project_management" / "rmtguard_project_gantt.png",
        "04_gantt_and_figures",
        "RMTGuard_PROJECT_GANTT.png",
        "Gantt chart PNG",
    ),
    CopyItem(
        ROOT / "figures" / "project_management" / "rmtguard_project_gantt.pdf",
        "04_gantt_and_figures",
        "RMTGuard_PROJECT_GANTT.pdf",
        "Gantt chart PDF",
    ),
    CopyItem(
        ROOT / "docs" / "manual_next_actions_20_50.md",
        "02_manual_actions",
        "RMTGuard_MANUAL_NEXT_ACTIONS_20_50.md",
        "manual author action checklist",
    ),
    CopyItem(
        ROOT / "docs" / "manual_author_execution_steps.md",
        "02_manual_actions",
        "RMTGuard_MANUAL_AUTHOR_EXECUTION_STEPS.md",
        "author execution checklist",
    ),
    CopyItem(
        ROOT / "docs" / "public_release_blocker_report.md",
        "03_release_evidence",
        "RMTGuard_PUBLIC_RELEASE_BLOCKER_REPORT.md",
        "release blocker report",
    ),
    CopyItem(
        ROOT / "manuscript" / "code_availability_finalization_draft.md",
        "03_release_evidence",
        "RMTGuard_CODE_AVAILABILITY_FINALIZATION_DRAFT.md",
        "code availability draft",
    ),
    CopyItem(
        ROOT / "manuscript" / "title_page_author_metadata.md",
        "05_author_metadata",
        "RMTGuard_TITLE_PAGE_AUTHOR_METADATA.md",
        "title-page author metadata",
    ),
    CopyItem(
        ROOT / "docs" / "author_declarations_and_credit_roles.md",
        "05_author_metadata",
        "RMTGuard_AUTHOR_DECLARATIONS_AND_CREDIT_ROLES.md",
        "author declarations and CRediT roles",
    ),
    CopyItem(
        ROOT / "docs" / "nature_methods_48h_execution_packet.md",
        "06_next_sprint_inputs",
        "RMTGuard_NATURE_METHODS_48H_EXECUTION_PACKET.md",
        "48-hour Nature Methods science execution packet",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "nature_methods_48h_execution_packet.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_NATURE_METHODS_48H_EXECUTION_PACKET.tsv",
        "machine-readable 48-hour execution packet",
    ),
    CopyItem(
        ROOT / "manuscript" / "claim_scope_final.md",
        "06_next_sprint_inputs",
        "RMTGuard_CLAIM_SCOPE_FINAL.md",
        "locked final claim boundary for current evidence",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "claim_scope_final_audit.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_CLAIM_SCOPE_FINAL_AUDIT.tsv",
        "machine-readable claim scope audit",
    ),
    CopyItem(
        ROOT / "docs" / "p0_component_ablation_run_sheet.md",
        "06_next_sprint_inputs",
        "RMTGuard_P0_COMPONENT_ABLATION_RUN_SHEET.md",
        "P0 component ablation run sheet",
    ),
    CopyItem(
        ROOT / "results" / "ablation" / "p0_component_ablation_run_sheet.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_P0_COMPONENT_ABLATION_RUN_SHEET.tsv",
        "machine-readable P0 component ablation run sheet",
    ),
    CopyItem(
        ROOT / "docs" / "manuscript_grade_null_power_grid_design.md",
        "06_next_sprint_inputs",
        "RMTGuard_NULL_POWER_GRID_DESIGN.md",
        "manuscript-grade null and power grid design",
    ),
    CopyItem(
        ROOT / "results" / "calibration" / "manuscript_grade_null_power_grid_design.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_NULL_POWER_GRID_DESIGN.tsv",
        "machine-readable null and power grid design",
    ),
    CopyItem(
        ROOT / "docs" / "added_dataset_annotation_boundary.md",
        "06_next_sprint_inputs",
        "RMTGuard_ADDED_DATASET_ANNOTATION_BOUNDARY.md",
        "annotation boundary table for added datasets",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "added_dataset_annotation_boundary.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_ADDED_DATASET_ANNOTATION_BOUNDARY.tsv",
        "machine-readable annotation boundary table",
    ),
]


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _copy_atomic(source: Path, destination: Path) -> str:
    if not source.exists():
        return "missing"
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".tmp")
    shutil.copy2(source, tmp)
    tmp.replace(destination)
    return "copied"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _package_readme(today: date) -> str:
    return f"""# RMTGuard 20-50 Publication Shared Package

Generated: {today.isoformat()}

This folder is a reusable handoff snapshot for RMTGuard and other
publication-oriented bioinformatics projects. It contains only project reports,
manual checklists, release evidence, next-sprint run sheets, and
figure-management files. It does not contain raw data, processed expression
matrices, tokens, passwords, or private clinical materials.

## Current RMTGuard Status

- Public GitHub repository: https://github.com/healthgreat/rmtguard
- GitHub Release: https://github.com/healthgreat/rmtguard/releases/tag/v0.1.0
- Zenodo DOI: https://doi.org/10.5281/zenodo.20012350
- Strict 20-50 JIF target: Nature Methods only after gate recovery.
- Current readiness score: 83/100.
- Acceptance guarantee: impossible.

## Main Files

- `01_project_status/RMTGuard_JIF20_50_GAP_ASSESSMENT.md`
- `01_project_status/RMTGuard_PUBLICATION_EXECUTION_BOARD.md`
- `01_project_status/RMTGuard_NATURE_METHODS_NEXT_ROUND_GATE_BOARD.md`
- `01_project_status/RMTGuard_PROJECT_GANTT.md`
- `02_manual_actions/RMTGuard_MANUAL_NEXT_ACTIONS_20_50.md`
- `03_release_evidence/RMTGuard_PUBLIC_RELEASE_BLOCKER_REPORT.md`
- `04_gantt_and_figures/RMTGuard_PROJECT_GANTT.png`
- `05_author_metadata/RMTGuard_TITLE_PAGE_AUTHOR_METADATA.md`
- `06_next_sprint_inputs/RMTGuard_NATURE_METHODS_48H_EXECUTION_PACKET.md`
- `06_next_sprint_inputs/RMTGuard_P0_COMPONENT_ABLATION_RUN_SHEET.md`
- `06_next_sprint_inputs/RMTGuard_NULL_POWER_GRID_DESIGN.md`
- `06_next_sprint_inputs/RMTGuard_ADDED_DATASET_ANNOTATION_BOUNDARY.md`

## Manual Inputs Still Needed

1. Confirm final correspondence postal code.
2. Confirm funding statement.
3. Confirm competing interests statement.
4. Confirm ethics/public-data-use statement.
5. Confirm CRediT author roles.
6. Choose whether PDAC/TME remains a main figure or is demoted to supplement.
7. Re-check JCR, CAS partition, and warning-list status immediately before
   journal submission.

## Reuse Rule

Use this package as a snapshot. If the RMTGuard source reports change, rerun:

```bash
python scripts/export_shared_project_info.py
```
"""


def _project_index(today: date, package_dir: Path) -> str:
    return f"""# RMTGuard 20-50 Status Index

Updated: {today.isoformat()}

Package path:

```text
{package_dir}
```

## One-line Status

RMTGuard has passed the public release engineering gate, but is not ready for a
strict 20-50 JIF submission because the remaining blockers are scientific:
stability-superiority is not supported, manuscript-grade component ablations
need final repeats/CI, realistic null and power grids need execution, and the
PDAC/TME biological showcase needs deepening or demotion.

## Fast Open

- Gap report: `{package_dir / "01_project_status" / "RMTGuard_JIF20_50_GAP_ASSESSMENT.md"}`
- Next-round gate board: `{package_dir / "01_project_status" / "RMTGuard_NATURE_METHODS_NEXT_ROUND_GATE_BOARD.md"}`
- 48-hour execution packet: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_NATURE_METHODS_48H_EXECUTION_PACKET.md"}`
- P0 ablation run sheet: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_P0_COMPONENT_ABLATION_RUN_SHEET.md"}`
- Null/power grid design: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_NULL_POWER_GRID_DESIGN.md"}`
- Gantt PNG: `{package_dir / "04_gantt_and_figures" / "RMTGuard_PROJECT_GANTT.png"}`
- Manual checklist: `{package_dir / "02_manual_actions" / "RMTGuard_MANUAL_NEXT_ACTIONS_20_50.md"}`
- Release blocker report: `{package_dir / "03_release_evidence" / "RMTGuard_PUBLIC_RELEASE_BLOCKER_REPORT.md"}`

## Current Journal Route

- Strict 20-50 JIF target: `Nature Methods`, only after gate recovery.
- Most realistic high-quality fallback: `Genome Biology`, but not strict 20-50
  by 2024 JIF.
- Safe fallback if method impact remains incremental: `Bioinformatics` or
  `NAR Genomics and Bioinformatics`.

## Evidence Boundary

This index is a local project-management artifact. It does not prove acceptance
or editorial fit. Re-check journal metrics, CAS partition, warning list, and
final submission policies before sending any manuscript.
"""


def _root_registry(today: date, package_dir: Path) -> str:
    return f"""# Project Shared Information Registry

Updated: {today.isoformat()}

This registry points to reusable information packages that can be reused across
bioinformatics/manuscript projects. It must not contain tokens, passwords, raw
patient data, or private clinical data.

## Active Packages

| Project | Package Path | Primary Use | Status |
| --- | --- | --- | --- |
| RMTGuard | `{package_dir}` | 20-50 JIF methods-paper routing, GitHub/Zenodo release evidence, manual submission checks, external-AI review handoff, next-sprint gate execution | active snapshot |

## Common Templates

- Journal metrics/CAS/warning-list template:
  `投稿前手动操作模板/JOURNAL_METRICS_CAS_WARNING_VERIFICATION_TEMPLATE.md`
- Methods-paper external AI review prompt:
  `AI外审通用模板/METHODS_PAPER_EXTERNAL_AI_REVIEW_PROMPT.md`

## Reuse Rule

Use the package as a snapshot. Before quoting numbers or journal status in a new
project, re-check the source project report and current journal metrics.
"""


def _journal_template(today: date) -> str:
    return f"""# Journal Metrics, CAS Zone, And Warning List Verification Template

Updated: {today.isoformat()}

Use this template for any project that depends on journal impact factor,
Chinese Academy of Sciences partition, or warning-list status.

## Links

- Journal Citation Reports: https://jcr.clarivate.com
- CAS partition table: https://www.fenqubiao.com
- CAS warning list portal: https://ewl.fenqubiao.com

## Manual Steps

1. Open JCR through institutional library/VPN.
2. Search the candidate journal by exact title.
3. Record 2024 JIF, 5-year JIF, category, rank, and quartile.
4. Open CAS partition table and record major category, subcategory, and Top
   status.
5. Open CAS warning-list portal and record whether the journal appears.
6. Save the verification date.

## Copy-back Table

```text
Journal | 2024 JIF | 5-year JIF | JCR category/quartile | CAS major zone | CAS minor zone | Top? | Warning-list? | Verification date
Nature Methods |  |  |  |  |  |  |  |
Nature Communications |  |  |  |  |  |  |  |
Genome Biology |  |  |  |  |  |  |  |
Cell Genomics |  |  |  |  |  |  |  |
Bioinformatics |  |  |  |  |  |  |  |
```
"""


def _external_review_prompt(today: date) -> str:
    return f"""# Methods Paper External AI Review Prompt

Updated: {today.isoformat()}

Use this prompt when sending a bioinformatics methods-paper package to another
AI model for pre-review.

```text
You are acting as a strict external reviewer for a bioinformatics methods paper.
Please audit the attached package as if deciding whether it is ready for a
high-impact genomics/methods journal.

Focus on:
1. P0 blockers that would cause desk rejection.
2. Unsupported or over-strong claims.
3. Benchmark design weaknesses.
4. Missing baselines, ablations, or statistical tests.
5. Figure/table clarity and source-data traceability.
6. Code/data availability and reproducibility.
7. Journal fit and realistic fallback route.

Please return:
- P0 blockers
- P1 major revisions
- Claim audit
- Method novelty audit
- Figure-by-figure critique
- Minimal next experiment set
- Final go/no-go recommendation

Do not give encouragement-only feedback. Tie every criticism to a concrete
file, figure, table, result, or missing validation step when possible.
```
"""


def _write_manifest(rows: list[dict[str, str]]) -> None:
    MANIFEST_TSV.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST_TSV.with_suffix(MANIFEST_TSV.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "role",
                "status",
                "source_path",
                "shared_path",
                "notes",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(MANIFEST_TSV)

    lines = [
        "# Shared Information Export Manifest",
        "",
        "Generated by `python scripts/export_shared_project_info.py`.",
        "",
        "| Role | Status | Source | Shared Path |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['role']} | `{row['status']}` | `{row['source_path']}` | `{row['shared_path']}` |"
        )
    _write_text_atomic(MANIFEST_MD, "\n".join(lines))


def export(shared_root: Path) -> list[dict[str, str]]:
    today = date.today()
    package_dir = shared_root / PACKAGE_DIRNAME
    rows: list[dict[str, str]] = []

    for item in COPY_ITEMS:
        destination = package_dir / item.destination_subdir / item.destination_name
        status = _copy_atomic(item.source, destination)
        rows.append(
            {
                "role": item.role,
                "status": status,
                "source_path": _rel(item.source),
                "shared_path": str(destination),
                "notes": "source copied" if status == "copied" else "source missing",
            }
        )

    generated_files = [
        (
            "shared package README",
            package_dir / "README.md",
            _package_readme(today),
        ),
        (
            "shared root registry",
            shared_root / "PROJECT_SHARED_INFO_REGISTRY.md",
            _root_registry(today, package_dir),
        ),
        (
            "project status index",
            shared_root / "项目信息索引" / "RMTGuard_20_50_STATUS_INDEX.md",
            _project_index(today, package_dir),
        ),
        (
            "journal verification template",
            shared_root
            / "投稿前手动操作模板"
            / "JOURNAL_METRICS_CAS_WARNING_VERIFICATION_TEMPLATE.md",
            _journal_template(today),
        ),
        (
            "methods paper external AI review prompt",
            shared_root
            / "AI外审通用模板"
            / "METHODS_PAPER_EXTERNAL_AI_REVIEW_PROMPT.md",
            _external_review_prompt(today),
        ),
    ]
    for role, destination, text in generated_files:
        _write_text_atomic(destination, text)
        rows.append(
            {
                "role": role,
                "status": "written",
                "source_path": "generated",
                "shared_path": str(destination),
                "notes": "generated shared helper",
            }
        )

    _write_manifest(rows)
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export reusable RMTGuard publication artifacts."
    )
    parser.add_argument(
        "--shared-root",
        type=Path,
        default=DEFAULT_SHARED_ROOT,
        help="Shared information root folder.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = export(args.shared_root)
    print(MANIFEST_TSV)
    print(MANIFEST_MD)
    print(args.shared_root / PACKAGE_DIRNAME)
    copied = sum(1 for row in rows if row["status"] in {"copied", "written"})
    print(f"shared_items\t{copied}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
