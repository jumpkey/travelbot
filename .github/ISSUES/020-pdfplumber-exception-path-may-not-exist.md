# Issue 020: pdfplumber exception class path may not exist

**Priority:** Medium
**Category:** Correctness
**Status:** Open
**Location:** `travelbot/pdf_processor.py:39`

## Problem

The PDF processor catches a specific exception:

```python
except pdfplumber.utils.exceptions.PdfminerException as e_pdf_related:
```

The module path `pdfplumber.utils.exceptions.PdfminerException` is version-dependent and may not exist in all versions of pdfplumber. If the path is invalid, this handler is dead code and PDF-specific errors fall through to the generic `Exception` catch on line 42.

## Impact

- If the exception path doesn't exist in the installed version, importing or running the code could raise `AttributeError`
- Even if it doesn't error at import time (since it's in a handler), the specific exception will never be caught, removing the distinction between PDF errors and other errors

## Root Cause

The exception class path was written for a specific version of pdfplumber and may not be stable across versions. The `pdfplumber` library's internal exception hierarchy has changed between releases.

## Suggested Fix

1. Test whether the exception class exists at import time:
   ```python
   try:
       from pdfplumber.utils.exceptions import PdfminerException
   except ImportError:
       PdfminerException = Exception  # fallback
   ```
2. Or use a broader exception type that is guaranteed to exist across versions

## Acceptance Criteria

- [ ] PDF-specific exceptions are caught reliably across pdfplumber versions
- [ ] No `AttributeError` when running with different pdfplumber versions
- [ ] Error messages still distinguish between PDF errors and other errors
