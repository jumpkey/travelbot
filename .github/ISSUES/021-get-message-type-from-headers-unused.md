# Issue 021: get_message_type_from_headers function is unused

**Priority:** Low
**Category:** Efficiency
**Status:** Open
**Location:** `travelbot/auto_reply_filter.py:108-157`

## Problem

The function `get_message_type_from_headers()` is defined in `auto_reply_filter.py` and has tests in `test_auto_reply_filter.py` (lines 266-318), but it is never called from `daemon.py` or any other module.

The daemon uses:
- `should_skip_auto_reply()` for Layer 1 (heuristic pre-LLM filtering)
- The LLM itself for Layer 3 (`message_type` field in LLM response)

`get_message_type_from_headers()` provides overlapping functionality with `should_skip_auto_reply()` but with a different return type (message type string vs skip boolean).

## Impact

- Dead code increases maintenance burden
- Tests for unused code consume CI time
- May confuse developers about the intended filtering architecture

## Root Cause

The function was likely written as an alternative approach to message classification but `should_skip_auto_reply()` was chosen instead. The function was never removed.

## Suggested Fix

Either:
1. Remove `get_message_type_from_headers()` and its tests if it's truly unused
2. Or integrate it into the daemon's processing pipeline if it provides value (e.g., use it for logging/metrics)

## Acceptance Criteria

- [ ] Dead code is removed, OR the function is integrated into the processing pipeline
- [ ] If removed, corresponding tests are also removed
