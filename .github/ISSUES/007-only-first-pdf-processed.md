# Issue 007: Only first PDF attachment is processed

**Priority:** Medium  
**Category:** Correctness  
**Status:** Open  
**Location:** `travelbot/email_client.py:582`

## Problem

The code explicitly breaks after the first PDF with a comment noting this as "MVP" behavior. Many travel bookings come as multiple PDFs (multi-leg flights, separate hotel/car confirmations). Missing attachments means incomplete itineraries.

## Impact

- Multi-PDF travel confirmations are incompletely processed
- Users may miss flight legs, hotel bookings, or car rentals
- Generated calendar is incomplete
- Undermines "comprehensive travel detection" goal

## Root Cause

In `download_pdf_attachments()` at line 582:

```python
saved_filepath = filepath # Store path of first successfully saved PDF
break # MVP: Download first PDF attachment found and then stop
```

The function returns after processing the first PDF, ignoring any additional attachments.

## Suggested Fix

1. Extend to download all PDF attachments:
   ```python
   saved_filepaths = []
   for part in msg.walk():
       # ... existing PDF detection logic ...
       if is_pdf:
           filepath = save_pdf(part)
           saved_filepaths.append(filepath)
   return saved_filepaths  # Return list instead of single path
   ```

2. Update `get_complete_email_content` to handle multiple PDFs:
   - Iterate through all downloaded PDFs
   - Concatenate extracted text with separators
   - Track all filepaths for cleanup

3. Add per-attachment size caps (see Issue 006) to prevent prompt explosion

## Acceptance Criteria

- [ ] All PDF attachments are downloaded and processed
- [ ] Extracted text from multiple PDFs is combined
- [ ] Size limits prevent excessive prompt length
- [ ] All temporary files are cleaned up properly
