# TravelBot Issue Tracker

This directory contains documented issues and improvement opportunities for the TravelBot codebase.

## Issue Summary

### Critical (Reliability)

| ID | Title | Location | Status |
|----|-------|----------|--------|
| [001](001-poison-emails-infinite-retry.md) | Poison emails cause infinite retry loops | `daemon.py:708-763` | Open |
| [002](002-llm-call-no-timeout.md) | LLM call has no timeout | `daemon.py:518` | Open |
| [003](003-fragile-json-parsing.md) | Fragile JSON parsing of LLM output | `daemon.py:527-544` | Open |
| [004](004-smtp-no-timeout-retry.md) | SMTP send has no timeout or retry | `daemon.py:696-699` | Open |
| [010](010-no-auto-reply-loop-protection.md) | No protection against auto-reply email loops | `daemon.py:550-596`, `email_client.py:715-776` | Open |

### High (Correctness/Reliability)

| ID | Title | Location | Status |
|----|-------|----------|--------|
| [005](005-ics-content-not-validated.md) | ICS content never validated | `daemon.py:683-692` | Open |
| [006](006-max-pdf-size-not-enforced.md) | max_pdf_size_mb config not enforced | `email_client.py`, `pdf_processor.py` | Open |

### Medium (Correctness/Efficiency)

| ID | Title | Location | Status |
|----|-------|----------|--------|
| [007](007-only-first-pdf-processed.md) | Only first PDF attachment processed | `email_client.py:582` | Open |
| [008](008-email-body-duplicated.md) | Email body duplicated from plain+HTML | `email_client.py:679-695` | Open |
| [009](009-rfc2047-headers-not-decoded.md) | RFC2047 headers not decoded | `email_client.py:739-740` | Open |

## Workflow

1. Issues are documented in individual markdown files
2. When work begins on an issue, update its Status to "In Progress"
3. PRs should reference the issue ID (e.g., "Fixes #001")
4. When merged, update Status to "Closed"

## Adding New Issues

Create a new file following the naming convention: `NNN-short-description.md`

Use the template:
```markdown
# Issue NNN: Title

**Priority:** Critical/High/Medium/Low  
**Category:** Reliability/Correctness/Efficiency/Enhancement  
**Status:** Open  
**Location:** `file.py:line-range`

## Problem
[Description of the issue]

## Impact
[What goes wrong and why it matters]

## Root Cause
[Technical explanation with code references]

## Suggested Fix
[Proposed solution approach]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
```
