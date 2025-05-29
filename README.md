# travelbot

# Travel Email Processor MVP - Focused Requirements

## 1. MVP Scope Definition

**Core Focus**: Process travel emails containing PDF itineraries to extract flight and hotel information, then generate Outlook calendar entries.

**Extracted Data Limited To**:
- **Flight**: Airline, confirmation number, departure/arrival times, departure/arrival airports
- **Hotel**: Name, address, confirmation number

**Out of Scope for MVP**:
- Car rentals, meetings, conferences
- Multi-leg complex itineraries  
- International timezone handling beyond basic conversion
- Multiple email accounts
- Advanced error recovery
- User interface or dashboard

## 2. MVP Functional Requirements

### 2.1 Email Processing (Simplified)

**MVP-FR-001: Basic IMAP Connection**
- Connect to single email account using username/password authentication
- Support Gmail and Outlook/Exchange with SSL
- No OAuth2 requirement for MVP

**MVP-FR-002: Simple Email Search**
- Search for unread emails with PDF attachments
- Basic subject line filtering (keywords: "itinerary", "confirmation", "travel", "booking")
- Mark processed emails to avoid reprocessing

**MVP-FR-003: PDF Attachment Extraction**
- Download first PDF attachment from qualifying emails
- Basic PDF validation (file size < 10MB, valid PDF header)
- Skip password-protected PDFs

### 2.2 Content Processing (Focused)

**MVP-FR-004: Basic PDF Text Extraction**
- Extract text using pdfplumber library only
- No OCR capability required
- Handle standard text-based PDFs from major travel sites

**MVP-FR-005: Simple LLM Integration**
- Use OpenAI API only (no multi-provider support)
- Fixed prompt template for flight/hotel extraction
- Basic error handling for API failures

**MVP-FR-006: Limited Information Extraction**
- Extract flight information: airline name, confirmation number, departure time/airport, arrival time/airport
- Extract hotel information: hotel name, address, confirmation number
- Return structured JSON with only these fields
- Skip extraction if confidence is low

### 2.3 Calendar Generation (Basic)

**MVP-FR-007: Simple Calendar Events**
- Create two event types only: flight departure and hotel checkin
- Flight events: 3-hour duration starting at departure time
- Hotel events: 24-hour duration starting at checkin date
- Basic event descriptions with confirmation numbers

**MVP-FR-008: Basic iCalendar Generation**
- Generate single .ics file with extracted events
- Use system timezone for all events (no timezone conversion)
- Basic event validation

**MVP-FR-009: Simple Email Response**
- Send plain text email response with calendar attachment
- Fixed email template with extracted information summary
- No delivery confirmation tracking

### 2.4 Configuration (Minimal)

**MVP-FR-010: Basic Configuration**
- Single YAML config file with email credentials and OpenAI API key
- No encryption of stored credentials
- Basic logging to console and file

## 3. MVP Technical Architecture

### 3.1 Simplified Project Structure
```
travel_mvp/
├── src/
│   ├── main.py              # Single entry point
│   ├── config.py            # Simple config loading
│   ├── email_client.py      # Basic IMAP/SMTP
│   ├── pdf_processor.py     # PDF text extraction
│   ├── llm_client.py        # OpenAI API client
│   └── calendar_generator.py # iCalendar creation
├── config.yaml              # Configuration file
├── requirements.txt         # Dependencies
└── README.md
```

### 3.2 Minimal Dependencies
```
# Core functionality only
imaplib, smtplib, email (standard library)
pdfplumber>=0.9.0
openai>=1.3.0
icalendar>=5.0.0
pyyaml>=6.0
python-dateutil>=2.8.0
```

### 3.3 Single Workflow Implementation
```python
# Simplified main.py workflow
def main():
    1. Load config from YAML file
    2. Connect to email via IMAP
    3. Search for unread emails with PDF attachments
    4. For each email:
       a. Download first PDF attachment
       b. Extract text using pdfplumber
       c. Send text to OpenAI for flight/hotel extraction
       d. Parse JSON response
       e. Generate calendar events for flight + hotel
       f. Create .ics file
       g. Send email response with attachment
       h. Mark email as read
    5. Disconnect and exit
```

