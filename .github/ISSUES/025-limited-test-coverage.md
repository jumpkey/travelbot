# Issue 025: Test coverage limited to single module

**Priority:** Low
**Category:** Reliability
**Status:** Open
**Location:** `tests/`

## Problem

Only `auto_reply_filter.py` has tests (`tests/test_auto_reply_filter.py`, 409 lines, 30+ test cases). The following core modules have no test coverage:

1. **`daemon.py`** (1,242 lines) - Main processing logic, LLM integration, email sending, poison email handling
2. **`email_client.py`** (849 lines) - IMAP operations, PDF downloading, email body extraction, IDLE support
3. **`pdf_processor.py`** (48 lines) - PDF text extraction

## Impact

- Core processing logic is untested; regressions in email handling, LLM interaction, or ICS generation would not be caught
- No automated validation of the 10 reliability fixes (Issues 001-010)
- Refactoring carries higher risk without test safety net

## Root Cause

Tests were only added for the auto-reply filter (Issue 010) as part of that specific feature. Testing the daemon and email client requires mocking external services (IMAP, SMTP, Azure OpenAI) which adds complexity.

## Suggested Fix

Add tests for critical paths with appropriate mocking:
1. `test_daemon.py`: JSON extraction, poison email tracking, reply address determination, ICS validation
2. `test_email_client.py`: Email body extraction (HTML preference, deduplication), RFC2047 header decoding, PDF size enforcement
3. `test_pdf_processor.py`: Basic PDF extraction, error handling for missing/corrupt files

## Acceptance Criteria

- [ ] Tests exist for `_extract_json_from_llm_response` (various input formats)
- [ ] Tests exist for `_record_email_failure` / poison email logic
- [ ] Tests exist for `determine_reply_address` (do-not-reply, forwarded, normal)
- [ ] Tests exist for `extract_email_body` (HTML preference, plain text fallback)
- [ ] Tests exist for `_decode_email_header` (RFC2047 encoded headers)
