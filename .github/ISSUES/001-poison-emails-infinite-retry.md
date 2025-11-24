# Issue 001: Poison emails cause infinite retry loops

**Priority:** Critical  
**Category:** Reliability  
**Status:** Open  
**Location:** `travelbot/daemon.py:708-763`

## Problem

When `process_single_email` fails for any reason (LLM error, JSON parse failure, SMTP failure), the email is NOT marked as seen. The daemon will reprocess the same failing email on every polling cycle indefinitely.

## Impact

- Burns API costs on repeated LLM calls for the same failing email
- Can trigger Azure OpenAI rate limits, affecting processing of other emails
- User never receives a response for the problematic email
- A single "poison" email can degrade system performance for all users

## Root Cause

Only the success path marks emails as seen (`mark_emails_as_seen([email_uid])` at line 744). Any exception in:
- PDF extraction
- LLM call
- JSON parsing
- ICS generation
- SMTP send

...causes `process_single_email` to return `False` without marking the message as seen.

## Suggested Fix

1. Track failures per UID (in memory or via IMAP flags)
2. After N failed attempts, stop retrying:
   - Mark as seen and move to a "TravelBot-Failed" folder for manual review
   - Or mark with a custom flag and skip flagged UIDs on future passes
3. Distinguish transient vs permanent errors:
   - **Transient:** network timeouts, 5xx from Azure, temporary SMTP issues - back off and retry with a cap
   - **Permanent:** JSON parse failures after retries, unsupported file types - send fallback email and mark as seen

## Acceptance Criteria

- [ ] Failed emails are not retried indefinitely
- [ ] After N failures, email is marked as processed (seen or moved)
- [ ] User receives some response (even if just "we couldn't process this")
- [ ] Transient errors are retried with backoff
- [ ] Permanent errors trigger fallback behavior
