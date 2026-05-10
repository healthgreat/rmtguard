# RMTGuard Email Draft Outputs

This folder contains local `.eml` drafts. These files are not sent by scripts.

## Files

- `RMTGuard_corresponding_author_signoff_email.eml`: send this first to request
  Figure 4 bounded-wording acknowledgement from Yi Miao and Han Yan.
- `RMTGuard_nature_methods_presubmission_inquiry_HOLD.eml`: locked Nature
  Methods presubmission draft. Do not send while the send packet reports a
  `hold_*` status.

## Boundary

The Nature Methods HOLD draft intentionally has no recipient because the
official submission/presubmission route must be verified manually immediately
before sending.

## Regenerate

```bash
python scripts/build_corresponding_author_email_packet.py
python scripts/build_nature_methods_presubmission_send_packet.py
```
