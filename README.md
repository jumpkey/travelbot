# TravelBot v1.0 - Professional Travel Email Processing System

🤖 **AI-powered travel itinerary processing with timezone intelligence**

TravelBot is a production-ready email processing daemon that monitors a designated mailbox for travel-related emails, extracts travel information using Azure OpenAI, and generates timezone-aware calendar responses. This system implements comprehensive travel detection and processing functionality with real-time email monitoring capabilities.

## 🌟 Key Features

- **⚡ Real-Time Processing**: IMAP IDLE support for instant email processing (2-5 second response time)
- **🔍 Comprehensive Travel Detection**: Flights, hotels, car rentals, restaurants, tours, meetings, and more
- **🌍 Timezone Intelligence**: Proper timezone handling with VTIMEZONE definitions for accurate calendar display
- **📧 Smart Email Processing**: Handles PDF attachments, HTML content, and forwarded emails
- **🧠 AI-Powered Extraction**: Uses Azure OpenAI GPT-4o-e2 for intelligent travel data parsing
- **📅 Professional Calendar Generation**: Creates standards-compliant iCalendar (.ics) files
- **💬 Tailored Email Responses**: Personalized travel digests instead of generic templates
- **🛡️ Production-Ready**: Fault-tolerant daemon with comprehensive error handling and automatic fallback
- **📱 Mobile-Friendly**: Calendar events adjust correctly when traveling across timezones
- **🗂️ Clean File Management**: Ephemeral work directories with automatic cleanup after processing

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Azure OpenAI API access
- IMAP/SMTP email server access
- Required Python packages (see `requirements.txt`)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd travelbot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the system**:
   ```bash
   cp travelbot/config.yaml.example travelbot/config.yaml
   # Edit config.yaml with your credentials
   ```

4. **Start the daemon**:
   ```bash
   # Foreground (testing)
   python3 scripts/start_travelbot.py
   
   # Background (production)
   nohup python3 scripts/start_travelbot.py > travelbot.log 2>&1 &
   ```

## 📁 Project Structure

```
travelbot/
├── travelbot/              # Core package
│   ├── __init__.py         # Package initialization
│   ├── daemon.py           # Main processing daemon
│   ├── email_client.py     # Email handling (IMAP)
│   ├── auto_reply_filter.py # Auto-reply/bounce detection (RFC 3834)
│   ├── pdf_processor.py    # PDF text extraction
│   └── config.yaml         # Configuration file
├── scripts/                # Startup and utility scripts
│   └── start_travelbot.py  # Main startup script
├── docs/                   # Documentation
│   ├── operations.md       # Operational guide
│   ├── configuration.md    # Configuration reference
│   └── api.md             # API documentation
├── work/                   # Ephemeral work directories
│   ├── attachments/        # PDF downloads (auto-cleaned)
│   └── ics_files/         # Generated calendar files (auto-cleaned)
├── requirements.txt        # Python dependencies
├── README.md              # This file
└── LICENSE                # License information
```

## ⚙️ Configuration

Key configuration areas in `travelbot/config.yaml`:

- **OpenAI/LLM**: Azure OpenAI credentials and model settings
- **Email**: IMAP/SMTP server configuration
- **Processing**: Timezone settings and default reply-to address

See [docs/configuration.md](docs/configuration.md) for detailed configuration options.

## 🔧 Usage Examples

### Command Line Options

```bash
# Default 30-second polling
python3 scripts/start_travelbot.py

# Custom polling interval
python3 scripts/start_travelbot.py --poll-interval 60

# Retain work files for debugging
python3 scripts/start_travelbot.py --retain-files

# Combined options
python3 scripts/start_travelbot.py --poll-interval 60 --retain-files

# Background operation with logging
nohup python3 scripts/start_travelbot.py --poll-interval 30 > travelbot.log 2>&1 &
```

**Options:**
- `--poll-interval SECONDS`: Email polling interval in seconds (default: 30)
- `--retain-files`: Retain work files (attachments and ICS files) after processing for debugging
- `--verbose`: Enable verbose logging for IDLE monitoring details

### Monitoring

```bash
# View live logs
tail -f travelbot.log

# Check process status
ps aux | grep start_travelbot

# Stop the daemon
pkill -f start_travelbot.py
```

## 📧 Email Processing Workflow

1. **Monitor**: Continuously monitors IMAP mailbox for unread emails using IDLE or polling
2. **Extract**: Retrieves email content including body text and PDF attachments
3. **Process**: Uses Azure OpenAI to detect travel services and extract details
4. **Generate**: Creates timezone-aware iCalendar files with proper VTIMEZONE definitions
5. **Respond**: Sends personalized email with calendar attachment
6. **Mark**: Marks original email as read to avoid reprocessing

