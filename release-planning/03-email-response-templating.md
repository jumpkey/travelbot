# 03 - Email Response Templating

## Overview

TravelBot v1.x constructs response emails with hardcoded formatting in `daemon.py:send_comprehensive_response_email()` (lines 854-935). The email body, subject line, footer, and calendar attachment notes are all assembled through string concatenation within the function. For v2.0, email formatting must be separated into templates, decoupled from both the Python code and the LLM prompt templates.

## Current State

### Email Construction (`send_comprehensive_response_email`)

The current response email is built as follows:

**Subject line** (line 868-870):
```
Re: {original_subject (max 100 chars)} - Complete Travel Itinerary
```

**Body — success path** (lines 880-908):
```
Your travel itinerary has been processed successfully!

{LLM-generated email_summary}

📅 CALENDAR ATTACHMENT:
The attached .ics file contains all your travel events with proper timezone handling.
Simply double-click the attachment to add all events to your Outlook or Google calendar.

✅ TIMEZONE INTELLIGENCE:
- Flight times show in local airport timezones
- Hotel times display in destination timezone
- Your calendar adjusts correctly when traveling
- International events handled properly

Best regards,
TravelBot Production Processing System
```

**Body — fallback path** (when ICS validation fails):
```
{LLM-generated email_summary}

⚠️ CALENDAR NOTE:
We were unable to generate a valid calendar attachment for this itinerary.
Please add the events to your calendar manually using the information above.

Best regards,
TravelBot Production Processing System
```

**Body — poison email fallback** (lines 968-1002):
```
We received your travel-related email but encountered difficulties processing it fully.

WHAT WE DETECTED:
- Your email appears to contain travel-related information
- Our automated processing was unable to extract the complete itinerary details

WHAT YOU CAN DO:
- Forward the original booking confirmation again
- Ensure the email contains clear booking details
- If this is a complex itinerary, try sending individual booking confirmations separately

We apologize for the inconvenience.

Best regards,
TravelBot Processing System
```

### Relationship to LLM Prompt

The LLM prompt (objective #2) instructs the model to produce an `email_summary` field with specific emoji-categorized formatting:

- ✈️ FLIGHTS & TRANSPORTATION
- 🏨 ACCOMMODATION
- 🍽️ DINING & RESERVATIONS
- 🎯 ACTIVITIES & TOURS
- 🤝 MEETINGS & APPOINTMENTS
- 🚗 GROUND TRANSPORTATION
- 🎫 ENTERTAINMENT & EVENTS
- 📋 OTHER TRAVEL SERVICES

This summary formatting is defined in the LLM prompt but rendered inside the email template. The two template systems must be coordinated.

## Proposed Template System

### Directory Structure

```
travelbot/
└── templates/
    └── email/
        ├── response_success.txt.j2       # Main success response
        ├── response_no_calendar.txt.j2    # Fallback when ICS invalid
        ├── response_error.txt.j2          # Poison email fallback
        ├── subject_line.txt.j2            # Subject line template
        ├── footer.txt.j2                  # Shared footer
        └── calendar_note.txt.j2           # Calendar attachment info
```

### Template Examples

**`response_success.txt.j2`**:
```jinja2
Your travel itinerary has been processed successfully!

{{ email_summary }}

{% include "calendar_note.txt.j2" %}

{% include "footer.txt.j2" %}
```

**`calendar_note.txt.j2`**:
```jinja2
📅 CALENDAR ATTACHMENT:
The attached .ics file contains all your travel events with proper timezone handling.
Simply double-click the attachment to add all events to your {{ calendar_client }} calendar.

✅ TIMEZONE INTELLIGENCE:
- Flight times show in local airport timezones
- Hotel times display in destination timezone
- Your calendar adjusts correctly when traveling
- International events handled properly
```

**`footer.txt.j2`**:
```jinja2
Best regards,
{{ bot_name | default("TravelBot Processing System") }}
```

**`subject_line.txt.j2`**:
```jinja2
Re: {{ original_subject | truncate(100) }} - Complete Travel Itinerary
```

**`response_error.txt.j2`**:
```jinja2
We received your travel-related email but encountered difficulties processing it fully.

WHAT WE DETECTED:
- Your email appears to contain travel-related information
- Our automated processing was unable to extract the complete itinerary details

WHAT YOU CAN DO:
- Forward the original booking confirmation again
- Ensure the email contains clear booking details
- If this is a complex itinerary, try sending individual booking confirmations separately

We apologize for the inconvenience.

{% include "footer.txt.j2" %}
```

### Configuration

Email template settings in `config.yaml`:

```yaml
templates:
  email:
    directory: "templates/email"
    variables:
      bot_name: "TravelBot Production Processing System"
      calendar_client: "Outlook or Google"
```

## Coordination with Prompt Templates

The LLM prompt templates (objective #2) define how the model should format the `email_summary` field. The email response templates consume this field. This creates a dependency:

1. **Prompt template** → tells the LLM how to format `email_summary` (emoji categories, section structure)
2. **Email template** → wraps `email_summary` with header, calendar notes, and footer

If the prompt template changes the summary format (e.g., removes emoji headers), the email template should still work because it treats `email_summary` as opaque content. However, if the email template needs to reference specific sections of the summary, a structured format (e.g., JSON sections instead of free text) would be more robust.

### Recommended Approach

Keep `email_summary` as opaque text injected into the email template. The prompt template controls summary formatting; the email template controls the surrounding envelope. This maintains clean separation between the two template systems.

## Requirements

### Functional Requirements

- [ ] Jinja2-based email template engine (can share infrastructure with prompt template engine from objective #2)
- [ ] Separate template files for success, no-calendar, and error response paths
- [ ] Subject line template with configurable format
- [ ] Shared footer template included by all response templates
- [ ] Configurable template variables via `config.yaml` (bot name, calendar client, etc.)
- [ ] Template loading at startup with validation
- [ ] Backward compatibility: rendered output must match current format when using default templates

### Non-Functional Requirements

- [ ] Templates are plain text, editable without Python knowledge
- [ ] Email templates are independent from LLM prompt templates (different directories, different concerns)
- [ ] Template rendering adds negligible latency
- [ ] Clear separation between email envelope (template) and email content (LLM-generated summary)

### Dependencies

- `jinja2` (shared with objective #2)
- `pyyaml` (already present)

## Risks and Open Questions

1. **HTML email support**: The current implementation sends plain text emails. Should v2.0 add HTML email templates? This would enable richer formatting but adds complexity (dual text/HTML parts, CSS inlining).
2. **Localization**: Should email templates support multiple languages? This is not in the current scope but the template system should not preclude it.
3. **Template testing**: How to validate that rendered emails look correct? Consider adding a template preview CLI command for development.
4. **Summary format coupling**: If a future prompt template produces a structured summary (JSON sections), the email template would need to iterate over sections. This should be designed for but not implemented until needed.
