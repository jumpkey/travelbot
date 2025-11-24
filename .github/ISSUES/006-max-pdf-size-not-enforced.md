# Issue 006: max_pdf_size_mb config is never enforced

**Priority:** High  
**Category:** Reliability  
**Status:** Open  
**Location:** `travelbot/email_client.py:522-603`, `travelbot/pdf_processor.py`

## Problem

The config defines `max_pdf_size_mb: 10` but this value is never read or used in the code. Large PDFs could cause memory issues or push the prompt over Azure's context limits (triggering 400/413 errors that feed into the infinite-retry problem).

## Impact

- Large PDFs can cause out-of-memory errors
- Oversized prompts trigger Azure API errors (400/413)
- API errors feed into infinite retry loop (Issue 001)
- Processing time increases significantly for large files

## Root Cause

The `max_pdf_size_mb` setting exists in config.yaml.example:
```yaml
search:
  keywords: ["itinerary", "confirmation", "travel", "booking"]
  max_pdf_size_mb: 10
```

But it's never referenced in:
- `download_pdf_attachments()` - no size check before download
- `extract_text_from_pdf()` - no size/page limit check
- `build_comprehensive_travel_prompt()` - no truncation of large content

## Suggested Fix

1. Enforce size limit in `download_pdf_attachments`:
   ```python
   max_size = self.config.get('email', {}).get('search', {}).get('max_pdf_size_mb', 10) * 1024 * 1024
   # Check Content-Length header or file size after download
   if file_size > max_size:
       print(f"Skipping PDF: {file_size} bytes exceeds limit")
       return None
   ```

2. Add page/character limits in PDF extraction:
   - Limit to first N pages
   - Truncate extracted text to reasonable length

3. Truncate prompt content:
   - Cap `body_text` and `pdf_text` in prompt construction
   - Add note to LLM that content may be truncated

## Acceptance Criteria

- [ ] `max_pdf_size_mb` config is actually enforced
- [ ] Oversized PDFs are skipped or truncated
- [ ] Prompt size stays within Azure context limits
- [ ] Truncation is logged and noted in prompt when it occurs
