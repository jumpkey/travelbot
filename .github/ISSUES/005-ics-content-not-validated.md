# Issue 005: ICS content never validated before sending

**Priority:** High  
**Category:** Correctness  
**Status:** Open  
**Location:** `travelbot/daemon.py:683-692`

## Problem

The `icalendar` library is listed in requirements.txt but never imported or used. The LLM-generated ICS content is written directly to file and attached without any validation. If the LLM produces syntactically invalid ICS, users receive broken calendar attachments that their apps may reject silently.

## Impact

- Users may receive calendar attachments that don't import
- Calendar apps may silently fail or show errors
- Core "calendarization" goal is not reliably met
- No feedback loop to detect or fix ICS generation issues

## Root Cause

The code at lines 683-692 writes ICS content directly without validation:

```python
# Generate unique ICS filename and save to work directory
ics_filepath = self.generate_unique_ics_filename(original_email['uid'])
with open(ics_filepath, 'w', encoding='utf-8') as f:
    f.write(ics_content)

# Read ICS file for email attachment
with open(ics_filepath, 'rb') as f:
    ics_data = f.read()
msg.add_attachment(ics_data, ...)
```

The `icalendar` library in requirements.txt is never used to validate the content.

## Suggested Fix

1. Parse `ics_content` using the `icalendar` library before writing:
   ```python
   from icalendar import Calendar
   try:
       cal = Calendar.from_ical(ics_content)
       # Optionally validate required components exist
   except Exception as e:
       # Handle invalid ICS
   ```

2. On parse failure:
   - Log the error with details
   - Optionally re-prompt LLM specifically for ICS repair
   - Fall back to sending email summary without attachment
   - Still mark email as processed

## Acceptance Criteria

- [ ] ICS content is validated before attachment
- [ ] Invalid ICS triggers fallback behavior
- [ ] User always receives useful response (with or without calendar)
- [ ] ICS validation errors are logged for debugging
