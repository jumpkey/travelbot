# Issue 002: LLM call has no timeout

**Priority:** Critical  
**Category:** Reliability  
**Status:** Open  
**Location:** `travelbot/daemon.py:518`

## Problem

The `requests.post(endpoint, headers=headers, json=data)` call to Azure OpenAI has no `timeout` parameter. If Azure OpenAI hangs or the network stalls, the entire daemon blocks indefinitely. No other emails will be processed.

## Impact

- Daemon can hang indefinitely on a single email
- All subsequent emails are blocked from processing
- No watchdog or recovery mechanism exists in the current code
- System appears "dead" with no error messages

## Root Cause

The `requests.post()` call at line 518 in `get_comprehensive_response_from_llm()` does not specify a timeout:

```python
response = requests.post(endpoint, headers=headers, json=data)
```

By default, `requests` will wait indefinitely for a response.

## Suggested Fix

1. Add explicit timeout parameter:
   ```python
   response = requests.post(endpoint, headers=headers, json=data, timeout=(5, 60))
   ```
   - 5 seconds for connection timeout
   - 60 seconds for read timeout (LLM responses can take time)

2. Wrap in retry logic with backoff for transient failures:
   - Connection resets
   - 5xx errors
   - Timeouts

3. Treat persistent timeout/LLM failures as part of the poison email logic (Issue 001)

## Acceptance Criteria

- [ ] LLM calls have explicit connect and read timeouts
- [ ] Transient failures are retried with exponential backoff
- [ ] Persistent failures trigger fallback behavior
- [ ] Daemon never hangs indefinitely on a single email
