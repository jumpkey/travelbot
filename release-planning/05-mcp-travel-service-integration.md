# 05 - MCP Travel Service Integration

## Overview

TravelBot v1.x is an LLM-only system: it extracts travel information from email text without querying any external travel services. For v2.0, the bot should integrate with travel service providers through MCP (Model Context Protocol) endpoints or RESTful APIs, enabling an agentic loop where the LLM can look up real-time flight status, hotel availability, pricing, and maps to enrich its responses.

## Current State

- **No external travel API integrations** exist in the codebase
- All travel data is extracted from email body text and PDF attachments via LLM analysis
- The `docs/api.md` mentions planned integrations (Google Calendar, flight tracking, hotel availability) but none are implemented
- The system is single-turn: one prompt in, one response out, no tool use or agentic loops
- No MCP server or client implementation exists

## Target Travel Service Providers

### Investigation Required

| Provider | Type | Potential Use Cases |
|----------|------|-------------------|
| **Google Flights** | API / MCP | Real-time flight status, pricing, route verification |
| **Expedia** | API | Hotel/flight package details, booking verification |
| **Travelocity** | API | Package deals, pricing comparison |
| **Booking.com** | API (Affiliate/Connectivity) | Hotel details, availability, pricing |
| **Hotels.com** | API | Hotel details, loyalty pricing |
| **Kayak.com** | API / MCP | Meta-search across providers, price comparison |
| **CarRentals.com** | API | Car rental availability and pricing |
| **Google Maps** | API / MCP | Location geocoding, distance/time calculations, venue details |

### API Availability Assessment

Each provider needs investigation across these dimensions:

1. **API existence**: Does a public or partner API exist?
2. **API type**: REST, GraphQL, MCP server, scraping required?
3. **Authentication**: API key, OAuth2, affiliate program membership?
4. **Rate limits**: Requests per second/day, cost per call?
5. **Data available**: What can be queried? (flights, hotels, pricing, status)
6. **Terms of service**: Commercial use allowed? Attribution requirements?
7. **MCP server availability**: Is there an existing MCP server implementation?

### MCP Server Landscape

MCP servers relevant to travel that may already exist or could be built:

- **Google Maps MCP server**: Geocoding, directions, place details
- **Flight tracking MCP server**: Real-time flight status via AviationStack, FlightAware, or similar
- **Weather MCP server**: Destination weather via OpenWeatherMap or similar
- **Currency conversion MCP server**: Real-time exchange rates for international travel

## Proposed Architecture

### MCP Client Integration

TravelBot would act as an **MCP client**, connecting to MCP servers that provide travel data tools:

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│              │     │                 │     │  MCP Servers     │
│  TravelBot   │────▶│  LLM Provider   │────▶│  - Google Maps   │
│  Daemon      │◀────│  (with tools)   │◀────│  - Flight Status │
│              │     │                 │     │  - Hotel Search  │
└──────────────┘     └─────────────────┘     └──────────────────┘
```

### Agentic Loop Design

The current single-turn architecture must evolve to support multi-turn tool use:

```
1. TravelBot sends prompt + available tools to LLM
2. LLM analyzes email, decides if tool calls would help
3. If tool call requested:
   a. TravelBot executes tool via MCP client
   b. Tool result returned to LLM
   c. LLM continues analysis with enriched data
   d. Repeat from step 3 if more tools needed
4. LLM produces final JSON response
5. TravelBot sends response email
```

**Loop constraints**:
- Maximum tool calls per email: configurable (default: 10)
- Maximum loop iterations: configurable (default: 5)
- Total timeout for agentic processing: configurable (default: 300s)
- Tool call failures should not prevent email processing — degrade gracefully

### Session Memory

For the agentic loop to work effectively, the system needs conversational context:

```python
class AgenticSession:
    """Manages multi-turn LLM interaction with tool use."""

    def __init__(self, provider: LLMProvider, tools: list[MCPTool]):
        self.messages = []       # Conversation history
        self.tool_results = []   # Tool call results
        self.iteration = 0       # Current loop iteration
        self.max_iterations = 5

    def run(self, initial_prompt: str) -> dict:
        """Execute agentic loop until LLM produces final response."""
```

### Tool Definitions

Tools exposed to the LLM via MCP:

```yaml
tools:
  - name: "lookup_flight_status"
    description: "Get real-time status of a flight by flight number and date"
    parameters:
      flight_number: string    # e.g., "AA1234"
      date: string             # e.g., "2026-03-15"
    returns: "Flight status including departure/arrival times, delays, gate info"

  - name: "search_hotel"
    description: "Search for hotel details by name and location"
    parameters:
      hotel_name: string
      city: string
      check_in: string
      check_out: string
    returns: "Hotel details including address, amenities, check-in/out times"

  - name: "geocode_location"
    description: "Get coordinates and details for a location"
    parameters:
      address: string
    returns: "Latitude, longitude, formatted address, place details"

  - name: "get_directions"
    description: "Get travel directions and time between two locations"
    parameters:
      origin: string
      destination: string
      mode: string            # driving, transit, walking
    returns: "Distance, duration, route summary"

  - name: "get_car_rental_location"
    description: "Get car rental pickup/dropoff location details"
    parameters:
      company: string
      location: string
    returns: "Address, hours, contact information"

  - name: "get_destination_weather"
    description: "Get weather forecast for a travel destination"
    parameters:
      city: string
      date: string
    returns: "Temperature, conditions, precipitation probability"
