# TravelBot v2.0 Release Planning

This directory contains planning documentation for the TravelBot v2.0 release. The goal is to make TravelBot more modular, support varied LLM providers, harden against malicious intent, and integrate with internet-based travel service providers.

## Current Architecture Summary

TravelBot v1.x is a Python daemon (~2,400 LOC) that monitors an IMAP mailbox for travel-related emails, processes them through Azure OpenAI (GPT-4o), and replies with a structured summary and ICS calendar attachment. Key characteristics:

- **Single LLM provider**: Azure OpenAI, hardcoded HTTP calls in `daemon.py`
- **Hardcoded prompts**: ~700-line prompt built via string concatenation in `build_comprehensive_travel_prompt()`
- **Hardcoded email templates**: Response formatting embedded in `send_comprehensive_response_email()`
- **No prompt injection defenses**: All instructions in a single user message; untrusted email content not delimited
- **No external integrations**: LLM-only analysis, no travel service APIs or MCP connections
- **Existing strengths**: 3-layer auto-reply prevention, poison email handling, filename sanitization, PDF size validation, ICS validation

## Planning Objectives

| # | Objective | Document | Summary |
|---|-----------|----------|---------|
| 1 | [Multi-LLM Provider Support](01-multi-llm-provider-support.md) | `01-multi-llm-provider-support.md` | Abstract provider interface supporting Anthropic, OpenAI, Azure OpenAI, Bedrock, Gemini, Cerebras, and Grok with a factory pattern and provider-selectable configuration |
| 2 | [Prompt Externalization](02-prompt-externalization.md) | `02-prompt-externalization.md` | Move prompts from hardcoded Python to Jinja2 filesystem templates with provider-specific overrides and example configurations |
| 3 | [Email Response Templating](03-email-response-templating.md) | `03-email-response-templating.md` | Separate email formatting into Jinja2 templates for success, error, and fallback response paths with configurable variables |
| 4 | [Security Hardening](04-security-hardening.md) | `04-security-hardening.md` | 5-layer defense against prompt injection: system prompt separation, input scanning, content boundary markers, output validation, and content length limits |
| 5 | [MCP Travel Service Integration](05-mcp-travel-service-integration.md) | `05-mcp-travel-service-integration.md` | MCP client integration with agentic loop for real-time travel data from Google Maps, flight trackers, and booking providers |

## Cross-Cutting Dependencies

The five objectives have significant interdependencies that should inform implementation ordering:

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  (1) Multi-LLM Provider Support ◄───────────────────┐  │
│       │                                              │  │
│       ▼                                              │  │
│  (2) Prompt Externalization ◄─── (4) Security        │  │
│       │                          Hardening           │  │
│       ▼                              │               │  │
│  (3) Email Response Templating       │               │  │
│                                      ▼               │  │
│                              (5) MCP Travel ─────────┘  │
│                                  Service Integration    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

- **Objective 1 → 2**: Provider selection determines which prompt template overrides are loaded
- **Objective 2 → 3**: Email response templates consume the `email_summary` field whose format is defined in prompt templates
- **Objective 4 → 2**: Security prompts (system prompt, guardrails) are injected via the prompt template system
- **Objective 1 → 5**: MCP tool-use requires providers that support function calling (`supports_mcp()`)
- **Objective 4 → 5**: Agentic loops expand the injection surface; security model must cover tool-use scenarios

## Recommended Implementation Order

Based on dependencies and risk:

1. **Objective 1: Multi-LLM Provider Support** — Foundation for all other objectives. Extracts the hardcoded Azure OpenAI integration into an abstract interface.
2. **Objective 4: Security Hardening** — High-severity gaps (prompt injection) should be addressed early, before new features expand the attack surface.
3. **Objective 2: Prompt Externalization** — Depends on provider abstraction and incorporates security prompt separation.
4. **Objective 3: Email Response Templating** — Follows the same template pattern as objective 2, lower risk.
5. **Objective 5: MCP Travel Service Integration** — Largest scope, most dependencies, highest risk. Should be phased internally (Maps first, then flights, then booking providers).

## New Dependencies Summary

| Dependency | Required By | Notes |
|-----------|-------------|-------|
| `jinja2` | Objectives 2, 3 | Template rendering engine |
| `boto3` | Objective 1 | Amazon Bedrock provider |
| `anthropic` | Objective 1 | Anthropic Claude provider (optional, can use raw HTTP) |
| `google-generativeai` | Objective 1 | Google Gemini provider (optional, can use raw HTTP) |
| MCP Python SDK | Objective 5 | MCP client for tool-use integration |
| Google Maps API key | Objective 5 | Geocoding, directions, place details |
| Flight data API subscription | Objective 5 | Real-time flight status |

## Scope Considerations

This planning documentation is intentionally comprehensive to inform manageable re-scoping. Not all items need to be in v2.0. Suggested minimum viable release:

**v2.0 MVP**:
- Objective 1: At least Anthropic + OpenAI + Azure OpenAI providers
- Objective 2: Basic prompt externalization with provider overrides
- Objective 4: System prompt separation + content boundary markers + output validation

**v2.1**:
- Objective 3: Email response templating
- Objective 4: Full input scanning guardrail
- Objective 1: Remaining providers (Bedrock, Gemini, Cerebras, Grok)

**v2.2+**:
- Objective 5: MCP integration, phased by provider (Maps → Flights → Booking)
