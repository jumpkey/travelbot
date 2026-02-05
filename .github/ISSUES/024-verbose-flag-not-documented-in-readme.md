# Issue 024: --verbose flag not documented in README

**Priority:** Low
**Category:** Documentation
**Status:** Open
**Location:** `README.md:112-115`

## Problem

The README lists CLI options as:

```
**Options:**
- `--poll-interval SECONDS`: Email polling interval in seconds (default: 30)
- `--retain-files`: Retain work files (attachments and ICS files) after processing for debugging
```

The `--verbose` flag (`daemon.py:1233-1234`) is not listed. It controls IDLE monitoring log verbosity and is useful for debugging real-time processing issues.

## Impact

- Users unaware of the `--verbose` option for debugging IDLE issues
- Incomplete CLI documentation

## Suggested Fix

Add `--verbose` to the README options list:

```
- `--verbose`: Enable verbose logging for IDLE monitoring details
```

Also add it to the `docs/api.md` constructor parameters.

## Acceptance Criteria

- [ ] `--verbose` is documented in README CLI options
- [ ] `--verbose` is documented in API docs constructor parameters
- [ ] `verbose` parameter of `start_idle_monitoring` is documented
