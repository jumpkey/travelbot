# Issue 019: Bare except clauses suppress all exceptions

**Priority:** Medium
**Category:** Correctness
**Status:** Fixed (branch `claude/review-code-docs-GEwGy`)
**Location:** `travelbot/daemon.py:218`, `travelbot/email_client.py:209`

## Fix Applied
- Replaced `except:` with `except Exception:` in `daemon.py` (`fallback_to_polling`)
- Replaced `except:` with `except Exception:` in `email_client.py` (`_reconnect`)
- `KeyboardInterrupt` and `SystemExit` now propagate correctly through cleanup paths

## Problem

Two locations use bare `except:` clauses without specifying exception types:

### daemon.py:218 (fallback_to_polling)
```python
try:
    self.email_client.idle_cleanup(self.idle_client)
except:
    pass
```

### email_client.py:209 (_reconnect)
```python
try:
    self.mail.close()
    self.mail.logout()
except:
    pass
```

## Impact

- `KeyboardInterrupt` and `SystemExit` are silently swallowed, making it harder to stop the daemon gracefully
- Genuine errors during cleanup are hidden, complicating debugging
- Violates PEP 8 and Python best practices

## Root Cause

Bare excepts were used for convenience in cleanup paths where errors are expected but should be ignored.

## Suggested Fix

Replace bare `except:` with `except Exception:` to allow `KeyboardInterrupt` and `SystemExit` to propagate:

```python
except Exception:
    pass
```

## Acceptance Criteria

- [x] No bare `except:` clauses remain in the codebase
- [x] All exception handlers specify at least `Exception`
- [x] Daemon can still be interrupted with Ctrl+C during cleanup
