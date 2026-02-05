# Issue 027: IDLE config values idle_fallback_polling and connection_retry_delay are never read

**Priority:** Low
**Category:** Correctness
**Status:** Fixed (branch `claude/review-code-docs-GEwGy`)
**Location:** `travelbot/config.yaml.example:34-36`, `travelbot/daemon.py:357,301`

## Fix Applied
- `connection_retry_delay`: `connect_to_mailbox()` now reads `self.config['email']['imap'].get('connection_retry_delay', 5)` instead of hardcoded `5`
- `idle_fallback_polling`: `fallback_to_polling()` now reads and applies `idle_fallback_polling` config value to override `self.poll_interval` when falling back from IDLE

## Problem

The configuration template defines these IDLE-related settings:

```yaml
idle_fallback_polling: 30      # Fallback polling interval if IDLE fails
connection_retry_delay: 5      # Delay between connection retries
```

But the daemon code never reads these values:

- **`idle_fallback_polling`**: When IDLE falls back to polling, it uses `self.poll_interval` (from the `--poll-interval` CLI argument), not this config value
- **`connection_retry_delay`**: The `connect_to_mailbox()` method hardcodes `time.sleep(5)` at line 357 instead of reading this config value

## Impact

- Users who change these config values expecting different behavior will see no effect
- Configuration appears more flexible than it actually is

## Root Cause

Config values were defined in the template but the code was written with hardcoded values instead of reading from config.

## Suggested Fix

Either:
1. Read and use these config values in the code:
   - `self.config['email']['imap'].get('connection_retry_delay', 5)` in `connect_to_mailbox()`
   - `self.config['email']['imap'].get('idle_fallback_polling', 30)` in `fallback_to_polling()`
2. Or remove the unused config keys from the template and docs

## Acceptance Criteria

- [x] Config values are either used by code or removed from config template
- [x] Documentation matches implementation
