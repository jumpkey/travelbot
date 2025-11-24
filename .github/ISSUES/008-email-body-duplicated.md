# Issue 008: Email body duplicated from both plain and HTML parts

**Priority:** Medium  
**Category:** Efficiency  
**Status:** Open  
**Location:** `travelbot/email_client.py:679-695`

## Problem

For multipart emails, the code appends both `text/plain` AND `text/html` (converted via html2text) to the body. Most emails include both with similar content, effectively doubling the body length.

## Impact

- Token usage and API costs are unnecessarily doubled
- Increased risk of hitting context limits
- LLM may be confused by duplicate content
- Processing time increases

## Root Cause

In `extract_email_body()` at lines 679-695:

```python
if content_type == "text/plain":
    # ... extract and append to body_text
    body_text += text + "\n\n"
    
elif content_type == "text/html":
    # ... convert and append to body_text
    text = html2text(html)
    body_text += text + "\n\n"
```

Both parts are appended when present, rather than choosing one.

## Suggested Fix

1. Prefer HTML when available (richer formatting for travel details):
   ```python
   html_text = None
   plain_text = None
   
   for part in msg.walk():
       if content_type == "text/html":
           html_text = html2text(html)
       elif content_type == "text/plain":
           plain_text = text
   
   # Prefer HTML, fall back to plain
   body_text = html_text if html_text else plain_text
   ```

2. Alternative: Prefer plain text if it's sufficient, as it's already clean

3. Add length capping regardless of which is chosen

## Acceptance Criteria

- [ ] Only one version of email body is extracted (HTML preferred)
- [ ] Token usage is reduced for multipart emails
- [ ] Travel information is not lost by the choice
- [ ] Fallback to plain text when HTML is unavailable