## 🌍 Timezone Intelligence

TravelBot provides enterprise-grade timezone handling:

- **Airport Recognition**: Automatically maps airports to their local timezones
- **Cross-Timezone Flights**: Departure times in origin timezone, arrival times in destination timezone
- **VTIMEZONE Definitions**: Includes proper daylight saving time rules
- **Mobile Compatibility**: Calendar events adjust correctly when traveling

Example: Boston flight departing 8:00 AM Eastern shows as "7:00 AM" in Central timezone calendars.

## 🎯 Supported Travel Services

- ✈️ **Flights**: Commercial airlines, private jets, charter flights
- 🏨 **Accommodation**: Hotels, vacation rentals, corporate housing
- 🚗 **Transportation**: Car rentals, rideshares, private drivers, shuttles
- 🍽️ **Dining**: Restaurant reservations with specific times
- 🎯 **Activities**: Tours, shows, entertainment, golf tee times
- 🤝 **Meetings**: Business appointments at specific venues
- 🎫 **Services**: Airport lounges, spa appointments, travel insurance

## 📚 Documentation

- [Operations Guide](docs/operations.md) - Deployment and monitoring
- [Configuration Reference](docs/configuration.md) - Detailed configuration options
- [API Documentation](docs/api.md) - Interfaces and data structures

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

[MIT License](LICENSE) - See LICENSE file for details.

## 📞 Support

For support and questions:
- Email: travelbot@example.com
- Documentation: [docs/](docs/)
- Issues: Use the project issue tracker

## 🔧 Issues Corrected

The following reliability and correctness issues have been addressed:

| Issue | Description | Fix Summary |
|-------|-------------|-------------|
| #001 | Poison emails cause infinite retry loops | In-memory failure tracking; after 3 failures, email marked as seen with fallback notification |
| #002 | LLM call has no timeout | Added 10s/120s connect/read timeout with exponential backoff retry |
| #003 | Fragile JSON parsing of LLM output | Robust JSON extraction handling various markdown fence styles |
| #004 | SMTP send has no timeout or retry | Added 30s timeout with exponential backoff retry for transient errors |
| #005 | ICS content never validated | Validation using icalendar library; graceful fallback if invalid |
| #006 | max_pdf_size_mb config not enforced | PDF size check before saving; skip oversized PDFs with logging |
| #007 | Only first PDF attachment processed | Process all PDF attachments; combine extracted text with separators |
| #008 | Email body duplicated from plain+HTML | Prefer HTML content; fall back to plain text; avoid duplication |
| #009 | RFC2047 headers not decoded | Decode Subject/From/To headers using email.header.decode_header() |
| #010 | No auto-reply loop protection | RFC 3834 compliant detection, rate limiting, self-loop prevention |
| #011 | Env var expansion not implemented | Recursive `${VAR}` expansion in config via `_expand_env_vars()` |
| #012 | sys.path manipulation in email_client | Replaced with relative import (`from .pdf_processor import ...`) |
| #013 | API docs wrong return type for search_emails | Updated docs to match structured `{success, uids, error}` format |
| #014 | API docs reference PyPDF2 | Updated to pdfplumber |
| #015 | POP3 documented but not implemented | Removed POP3 references from config, docs, and README |
| #016 | \_\_init\_\_.py missing TravelBotDaemon | Added import and `__all__` entry |
| #017 | Documented config options not implemented | Removed aspirational config sections (filters, custom prompts, logging) |
| #018 | API docs outdated signatures | Updated constructor, method signatures, and data structures |
| #019 | Bare except clauses | Replaced `except:` with `except Exception:` |
| #020 | pdfplumber exception path may not exist | Import-time resolution with `AttributeError` fallback |
| #021 | Unused get_message_type_from_headers | Removed dead code and corresponding tests |
| #022 | Redundant imports and stray pass | Module-level imports; removed stray `pass` |
| #023 | Daemon docstring wrong filename | Updated to reference `scripts/start_travelbot.py` |
| #024 | --verbose not in README | Added to CLI options list |
| #026 | Rate limiter state lost on restart | Documented as known limitation (secondary safety net) |
| #027 | IDLE config values not wired up | `connection_retry_delay` and `idle_fallback_polling` now read from config |

See [.github/ISSUES/](.github/ISSUES/) for detailed issue documentation.

## 🎯 Version

**TravelBot v1.0.0** - Professional production release

---

*Built with ❤️ for intelligent travel management*
