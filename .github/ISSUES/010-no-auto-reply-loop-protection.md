# Issue 010: No protection against auto-reply email loops

**Priority:** Critical  
**Category:** Reliability / Security  
**Status:** Open  
**Location:** `travelbot/daemon.py:550-596`, `travelbot/email_client.py:715-776`

## Problem

The system has no mechanism to detect and skip auto-generated emails (out-of-office replies, bounce messages, ticketing system auto-responses). This has caused email loops that resulted in the hosting provider flagging the system as a potential spam generator.

## Impact

- **Spam flagging:** Hosting provider flagged TravelBot as potential spam generator
- **Email loops:** Continuous back-and-forth with auto-responders
- **Wasted resources:** LLM API calls on non-travel auto-reply content
- **Reputation damage:** Sender reputation degradation affects deliverability
- **Service disruption:** May result in account suspension by email provider

## Root Cause

### No Header-Based Detection

The code never checks standard auto-reply headers defined in RFC 3834:

```python
# These headers are NEVER checked anywhere in the codebase:
# - Auto-Submitted: auto-replied | auto-generated | auto-notified
# - X-Auto-Response-Suppress: All | OOF | DR | RN | NRN
# - Precedence: bulk | junk | list
# - Return-Path: <> (empty, indicates bounce)
# - List-Id, List-Unsubscribe (mailing list indicators)
```

### Insufficient From Address Filtering

`determine_reply_address()` at lines 550-596 only checks for these patterns in the From address:

```python
do_not_reply_indicators = [
    'noreply', 'no-reply', 'do-not-reply', 'donotreply',
    'auto-confirm', 'automated', 'system', 'notification'
]
```

This misses:
- `MAILER-DAEMON` and `postmaster` (bounce senders)
- Normal user addresses sending OOO replies
- Ticketing systems with custom From addresses

### No Self-Loop Prevention

No check exists to prevent replying to emails from TravelBot's own address (`config['smtp']['user']`).

### Headers Not Exposed

`get_complete_email_content()` extracts only Subject, From, To, Date, and body. Auto-reply headers are discarded and never passed to the daemon for filtering decisions.

## Loop Scenarios

### Scenario 1: Out-of-Office Loop (Most Likely Cause)

```
1. User A sends travel email to TravelBot
2. TravelBot processes and sends ICS response to user@example.com
3. User A has OOO auto-reply enabled
4. OOO reply arrives in TravelBot inbox:
   - From: user@example.com (looks like normal user)
   - Subject: "Automatic reply: Re: Travel Itinerary..."
   - Headers: Auto-Submitted: auto-replied (IGNORED)
5. TravelBot processes OOO as new email, sends ANOTHER response
6. If OOO is misconfigured, it sends another reply
7. Loop continues until manual intervention
```

### Scenario 2: Bounce Message Processing

```
1. TravelBot sends to invalid/full mailbox
2. Remote MTA sends DSN (Delivery Status Notification):
   - From: MAILER-DAEMON@host or Mail Delivery Subsystem
   - Return-Path: <> (empty)
   - Auto-Submitted: auto-generated
3. TravelBot processes bounce, sends response to MAILER-DAEMON
4. Wasted traffic, looks like bot-to-system spam
```

### Scenario 3: Ticketing System Loop

```
1. Corporate user forwards travel email to TravelBot
2. TravelBot sends response
3. Corporate ticketing system auto-acknowledges: "Ticket #12345 created"
4. TravelBot processes acknowledgment, sends another response
5. Ticketing system creates another ticket...
```

### Scenario 4: Self-Loop

```
1. If sent messages are copied to INBOX as unread
2. Or if bounces wrap original message with TravelBot as From
3. TravelBot processes its own previous response
4. Sends response to itself, creating infinite loop
```

## Interaction with Other Issues

This issue amplifies **Issue 001 (Infinite Retry Loops)**:
- If an OOO or bounce triggers an LLM/JSON error, it will be retried indefinitely
- Each retry may generate additional outbound messages
- Combined effect is exponential spam-like behavior

## Suggested Fix

### Phase 1: Header-Based Detection (Immediate)

Add a function to classify message type before processing:

```python
def should_skip_auto_reply(self, msg, email_content):
    """Check if email is auto-generated and should not receive a reply."""
    
    # RFC 3834: Auto-Submitted header
    auto_submitted = msg.get('Auto-Submitted', '').lower()
    if auto_submitted and auto_submitted != 'no':
        return True, f"Auto-Submitted: {auto_submitted}"
    
    # Precedence header (bulk, junk, list)
    precedence = msg.get('Precedence', '').lower()
    if precedence in ('bulk', 'junk', 'list', 'auto_reply'):
        return True, f"Precedence: {precedence}"
    
    # Empty Return-Path indicates bounce
    return_path = msg.get('Return-Path', '')
    if return_path == '<>' or not return_path.strip():
        return True, "Empty Return-Path (bounce)"
    
    # X-Auto-Response-Suppress
    if msg.get('X-Auto-Response-Suppress'):
        return True, "X-Auto-Response-Suppress present"
    
    # Mailing list indicators
    if msg.get('List-Id') or msg.get('List-Unsubscribe'):
        return True, "Mailing list headers present"
    
    return False, None
```

### Phase 2: Address-Based Blocking

Extend `determine_reply_address()`:

```python
# Add to do_not_reply_indicators:
blocked_senders = [
    'mailer-daemon', 'postmaster', 'mail-daemon',
    'bounce', 'returned', 'undeliverable'
]

# Add self-loop prevention:
if from_addr == self.config['smtp']['user'].lower():
    return None  # Don't reply to ourselves
```

### Phase 3: Subject Pattern Detection

```python
auto_reply_subjects = [
    'out of office', 'automatic reply', 'auto-reply', 'autoreply',
    'away from', 'on vacation', 'delivery status', 'undeliverable',
    'returned mail', 'mail delivery failed', 'failure notice'
]
```

### Phase 4: Per-Recipient Rate Limiting

Add tracking to prevent sending more than N responses to the same address within a time window:

```python
# In-memory or persistent tracking
self.reply_counts = {}  # {email: (count, first_reply_time)}
MAX_REPLIES_PER_RECIPIENT = 3
RATE_LIMIT_WINDOW_HOURS = 24
```

### Phase 5: Expose Headers in EmailClient

Modify `get_complete_email_content()` to include relevant headers:

```python
email_content = {
    # ... existing fields ...
    'headers': {
        'auto_submitted': msg.get('Auto-Submitted'),
        'precedence': msg.get('Precedence'),
        'return_path': msg.get('Return-Path'),
        'x_auto_response_suppress': msg.get('X-Auto-Response-Suppress'),
        'list_id': msg.get('List-Id'),
    },
    'raw_msg': msg  # For additional header checks
}
```

## Acceptance Criteria

- [ ] Auto-generated emails (OOO, bounces) are detected and skipped
- [ ] Skipped emails are still marked as seen (no infinite retry)
- [ ] Standard RFC 3834 headers are checked (Auto-Submitted, Precedence)
- [ ] MAILER-DAEMON and postmaster senders are blocked
- [ ] Self-loop prevention (don't reply to own address)
- [ ] Common OOO subject patterns are detected
- [ ] Per-recipient rate limiting prevents runaway loops
- [ ] Skipped emails are logged for debugging
- [ ] Headers are exposed in email_content for filtering decisions

## References

- RFC 3834: Recommendations for Automatic Responses to Electronic Mail
- RFC 5321: Simple Mail Transfer Protocol (bounce handling)
- Microsoft Auto-Response-Suppress header documentation
