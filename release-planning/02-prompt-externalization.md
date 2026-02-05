# 02 - Prompt Externalization

## Overview

TravelBot v1.x builds its entire LLM prompt inside `daemon.py:build_comprehensive_travel_prompt()` (lines 422-538). This function constructs a ~700+ line prompt through string concatenation, mixing static instructions with dynamic email content. For v2.0, prompts must be moved to filesystem-based templates loaded at startup, with support for provider-specific variations.

## Current State

### Prompt Construction

The current prompt is assembled in `build_comprehensive_travel_prompt()` and consists of these hardcoded sections:

| Section | Content | Lines (approx) |
|---------|---------|-----------------|
| Email metadata | Subject, From, Date | ~10 |
| Email body | Plain text + HTML-to-text + PDF text | Variable |
| Travel service detection | 60+ named services across categories | ~100 |
| Timezone intelligence | Airport-to-timezone mapping, VTIMEZONE rules | ~80 |
| Category mapping | ICS CATEGORIES and TRANSP values for 11 types | ~60 |
| Email summary formatting | Emoji-categorized sections (7 categories) | ~50 |
| Message classification | 4 message types with classification rules | ~40 |
| Output format specification | JSON schema with field descriptions | ~30 |

### Problems with Current Approach

1. **Monolithic**: All prompt logic is in one Python function, making it hard to iterate on individual sections
2. **Provider-locked**: Prompt structure and wording are optimized for GPT-4o; other models may need different instruction styles
3. **No version control visibility**: Prompt changes are buried in Python code diffs, not visible as document changes
4. **Testing difficulty**: Cannot test prompt variations without modifying Python code
5. **Non-developer editing**: Travel domain experts cannot modify prompts without Python knowledge

## Proposed Template System

### Directory Structure

```
travelbot/
└── prompts/
    ├── base/
    │   ├── travel-detection.md.j2
    │   ├── timezone-intelligence.md.j2
    │   ├── category-mapping.md.j2
    │   ├── summary-formatting.md.j2
    │   ├── message-classification.md.j2
    │   ├── output-format.md.j2
    │   └── master.md.j2              # Assembles all sections
    │
    ├── providers/
    │   ├── azure_openai/
    │   │   └── overrides.yaml        # Provider-specific tweaks
    │   ├── anthropic/
    │   │   └── overrides.yaml
    │   ├── gemini/
    │   │   └── overrides.yaml
    │   └── bedrock/
    │       └── overrides.yaml
    │
    └── examples/
        ├── azure_openai_prompt.md    # Rendered example for GPT-4o
        ├── anthropic_prompt.md       # Rendered example for Claude
        └── gemini_prompt.md          # Rendered example for Gemini
```

### Template Engine

Jinja2 is the recommended template engine:

- Already widely used in Python ecosystems
- Supports template inheritance, includes, and macros
- Lightweight dependency
- Familiar syntax for non-developers

### Master Template (`master.md.j2`)

The master template assembles all sections and injects dynamic email data:

```jinja2
{%- if provider_system_prompt %}
{{ provider_system_prompt }}
{%- endif %}

EMAIL METADATA:
Subject: {{ email.subject }}
From: {{ email.sender }}
Date: {{ email.date }}

EMAIL BODY:
{{ email.body }}

{%- if email.pdf_text %}

PDF ATTACHMENT CONTENT:
{{ email.pdf_text }}
{%- endif %}

{% include "travel-detection.md.j2" %}

{% include "timezone-intelligence.md.j2" %}

{% include "category-mapping.md.j2" %}

{% include "summary-formatting.md.j2" %}

{% include "message-classification.md.j2" %}

{% include "output-format.md.j2" %}
```

### Provider Overrides (`overrides.yaml`)

Each provider can customize prompt behavior without duplicating the full template:

```yaml
# prompts/providers/anthropic/overrides.yaml
system_prompt: |
  You are a travel itinerary processing assistant. You analyze emails
  containing travel bookings and produce structured calendar data.

instruction_style: "direct"    # vs "role-play" for models that benefit from it
json_instruction: |
  Return your response as valid JSON with no surrounding text or markdown fences.
temperature: 0.0
max_tokens: 8000
```

### Template Loading

Templates are loaded once at daemon startup and cached:

```python
class PromptTemplateEngine:
    def __init__(self, prompts_dir: str, provider: str):
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.join(prompts_dir, "base")),
            undefined=jinja2.StrictUndefined
        )
        self.master = self.env.get_template("master.md.j2")
        self.overrides = self._load_overrides(prompts_dir, provider)

    def render(self, email_data: dict) -> str:
        return self.master.render(
            email=email_data,
            provider_system_prompt=self.overrides.get("system_prompt", ""),
            **self.overrides
        )
```

## Requirements

### Functional Requirements

- [ ] Jinja2-based template engine that loads prompt templates from `prompts/base/`
- [ ] Master template that assembles all prompt sections via `{% include %}` directives
- [ ] Individual template files for each prompt section (travel detection, timezone, categories, summary format, classification, output format)
- [ ] Provider-specific override mechanism via `prompts/providers/<name>/overrides.yaml`
- [ ] Template loading at startup with validation (fail fast on missing templates)
- [ ] Template variable injection for email metadata, body, and PDF content
- [ ] Example rendered prompts for at least 3 providers (Azure OpenAI, Anthropic, Gemini)
- [ ] Backward compatibility: existing prompt behavior must be preserved when using Azure OpenAI templates

### Non-Functional Requirements

- [ ] Templates are plain text/markdown, editable without Python knowledge
- [ ] Template changes do not require daemon restart (or provide a reload mechanism)
- [ ] Template rendering must not introduce significant latency (< 50ms)
- [ ] Clear error messages when templates reference undefined variables (Jinja2 `StrictUndefined`)
- [ ] Templates are version-controlled alongside code

### Dependencies

- `jinja2` (new dependency)
- `pyyaml` (already present)

## Migration Plan

1. **Extract**: Pull each prompt section from `build_comprehensive_travel_prompt()` into individual `.md.j2` template files
2. **Parameterize**: Replace hardcoded email data insertion with Jinja2 variables (`{{ email.subject }}`, etc.)
3. **Assemble**: Create master template that includes all section templates
4. **Test**: Render templates with test email data and compare output to current hardcoded prompt
5. **Integrate**: Replace `build_comprehensive_travel_prompt()` call with `PromptTemplateEngine.render()`
6. **Provider variations**: Create override files for each target provider

## Interaction with Other Objectives

- **Objective #1 (Multi-LLM Provider Support)**: Provider selection determines which override file is loaded. The provider name from `config.yaml` maps to a directory under `prompts/providers/`.
- **Objective #3 (Email Response Templating)**: Email response templates are separate from LLM prompt templates but follow the same filesystem-based pattern. The prompt output format section must reference the email template structure.
- **Objective #4 (Security Hardening)**: Security/guardrail prompts can be injected as additional template sections or via the master template's system prompt block.

## Risks and Open Questions

1. **Prompt regression**: Moving from code to templates risks subtle formatting differences. A diff-based regression test comparing rendered templates to the current hardcoded output is essential.
2. **Template complexity**: Jinja2 supports conditionals and loops, which could lead to overly complex templates. Establish conventions limiting template logic to simple includes and variable substitution.
3. **Hot reload safety**: If template hot-reload is supported, what happens if a template is partially written when the daemon reads it? A file-locking or atomic-swap mechanism may be needed.
4. **Prompt versioning**: Should templates be versioned independently of the codebase? This could support A/B testing of prompt variations.
