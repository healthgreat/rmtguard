# Nature Methods Presubmission Draft

Status: not submission-ready. This draft is generated from local benchmark evidence and must not be submitted until the software-release blockers are resolved.

## Working Title

RMTGuard: random-matrix noise control for reproducible single-cell cell-state discovery

## Current Decision

- Gate recommendation: `continue_benchmarking`
- Nature Methods route: `not ready`
- Genome Biology fallback: `not ready until software_release is complete`

## Central Claim

Random-matrix noise control can reduce subjective parameter choices in scRNA-seq cell-state discovery while preserving interpretable biological structure.

This claim is currently supported only within the benchmark scope listed below. It should be written as callability-aware noise control, not broad superiority over every fixed-PC workflow.

## Evidence That Can Be Used

- `noise_control_null` (pass): Pure-null benchmark retained 1 signal PC(s), satisfying the pre-specified <=1 criterion.
- `diagnostic_no_call_validation` (pass): Diagnostic no-call validation passed 3/3 hard scenarios; pure-null status=diagnostic_no_call reason=insufficient_signal_pcs_for_embedding.
- `rare_state_retention` (pass): Rare-state synthetic ARI reached 0.9234648221808079.
- `public_benchmark_breadth` (pass): 4 real datasets are present: baron_pancreas, kang_ifnb_pbmc, pbmc3k_10x, pbmc68k_zheng2017.
- `annotation_noninferiority` (pass): Kang ARI RMTGuard=0.7846371079756893 vs fixed30=0.6806962449348877; Baron ARI RMTGuard=0.7521329786400153 vs fixed30=0.7966821335853982; PBMC68k absolute ARI remains weak.
- `pdac_tme_showcase` (pass): GSE154778 signatures: ['ductal_malignant_context', 'immune_myeloid']; GSE263733 validation ARI=0.5680419676901498, NMI=0.6866858928242938.
- `figure_source_data` (pass): Figure source-data and draft render manifests exist for Figures 1-5.

## Claims That Must Stay Guarded

- `pbmc3k_stability` (fail): Do not claim RMTGuard outperforms fixed-PC baselines on every dataset or that PBMC68k yields a positive cell-state discovery.
- `software_release` (pending): Do not state that code is DOI-archived or fully released before the external release exists.

## Blocking Items

- `Nature Methods gate decision` (blocked): Resolve software_release pending before submission.
- `Callability-aware stability/no-call` (fail): Keep wording callability-aware and do not claim broad fixed-PC superiority.
- `Software release` (pending): Requires real GitHub Release and Zenodo DOI.

## Draft Results Narrative

### 1. RMTGuard defines a noise-control contract for scRNA-seq embeddings

The method estimates a random-matrix null spectrum after preprocessing and uses the MP edge, finite-sample edge checks, permutation calibration where enabled, HVG spectral plateau diagnostics, and near-edge PC stability to decide which structure is allowed into downstream embedding and graph construction.

### 2. Synthetic stress tests support false-signal control and rare-state retention

The current synthetic benchmark passes the pure-null false-signal criterion and retains the planted rare-state signal. The text should state the simulated assumptions and avoid claiming exact calibration outside the tested settings.

### 3. Public benchmarks support a callability-aware stability/no-call claim

Four public real datasets are present in Phase 1. RMTGuard exceeds all non-RMTGuard baselines on Kang IFN-beta PBMC, is close to fixed `n_pcs=30` on Baron pancreas and PBMC3k, and returns diagnostic no-call on PBMC68k/Zheng 2017 where the strongest stable comparator also has weak annotation recovery. This should be presented as callability-aware noise control, not as a claim that RMTGuard beats fixed-PC baselines on every dataset.

### 4. PDAC/TME is a public biological use case, not a disease-mechanism claim

GSE154778 and GSE263733 currently support immune and ductal-context marker structure with external validation. The manuscript must not describe this as a standalone CAF or fibroblast-state discovery without stronger evidence.

### 5. Software release is the remaining hard external blocker

Local release manifests, checksums, staging plans, and figure source data exist. A local release tag exists, but the software-release gate remains pending until a real GitHub repository, GitHub Release, and Zenodo DOI exist.

## Manuscript Decision Boundary

Use this draft for internal manuscript assembly only. Nature Methods submission should wait until `software_release` is pass and the final text preserves the callability-aware stability/no-call boundary. If reviewers reject the no-call framing as insufficient methodological advance, reframe to Genome Biology or lower.
