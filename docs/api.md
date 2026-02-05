# TravelBot v1.0 API Documentation

API reference and data structures for TravelBot v1.0, including IMAP IDLE functionality and real-time email processing capabilities.

## 📚 Core Classes

### TravelBotDaemon

Main processing daemon class that handles email monitoring and travel processing with IMAP IDLE support.

```python
from travelbot.daemon import TravelBotDaemon

daemon = TravelBotDaemon(config_path="config.yaml", poll_interval=30, retain_files=False)
daemon.run_main_loop()  # Automatically chooses IDLE or polling mode
```

#### Constructor Parameters

- **config_path** (str): Path to configuration file (default: "config.yaml")
- **poll_interval** (int): Email polling interval in seconds (default: 30)
- **retain_files** (bool): Retain work files after processing for debugging (default: False)
- **verbose** (bool): Enable verbose logging for IDLE monitoring (default: False)

#### Methods

##### `run_main_loop()`
Unified entry point that automatically chooses IDLE or polling mode based on server capabilities.

```python
daemon.run_main_loop()
```

##### `run_idle_loop()`
Starts the IMAP IDLE loop for real-time email processing (2-5 second response time).

```python
daemon.run_idle_loop()
```

##### `run_polling_loop()`
Starts the traditional polling loop for continuous email monitoring.

```python
daemon.run_polling_loop()
```

##### `connect_to_mailbox()`
Connects to the email server with retry logic.

**Returns**: `bool` - True if connection successful

##### `check_server_capabilities()`
Checks server IDLE capability and configures daemon accordingly.

##### `process_single_email(email_uid)`
Processes a single email with comprehensive travel detection.

**Parameters**:
- `email_uid` (str): Email UID to process

**Returns**: `bool` - True if processing successful

##### `check_and_process_emails(reason, idle_triggered=False)`
Safely checks and processes emails with proper error handling.

**Parameters**:
- `reason` (str): Reason for check (e.g., "startup", "IDLE notification")
- `idle_triggered` (bool): Whether triggered by IDLE notification (default: False)

### EmailClient

Email handling class for IMAP operations with IDLE support.

```python
from travelbot.email_client import EmailClient

client = EmailClient()
client.connect_imap("imap.gmail.com", "user@gmail.com", "password")
```

#### Methods

##### `connect_imap(host, username, password)`
Connects to IMAP server.

**Parameters**:
- `host` (str): IMAP server hostname
- `username` (str): Email username
- `password` (str): Email password

**Returns**: `imaplib.IMAP4_SSL` - IMAP connection object or None

##### `check_idle_support()`
Checks if server supports IMAP IDLE extension.

**Returns**: `bool` - True if IDLE supported

##### `setup_idle_connection(hostname, username, password)`
Sets up dedicated IDLE connection with IMAPClient.

**Parameters**:
- `hostname` (str): IMAP server hostname
- `username` (str): Email username
- `password` (str): Email password

**Returns**: `IMAPClient` - IDLE client connection

##### `start_idle_monitoring(idle_client, callback, timeout=1740, verbose=False)`
Starts IDLE monitoring with callback for new messages.

**Parameters**:
- `idle_client` (IMAPClient): IDLE connection client
- `callback` (callable): Function to call on new messages
- `timeout` (int): IDLE timeout in seconds (default: 1740)
- `verbose` (bool): Enable verbose IDLE logging (default: False)

**Returns**: `threading.Thread` - IDLE monitoring thread

##### `handle_idle_response(response)`
Processes IDLE server responses.

**Parameters**:
- `response`: IDLE server response

**Returns**: `dict` - Parsed response with type and details

##### `search_emails(criteria, charset='UTF-8', max_retries=3)`
Searches for emails matching criteria with connection recovery and retry logic.

**Parameters**:
- `criteria` (list): Search criteria (e.g., `['UNSEEN']`)
- `charset` (str): Character set for search (default: `'UTF-8'`)
- `max_retries` (int): Maximum retry attempts on failure (default: 3)

**Returns**: `dict` - Structured result:
```python
{
    'success': True,        # Whether the search succeeded
    'uids': ['1', '2'],    # List of matching email UIDs (empty list if none)
    'error': None           # Error message string, or None on success
}
```

##### `get_complete_email_content(uid, download_folder="attachments", max_pdf_size_mb=10)`
Extracts complete email content including attachments.

**Parameters**:
- `uid` (str): Email UID
- `download_folder` (str): Directory for PDF downloads (default: `"attachments"`)
- `max_pdf_size_mb` (int): Maximum PDF size in MB to process (default: 10)

**Returns**: `dict` - Email content dictionary, or `None` on failure

##### `generate_unique_filename(base_filename, directory)`
Generates unique filename with timestamp and UUID prefix.

**Parameters**:
- `base_filename` (str): Base filename
- `directory` (str): Target directory

**Returns**: `str` - Unique filename

## 📊 Data Structures

### Email Content Dictionary

