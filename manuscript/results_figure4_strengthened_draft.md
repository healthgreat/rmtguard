# Results Draft: Figure 4 Strengthened PDAC/TME Application

Generated: 2026-05-11

## Bounded PDAC/TME Application

We next used public PDAC/TME scRNA-seq datasets as a bounded biological
application of RMTGuard. This analysis was designed to test whether callable
RMTGuard clusters could be interpreted with marker, pathway, external-signature,
and atlas-marker evidence, not to establish a new PDAC mechanism or clinical
biomarker.

FDR-controlled marker testing identified 9802 positive
cluster-marker rows at BH-FDR <=0.05, while 3 tiny clusters were skipped
by the pre-specified rule. Marker-score summaries separated interpretable
ductal/malignant-context, immune-myeloid, T/NK, B/plasma, CAF/fibroblast, and
endothelial programs across GSE154778 and GSE263733, supporting Figure 4 as a
cell-state interpretability showcase.

External-signature transfer provided additional public-data support but also
retained non-transferring cases as boundary evidence. In the external validation
layer, 5 primary signatures matched expected public labels,
4 matched validation RMTGuard cluster signatures, and the
shared top marker families were ductal/malignant-context, immune-myeloid. This supports selected ductal and
myeloid marker families as reproducible public-data signatures, while it does
not support a clinical-validation or mechanism-discovery claim.

The pathway and atlas-marker layers were used to add biological context without
overstating causality. Rank-based testing identified 189 Hallmark and
1466 Reactome rows at BH-FDR <=0.05 with positive rank effect, of which
215 were retained as manuscript-interpretable after excluding
low-specificity labels. Representative pathway examples included HALLMARK_EPITHELIAL_MESENCHYMAL_TRANSITION in ductal/malignant-context (-log10 BH-FDR=25.21); REACTOME_CYTOKINE_SIGNALING_IN_IMMUNE_SYSTEM in T/NK (-log10 BH-FDR=23.88); HALLMARK_TNFA_SIGNALING_VIA_NFKB in immune-myeloid (-log10 BH-FDR=19.67).
Published atlas-marker comparison identified 7 cluster-signature rows
with at least two marker overlaps, including GSE154778 cluster 3 immune-myeloid (10 markers, Peng et al., Cell Research 2019); GSE263733 cluster 2 immune-myeloid (10 markers, Peng et al., Cell Research 2019); GSE263733 cluster 0 T/NK (9 markers, Oh et al., Nature Communications 2023). These results are
consistent with public PDAC/TME marker and pathway programs.

Importantly, the PDAC/TME application is not presented as a stability-superiority
result. Subsampling stability was reported as a boundary rather than a superiority claim: GSE154778 RMTGuard mean pairwise ARI=0.619 versus the strongest baseline scanpy_default_like=0.793, and GSE263733 RMTGuard mean pairwise ARI=0.704 versus scanpy_default_like=0.785. We therefore use Figure 4 to demonstrate a
transparent, source-data-backed biological application with explicit boundaries:
no new PDAC mechanism, no new CAF subtype, no prognosis or therapy-response
claim, no patient-level clinical utility, and no spatial or protein validation
is claimed from the current evidence package.
