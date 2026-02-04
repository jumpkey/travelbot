# Issue 003: Fragile JSON parsing of LLM output

**Priority:** Critical  
**Category:** Reliability  
**Status:** Fixed (PR #13)  
**Location:** `travelbot/daemon.py:527-544`

## Fix Applied
- Added `_extract_json_from_llm_response()` method for robust JSON extraction
- Handles various markdown fence styles (```json, ```, ~~~)
- Falls back to finding first `{` and last `}` to extract JSON
- Logs problematic content for debugging

## Problem

The code only strips markdown fences at the outermost layer, then does a straight `json.loads()`. LLMs periodically return minor formatting glitches (extra commentary, leading text, truncated responses). Any parse failure raises an exception that feeds into the infinite-retry problem (Issue 001).

## Impact

- Minor LLM formatting variations cause complete processing failure
- User receives no response for emails with valid travel content
- Repeated LLM calls on the same email burn API costs
- Higher chance of rate limiting affecting other emails

## Root Cause

The JSON extraction logic at lines 527-544 is brittle:

```python
# Only handles these specific patterns:
if content.startswith("```json") and content.endswith("```"):
    content = content[7:-3].strip()
elif content.startswith("```") and content.endswith("```"):
    content = content[3:-3].strip()

# Then immediately tries to parse
parsed_response = json.loads(content)
```

This fails when:
- LLM adds commentary before/after the JSON
- Response is truncated (no closing ```)
- Extra whitespace or newlines around fences
- Different fence styles (e.g., ~~~)

## Suggested Fix

1. Harden output parsing:
   - Find the first `{` and last `}` to extract JSON substring
   - Handle various fence styles and positions
   - Strip any leading/trailing non-JSON text

2. Add retry with re-prompting:
   - If JSON parsing fails, optionally ask LLM to "repair" the output
   - Limit to 1-2 repair attempts

3. Implement structured fallback:
   - If JSON parsing fails after retries, send a simpler text-only reply
   - Log the failure for debugging but mark email as processed

## Acceptance Criteria

- [ ] JSON extraction handles common LLM output variations
- [ ] Parse failures trigger retry/repair logic
- [ ] Persistent failures result in fallback response (not infinite retry)
- [ ] User always receives some response for valid travel emails
