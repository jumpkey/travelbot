# Issue 017: Documented configuration options have no implementation

**Priority:** Medium
**Category:** Documentation
**Status:** Fixed (branch `claude/review-code-docs-GEwGy`)
**Location:** `docs/configuration.md:156-202`

## Fix Applied
- Removed `subject_filters` and `sender_filters` from the Advanced Configuration search example
- Removed the entire `openai.custom_prompts` section
- Removed the entire `logging` configuration section
- Removed `logging` from the Production Configuration template
- All remaining documented configuration options now correspond to code that reads them

## Problem

Several configuration sections documented in `docs/configuration.md` have no corresponding implementation in the code:

1. **`logging` section** (lines 196-202): `level`, `format`, `file_rotation` settings
   - The daemon uses hardcoded `print()` statements with `flush=True`, not a configurable logging framework

2. **`email.search.subject_filters`** (lines 172-174): Subject-based filtering
   - No code reads or applies subject filters

3. **`email.search.sender_filters`** (lines 175-179): Sender-based filtering
   - No code reads or applies sender filters

4. **`openai.custom_prompts`** section (lines 184-191): Custom system messages, max_tokens, temperature, timeout
   - The prompt is hardcoded in `build_comprehensive_travel_prompt()`; `max_tokens` and `temperature` are hardcoded in `get_comprehensive_response_from_llm()`

## Impact

- Users attempting to configure logging, filtering, or custom prompts will find the settings are silently ignored
- Creates false expectations about system configurability
- Time wasted debugging why configuration changes have no effect

## Root Cause

Documentation was written aspirationally, describing planned features that were never implemented.

## Suggested Fix

Either:
1. Remove the undocumented sections from `docs/configuration.md` and note them as future enhancements
2. Or implement the features to match the documentation

## Acceptance Criteria

- [x] Every documented configuration option has a corresponding code path that reads and uses it
- [x] Or undocumented options are removed from the docs with a note in the "Future Enhancements" section
