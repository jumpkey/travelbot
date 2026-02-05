# Issue 014: API docs reference PyPDF2 instead of pdfplumber

**Priority:** Medium
**Category:** Documentation
**Status:** Open
**Location:** `docs/api.md:371`

## Problem

The "External Dependencies" section of the API documentation lists:

```python
import PyPDF2          # PDF text extraction
```

However, the codebase uses `pdfplumber` for PDF text extraction (see `pdf_processor.py:1` and `requirements.txt:1`). `PyPDF2` is not a dependency and is never used.

## Impact

- Developers may install PyPDF2 unnecessarily
- Confusion about which library is actually used for PDF processing
- Misalignment between docs and `requirements.txt`

## Root Cause

Documentation was likely written from memory or an earlier version of the code that used PyPDF2, and was not verified against the actual imports.

## Suggested Fix

Replace `import PyPDF2  # PDF text extraction` with `import pdfplumber  # PDF text extraction` in `docs/api.md`.

## Acceptance Criteria

- [ ] API docs reference `pdfplumber`, not `PyPDF2`
- [ ] All dependency references in docs match `requirements.txt`
