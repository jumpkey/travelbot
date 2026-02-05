# Issue 026: In-memory rate limiter state lost on daemon restart

**Priority:** Low
**Category:** Reliability
**Status:** Open
**Location:** `travelbot/auto_reply_filter.py:160-224`, `travelbot/daemon.py:57`

## Problem

The `ReplyRateLimiter` stores reply history in a Python dict (`self._reply_history`). When the daemon restarts (crash, manual restart, system reboot), all rate-limit state is lost. This means:

1. If the daemon is in an auto-reply loop and is restarted, the loop resumes
2. The 3-reply-per-hour limit resets to 0 on every restart

## Impact

- In a reply storm scenario, restarting the daemon re-enables replies to addresses that should be rate-limited
- Reduces effectiveness of the rate-limiting safety net (Layer 2 of loop prevention)
- For typical operation this is low impact since auto-reply detection (Layer 1) catches most cases

## Root Cause

The rate limiter was designed for simplicity using in-memory storage. No persistence mechanism was implemented.

## Suggested Fix

Options (in order of complexity):
1. **Accept the limitation** and document it as a known constraint
2. **File-based persistence**: Write rate-limit state to a JSON file in the work directory, load on startup
3. **SQLite**: Use a lightweight database for reply history (also useful for future analytics)

## Acceptance Criteria

- [ ] Rate-limit state survives daemon restarts, OR the limitation is documented
- [ ] Rate limiter still performs well (no I/O bottleneck on every email)
