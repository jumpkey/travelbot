# Issue 013: API docs show wrong return type for search_emails

**Priority:** High
**Category:** Documentation
**Status:** Fixed (branch `claude/review-code-docs-GEwGy`)
**Location:** `docs/api.md:127-132`

## Fix Applied
- Updated `search_emails` docs to show correct `dict` return type with `success`, `uids`, and `error` fields
- Updated `get_complete_email_content` signature to include `max_pdf_size_mb` parameter
- Updated Email Content Dictionary to include `pdf_filepaths` (list) field
- Updated LLM Response Structure to include `message_type` and `message_type_reason` fields
- Fixed PyPDF2 reference to pdfplumber in External Dependencies section

## Problem

The API documentation states that `search_emails(criteria)` returns `list` (a list of email UIDs), but the actual implementation returns a `dict` with structured response format:

```python
{'success': bool, 'uids': list, 'error': str|None}
```

This was changed during the structured response refactoring but the docs were not updated.

## Impact

- Any external integrator following the API docs will encounter `TypeError` when trying to iterate over the result
- Internal consumers (e.g., `search_for_unread_emails` in daemon.py) already handle both formats with fallback logic, but new code written against the docs will break

## Root Cause

The `search_emails` method was refactored to return structured dicts for better error handling, but `docs/api.md` was not updated to reflect the new return type.

## Suggested Fix

Update `docs/api.md` to document the actual return type:

```python
Returns: dict - {'success': bool, 'uids': list[str], 'error': str|None}
```

Also update the `get_complete_email_content` signature docs to include the `max_pdf_size_mb` parameter.

## Acceptance Criteria

- [x] `search_emails` return type is correctly documented as `dict`
- [x] Dict fields (`success`, `uids`, `error`) are documented
- [x] Example code in docs uses the correct return type
