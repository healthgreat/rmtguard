# Freeze-aligned figure legends draft



Generated: 2026-05-12



Status: draft legends for manuscript assembly; not final journal artwork captions.



## Figure 1. RMTGuard random-matrix callability workflow.

Schematic and diagnostic outputs for the RMTGuard workflow. The method uses random-matrix spectral diagnostics, adaptive embedding decisions and explicit callability outputs to separate supported signal from high-dimensional noise. This figure should be read as a workflow and diagnostic overview, not as a claim of new random-matrix theory. Source data: `results/figures/source_data/figure1_algorithm_diagnostics.tsv`.



## Figure 2. Synthetic calibration of false-signal and rare-state behavior.

Synthetic null, planted-signal and rare-state scenarios evaluate whether the workflow controls false signal under tested null families while retaining detectable rare states. Realistic null simulations covered gene-permutation, library-multinomial and library-stratified gene nulls; the maximum observed false-signal rate in the current 50-repeat summary was 0%. Rare-state power is claim-bounded: moderate prevalence/effect regimes are supported, whereas prevalence 0.02/effect size 2.5 remains weak. Source data: `results/calibration/realistic_null_summary.tsv` and `results/calibration/rare_state_power_summary.tsv`.



## Figure 3. Public benchmark callability, caveats and no-call decisions.

Public benchmark panels report RMTGuard performance alongside fixed-PC, elbow, Scanpy-like, Seurat and scLENSpy comparators where available. The callability map includes PBMC68k/Zheng 2017 as a diagnostic no-call (annotation ARI 0.081), not a biological discovery. PBMC3k, Kang IFN-beta PBMC and Baron pancreas are retained as caveated benchmark contexts. The legend must not state that RMTGuard outperforms all fixed-PC or elbow baselines. Source data: `results/callability/no_call_decision_map.tsv`, `results/submission/sclens_vs_rmtguard_stability_nrand20.tsv` and related Figure 3 source-data tables.



## Figure 4. Bounded PDAC/TME public-data application.

RMTGuard is applied to public PDAC/TME datasets to illustrate marker, pathway and atlas-context interpretation under the current callability framework. The figure supports a methods-paper use case only. It does not establish a new PDAC mechanism, clinical biomarker, prognosis model, therapy-response predictor, spatial validation or protein-level validation. Source data: `results/figures/source_data/figure4_pdac_tme_strengthened_source.tsv`.



## Figure 5. Ablation, reproducibility and release readiness.

Main Figure 5 summarizes runtime, memory, submission-gate status and the PBMC3k stability-ablation panel used for software/reproducibility reporting. The public repository, GitHub Release and Zenodo DOI support code availability for the archived release, while post-release working-branch changes should not be described as part of the immutable DOI snapshot unless a new release is issued. Source data: `results/figures/source_data/figure5_runtime_memory_summary.tsv`, `results/figures/source_data/figure5_gate_evidence.tsv`, `results/figures/source_data/figure5_ablation_stability_summary.tsv` and release manifests.



## Extended Data Figure. Real-data ablation annotation monitor.

The real-data ablation forest plot summarizes annotation-ARI and batch-ARI deltas for tested RMTGuard component variants across labeled public datasets. This panel supports component-sensitivity discussion under the tested datasets and repeats, but it should not be described as proving universal component necessity. Source data: `results/figures/source_data/figure5_realdata_ablation_delta_summary.tsv`.



## Extended Data Figure. Topology stress and Paul15 real-data topology monitor.

Synthetic topology stress tests evaluate line, branch and loop geometry (branching_trajectory, trustworthiness 0.924; cyclic_loop, trustworthiness 0.951; linear_trajectory, trustworthiness 0.933). The Paul15 hematopoiesis monitor uses an annotation-derived cluster graph rather than experimentally measured pseudotime. RMTGuard had higher annotation ARI (0.270) and lower neighbor tree distance (1.153) than fixed 30 PCs (1.289) and fixed 50 PCs (1.435), but fixed-PC baselines had higher centroid tree rho/reference edge recall. This extended figure should therefore be described as topology monitoring with trade-offs, not as trajectory-method superiority. Source data: `results/submission/topology_stress_summary.tsv` and `results/submission/realdata_topology_summary.tsv`.
