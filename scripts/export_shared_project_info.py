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
        ROOT / "docs" / "genome_biology_fallback_v2_packet.md",
        "01_project_status",
        "RMTGuard_GENOME_BIOLOGY_FALLBACK_V2_PACKET.md",
        "Genome Biology v2 fallback packet",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "genome_biology_fallback_v2_checklist.tsv",
        "01_project_status",
        "RMTGuard_GENOME_BIOLOGY_FALLBACK_V2_CHECKLIST.tsv",
        "machine-readable Genome Biology v2 fallback checklist",
    ),
    CopyItem(
        ROOT / "manuscript" / "genome_biology_abstract_v2.md",
        "01_project_status",
        "RMTGuard_GENOME_BIOLOGY_ABSTRACT_V2.md",
        "Genome Biology v2 abstract draft",
    ),
    CopyItem(
        ROOT / "manuscript" / "genome_biology_cover_letter_v2.md",
        "01_project_status",
        "RMTGuard_GENOME_BIOLOGY_COVER_LETTER_V2.md",
        "Genome Biology v2 cover letter draft",
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
        ROOT / "docs" / "p0_science_sprint_status.md",
        "06_next_sprint_inputs",
        "RMTGuard_P0_SCIENCE_SPRINT_STATUS.md",
        "P0 science sprint execution status",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "p0_science_sprint_status.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_P0_SCIENCE_SPRINT_STATUS.tsv",
        "machine-readable P0 science sprint execution status",
    ),
    CopyItem(
        ROOT / "docs" / "pdac_tme_route_decision_packet.md",
        "06_next_sprint_inputs",
        "RMTGuard_PDAC_TME_ROUTE_DECISION_PACKET.md",
        "PDAC/TME main-figure versus supplement decision packet",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "pdac_tme_route_decision_packet.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_PDAC_TME_ROUTE_DECISION_PACKET.tsv",
        "machine-readable PDAC/TME route decision packet",
    ),
    CopyItem(
        ROOT / "metadata" / "pdac_tme_route_decision_template.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_PDAC_TME_ROUTE_DECISION_TEMPLATE.tsv",
        "author-controlled PDAC/TME route decision template",
    ),
    CopyItem(
        ROOT / "docs" / "pdac_tme_dual_route_preflight.md",
        "06_next_sprint_inputs",
        "RMTGuard_PDAC_TME_DUAL_ROUTE_PREFLIGHT.md",
        "PDAC/TME dual-route data preflight",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "pdac_tme_dual_route_preflight.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_PDAC_TME_DUAL_ROUTE_PREFLIGHT.tsv",
        "machine-readable PDAC/TME dual-route preflight",
    ),
    CopyItem(
        ROOT / "docs" / "pdac_tme_dual_route_runbook.md",
        "06_next_sprint_inputs",
        "RMTGuard_PDAC_TME_DUAL_ROUTE_RUNBOOK.md",
        "PDAC/TME dual-route execution runbook",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "pdac_tme_dual_route_runbook.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_PDAC_TME_DUAL_ROUTE_RUNBOOK.tsv",
        "machine-readable PDAC/TME dual-route runbook",
    ),
    CopyItem(
        ROOT / "docs" / "pdac_tme_deep_validation.md",
        "06_next_sprint_inputs",
        "RMTGuard_PDAC_TME_DEEP_VALIDATION.md",
        "PDAC/TME deep validation first-pass report",
    ),
    CopyItem(
        ROOT / "results" / "pdac_tme" / "deep_validation" / "pdac_deep_validation_summary.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_PDAC_TME_DEEP_VALIDATION_SUMMARY.tsv",
        "machine-readable PDAC/TME deep validation summary",
    ),
    CopyItem(
        ROOT / "results" / "pdac_tme" / "deep_validation" / "pdac_de_markers_fdr.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_PDAC_TME_DE_MARKERS_FDR.tsv",
        "FDR-controlled PDAC/TME cluster marker table",
    ),
    CopyItem(
        ROOT / "results" / "pdac_tme" / "deep_validation" / "pdac_marker_set_enrichment.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_PDAC_TME_MARKER_SET_ENRICHMENT.tsv",
        "PDAC/TME marker-set enrichment table",
    ),
    CopyItem(
        ROOT / "results" / "pdac_tme" / "deep_validation" / "pdac_external_signature_validation.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_PDAC_TME_EXTERNAL_SIGNATURE_VALIDATION.tsv",
        "PDAC/TME external signature validation table",
    ),
    CopyItem(
        ROOT / "results" / "figures" / "source_data" / "figure4_pdac_tme_deep_validation.tsv",
        "04_gantt_and_figures",
        "RMTGuard_FIGURE4_PDAC_TME_DEEP_VALIDATION_SOURCE_DATA.tsv",
        "Figure 4 PDAC/TME source data",
    ),
    CopyItem(
        ROOT / "docs" / "pdac_tme_pathway_atlas_validation.md",
        "06_next_sprint_inputs",
        "RMTGuard_PDAC_TME_PATHWAY_ATLAS_VALIDATION.md",
        "PDAC/TME pathway and atlas validation report",
    ),
    CopyItem(
        ROOT / "docs" / "pdac_tme_figure4_strengthening_board.md",
        "06_next_sprint_inputs",
        "RMTGuard_PDAC_TME_FIGURE4_STRENGTHENING_BOARD.md",
        "PDAC/TME Figure 4 strengthening board",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "pdac_tme_figure4_strengthening_board.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_PDAC_TME_FIGURE4_STRENGTHENING_BOARD.tsv",
        "machine-readable PDAC/TME Figure 4 strengthening board",
    ),
    CopyItem(
        ROOT / "manuscript" / "figure4_strengthened_panel_blueprint.md",
        "04_gantt_and_figures",
        "RMTGuard_FIGURE4_STRENGTHENED_PANEL_BLUEPRINT.md",
        "strengthened Figure 4 panel blueprint",
    ),
    CopyItem(
        ROOT / "figures" / "manuscript" / "figure4_pdac_tme_strengthened.png",
        "04_gantt_and_figures",
        "RMTGuard_FIGURE4_PDAC_TME_STRENGTHENED.png",
        "strengthened Figure 4 PNG",
    ),
    CopyItem(
        ROOT / "figures" / "manuscript" / "figure4_pdac_tme_strengthened.pdf",
        "04_gantt_and_figures",
        "RMTGuard_FIGURE4_PDAC_TME_STRENGTHENED.pdf",
        "strengthened Figure 4 vector PDF",
    ),
    CopyItem(
        ROOT / "figures" / "manuscript" / "figure4_pdac_tme_strengthened_manifest.tsv",
        "04_gantt_and_figures",
        "RMTGuard_FIGURE4_PDAC_TME_STRENGTHENED_MANIFEST.tsv",
        "strengthened Figure 4 render manifest",
    ),
    CopyItem(
        ROOT / "results" / "figures" / "source_data" / "figure4_pdac_tme_strengthened_source.tsv",
        "04_gantt_and_figures",
        "RMTGuard_FIGURE4_PDAC_TME_STRENGTHENED_SOURCE_DATA.tsv",
        "strengthened Figure 4 source data",
    ),
    CopyItem(
        ROOT / "results" / "pdac_tme" / "pathway_atlas_validation" / "pdac_pathway_atlas_validation_summary.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_PDAC_TME_PATHWAY_ATLAS_SUMMARY.tsv",
        "machine-readable PDAC/TME pathway and atlas validation summary",
    ),
    CopyItem(
        ROOT / "results" / "pdac_tme" / "pathway_atlas_validation" / "pdac_pathway_rank_enrichment.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_PDAC_TME_PATHWAY_RANK_ENRICHMENT.tsv",
        "rank-based Hallmark/Reactome PDAC/TME pathway enrichment table",
    ),
    CopyItem(
        ROOT / "results" / "pdac_tme" / "pathway_atlas_validation" / "pdac_atlas_marker_citation_mapping.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_PDAC_TME_ATLAS_MARKER_CITATION_MAPPING.tsv",
        "PDAC/TME atlas marker citation mapping table",
    ),
    CopyItem(
        ROOT / "results" / "figures" / "source_data" / "figure4_pdac_tme_pathway_atlas_source.tsv",
        "04_gantt_and_figures",
        "RMTGuard_FIGURE4_PDAC_TME_PATHWAY_ATLAS_SOURCE_DATA.tsv",
        "Figure 4 PDAC/TME pathway and atlas source data",
    ),
    CopyItem(
        ROOT / "docs" / "mentor_journal_decision_2026-05-10.md",
        "01_project_status",
        "RMTGuard_MENTOR_JOURNAL_DECISION_2026-05-10.md",
        "mentor journal route decision memo",
    ),
    CopyItem(
        ROOT / "docs" / "competitor_positioning_concord_sclens_2026-05-12.md",
        "01_project_status",
        "RMTGuard_COMPETITOR_POSITIONING_CONCORD_SCLENS.md",
        "CONCORD and scLENS competitor positioning memo",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "competitor_positioning_matrix.tsv",
        "01_project_status",
        "RMTGuard_COMPETITOR_POSITIONING_MATRIX.tsv",
        "machine-readable competitor positioning matrix",
    ),
    CopyItem(
        ROOT / "docs" / "benchmark_upgrade_from_concord_sclens_2026-05-12.md",
        "06_next_sprint_inputs",
        "RMTGuard_BENCHMARK_UPGRADE_FROM_CONCORD_SCLENS.md",
        "benchmark upgrade checklist from CONCORD and scLENS",
    ),
    CopyItem(
        ROOT / "docs" / "p0_benchmark_upgrade_status_2026-05-12.md",
        "06_next_sprint_inputs",
        "RMTGuard_P0_BENCHMARK_UPGRADE_STATUS.md",
        "P0 benchmark upgrade status after scLENSpy n_rand_matrix=20",
    ),
    CopyItem(
        ROOT / "docs" / "topology_stress_benchmark_2026-05-12.md",
        "06_next_sprint_inputs",
        "RMTGuard_TOPOLOGY_STRESS_BENCHMARK.md",
        "CONCORD-style topology stress benchmark report",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "benchmark_upgrade_from_concord_sclens.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_BENCHMARK_UPGRADE_FROM_CONCORD_SCLENS.tsv",
        "machine-readable benchmark upgrade action table",
    ),
    CopyItem(
        ROOT / "docs" / "current_evidence_freeze_2026-05-12.md",
        "01_project_status",
        "RMTGuard_CURRENT_EVIDENCE_FREEZE.md",
        "current evidence-freeze report",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "current_evidence_freeze_manifest.tsv",
        "01_project_status",
        "RMTGuard_CURRENT_EVIDENCE_FREEZE_MANIFEST.tsv",
        "machine-readable current evidence-freeze manifest",
    ),
    CopyItem(
        ROOT / "manuscript" / "results_freeze_aligned_draft.md",
        "07_presubmission",
        "RMTGuard_RESULTS_FREEZE_ALIGNED_DRAFT.md",
        "freeze-aligned Results draft",
    ),
    CopyItem(
        ROOT / "manuscript" / "figure_legends_freeze_aligned.md",
        "07_presubmission",
        "RMTGuard_FIGURE_LEGENDS_FREEZE_ALIGNED.md",
        "freeze-aligned figure legends draft",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "freeze_aligned_text_audit.tsv",
        "07_presubmission",
        "RMTGuard_FREEZE_ALIGNED_TEXT_AUDIT.tsv",
        "machine-readable claim audit for freeze-aligned text",
    ),
    CopyItem(
        ROOT / "output" / "doc" / "RMTGuard_external_review_packet_2026-05-12.docx",
        "07_presubmission",
        "RMTGuard_EXTERNAL_REVIEW_PACKET_2026-05-12.docx",
        "Word handoff packet for external scientific review",
    ),
    CopyItem(
        ROOT / "docs" / "nature_reporting_summary_draft.md",
        "07_presubmission",
        "RMTGuard_NATURE_REPORTING_SUMMARY_DRAFT.md",
        "Nature reporting-summary worksheet",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "reporting_summary_draft.tsv",
        "07_presubmission",
        "RMTGuard_NATURE_REPORTING_SUMMARY_DRAFT.tsv",
        "machine-readable Nature reporting-summary worksheet",
    ),
    CopyItem(
        ROOT / "docs" / "figure_caption_source_audit.md",
        "04_gantt_and_figures",
        "RMTGuard_FIGURE_CAPTION_SOURCE_AUDIT.md",
        "figure-caption-source consistency audit",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "figure_caption_source_audit.tsv",
        "04_gantt_and_figures",
        "RMTGuard_FIGURE_CAPTION_SOURCE_AUDIT.tsv",
        "machine-readable figure-caption-source audit",
    ),
    CopyItem(
        ROOT / "docs" / "post_release_version_coverage_audit.md",
        "03_release_evidence",
        "RMTGuard_POST_RELEASE_VERSION_COVERAGE_AUDIT.md",
        "post-release version coverage audit",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "post_release_version_coverage_audit.tsv",
        "03_release_evidence",
        "RMTGuard_POST_RELEASE_VERSION_COVERAGE_AUDIT.tsv",
        "machine-readable post-release version coverage audit",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "post_release_changed_files.tsv",
        "03_release_evidence",
        "RMTGuard_POST_RELEASE_CHANGED_FILES.tsv",
        "post-release changed-file classification table",
    ),
    CopyItem(
        ROOT / "docs" / "v0_1_1_release_preflight.md",
        "03_release_evidence",
        "RMTGuard_V0_1_1_RELEASE_PREFLIGHT.md",
        "v0.1.1 no-action release preflight",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "v0_1_1_release_preflight.tsv",
        "03_release_evidence",
        "RMTGuard_V0_1_1_RELEASE_PREFLIGHT.tsv",
        "machine-readable v0.1.1 no-action release preflight",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "topology_stress_summary.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_TOPOLOGY_STRESS_SUMMARY.tsv",
        "machine-readable topology stress benchmark summary",
    ),
    CopyItem(
        ROOT / "figures" / "manuscript" / "figure_topology_stress.png",
        "04_gantt_and_figures",
        "RMTGuard_TOPOLOGY_STRESS.png",
        "topology stress benchmark PNG",
    ),
    CopyItem(
        ROOT / "figures" / "manuscript" / "figure_topology_stress.pdf",
        "04_gantt_and_figures",
        "RMTGuard_TOPOLOGY_STRESS.pdf",
        "topology stress benchmark PDF",
    ),
    CopyItem(
        ROOT / "figures" / "manuscript" / "topology_stress_figure_manifest.tsv",
        "04_gantt_and_figures",
        "RMTGuard_TOPOLOGY_STRESS_FIGURE_MANIFEST.tsv",
        "topology stress figure manifest",
    ),
    CopyItem(
        ROOT / "docs" / "realdata_topology_benchmark_2026-05-12.md",
        "06_next_sprint_inputs",
        "RMTGuard_REALDATA_TOPOLOGY_BENCHMARK.md",
        "Paul15 real-data topology monitor report",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "realdata_topology_summary.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_REALDATA_TOPOLOGY_SUMMARY.tsv",
        "machine-readable Paul15 real-data topology summary",
    ),
    CopyItem(
        ROOT / "results" / "figures" / "source_data" / "figure_realdata_topology_source.tsv",
        "04_gantt_and_figures",
        "RMTGuard_REALDATA_TOPOLOGY_SOURCE_DATA.tsv",
        "Paul15 real-data topology figure source data",
    ),
    CopyItem(
        ROOT / "figures" / "manuscript" / "figure_realdata_topology_benchmark.png",
        "04_gantt_and_figures",
        "RMTGuard_REALDATA_TOPOLOGY.png",
        "Paul15 real-data topology monitor PNG",
    ),
    CopyItem(
        ROOT / "figures" / "manuscript" / "figure_realdata_topology_benchmark.pdf",
        "04_gantt_and_figures",
        "RMTGuard_REALDATA_TOPOLOGY.pdf",
        "Paul15 real-data topology monitor PDF",
    ),
    CopyItem(
        ROOT / "figures" / "manuscript" / "figure_realdata_topology_benchmark.tiff",
        "04_gantt_and_figures",
        "RMTGuard_REALDATA_TOPOLOGY.tiff",
        "Paul15 real-data topology monitor TIFF",
    ),
    CopyItem(
        ROOT / "figures" / "manuscript" / "figure_realdata_topology_manifest.tsv",
        "04_gantt_and_figures",
        "RMTGuard_REALDATA_TOPOLOGY_MANIFEST.tsv",
        "Paul15 real-data topology render manifest",
    ),
    CopyItem(
        ROOT / "docs" / "no_call_decision_map.md",
        "06_next_sprint_inputs",
        "RMTGuard_NO_CALL_DECISION_MAP.md",
        "Figure 3 callability and no-call decision map report",
    ),
    CopyItem(
        ROOT / "results" / "callability" / "no_call_decision_map.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_NO_CALL_DECISION_MAP.tsv",
        "machine-readable callability and no-call decision map",
    ),
    CopyItem(
        ROOT
        / "results"
        / "figures"
        / "source_data"
        / "figure3_callability_decision_map.tsv",
        "04_gantt_and_figures",
        "RMTGuard_FIGURE3_CALLABILITY_DECISION_MAP_SOURCE_DATA.tsv",
        "Figure 3 callability decision-map source data",
    ),
    CopyItem(
        ROOT / "figures" / "manuscript" / "figure_no_call_decision_map.png",
        "04_gantt_and_figures",
        "RMTGuard_NO_CALL_DECISION_MAP.png",
        "Figure 3 callability and no-call decision map PNG",
    ),
    CopyItem(
        ROOT / "figures" / "manuscript" / "figure_no_call_decision_map.pdf",
        "04_gantt_and_figures",
        "RMTGuard_NO_CALL_DECISION_MAP.pdf",
        "Figure 3 callability and no-call decision map PDF",
    ),
    CopyItem(
        ROOT / "figures" / "manuscript" / "figure_no_call_decision_map.tiff",
        "04_gantt_and_figures",
        "RMTGuard_NO_CALL_DECISION_MAP.tiff",
        "Figure 3 callability and no-call decision map TIFF",
    ),
    CopyItem(
        ROOT / "figures" / "manuscript" / "no_call_decision_map_manifest.tsv",
        "04_gantt_and_figures",
        "RMTGuard_NO_CALL_DECISION_MAP_MANIFEST.tsv",
        "Figure 3 callability decision-map render manifest",
    ),
    CopyItem(
        ROOT / "docs" / "sclens_feasibility_check_2026-05-12.md",
        "06_next_sprint_inputs",
        "RMTGuard_SCLENS_FEASIBILITY_CHECK.md",
        "scLENS feasibility check report",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "sclens_feasibility_smoke.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_SCLENS_FEASIBILITY_SMOKE.tsv",
        "machine-readable scLENS smoke-test output",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "sclens_h5ad_smoke_summary.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_SCLENS_H5AD_SMOKE_SUMMARY.tsv",
        "machine-readable scLENSpy PBMC3k/Kang h5ad smoke summary",
    ),
    CopyItem(
        ROOT / "docs" / "sclens_stability_pilot_2026-05-12.md",
        "06_next_sprint_inputs",
        "RMTGuard_SCLENS_STABILITY_PILOT.md",
        "scLENSpy 10-repeat stability pilot report",
    ),
    CopyItem(
        ROOT
        / "results"
        / "submission"
        / "sclens_vs_rmtguard_stability_pilot.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_SCLENS_VS_RMTGUARD_STABILITY_PILOT.tsv",
        "machine-readable scLENSpy versus RMTGuard stability pilot table",
    ),
    CopyItem(
        ROOT / "docs" / "sclens_stability_nrand20_2026-05-12.md",
        "06_next_sprint_inputs",
        "RMTGuard_SCLENS_STABILITY_NRAND20.md",
        "scLENSpy n_rand_matrix=20 stability comparator report",
    ),
    CopyItem(
        ROOT
        / "results"
        / "submission"
        / "sclens_vs_rmtguard_stability_nrand20.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_SCLENS_VS_RMTGUARD_STABILITY_NRAND20.tsv",
        "machine-readable scLENSpy n_rand_matrix=20 versus RMTGuard table",
    ),
    CopyItem(
        ROOT / "docs" / "figure4_pdac_tme_wording_freeze.md",
        "06_next_sprint_inputs",
        "RMTGuard_FIGURE4_PDAC_TME_WORDING_FREEZE.md",
        "Figure 4 PDAC/TME bounded wording freeze",
    ),
    CopyItem(
        ROOT / "docs" / "nature_methods_go_no_go_final.md",
        "01_project_status",
        "RMTGuard_NATURE_METHODS_GO_NO_GO_FINAL.md",
        "Nature Methods final go/no-go control packet",
    ),
    CopyItem(
        ROOT / "manuscript" / "figure4_caption_bounded_draft.md",
        "04_gantt_and_figures",
        "RMTGuard_FIGURE4_CAPTION_BOUNDED_DRAFT.md",
        "Figure 4 bounded caption draft",
    ),
    CopyItem(
        ROOT / "manuscript" / "figure4_caption_strengthened_draft.md",
        "04_gantt_and_figures",
        "RMTGuard_FIGURE4_CAPTION_STRENGTHENED_DRAFT.md",
        "strengthened Figure 4 caption draft",
    ),
    CopyItem(
        ROOT / "manuscript" / "results_figure4_strengthened_draft.md",
        "04_gantt_and_figures",
        "RMTGuard_RESULTS_FIGURE4_STRENGTHENED_DRAFT.md",
        "strengthened Figure 4 Results draft",
    ),
    CopyItem(
        ROOT / "docs" / "figure4_strengthened_text_audit.md",
        "04_gantt_and_figures",
        "RMTGuard_FIGURE4_STRENGTHENED_TEXT_AUDIT.md",
        "strengthened Figure 4 text audit",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "figure4_strengthened_text_audit.tsv",
        "04_gantt_and_figures",
        "RMTGuard_FIGURE4_STRENGTHENED_TEXT_AUDIT.tsv",
        "machine-readable strengthened Figure 4 text audit",
    ),
    CopyItem(
        ROOT / "manuscript" / "corresponding_author_figure4_acknowledgement_template.md",
        "02_manual_actions",
        "RMTGuard_CORRESPONDING_AUTHOR_FIGURE4_ACKNOWLEDGEMENT_TEMPLATE.md",
        "corresponding-author Figure 4 acknowledgement template",
    ),
    CopyItem(
        ROOT / "manuscript" / "corresponding_author_signoff_packet.md",
        "02_manual_actions",
        "RMTGuard_CORRESPONDING_AUTHOR_SIGNOFF_PACKET.md",
        "corresponding-author sign-off packet",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "corresponding_author_signoff_packet.tsv",
        "02_manual_actions",
        "RMTGuard_CORRESPONDING_AUTHOR_SIGNOFF_PACKET.tsv",
        "machine-readable corresponding-author sign-off packet",
    ),
    CopyItem(
        ROOT / "output" / "doc" / "RMTGuard_corresponding_author_signoff_packet.docx",
        "02_manual_actions",
        "RMTGuard_CORRESPONDING_AUTHOR_SIGNOFF_PACKET.docx",
        "Word corresponding-author sign-off packet",
    ),
    CopyItem(
        ROOT / "metadata" / "corresponding_author_signoff_tracker.tsv",
        "02_manual_actions",
        "RMTGuard_CORRESPONDING_AUTHOR_SIGNOFF_TRACKER.tsv",
        "corresponding-author sign-off tracker",
    ),
    CopyItem(
        ROOT / "docs" / "corresponding_author_signoff_tracker.md",
        "02_manual_actions",
        "RMTGuard_CORRESPONDING_AUTHOR_SIGNOFF_TRACKER.md",
        "corresponding-author sign-off tracker report",
    ),
    CopyItem(
        ROOT / "manuscript" / "corresponding_author_signoff_email_draft.md",
        "02_manual_actions",
        "RMTGuard_CORRESPONDING_AUTHOR_SIGNOFF_EMAIL_DRAFT.md",
        "corresponding-author sign-off email draft",
    ),
    CopyItem(
        ROOT / "output" / "email" / "RMTGuard_corresponding_author_signoff_email.eml",
        "02_manual_actions",
        "RMTGuard_CORRESPONDING_AUTHOR_SIGNOFF_EMAIL.eml",
        "corresponding-author sign-off email EML draft",
    ),
    CopyItem(
        ROOT / "docs" / "corresponding_author_reply_intake_runbook.md",
        "02_manual_actions",
        "RMTGuard_CORRESPONDING_AUTHOR_REPLY_INTAKE_RUNBOOK.md",
        "corresponding-author reply intake runbook",
    ),
    CopyItem(
        ROOT / "manuscript" / "nature_methods_presubmission_inquiry.md",
        "07_presubmission",
        "RMTGuard_NATURE_METHODS_PRESUBMISSION_INQUIRY_DRAFT.md",
        "Nature Methods presubmission inquiry draft",
    ),
    CopyItem(
        ROOT / "manuscript" / "nature_methods_presubmission_send_packet.md",
        "07_presubmission",
        "RMTGuard_NATURE_METHODS_PRESUBMISSION_SEND_PACKET.md",
        "gated Nature Methods presubmission send packet",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "nature_methods_presubmission_send_packet.tsv",
        "07_presubmission",
        "RMTGuard_NATURE_METHODS_PRESUBMISSION_SEND_PACKET.tsv",
        "machine-readable Nature Methods presubmission send packet",
    ),
    CopyItem(
        ROOT / "docs" / "nature_methods_presubmission_send_runbook.md",
        "07_presubmission",
        "RMTGuard_NATURE_METHODS_PRESUBMISSION_SEND_RUNBOOK.md",
        "Nature Methods presubmission send runbook",
    ),
    CopyItem(
        ROOT / "docs" / "nature_methods_official_route_verification.md",
        "07_presubmission",
        "RMTGuard_NATURE_METHODS_OFFICIAL_ROUTE_VERIFICATION.md",
        "official-source Nature Methods route verification checklist",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "nature_methods_official_route_verification.tsv",
        "07_presubmission",
        "RMTGuard_NATURE_METHODS_OFFICIAL_ROUTE_VERIFICATION.tsv",
        "machine-readable official Nature Methods route verification checklist",
    ),
    CopyItem(
        ROOT / "output" / "email" / "RMTGuard_nature_methods_presubmission_inquiry_HOLD.eml",
        "07_presubmission",
        "RMTGuard_NATURE_METHODS_PRESUBMISSION_INQUIRY_HOLD.eml",
        "HOLD Nature Methods presubmission email draft",
    ),
    CopyItem(
        ROOT / "docs" / "component_ablation_benchmark.md",
        "06_next_sprint_inputs",
        "RMTGuard_COMPONENT_ABLATION_BENCHMARK.md",
        "20-repeat synthetic component ablation report",
    ),
    CopyItem(
        ROOT / "results" / "ablation" / "component_ablation_summary.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_COMPONENT_ABLATION_SUMMARY.tsv",
        "machine-readable 20-repeat synthetic component ablation summary",
    ),
    CopyItem(
        ROOT / "docs" / "realdata_ablation_annotation.md",
        "06_next_sprint_inputs",
        "RMTGuard_REALDATA_ABLATION_ANNOTATION.md",
        "20-repeat real-data component ablation annotation report",
    ),
    CopyItem(
        ROOT / "results" / "ablation" / "realdata_ablation_annotation_summary.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_REALDATA_ABLATION_ANNOTATION_SUMMARY.tsv",
        "machine-readable 20-repeat real-data component ablation annotation summary",
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
        ROOT / "docs" / "realistic_null_power_calibration.md",
        "06_next_sprint_inputs",
        "RMTGuard_REALISTIC_NULL_POWER_CALIBRATION.md",
        "50-repeat realistic null and rare-state power calibration report",
    ),
    CopyItem(
        ROOT / "results" / "calibration" / "realistic_null_summary.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_REALISTIC_NULL_SUMMARY.tsv",
        "machine-readable 50-repeat realistic null summary",
    ),
    CopyItem(
        ROOT / "results" / "calibration" / "rare_state_power_summary.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_RARE_STATE_POWER_SUMMARY.tsv",
        "machine-readable 50-repeat rare-state power summary",
    ),
    CopyItem(
        ROOT / "docs" / "rare_state_claim_boundary.md",
        "06_next_sprint_inputs",
        "RMTGuard_RARE_STATE_CLAIM_BOUNDARY.md",
        "rare-state power claim boundary report",
    ),
    CopyItem(
        ROOT / "results" / "submission" / "rare_state_claim_boundary.tsv",
        "06_next_sprint_inputs",
        "RMTGuard_RARE_STATE_CLAIM_BOUNDARY.tsv",
        "machine-readable rare-state power claim boundary",
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
- Current readiness score: 90/100.
- Acceptance guarantee: impossible.

## Main Files

- `01_project_status/RMTGuard_JIF20_50_GAP_ASSESSMENT.md`
- `01_project_status/RMTGuard_PUBLICATION_EXECUTION_BOARD.md`
- `01_project_status/RMTGuard_NATURE_METHODS_NEXT_ROUND_GATE_BOARD.md`
- `01_project_status/RMTGuard_GENOME_BIOLOGY_FALLBACK_V2_PACKET.md`
- `01_project_status/RMTGuard_GENOME_BIOLOGY_ABSTRACT_V2.md`
- `01_project_status/RMTGuard_GENOME_BIOLOGY_COVER_LETTER_V2.md`
- `01_project_status/RMTGuard_PROJECT_GANTT.md`
- `01_project_status/RMTGuard_MENTOR_JOURNAL_DECISION_2026-05-10.md`
- `01_project_status/RMTGuard_NATURE_METHODS_GO_NO_GO_FINAL.md`
- `01_project_status/RMTGuard_CURRENT_EVIDENCE_FREEZE.md`
- `01_project_status/RMTGuard_CURRENT_EVIDENCE_FREEZE_MANIFEST.tsv`
- `07_presubmission/RMTGuard_RESULTS_FREEZE_ALIGNED_DRAFT.md`
- `07_presubmission/RMTGuard_FIGURE_LEGENDS_FREEZE_ALIGNED.md`
- `07_presubmission/RMTGuard_FREEZE_ALIGNED_TEXT_AUDIT.tsv`
- `07_presubmission/RMTGuard_EXTERNAL_REVIEW_PACKET_2026-05-12.docx`
- `07_presubmission/RMTGuard_NATURE_REPORTING_SUMMARY_DRAFT.md`
- `07_presubmission/RMTGuard_NATURE_REPORTING_SUMMARY_DRAFT.tsv`
- `04_gantt_and_figures/RMTGuard_FIGURE_CAPTION_SOURCE_AUDIT.md`
- `04_gantt_and_figures/RMTGuard_FIGURE_CAPTION_SOURCE_AUDIT.tsv`
- `03_release_evidence/RMTGuard_POST_RELEASE_VERSION_COVERAGE_AUDIT.md`
- `03_release_evidence/RMTGuard_POST_RELEASE_VERSION_COVERAGE_AUDIT.tsv`
- `03_release_evidence/RMTGuard_V0_1_1_RELEASE_PREFLIGHT.md`
- `03_release_evidence/RMTGuard_V0_1_1_RELEASE_PREFLIGHT.tsv`
- `02_manual_actions/RMTGuard_MANUAL_NEXT_ACTIONS_20_50.md`
- `02_manual_actions/RMTGuard_CORRESPONDING_AUTHOR_FIGURE4_ACKNOWLEDGEMENT_TEMPLATE.md`
- `02_manual_actions/RMTGuard_CORRESPONDING_AUTHOR_SIGNOFF_PACKET.docx`
- `02_manual_actions/RMTGuard_CORRESPONDING_AUTHOR_SIGNOFF_EMAIL.eml`
- `02_manual_actions/RMTGuard_CORRESPONDING_AUTHOR_SIGNOFF_TRACKER.tsv`
- `02_manual_actions/RMTGuard_CORRESPONDING_AUTHOR_REPLY_INTAKE_RUNBOOK.md`
- `07_presubmission/RMTGuard_NATURE_METHODS_PRESUBMISSION_SEND_PACKET.md`
- `07_presubmission/RMTGuard_NATURE_METHODS_PRESUBMISSION_SEND_RUNBOOK.md`
- `07_presubmission/RMTGuard_NATURE_METHODS_OFFICIAL_ROUTE_VERIFICATION.md`
- `07_presubmission/RMTGuard_NATURE_METHODS_PRESUBMISSION_INQUIRY_HOLD.eml`
- `03_release_evidence/RMTGuard_PUBLIC_RELEASE_BLOCKER_REPORT.md`
- `04_gantt_and_figures/RMTGuard_PROJECT_GANTT.png`
- `04_gantt_and_figures/RMTGuard_FIGURE4_CAPTION_BOUNDED_DRAFT.md`
- `04_gantt_and_figures/RMTGuard_FIGURE4_CAPTION_STRENGTHENED_DRAFT.md`
- `04_gantt_and_figures/RMTGuard_RESULTS_FIGURE4_STRENGTHENED_DRAFT.md`
- `04_gantt_and_figures/RMTGuard_FIGURE4_STRENGTHENED_TEXT_AUDIT.md`
- `04_gantt_and_figures/RMTGuard_FIGURE4_PDAC_TME_STRENGTHENED.png`
- `04_gantt_and_figures/RMTGuard_FIGURE4_PDAC_TME_STRENGTHENED.pdf`
- `04_gantt_and_figures/RMTGuard_FIGURE4_PDAC_TME_STRENGTHENED_SOURCE_DATA.tsv`
- `04_gantt_and_figures/RMTGuard_NO_CALL_DECISION_MAP.png`
- `04_gantt_and_figures/RMTGuard_NO_CALL_DECISION_MAP.pdf`
- `04_gantt_and_figures/RMTGuard_FIGURE3_CALLABILITY_DECISION_MAP_SOURCE_DATA.tsv`
- `04_gantt_and_figures/RMTGuard_NO_CALL_DECISION_MAP.tiff`
- `05_author_metadata/RMTGuard_TITLE_PAGE_AUTHOR_METADATA.md`
- `06_next_sprint_inputs/RMTGuard_NATURE_METHODS_48H_EXECUTION_PACKET.md`
- `06_next_sprint_inputs/RMTGuard_P0_SCIENCE_SPRINT_STATUS.md`
- `06_next_sprint_inputs/RMTGuard_P0_BENCHMARK_UPGRADE_STATUS.md`
- `06_next_sprint_inputs/RMTGuard_TOPOLOGY_STRESS_BENCHMARK.md`
- `06_next_sprint_inputs/RMTGuard_TOPOLOGY_STRESS_SUMMARY.tsv`
- `06_next_sprint_inputs/RMTGuard_REALDATA_TOPOLOGY_BENCHMARK.md`
- `06_next_sprint_inputs/RMTGuard_REALDATA_TOPOLOGY_SUMMARY.tsv`
- `04_gantt_and_figures/RMTGuard_REALDATA_TOPOLOGY.png`
- `04_gantt_and_figures/RMTGuard_REALDATA_TOPOLOGY.pdf`
- `06_next_sprint_inputs/RMTGuard_NO_CALL_DECISION_MAP.md`
- `06_next_sprint_inputs/RMTGuard_NO_CALL_DECISION_MAP.tsv`
- `06_next_sprint_inputs/RMTGuard_PDAC_TME_ROUTE_DECISION_PACKET.md`
- `06_next_sprint_inputs/RMTGuard_PDAC_TME_DUAL_ROUTE_PREFLIGHT.md`
- `06_next_sprint_inputs/RMTGuard_PDAC_TME_DUAL_ROUTE_RUNBOOK.md`
- `06_next_sprint_inputs/RMTGuard_PDAC_TME_DEEP_VALIDATION.md`
- `06_next_sprint_inputs/RMTGuard_PDAC_TME_PATHWAY_ATLAS_VALIDATION.md`
- `06_next_sprint_inputs/RMTGuard_PDAC_TME_FIGURE4_STRENGTHENING_BOARD.md`
- `06_next_sprint_inputs/RMTGuard_FIGURE4_PDAC_TME_WORDING_FREEZE.md`
- `06_next_sprint_inputs/RMTGuard_SCLENS_STABILITY_PILOT.md`
- `06_next_sprint_inputs/RMTGuard_SCLENS_VS_RMTGUARD_STABILITY_PILOT.tsv`
- `06_next_sprint_inputs/RMTGuard_SCLENS_STABILITY_NRAND20.md`
- `06_next_sprint_inputs/RMTGuard_SCLENS_VS_RMTGUARD_STABILITY_NRAND20.tsv`
- `06_next_sprint_inputs/RMTGuard_COMPONENT_ABLATION_BENCHMARK.md`
- `06_next_sprint_inputs/RMTGuard_REALDATA_ABLATION_ANNOTATION.md`
- `06_next_sprint_inputs/RMTGuard_P0_COMPONENT_ABLATION_RUN_SHEET.md`
- `06_next_sprint_inputs/RMTGuard_NULL_POWER_GRID_DESIGN.md`
- `06_next_sprint_inputs/RMTGuard_REALISTIC_NULL_POWER_CALIBRATION.md`
- `06_next_sprint_inputs/RMTGuard_RARE_STATE_CLAIM_BOUNDARY.md`
- `06_next_sprint_inputs/RMTGuard_ADDED_DATASET_ANNOTATION_BOUNDARY.md`

## Manual Inputs Still Needed

1. Confirm final correspondence postal code.
2. Confirm funding statement.
3. Confirm competing interests statement.
4. Confirm ethics/public-data-use statement.
5. Confirm CRediT author roles.
6. Acknowledge that PDAC/TME remains a bounded public-data Figure 4 showcase
   using only supported pathway/atlas evidence.
7. Verify the official Nature Methods presubmission/submission route before
   sending any editor-facing inquiry.
8. Re-check JCR, CAS partition, and warning-list status immediately before
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
stability-superiority is not supported, synthetic and real-data component
ablation now have 20-repeat CI/annotation layers, realistic null and power
grids now have 50-repeat calibration output with a low-prevalence/effect
claim-boundary limitation, and the PDAC/TME biological
showcase now has DE/signature-transfer plus rank-based Hallmark/Reactome
pathway and atlas-marker support with limits; a scLENSpy `n_rand_matrix=20`
direct comparator is complete on PBMC3k and Kang but still needs broader
dataset coverage before broad superiority language; the Figure 3 no-call
decision map now has source data plus rendered PNG/PDF/TIFF assets; the Paul15
real-data topology monitor is complete with bounded trade-off wording; bounded
Figure 4 wording is frozen, and formal corresponding-author acknowledgement
remains.

## Fast Open

- Gap report: `{package_dir / "01_project_status" / "RMTGuard_JIF20_50_GAP_ASSESSMENT.md"}`
- Next-round gate board: `{package_dir / "01_project_status" / "RMTGuard_NATURE_METHODS_NEXT_ROUND_GATE_BOARD.md"}`
- Genome Biology fallback v2 packet: `{package_dir / "01_project_status" / "RMTGuard_GENOME_BIOLOGY_FALLBACK_V2_PACKET.md"}`
- Genome Biology abstract v2: `{package_dir / "01_project_status" / "RMTGuard_GENOME_BIOLOGY_ABSTRACT_V2.md"}`
- Genome Biology cover letter v2: `{package_dir / "01_project_status" / "RMTGuard_GENOME_BIOLOGY_COVER_LETTER_V2.md"}`
- 48-hour execution packet: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_NATURE_METHODS_48H_EXECUTION_PACKET.md"}`
- P0 science sprint status: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_P0_SCIENCE_SPRINT_STATUS.md"}`
- P0 benchmark upgrade status: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_P0_BENCHMARK_UPGRADE_STATUS.md"}`
- Current evidence freeze: `{package_dir / "01_project_status" / "RMTGuard_CURRENT_EVIDENCE_FREEZE.md"}`
- Current evidence freeze manifest: `{package_dir / "01_project_status" / "RMTGuard_CURRENT_EVIDENCE_FREEZE_MANIFEST.tsv"}`
- Topology stress benchmark: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_TOPOLOGY_STRESS_BENCHMARK.md"}`
- Topology stress summary: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_TOPOLOGY_STRESS_SUMMARY.tsv"}`
- Real-data topology benchmark: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_REALDATA_TOPOLOGY_BENCHMARK.md"}`
- Real-data topology summary: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_REALDATA_TOPOLOGY_SUMMARY.tsv"}`
- Real-data topology PNG: `{package_dir / "04_gantt_and_figures" / "RMTGuard_REALDATA_TOPOLOGY.png"}`
- Real-data topology PDF: `{package_dir / "04_gantt_and_figures" / "RMTGuard_REALDATA_TOPOLOGY.pdf"}`
- No-call decision-map report: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_NO_CALL_DECISION_MAP.md"}`
- No-call decision-map table: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_NO_CALL_DECISION_MAP.tsv"}`
- No-call decision-map PNG: `{package_dir / "04_gantt_and_figures" / "RMTGuard_NO_CALL_DECISION_MAP.png"}`
- No-call decision-map PDF: `{package_dir / "04_gantt_and_figures" / "RMTGuard_NO_CALL_DECISION_MAP.pdf"}`
- No-call decision-map TIFF: `{package_dir / "04_gantt_and_figures" / "RMTGuard_NO_CALL_DECISION_MAP.tiff"}`
- Figure 3 no-call source data: `{package_dir / "04_gantt_and_figures" / "RMTGuard_FIGURE3_CALLABILITY_DECISION_MAP_SOURCE_DATA.tsv"}`
- Component ablation benchmark: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_COMPONENT_ABLATION_BENCHMARK.md"}`
- Real-data ablation annotation: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_REALDATA_ABLATION_ANNOTATION.md"}`
- P0 ablation run sheet: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_P0_COMPONENT_ABLATION_RUN_SHEET.md"}`
- Null/power grid design: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_NULL_POWER_GRID_DESIGN.md"}`
- 50-repeat calibration: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_REALISTIC_NULL_POWER_CALIBRATION.md"}`
- Rare-state claim boundary: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_RARE_STATE_CLAIM_BOUNDARY.md"}`
- PDAC/TME deep validation: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_PDAC_TME_DEEP_VALIDATION.md"}`
- PDAC/TME pathway/atlas validation: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_PDAC_TME_PATHWAY_ATLAS_VALIDATION.md"}`
- PDAC/TME Figure 4 strengthening board: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_PDAC_TME_FIGURE4_STRENGTHENING_BOARD.md"}`
- Figure 4 PDAC/TME wording freeze: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_FIGURE4_PDAC_TME_WORDING_FREEZE.md"}`
- scLENSpy stability pilot: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_SCLENS_STABILITY_PILOT.md"}`
- scLENSpy versus RMTGuard pilot table: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_SCLENS_VS_RMTGUARD_STABILITY_PILOT.tsv"}`
- scLENSpy n_rand_matrix=20 report: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_SCLENS_STABILITY_NRAND20.md"}`
- scLENSpy n_rand_matrix=20 table: `{package_dir / "06_next_sprint_inputs" / "RMTGuard_SCLENS_VS_RMTGUARD_STABILITY_NRAND20.tsv"}`
- Strengthened Figure 4 caption draft: `{package_dir / "04_gantt_and_figures" / "RMTGuard_FIGURE4_CAPTION_STRENGTHENED_DRAFT.md"}`
- Strengthened Figure 4 Results draft: `{package_dir / "04_gantt_and_figures" / "RMTGuard_RESULTS_FIGURE4_STRENGTHENED_DRAFT.md"}`
- Strengthened Figure 4 text audit: `{package_dir / "04_gantt_and_figures" / "RMTGuard_FIGURE4_STRENGTHENED_TEXT_AUDIT.md"}`
- Strengthened Figure 4 PNG: `{package_dir / "04_gantt_and_figures" / "RMTGuard_FIGURE4_PDAC_TME_STRENGTHENED.png"}`
- Strengthened Figure 4 PDF: `{package_dir / "04_gantt_and_figures" / "RMTGuard_FIGURE4_PDAC_TME_STRENGTHENED.pdf"}`
- Strengthened Figure 4 source data: `{package_dir / "04_gantt_and_figures" / "RMTGuard_FIGURE4_PDAC_TME_STRENGTHENED_SOURCE_DATA.tsv"}`
- Nature Methods go/no-go packet: `{package_dir / "01_project_status" / "RMTGuard_NATURE_METHODS_GO_NO_GO_FINAL.md"}`
- Figure 4 author acknowledgement template: `{package_dir / "02_manual_actions" / "RMTGuard_CORRESPONDING_AUTHOR_FIGURE4_ACKNOWLEDGEMENT_TEMPLATE.md"}`
- Figure 4 author sign-off DOCX: `{package_dir / "02_manual_actions" / "RMTGuard_CORRESPONDING_AUTHOR_SIGNOFF_PACKET.docx"}`
- Figure 4 author sign-off email EML: `{package_dir / "02_manual_actions" / "RMTGuard_CORRESPONDING_AUTHOR_SIGNOFF_EMAIL.eml"}`
- Figure 4 author sign-off tracker: `{package_dir / "02_manual_actions" / "RMTGuard_CORRESPONDING_AUTHOR_SIGNOFF_TRACKER.tsv"}`
- Figure 4 reply intake runbook: `{package_dir / "02_manual_actions" / "RMTGuard_CORRESPONDING_AUTHOR_REPLY_INTAKE_RUNBOOK.md"}`
- Nature Methods presubmission inquiry draft: `{package_dir / "07_presubmission" / "RMTGuard_NATURE_METHODS_PRESUBMISSION_INQUIRY_DRAFT.md"}`
- Freeze-aligned Results draft: `{package_dir / "07_presubmission" / "RMTGuard_RESULTS_FREEZE_ALIGNED_DRAFT.md"}`
- Freeze-aligned figure legends draft: `{package_dir / "07_presubmission" / "RMTGuard_FIGURE_LEGENDS_FREEZE_ALIGNED.md"}`
- Freeze-aligned text audit: `{package_dir / "07_presubmission" / "RMTGuard_FREEZE_ALIGNED_TEXT_AUDIT.tsv"}`
- External review Word packet: `{package_dir / "07_presubmission" / "RMTGuard_EXTERNAL_REVIEW_PACKET_2026-05-12.docx"}`
- Nature reporting-summary worksheet: `{package_dir / "07_presubmission" / "RMTGuard_NATURE_REPORTING_SUMMARY_DRAFT.md"}`
- Figure-caption-source audit: `{package_dir / "04_gantt_and_figures" / "RMTGuard_FIGURE_CAPTION_SOURCE_AUDIT.md"}`
- Post-release version coverage audit: `{package_dir / "03_release_evidence" / "RMTGuard_POST_RELEASE_VERSION_COVERAGE_AUDIT.md"}`
- v0.1.1 release preflight: `{package_dir / "03_release_evidence" / "RMTGuard_V0_1_1_RELEASE_PREFLIGHT.md"}`
- Nature Methods presubmission send packet: `{package_dir / "07_presubmission" / "RMTGuard_NATURE_METHODS_PRESUBMISSION_SEND_PACKET.md"}`
- Nature Methods presubmission send runbook: `{package_dir / "07_presubmission" / "RMTGuard_NATURE_METHODS_PRESUBMISSION_SEND_RUNBOOK.md"}`
- Nature Methods official route verification: `{package_dir / "07_presubmission" / "RMTGuard_NATURE_METHODS_OFFICIAL_ROUTE_VERIFICATION.md"}`
- Nature Methods presubmission HOLD email: `{package_dir / "07_presubmission" / "RMTGuard_NATURE_METHODS_PRESUBMISSION_INQUIRY_HOLD.eml"}`
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
