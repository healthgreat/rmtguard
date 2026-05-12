# Freeze-aligned Results draft



Generated: 2026-05-12



Status: draft text for manuscript assembly; not a submission-ready final Results section.



## RMTGuard implements a diagnostic random-matrix callability workflow



RMTGuard was evaluated as a callability-aware random-matrix workflow rather than as a universal replacement for fixed-parameter single-cell analysis. The current evidence freeze contains 23 manuscript-facing items with 0 missing files, linking algorithm figures, source-data tables, release evidence, public benchmarks, topology monitors and manual author blockers. This freeze defines the Results boundary used below: supported structures may be reported, but diagnostic no-call and caveated-call outcomes are not relabelled as biological discoveries. [Evidence: docs/current_evidence_freeze_2026-05-12.md]



## Null and rare-state calibration support bounded noise-control claims



Across 50-repeat realistic null experiments covering gene_permutation_null, library_multinomial_null, library_stratified_gene_null, the maximum observed false-signal rate was 0%. These results support a bounded false-signal-control claim under the tested count-preserving null families, not universal type-I-error calibration for every scRNA-seq preprocessing regime. [Evidence: results/calibration/realistic_null_summary.tsv]

Rare-state simulations also showed a clear operating boundary. Power was high in the tested prevalence 0.02 setting only at effect size 6.0, and all tested prevalence >=0.04 settings had power at least 84%; the weakest setting, prevalence 0.02 and effect size 2.5, had power 12% and mean rare-state F1 0.151. The manuscript should therefore describe rare-state retention as supported for tested moderate settings and explicitly limited in the lowest-prevalence, weak-effect regime. [Evidence: results/calibration/rare_state_power_summary.tsv]



## Public benchmarks support callability and caveat reporting, not broad superiority



The callability decision map classified the current benchmark rows as 2 diagnostic no-call rows, 3 caveated real-data calls, 2 synthetic positive-control passes and 4 stress-monitor rows. PBMC68k/Zheng 2017 was kept as a diagnostic no-call with annotation ARI 0.081 and stability gap 0.206, whereas PBMC3k, Kang IFN-beta PBMC and Baron pancreas were retained only as caveated benchmark contexts. [Evidence: results/callability/no_call_decision_map.tsv]

Specifically, PBMC3k showed RMTGuard stability 0.891 with a gap of 0.095 to the strongest comparator; Kang IFN-beta PBMC showed annotation ARI 0.785 and stability gap 0.054; Baron pancreas showed annotation ARI 0.752 and stability gap 0.121. These results support transparent reporting of when RMTGuard proceeds and when it refuses or caveats a result, but they do not support a statement that RMTGuard is always more stable than elbow or fixed-PC workflows. [Evidence: results/callability/no_call_decision_map.tsv]

A direct scLENSpy comparison reduced the risk that the work lacks an RMT-like comparator. In 10-repeat subsampling, RMTGuard mean pairwise ARI was 0.867 on PBMC3k and 0.789 on Kang IFN-beta PBMC, compared with scLENSpy n_rand_matrix=20 values of 0.694 and 0.586, respectively. This comparison is limited to the tested Python scLENSpy configuration and two datasets. [Evidence: results/submission/sclens_vs_rmtguard_stability_nrand20.tsv]



## Topology benchmarks show monitored geometry preservation with real-data trade-offs



Synthetic CONCORD-style topology stress tests showed that RMTGuard preserved line, branch and loop geometry under the tested simulations (branching_trajectory: trustworthiness 0.924, continuity 0.881, kNN recall 0.301; cyclic_loop: trustworthiness 0.951, continuity 0.933, kNN recall 0.422; linear_trajectory: trustworthiness 0.933, continuity 0.881, kNN recall 0.301). These simulations support topology monitoring as part of the benchmark arc, but they do not establish RMTGuard as a dedicated trajectory-inference method. [Evidence: results/submission/topology_stress_summary.tsv]

On Paul15 hematopoiesis, an annotation-derived real-data topology monitor showed a mixed trade-off. RMTGuard had higher annotation ARI (0.270) than fixed 30 PCs (0.176) and fixed 50 PCs (0.088), and lower neighbor tree distance (1.153) than fixed 30 PCs (1.289) and fixed 50 PCs (1.435). However, fixed-PC baselines had higher centroid tree rho (0.246 and 0.236) than RMTGuard (0.232), and fixed 50 PCs had the highest reference edge recall (0.650 versus 0.600 for RMTGuard). This figure should be presented as a real-data topology monitor with explicit trade-offs, not as broad topology superiority. [Evidence: results/submission/realdata_topology_summary.tsv]



## PDAC/TME application and ablation evidence remain bounded



The PDAC/TME analysis is retained as a public-data application that connects RMTGuard-selected structures to marker, pathway and atlas-context evidence. It should be described as a bounded methods-paper showcase and not as a new PDAC mechanism, prognosis marker, therapy-response model, spatial validation or protein-level validation. [Evidence: docs/figure4_pdac_tme_wording_freeze.md; results/figures/source_data/figure4_pdac_tme_strengthened_source.tsv]

Component ablation and real-data annotation checks support discussion of the tested RMTGuard modules, but the manuscript should avoid universal component-necessity language. The correct wording is that MP/TW-style edge checks, near-edge stability, no-call logic and related safeguards contributed under the benchmark settings captured in the current source data. [Evidence: docs/component_ablation_benchmark.md; docs/realdata_ablation_annotation.md]