## 4. MVP Data Structures

### 4.1 Extraction Data Model
```python
# Simple data classes for MVP
@dataclass
class FlightInfo:
    airline: str
    confirmation: str
    departure_time: datetime
    departure_airport: str
    arrival_time: datetime
    arrival_airport: str

@dataclass  
class HotelInfo:
    name: str
    address: str
    confirmation: str
    checkin_date: date

@dataclass
class TravelData:
    flight: Optional[FlightInfo]
    hotel: Optional[HotelInfo]
```

### 4.2 LLM Prompt Template
```
Extract flight and hotel information from this travel document.
Return only JSON with this exact structure:
{
  "flight": {
    "airline": "airline name",
    "confirmation": "confirmation number", 
    "departure_time": "YYYY-MM-DD HH:MM",
    "departure_airport": "airport code",
    "arrival_time": "YYYY-MM-DD HH:MM", 
    "arrival_airport": "airport code"
  },
  "hotel": {
    "name": "hotel name",
    "address": "full address",
    "confirmation": "confirmation number",
    "checkin_date": "YYYY-MM-DD"
  }
}
If information is not found, use null for that section.
```

## 5. MVP Success Criteria

### 5.1 Core Functionality Validation
- Successfully connects to Gmail/Outlook email accounts
- Identifies travel emails with PDF attachments
- Extracts flight information from common travel booking PDFs (Expedia, airline confirmations)
- Extracts hotel information from booking confirmations
- Generates valid .ics calendar files
- Sends response emails with calendar attachments
- Calendar files import successfully into Outlook

### 5.2 MVP Performance Targets
- Process single email with PDF in under 60 seconds
- Handle PDFs up to 10MB in size
- 80% accuracy on major travel booking formats
- Basic error handling prevents system crashes

### 5.3 MVP Testing Strategy
```python
# Essential tests only
test_email_connection()           # Can connect to email server
test_pdf_text_extraction()       # Extracts text from sample PDFs
test_openai_api_integration()     # Makes successful API calls
test_json_parsing()              # Parses LLM responses correctly
test_calendar_generation()       # Creates valid .ics files
test_email_response_sending()    # Sends emails with attachments
test_end_to_end_workflow()       # Complete workflow with sample data
```

## 6. MVP Limitations and Known Issues

### 6.1 Scope Limitations
- Single email account only
- No car rental or complex itinerary support
- No timezone conversion (uses system timezone)
- No advanced error recovery or retry logic
- No user interface or monitoring dashboard
- No concurrent processing

### 6.2 Quality Limitations
- Basic PDF extraction may fail on image-heavy documents
- LLM extraction accuracy depends on document format consistency
- No validation of extracted data accuracy
- Minimal error handling and logging
- No data persistence or audit trail

### 6.3 Security Limitations
- Credentials stored in plain text configuration
- No input validation or sanitization
- No secure credential management
- Basic logging may expose sensitive information

## 7. MVP Development Timeline

### Week 1: Core Infrastructure
- Basic email connection and PDF extraction
- OpenAI API integration
- Simple configuration system

### Week 2: Data Processing
- LLM prompt development and testing
- JSON response parsing
- Calendar event generation

### Week 3: Integration and Testing
- End-to-end workflow implementation
- Basic testing with sample travel documents
- Email response functionality

### Week 4: Validation and Documentation
- Testing with real travel booking PDFs
- Bug fixes and basic error handling
- Documentation and deployment setup

## 8. Post-MVP Enhancement Path

### Phase 2 Additions (Future)
- Multi-timezone support
- Car rental extraction
- Enhanced error handling
- OAuth2 authentication
- Multiple email account support

### Phase 3 Additions (Future)
- Complex itinerary support
- User interface
- Advanced monitoring and logging
- Security enhancements
- Performance optimization

This MVP focuses exclusively on the core value proposition: automatically extracting flight and hotel information from travel emails and creating calendar entries. It eliminates complexity while delivering immediate value to users.
