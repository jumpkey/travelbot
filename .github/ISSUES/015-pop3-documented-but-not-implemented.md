# Issue 015: POP3 support documented but not implemented

**Priority:** Medium
**Category:** Documentation
**Status:** Fixed (branch `claude/review-code-docs-GEwGy`)
**Location:** `travelbot/config.yaml.example:38-44`, `docs/configuration.md:67-70`, `README.md:64`

## Fix Applied
- Removed `pop3:` configuration section from `config.yaml.example`
- Removed `client_type` setting from `config.yaml.example` (only IMAP is supported)
- Removed POP3 section and `client_type` references from `docs/configuration.md`
- Updated email client notes to state IMAP-only support
- Changed README project structure from "IMAP/POP3" to "IMAP"
- Removed `client_type` from Configuration Structure in `docs/api.md`

## Problem

Multiple locations document POP3 as a supported email client type:

1. `config.yaml.example` includes a full `pop3:` configuration section
2. `docs/configuration.md` documents POP3 settings and says "Only one client type is used based on `client_type` setting"
3. `README.md` project structure describes `email_client.py` as handling "IMAP/POP3"

However, there is no POP3 implementation anywhere in the codebase. `EmailClient` only implements IMAP operations.

## Impact

- Users may attempt to configure POP3 and find it doesn't work, with no clear error message
- The `client_type` configuration option is never read by any code
- Creates false expectations about protocol support

## Root Cause

POP3 was likely planned as an alternative protocol but never implemented. The configuration template and documentation were written speculatively.

## Suggested Fix

Either:
1. Remove all POP3 references from config template, docs, and README (preferred, since POP3 is not needed for this use case)
2. Or implement POP3 support in EmailClient

## Acceptance Criteria

- [x] Documentation accurately reflects supported protocols
- [x] No configuration options reference unimplemented features
- [x] README project structure description is accurate
