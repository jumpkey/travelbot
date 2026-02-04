# Issue 004: SMTP send has no timeout or retry

**Priority:** Critical  
**Category:** Reliability  
**Status:** Fixed (PR #13)  
**Location:** `travelbot/daemon.py:696-699`

## Fix Applied
- Added 30 second timeout to `smtplib.SMTP` connection
- Added `_send_email_with_retry()` method with exponential backoff (3 attempts)
- Retries on transient errors (disconnect, connection, timeout, network)
- Does not retry on authentication or recipient errors

## Problem

The `smtplib.SMTP` connection has no explicit timeout. A misbehaving SMTP server could block the daemon. Also, transient SMTP failures cause the email to be retried indefinitely (feeds into Issue 001).

## Impact

- Daemon can hang on SMTP connection/send
- Transient SMTP failures (network blips, server overload) cause permanent processing failure
- User never receives response even though travel extraction succeeded
- Email stays in infinite retry loop

## Root Cause

The SMTP code at lines 696-699 has no timeout or retry logic:

```python
with smtplib.SMTP(self.config['smtp']['host'], self.config['smtp']['port']) as smtp:
    smtp.starttls()
    smtp.login(self.config['smtp']['user'], self.config['smtp']['password'])
    smtp.send_message(msg)
```

On any exception, the function returns `(False, ics_filepath)`, which triggers the infinite retry behavior.

## Suggested Fix

1. Add socket timeout:
   ```python
   import socket
   socket.setdefaulttimeout(30)  # Or use SMTP timeout parameter
   ```

2. Implement retry with backoff for transient errors:
   - 4xx responses
   - Connection timeouts
   - Temporary network failures

3. Distinguish "email failed but itinerary extracted" from "couldn't extract":
   - After N send failures, consider alternative notification
   - Or mark email as processed with a note about send failure

## Acceptance Criteria

- [ ] SMTP operations have explicit timeouts
- [ ] Transient SMTP failures are retried with backoff
- [ ] Persistent send failures don't cause infinite retry
- [ ] Successfully extracted itineraries aren't lost due to send failures