Structure returned by `get_complete_email_content()`:

```python
{
    'uid': '123',                    # Email UID
    'subject': 'Travel Itinerary',   # Decoded subject (RFC2047)
    'from': 'sender@example.com',    # Decoded sender address (RFC2047)
    'to': 'recipient@example.com',   # Decoded recipient address (RFC2047)
    'date': '2025-05-30',           # Email date
    'body_text': 'Email body...',   # Email body (HTML preferred, plain text fallback)
    'pdf_text': 'Extracted PDF...',  # Combined text from all PDF attachments
    'pdf_filepaths': ['/path/to/file1.pdf', '/path/to/file2.pdf'],  # All PDF file paths
    'pdf_filepath': '/path/to/file1.pdf'  # First PDF path (backward compatibility)
}
```

### Configuration Structure

Configuration loaded from `config.yaml`:

```python
{
    'openai': {
        'provider': 'azure',
        'api_key': 'your-key',
        'model': 'gpt-4o-e2',
        'endpoint': 'https://...',
        'api_version': '2024-02-15-preview',
        'deployment': 'your-model-deployment'
    },
    'smtp': {
        'host': 'smtp.example.com',
        'port': 587,
        'user': 'travelbot@example.com',
        'password': 'password'
    },
    'email': {
        'imap': {
            'host': 'imap.example.com',
            'port': 993,
            'username': 'account@example.com',
            'password': 'password',
            'idle_enabled': True,
            'idle_timeout': 1740,
            'idle_fallback_polling': 30,
            'connection_retry_delay': 5,
            'max_connection_retries': 3
        },
        'search': {
            'keywords': ['itinerary', 'confirmation', 'travel'],
            'max_pdf_size_mb': 10
        }
    },
    'processing': {
        'timezone': 'America/New_York',
        'default_reply_to': 'user@example.com'
    }
}
```

### IDLE Response Structure

Response from `handle_idle_response()`:

```python
{
    'type': 'new_message',           # Response type: 'new_message', 'message_updated', 'message_deleted', 'other'
    'count': 5,                      # Message count (for EXISTS responses)
    'response': '* 5 EXISTS'         # Raw server response
}
```

### LLM Response Structure

JSON response from Azure OpenAI:

```python
{
    'message_type': 'TRAVEL_ITINERARY',   # Classification: TRAVEL_ITINERARY, AUTO_REPLY, BOUNCE, NON_TRAVEL
    'message_type_reason': 'Contains flight and hotel bookings',  # Brief classification rationale
    'ics_content': 'BEGIN:VCALENDAR\nVERSION:2.0\n...',          # Generated .ics calendar content
    'email_summary': 'Your Boston Travel Itinerary...'            # Professional travel digest
}
```

## 🔌 Integration Examples

### IDLE Mode Usage

```python
from travelbot.daemon import TravelBotDaemon

# Daemon with IDLE support
daemon = TravelBotDaemon(retain_files=True)  # Keep files for debugging

# Check if IDLE is enabled
if daemon.idle_enabled:
    print("🟢 IDLE mode enabled - real-time processing")
    daemon.run_idle_loop()
else:
    print("🟡 Polling mode - traditional processing")
    daemon.run_polling_loop()
```

### Custom IDLE Callback

```python
from travelbot.email_client import EmailClient

def custom_idle_callback(response):
    print(f"Custom IDLE handler: {response}")
    # Return True to signal new message detected
    return b'EXISTS' in str(response)

client = EmailClient()
client.connect_imap("imap.example.com", "user", "pass")

# Setup IDLE with custom callback
idle_client = client.setup_idle_connection("imap.example.com", "user", "pass")
idle_thread = client.start_idle_monitoring(idle_client, custom_idle_callback, timeout=300)
```

### Unified Mode Selection

```python
from travelbot.daemon import TravelBotDaemon

# Automatic mode selection based on server capabilities
daemon = TravelBotDaemon()
daemon.run_main_loop()  # Chooses IDLE or polling automatically
```

### Configuration-Based Startup

```python
import yaml
from travelbot.daemon import TravelBotDaemon

# Load and modify configuration
with open('travelbot/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Disable IDLE for testing
config['email']['imap']['idle_enabled'] = False

# Create daemon with modified config
daemon = TravelBotDaemon()
daemon.config = config
daemon.run_main_loop()  # Will use polling mode
```

## 🧪 Testing Utilities

### IDLE Capability Testing

```python
from travelbot.email_client import EmailClient

client = EmailClient()
if client.connect_imap("imap.example.com", "user", "password"):
    idle_supported = client.check_idle_support()
    print(f"IDLE support: {'Yes' if idle_supported else 'No'}")
    client.logout()
```

### Mock IDLE Response

