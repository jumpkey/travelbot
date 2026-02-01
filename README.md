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
│   ├── email_client.py     # Email handling (IMAP/POP3)
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

## 🎯 Version

**TravelBot v1.0.0** - Professional production release

---

*Built with ❤️ for intelligent travel management*
