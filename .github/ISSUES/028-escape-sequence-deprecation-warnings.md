# Issue 028: Invalid escape sequence DeprecationWarnings in email_client.py

**Priority:** Low
**Category:** Code Quality
**Status:** Fixed (branch `claude/review-code-docs-GEwGy`)
**Location:** `travelbot/email_client.py:334,337`

## Fix Applied
- Changed `'(\Seen)'` to `r'(\Seen)'` (raw strings) in `mark_emails_as_seen` and `mark_emails_as_unseen`
- Eliminates 2 DeprecationWarnings about invalid escape sequence `\S`

## Problem

The `mark_emails_as_seen()` and `mark_emails_as_unseen()` methods pass `'(\Seen)'` as a string argument. Python interprets `\S` as an invalid escape sequence and emits a DeprecationWarning. In future Python versions this will become a SyntaxError.

## Impact

- 2 DeprecationWarnings on every test run and during daemon operation
- Will break in future Python versions when invalid escape sequences become errors

## Acceptance Criteria

- [x] No DeprecationWarnings related to escape sequences
- [x] IMAP flag operations still work correctly
