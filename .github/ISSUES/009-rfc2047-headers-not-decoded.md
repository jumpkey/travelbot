# Issue 009: RFC2047 encoded headers not decoded

**Priority:** Medium  
**Category:** Correctness  
**Status:** Fixed (PR #14)  
**Location:** `EmailClient._decode_email_header`, `EmailClient.get_complete_email_content`

## Fix Applied
- Added `_decode_email_header()` helper method using `email.header.decode_header()`
- Applied decoding to Subject, From, and To headers in `get_complete_email_content()`
- Handles international characters with proper charset detection
- Falls back to original string if decoding fails

## Problem

`msg.get('Subject')` and `msg.get('From')` don't decode RFC2047 encoded headers (e.g., `=?UTF-8?B?...?=`). International senders or subjects with special characters will appear garbled in logs and potentially in responses.

## Impact

- International email subjects appear as encoded strings
- Sender names with non-ASCII characters are garbled
- Logs are hard to read for international emails
- Response emails may include garbled subject lines

## Root Cause

In `get_complete_email_content()` at lines 739-740:

```python
email_content = {
    'uid': email_uid,
    'subject': msg.get('Subject', 'No Subject'),  # Not decoded
    'from': msg.get('From', 'Unknown Sender'),    # Not decoded
    ...
}
```

RFC2047 encoding (e.g., `=?UTF-8?B?VHJhdmVsIENvbmZpcm1hdGlvbg==?=`) is not decoded.

## Suggested Fix

Use `email.header.decode_header()` to properly decode:

```python
from email.header import decode_header

def decode_email_header(header_value):
    if not header_value:
        return ''
    decoded_parts = decode_header(header_value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or 'utf-8', errors='replace'))
        else:
            result.append(part)
    return ''.join(result)

# Usage:
'subject': decode_email_header(msg.get('Subject')) or 'No Subject',
'from': decode_email_header(msg.get('From')) or 'Unknown Sender',
```

## Acceptance Criteria

- [ ] RFC2047 encoded subjects are properly decoded
- [ ] RFC2047 encoded sender names are properly decoded
- [ ] International characters display correctly in logs
- [ ] Response emails have correct subject lines
