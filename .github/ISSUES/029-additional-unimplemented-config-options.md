# Issue 029: Additional unimplemented config options (timezone, download_folder, keywords)

**Priority:** Medium
**Category:** Documentation
**Status:** Fixed (branch `claude/review-code-docs-GEwGy`)
**Location:** `docs/configuration.md`, `travelbot/config.yaml.example`

## Fix Applied
- Removed `processing.timezone` from docs, config example, and configuration templates
- Removed `processing.download_folder` from docs, config example, and configuration templates
- Removed `email.search.keywords` from docs, config example, and Advanced Configuration section
- Removed Timezone Reference section from configuration.md
- Removed timezone-related troubleshooting entry

## Problem

Three additional configuration options were documented but never read by the code:

1. **`processing.timezone`**: Documented as "System timezone for calendar events" but never read. Timezones are handled entirely by the LLM in the prompt.
2. **`processing.download_folder`**: Documented as "Folder for PDF downloads" but hardcoded to `work/attachments` in daemon.py.
3. **`email.search.keywords`**: Documented as search terms for filtering emails but daemon always searches for `['UNSEEN']`.

## Impact

Same as Issue 017 - users who configure these values see no effect.

## Acceptance Criteria

- [x] Every documented configuration option has a corresponding code path
- [x] Config example only contains options that are actually used
