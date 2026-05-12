# RMTGuard Email Draft Outputs

This folder contains local `.eml` drafts. These files are not sent by scripts.

## Files

- `RMTGuard_author_declaration_confirmation_email.eml`: request final author
  confirmation for title-page metadata, CRediT, funding, competing interests,
  public-data ethics, reporting summary, and bounded Figure 4 wording.
- `RMTGuard_corresponding_author_signoff_email.eml`: narrower Figure 4
  bounded-wording acknowledgement email for Yi Miao and Han Yan.
- `RMTGuard_nature_methods_presubmission_inquiry_HOLD.eml`: locked Nature
  Methods presubmission draft. Do not send while the send packet reports a
  `hold_*` status.

## Boundary

The author-declaration and corresponding-author sign-off emails can be used
only to request author acknowledgement. The Nature Methods HOLD draft
intentionally has no recipient because the official route must be verified
manually immediately before sending.

## Regenerate

```bash
python scripts/build_author_declaration_email_packet.py
python scripts/build_corresponding_author_email_packet.py
python scripts/build_nature_methods_presubmission_send_packet.py
```