```

### Configuration

```yaml
mcp:
  enabled: true
  max_tool_calls_per_email: 10
  max_iterations: 5
  timeout_seconds: 300

  servers:
    google_maps:
      transport: "stdio"       # or "sse"
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-google-maps"]
      env:
        GOOGLE_MAPS_API_KEY: "${GOOGLE_MAPS_API_KEY}"

    flight_tracker:
      transport: "sse"
      url: "http://localhost:8080/mcp"
      api_key: "${FLIGHT_API_KEY}"

agentic:
  enabled: true
  session_memory: true
  planning_enabled: true       # Allow LLM to plan multi-step lookups
```

## Planning Capabilities

When the LLM receives a complex itinerary with multiple legs, it should be able to plan its tool usage:

1. **Identify enrichment opportunities**: Which bookings would benefit from real-time data?
2. **Prioritize tool calls**: Flight status is more time-sensitive than hotel directions
3. **Batch related lookups**: Get directions for multiple legs in sequence
4. **Graceful degradation**: If a tool fails, proceed with available data

Example planning for a multi-leg trip email:
```
Plan:
1. Look up flight AA1234 status (departure delay affects hotel check-in)
2. Look up flight UA5678 status (connecting flight)
3. Geocode hotel address for calendar event location
4. Get directions from airport to hotel
5. Produce calendar events with enriched data
```

## Google Maps Integration

Google Maps is the most broadly useful integration, providing:

- **Geocoding**: Convert hotel/venue names to coordinates for calendar events
- **Directions**: Travel time estimates between venues
- **Place details**: Addresses, phone numbers, hours for venues mentioned in bookings
- **Timezone**: Verify timezone for locations (supplements current airport-code mapping)

This is particularly valuable because the current system relies entirely on the LLM's training data for location details, which may be outdated or imprecise.

## Requirements

### Functional Requirements

- [ ] MCP client implementation that can connect to MCP servers (stdio and SSE transports)
- [ ] Agentic loop supporting multi-turn LLM interactions with tool calls
- [ ] Session memory for maintaining conversation context during tool use loops
- [ ] Configurable tool definitions exposed to the LLM
- [ ] Google Maps MCP server integration (geocoding, directions, place details)
- [ ] Flight status lookup tool (provider TBD based on API availability investigation)
- [ ] Configurable loop constraints (max iterations, max tool calls, timeout)
- [ ] Graceful degradation: tool failures do not prevent email processing
- [ ] Planning capability: LLM can plan multi-step tool usage for complex itineraries

### Non-Functional Requirements

- [ ] MCP server connections are managed and pooled (not created per-email)
- [ ] Tool call latency is logged and monitored
- [ ] Total processing time with tools should not exceed configurable timeout
- [ ] Tool results are cached where appropriate (e.g., geocoding results for same address)
- [ ] MCP integration is optional: system works without any MCP servers configured

### Investigation Deliverables

- [ ] API availability report for each target provider (Google Flights, Expedia, Travelocity, Booking.com, Hotels.com, Kayak.com, CarRentals.com)
- [ ] Existing MCP server inventory for travel-related tools
- [ ] Cost analysis for API usage at expected email volume
- [ ] Terms of service review for commercial use of each API

### Dependencies

- MCP Python SDK (for client implementation)
- Provider-specific API keys and accounts
- `google-maps-services-python` or Google Maps MCP server
- Flight data API subscription (AviationStack, FlightAware, or similar)

## Interaction with Other Objectives

- **Objective #1 (Multi-LLM Provider Support)**: Not all providers support tool use equally. The provider interface's `supports_mcp()` method indicates whether the agentic loop can be used. Providers without tool-use support fall back to single-turn processing.
- **Objective #2 (Prompt Externalization)**: The agentic prompt (including tool descriptions and planning instructions) must be part of the template system.
- **Objective #4 (Security Hardening)**: The agentic loop multiplies injection surface area. Each tool call result is untrusted data that must be delimited and guarded. The security system prompt must cover tool-use scenarios.

## Risks and Open Questions

1. **API cost**: External API calls have per-request costs. At scale, flight status and maps lookups for every email could become expensive. A cost-benefit analysis is needed to determine which enrichments are worth the cost.
2. **Latency**: Adding tool calls to the processing loop increases end-to-end latency from seconds to potentially minutes. Users expect timely responses. Consider making enrichment optional or asynchronous.
3. **API availability**: Some travel providers (Expedia, Travelocity) may not have publicly available APIs, or may require affiliate program membership. Investigation is needed before committing to specific integrations.
4. **Provider tool-use support**: The agentic loop requires LLM providers that support function/tool calling. Not all providers in objective #1 support this equally. A fallback single-turn path must always exist.
5. **Scope creep**: The agentic loop with planning capabilities is a significant architectural change. Consider phasing: Phase 1 with Google Maps only, Phase 2 with flight status, Phase 3 with booking provider APIs.
6. **Data freshness**: Cached tool results could become stale (e.g., flight delay info changes frequently). Cache TTLs must be appropriate per data type.
