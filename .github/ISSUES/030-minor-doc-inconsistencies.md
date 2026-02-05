# Issue 030: Minor documentation inconsistencies

**Priority:** Low
**Category:** Documentation
**Status:** Fixed (branch `claude/review-code-docs-GEwGy`)
**Location:** `README.md:60-79`, `docs/api.md:14`

## Fix Applied
- Added `auto_reply_filter.py` to README project structure listing
- Added `verbose` parameter to api.md constructor example
- Moved `import time` from `ReplyRateLimiter.__init__` to module level in `auto_reply_filter.py`

## Problem

1. README project structure omitted `auto_reply_filter.py` from the file listing
2. api.md constructor usage example didn't include the `verbose` parameter (though it was documented in the parameter list)
3. `auto_reply_filter.py` had `import time` inside `ReplyRateLimiter.__init__` instead of at module level

## Acceptance Criteria

- [x] README project structure lists all source files
- [x] API docs constructor example matches actual signature
- [x] No local imports of modules that should be at module level
