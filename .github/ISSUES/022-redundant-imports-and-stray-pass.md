# Issue 022: Redundant local imports and stray pass statement

**Priority:** Low
**Category:** Code Quality
**Status:** Open
**Location:** `travelbot/daemon.py:179,205,295`, `travelbot/email_client.py:849`

## Problem

### Redundant local imports in daemon.py

`time` is imported at module level (line 18) but is re-imported locally inside methods:
- Line 179: `import time` inside `check_and_process_emails()`
- Line 145: `import time` inside `search_emails()` in `email_client.py`

`traceback` is imported locally in multiple methods (lines 205, 295, etc.) instead of once at the top of the file.

### Stray pass statement in email_client.py

Line 849 has a bare `pass` statement at module level that serves no purpose.

## Impact

- Minor code clutter and inconsistency
- Slightly confusing for developers reading the code (suggests the imports might not be available at module level)

## Root Cause

Local imports were likely added during debugging or incremental development and not cleaned up. The `pass` statement may be left over from a class or function that was removed.

## Suggested Fix

1. Remove redundant local `import time` statements (already imported at module level)
2. Add `import traceback` at the top of `daemon.py` and remove all local imports
3. Remove the stray `pass` at `email_client.py:849`

## Acceptance Criteria

- [ ] No redundant local imports of modules already imported at module level
- [ ] `traceback` imported once at module level if used
- [ ] No stray `pass` statements at module level
