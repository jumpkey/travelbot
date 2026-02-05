# Issue 023: Daemon module docstring references wrong filename

**Priority:** Low
**Category:** Documentation
**Status:** Fixed (branch `claude/review-code-docs-GEwGy`)
**Location:** `travelbot/daemon.py:10-13`

## Fix Applied
- Updated module docstring to reference `scripts/start_travelbot.py` instead of `travelbot_daemon.py`
- Added `--retain-files` and `--verbose` flags to the usage example

## Problem

The module docstring says:

```
Usage:
    python3 travelbot_daemon.py [--poll-interval SECONDS]

For background operation:
    nohup python3 travelbot_daemon.py > travelbot.log 2>&1 &
```

The file is actually `travelbot/daemon.py` and is launched via `scripts/start_travelbot.py`. The documented command `python3 travelbot_daemon.py` does not work.

## Impact

- Minor confusion for developers reading the source code
- Inconsistent with README and operations docs which show the correct command

## Suggested Fix

Update the docstring to reference the correct entry point:

```
Usage:
    python3 scripts/start_travelbot.py [--poll-interval SECONDS]
```

## Acceptance Criteria

- [x] Daemon module docstring shows correct usage command
- [x] Usage is consistent with README and operations docs