```python
# Mock IDLE responses for testing
mock_responses = [
    (b'4', b'EXISTS'),           # New message
    (b'2', b'RECENT'),           # Recent message
    (b'3', b'FETCH', (b'FLAGS', (b'\\Seen',))),  # Flag update
    (b'OK', b'Still here')       # Keepalive
]

def test_idle_handler(response):
    parsed = email_client.handle_idle_response(response)
    print(f"Response type: {parsed['type']}")
    return parsed['type'] == 'new_message'
```

### Email Processing Test

```python
# Test email processing workflow
from travelbot.daemon import TravelBotDaemon

daemon = TravelBotDaemon(retain_files=True)  # Keep files for inspection
daemon.connect_to_mailbox()

# Process specific email UID
success = daemon.process_single_email('123')
print(f"Processing {'successful' if success else 'failed'}")

daemon.email_client.logout()
```

## 🔗 External Dependencies

### Required Packages

```python
# Core dependencies
import imaplib          # Standard IMAP
import smtplib         # SMTP sending
import email           # Email parsing
import yaml            # Configuration
import requests        # Azure OpenAI API

# IDLE functionality
from imapclient import IMAPClient  # IDLE support
import backoff         # Retry logic
import threading       # IDLE monitoring

# PDF processing
import pdfplumber      # PDF text extraction
from html2text import html2text  # HTML conversion
```

### IDLE Dependencies

IDLE functionality requires additional packages:

```bash
pip install IMAPClient>=2.3.1
pip install backoff>=2.2.1
```

If these packages are not available, TravelBot falls back to polling mode.

## 📝 File Management

### Work Directory Structure

```
work/
├── attachments/         # PDF downloads
│   └── timestamp_uuid_filename.pdf
└── ics_files/          # Generated calendar files
    └── itinerary_timestamp_uuid_emailuid.ics
```

### Unique Filename Generation

```python
from travelbot.email_client import EmailClient

client = EmailClient()

# Generate unique PDF filename
pdf_filename = client.generate_unique_filename(
    "travel_itinerary.pdf", 
    "work/attachments"
)
# Result: "1748949892_80e4ce7c_travel_itinerary.pdf"

# Generate unique ICS filename
daemon = TravelBotDaemon()
ics_path = daemon.generate_unique_ics_filename("123")
# Result: "work/ics_files/itinerary_1748949892_80e4ce7c_123.ics"
```

## 🚨 Error Handling

### IDLE-Specific Errors

```python
# IDLE connection failures
try:
    idle_client = email_client.setup_idle_connection(host, user, password)
except Exception as e:
    print(f"IDLE setup failed: {e}")
    # Fallback to polling mode

# IDLE monitoring errors
def error_handling_callback(response):
    try:
        return email_client.handle_idle_response(response)
    except Exception as e:
        print(f"IDLE callback error: {e}")
        return False
```

### Connection Recovery

```python
# Automatic connection recovery in daemon
def run_with_recovery():
    consecutive_errors = 0
    max_errors = 3
    
    while running:
        try:
            # Process emails
            consecutive_errors = 0  # Reset on success
        except Exception as e:
            consecutive_errors += 1
            if consecutive_errors >= max_errors:
                # Reconnect or fallback
                break
```

## 🎯 Command Line Interface

### Daemon Arguments

```bash
# Basic usage
python3 scripts/start_travelbot.py

# Custom polling interval
python3 scripts/start_travelbot.py --poll-interval 60

# Retain files for debugging
python3 scripts/start_travelbot.py --retain-files

# Combined options
python3 scripts/start_travelbot.py --poll-interval 30 --retain-files
```

### Argument Parsing

```python
import argparse

parser = argparse.ArgumentParser(description='TravelBot Email Processing Daemon')
parser.add_argument('--poll-interval', type=int, default=30,
                   help='Email polling interval in seconds (default: 30)')
parser.add_argument('--retain-files', action='store_true',
                   help='Retain work files after processing for debugging')
parser.add_argument('--verbose', action='store_true',
                   help='Enable verbose logging for IDLE monitoring')

args = parser.parse_args()
daemon = TravelBotDaemon(
    poll_interval=args.poll_interval,
    retain_files=args.retain_files,
    verbose=args.verbose
)
```

## 🔮 Future Enhancements

The following features are planned for future releases:

### Planned Features

- **Asynchronous Processing**: Handle multiple emails concurrently
- **Email Body Requests**: Process user requests from email content
- **Database Integration**: Store processing history and analytics
- **Multi-Mailbox Support**: Monitor multiple email accounts
- **Webhook Integration**: Real-time notifications via webhooks
- **Template Customization**: Configurable email response templates
- **Advanced Filtering**: Smart filtering based on sender patterns
- **Performance Metrics**: Built-in monitoring and statistics

### Potential Integrations

- **Calendar APIs**: Direct integration with Google Calendar, Outlook
- **Travel APIs**: Real-time flight tracking, hotel availability
- **Notification Services**: Slack, Discord, SMS notifications
- **Cloud Storage**: Backup processing results to cloud storage

---

For configuration details, see [configuration.md](configuration.md).
For operational procedures, see [operations.md](operations.md).
