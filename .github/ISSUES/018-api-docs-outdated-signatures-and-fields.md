# Issue 018: API docs have outdated method signatures and data structures

**Priority:** Medium
**Category:** Documentation
**Status:** Fixed (branch `claude/review-code-docs-GEwGy`)
**Location:** `docs/api.md:20-22, 114, 134-168, 232-237`

## Fix Applied
- Added `verbose` parameter to TravelBotDaemon constructor docs
- Added `verbose` parameter to `start_idle_monitoring` docs
- Items 3-5 (get_complete_email_content, Email Content Dict, LLM Response) were already fixed in the Issue 013 batch
- Added `--verbose` to argument parsing example in CLI section

## Problem

Multiple method signatures and data structures in the API docs are outdated:

### 1. TravelBotDaemon constructor (line 20-22)
- **Docs:** `TravelBotDaemon(config_path, poll_interval, retain_files)`
- **Actual:** Also accepts `verbose` parameter

### 2. start_idle_monitoring (line 114)
- **Docs:** `start_idle_monitoring(idle_client, callback, timeout=1740)`
- **Actual:** Also accepts `verbose=False` parameter

### 3. get_complete_email_content (line 134)
- **Docs:** `get_complete_email_content(uid, download_folder="work/attachments")`
- **Actual:** Also accepts `max_pdf_size_mb=10` parameter

### 4. Email Content Dictionary (lines 158-168)
- **Docs:** Shows only `pdf_filepath` (str)
- **Actual:** Also includes `pdf_filepaths` (list) added in Issue 007

### 5. LLM Response Structure (lines 232-237)
- **Docs:** Shows only `ics_content` and `email_summary`
- **Actual:** Also includes `message_type` and `message_type_reason` fields

## Impact

- Integrators write code against incorrect signatures
- Missing parameters lead to unexpected behavior or errors
- Data structure mismatches cause KeyError or missing data

## Root Cause

API docs were not updated when Issues 006, 007, and 010 were implemented, and when the `--verbose` flag was added.

## Suggested Fix

Update all method signatures and data structures in `docs/api.md` to match the current implementation.

## Acceptance Criteria

- [x] All method signatures in docs match actual code
- [x] All data structure fields in docs match actual code
- [x] New parameters have descriptions and default values documented
