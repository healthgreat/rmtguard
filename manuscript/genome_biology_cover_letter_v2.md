# Genome Biology Cover Letter v2

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

https://github.com/healthgreat/rmtguard

Archive identifier metadata currently records 10.5281/zenodo.20012350, but the exact submitted commit
must be archived again if it differs from the currently archived tagged
release. Current release check: `release_refresh_required` (Current commit is v0.1.0-28-gcd949fb, after archived v0.1.0; make a new GitHub/Zenodo archive for the submitted version.).

We believe this controlled framing will be useful to Genome Biology readers who
need transparent single-cell workflows that report supported structure,
diagnostic no-calls, and benchmark limitations in a reusable software package.

Sincerely,

[TO CONFIRM: corresponding author]
