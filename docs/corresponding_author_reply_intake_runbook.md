# Corresponding Author Reply Intake Runbook

Generated for the RMTGuard Nature Methods presubmission route.

## Purpose

This runbook records exactly how to process replies from Yi Miao and Han Yan
after the Figure 4 sign-off email is sent. It prevents accidental manual
editing of the go/no-go state.

## Current Gate

- Full Nature Methods submission: `NO-GO`.
- Nature Methods presubmission inquiry: `conditional go after both
  corresponding authors confirm the bounded Figure 4 wording`.
- Current tracker: `metadata/corresponding_author_signoff_tracker.tsv`.

## What Counts As Confirmation

Only mark an author as `confirmed` if the reply explicitly accepts this
boundary:

> Figure 4 will be presented only as a bounded public-data PDAC/TME showcase of
> RMTGuard callability, not as a new PDAC mechanism, CAF discovery, prognosis,
> therapy-response, clinical-validation, or patient-level claim.

Do not mark `confirmed` if the reply asks to describe Figure 4 as a new
mechanism, clinical validation, prognosis, therapy response, patient-level
finding, or standalone CAF discovery.

## Save Reply Evidence

Save each author reply or signed confirmation as a file, for example:

```text
metadata/author_reply_evidence/yi_miao_figure4_confirmation_YYYYMMDD.eml
metadata/author_reply_evidence/han_yan_figure4_confirmation_YYYYMMDD.eml
```

The evidence file can be a saved `.eml`, `.pdf`, `.docx`, `.txt`, or `.md`.

## Record A Confirmation

After saving the evidence file, run:

```bash
python scripts/record_corresponding_author_signoff.py \
  --author-email miaoyi@njmu.edu.cn \
  --status confirmed \
  --evidence-path metadata/author_reply_evidence/yi_miao_figure4_confirmation_YYYYMMDD.eml \
  --notes "Confirmed bounded Figure 4 wording by email."
```

For Han Yan:

```bash
python scripts/record_corresponding_author_signoff.py \
  --author-email carrick8862@163.com \
  --status confirmed \
  --evidence-path metadata/author_reply_evidence/han_yan_figure4_confirmation_YYYYMMDD.eml \
  --notes "Confirmed bounded Figure 4 wording by email."
```

The script automatically refreshes:

- `docs/corresponding_author_signoff_tracker.md`
- `docs/nature_methods_go_no_go_final.md`
- `D:\99、共用信息\RMTGuard_20_50投稿资料包`

## Record A Revision Request

If an author requests wording changes, run:

```bash
python scripts/record_corresponding_author_signoff.py \
  --author-email miaoyi@njmu.edu.cn \
  --status needs_revision \
  --evidence-path metadata/author_reply_evidence/yi_miao_figure4_revision_request_YYYYMMDD.eml \
  --notes "Author requested Figure 4 wording revision."
```

Then do not send the Nature Methods presubmission inquiry until the revised
wording passes claim-boundary lint and the author later confirms it.

## Dry Run

Use `--dry-run` to validate the command without changing the tracker:

```bash
python scripts/record_corresponding_author_signoff.py \
  --author-email miaoyi@njmu.edu.cn \
  --status pending_author_reply \
  --dry-run
```

## Final Check

After both authors are marked `confirmed`, rerun:

```bash
python scripts/build_nature_methods_go_no_go_final.py
python scripts/lint_claim_boundaries.py
python scripts/validate_claim_traceability.py
```

Proceed only if:

- `docs/nature_methods_go_no_go_final.md` reports corresponding-author
  acknowledgement as `all_confirmed`.
- claim-boundary lint has `violations 0`.
- claim traceability has `violations 0`.
