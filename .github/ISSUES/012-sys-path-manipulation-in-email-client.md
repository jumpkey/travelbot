# Issue 012: sys.path manipulation instead of relative import in email_client.py

**Priority:** High
**Category:** Correctness
**Status:** Fixed (branch `claude/review-code-docs-GEwGy`)
**Location:** `travelbot/email_client.py:813-815`

## Fix Applied
- Replaced three-line `sys.path.append` + absolute import with a single relative import: `from .pdf_processor import extract_text_from_pdf`
- The import is now inside `get_complete_email_content()` at the point of use (lazy import), consistent with the existing try/except error handling around PDF extraction

## Problem

Inside `get_complete_email_content()`, the code uses `sys.path.append` and an absolute import instead of a relative import to access `pdf_processor`:

```python
import sys
sys.path.append(os.path.dirname(__file__))
from pdf_processor import extract_text_from_pdf
```

This should be a relative import (`from .pdf_processor import extract_text_from_pdf`), which is already the pattern used in `__init__.py`.

## Impact

- `sys.path.append` is cumulative: every email processed adds a duplicate entry to `sys.path`, creating a minor memory leak in the long-running daemon
- Can cause subtle import conflicts if another module named `pdf_processor` exists elsewhere on the path
- Violates Python packaging conventions for intra-package imports

## Root Cause

The import was likely written before the module was organized as a proper package with `__init__.py`, and was not updated when the package structure was established.

## Suggested Fix

Replace the three lines with a single relative import at the top of `email_client.py`:

```python
from .pdf_processor import extract_text_from_pdf
```

Remove the `sys.path.append` and local `import sys` from `get_complete_email_content()`.

## Acceptance Criteria

- [x] `pdf_processor` is imported via relative import
- [x] No `sys.path.append` calls remain in `email_client.py`
- [x] PDF extraction still works correctly (existing tests pass)
