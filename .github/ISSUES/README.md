# TravelBot Issue Tracker

This directory contains documented issues and improvement opportunities for the TravelBot codebase.

## Issue Summary

### Critical (Reliability)

| ID | Title | Location | Status |
|----|-------|----------|--------|
| [001](001-poison-emails-infinite-retry.md) | Poison emails cause infinite retry loops | `TravelBotDaemon.process_single_email` | Fixed (PR #13) |
| [002](002-llm-call-no-timeout.md) | LLM call has no timeout | `TravelBotDaemon.get_comprehensive_response_from_llm` | Fixed (PR #13) |
| [003](003-fragile-json-parsing.md) | Fragile JSON parsing of LLM output | `TravelBotDaemon._extract_json_from_llm_response` | Fixed (PR #13) |
| [004](004-smtp-no-timeout-retry.md) | SMTP send has no timeout or retry | `TravelBotDaemon._send_email_with_retry` | Fixed (PR #13) |
| [010](010-no-auto-reply-loop-protection.md) | No protection against auto-reply email loops | `auto_reply_filter.py`, `email_client.py` | Fixed (PR #11) |

### High (Correctness/Reliability)

| ID | Title | Location | Status |
|----|-------|----------|--------|
| [005](005-ics-content-not-validated.md) | ICS content never validated | `TravelBotDaemon._validate_ics_content` | Fixed (PR #13) |
| [006](006-max-pdf-size-not-enforced.md) | max_pdf_size_mb config not enforced | `EmailClient.download_pdf_attachments` | Fixed (PR #14) |
| [011](011-env-var-expansion-not-implemented.md) | Env var expansion documented but not implemented | `daemon.py:73-76`, `docs/configuration.md` | Fixed |
| [012](012-sys-path-manipulation-in-email-client.md) | sys.path manipulation instead of relative import | `email_client.py:813-815` | Fixed |
| [013](013-search-emails-return-type-wrong-in-docs.md) | API docs show wrong return type for search_emails | `docs/api.md:127-132` | Fixed |

### Medium (Correctness/Efficiency)

| ID | Title | Location | Status |
|----|-------|----------|--------|
| [007](007-only-first-pdf-processed.md) | Only first PDF attachment processed | `EmailClient.download_pdf_attachments` | Fixed (PR #14) |
| [008](008-email-body-duplicated.md) | Email body duplicated from plain+HTML | `EmailClient.extract_email_body` | Fixed (PR #14) |
| [009](009-rfc2047-headers-not-decoded.md) | RFC2047 headers not decoded | `EmailClient._decode_email_header` | Fixed (PR #14) |
| [014](014-api-docs-reference-pypdf2-not-pdfplumber.md) | API docs reference PyPDF2 instead of pdfplumber | `docs/api.md:371` | Fixed |
| [015](015-pop3-documented-but-not-implemented.md) | POP3 support documented but not implemented | `config.yaml.example`, `docs/`, `README.md` | Fixed |
| [016](016-init-missing-travelbot-daemon-export.md) | \_\_init\_\_.py doesn't export TravelBotDaemon | `travelbot/__init__.py:16-31` | Fixed |
| [017](017-documented-config-options-not-implemented.md) | Documented config options have no implementation | `docs/configuration.md:156-202` | Fixed |
| [018](018-api-docs-outdated-signatures-and-fields.md) | API docs have outdated signatures and data structures | `docs/api.md` (multiple locations) | Fixed |
| [019](019-bare-except-clauses.md) | Bare except clauses suppress all exceptions | `daemon.py:218`, `email_client.py:209` | Fixed |
| [020](020-pdfplumber-exception-path-may-not-exist.md) | pdfplumber exception class path may not exist | `pdf_processor.py:39` | Fixed |

### Low (Code Quality/Enhancement)

| ID | Title | Location | Status |
|----|-------|----------|--------|
| [021](021-get-message-type-from-headers-unused.md) | get_message_type_from_headers function is unused | `auto_reply_filter.py:108-157` | Open |
| [022](022-redundant-imports-and-stray-pass.md) | Redundant local imports and stray pass statement | `daemon.py`, `email_client.py:849` | Open |
| [023](023-daemon-docstring-references-wrong-filename.md) | Daemon module docstring references wrong filename | `daemon.py:10-13` | Open |
| [024](024-verbose-flag-not-documented-in-readme.md) | --verbose flag not documented in README | `README.md:112-115` | Open |
| [025](025-limited-test-coverage.md) | Test coverage limited to single module | `tests/` | Open |
| [026](026-rate-limiter-state-lost-on-restart.md) | In-memory rate limiter state lost on restart | `auto_reply_filter.py:160-224` | Open |
| [027](027-idle-config-values-not-read.md) | IDLE config values never read from config | `config.yaml.example:34-36`, `daemon.py` | Open |

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
