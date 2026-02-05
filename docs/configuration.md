# TravelBot Configuration Reference

Complete configuration reference for TravelBot v1.0.

## 📁 Configuration File

The main configuration is stored in `travelbot/config.yaml`. This file contains all settings for email processing, AI integration, and system behavior.

## 🔧 Configuration Sections

### OpenAI/LLM Configuration

```yaml
openai:
  provider: "azure"              # Provider type (currently supports "azure")
  api_key: "your-azure-api-key"  # Your Azure OpenAI API key
  model: "your-model-deployment" # Your Azure model deployment name
  endpoint: "https://your-resource.openai.azure.com/openai/deployments/your-model-deployment/chat/completions?api-version=2024-02-15-preview"
  api_version: "2024-02-15-preview"  # Azure API version
  deployment: "your-model-deployment" # Your Azure deployment name (usually same as model)
```

**Required Fields**:
- `api_key`: Your Azure OpenAI API key
- `endpoint`: Complete Azure OpenAI endpoint URL
- `model`: Deployment name in Azure

**Optional Fields**:
- `provider`: Defaults to "azure"
- `api_version`: Defaults to "2024-02-15-preview"
- `deployment`: Defaults to model name

### SMTP Configuration (Outgoing Email)

```yaml
smtp:
  host: "smtp.example.com"      # SMTP server hostname
  port: 587                     # SMTP port (587 for STARTTLS, 465 for SSL)
  user: "travelbot@example.com" # Email account username
  password: "your-password"     # Email account password
```

**Common SMTP Settings**:
- **Gmail**: `smtp.gmail.com:587` (requires app password)
- **Outlook**: `smtp-mail.outlook.com:587`
- **DreamHost**: `smtp.dreamhost.com:587`
- **Custom**: Contact your email provider

### Email Client Configuration

```yaml
email:
  imap:
    host: "imap.example.com"    # IMAP server hostname
    port: 993                   # IMAP port (993 for SSL, 143 for STARTTLS)
    username: "account@example.com"  # Email account username
    password: "your-password"   # Email account password
    # IDLE settings for real-time email processing
    idle_enabled: true          # Enable IMAP IDLE for real-time processing
    idle_timeout: 1740          # IDLE timeout in seconds (29 minutes)
    idle_fallback_polling: 30   # Fallback polling interval if IDLE fails
    connection_retry_delay: 5   # Delay between connection retries
    max_connection_retries: 3   # Maximum connection retry attempts

  search:
    keywords: ["itinerary", "confirmation", "travel", "booking"]  # Search terms
    max_pdf_size_mb: 10         # Maximum PDF attachment size to process
```

**Email Client Notes**:
- TravelBot uses IMAP for email access, with support for IMAP IDLE for real-time processing

**Common Email Settings**:
- **Gmail**: `imap.gmail.com:993` / `smtp.gmail.com:587`
- **Outlook**: `outlook.office365.com:993` / `smtp-mail.outlook.com:587`
- **DreamHost**: `imap.dreamhost.com:993` / `smtp.dreamhost.com:587`

### Processing Configuration

```yaml
processing:
  download_folder: "attachments"      # Folder for PDF downloads
  timezone: "America/New_York"        # System timezone for calendar events
  default_reply_to: "user@example.com"  # Default address for do-not-reply emails
```

**Processing Options**:
- `download_folder`: Relative or absolute path for PDF storage
- `timezone`: System timezone (see [timezone list](#timezone-reference))
- `default_reply_to`: Used when original sender is do-not-reply address

## 🔒 Security Configuration

### Credential Management

**Environment Variables** (Recommended):
```bash
export TRAVELBOT_OPENAI_KEY="your-api-key"
export TRAVELBOT_EMAIL_PASSWORD="your-password"
```

**Configuration File Reference**:
```yaml
openai:
  api_key: "${TRAVELBOT_OPENAI_KEY}"
email:
  imap:
    password: "${TRAVELBOT_EMAIL_PASSWORD}"
smtp:
  password: "${TRAVELBOT_EMAIL_PASSWORD}"
```

### File Permissions

```bash
chmod 600 travelbot/config.yaml    # Owner read/write only
chmod 700 travelbot/               # Owner access only
```

## 🌍 Timezone Reference

Common timezone identifiers for the `processing.timezone` setting:

### North America
- `America/New_York` - Eastern Time
- `America/Chicago` - Central Time  
- `America/Denver` - Mountain Time
- `America/Los_Angeles` - Pacific Time
- `America/Toronto` - Eastern (Canada)
- `America/Vancouver` - Pacific (Canada)

### Europe
- `Europe/London` - GMT/BST
- `Europe/Paris` - CET/CEST
- `Europe/Berlin` - CET/CEST
- `Europe/Rome` - CET/CEST
- `Europe/Madrid` - CET/CEST

### Asia-Pacific
- `Asia/Tokyo` - Japan Standard Time
- `Asia/Shanghai` - China Standard Time
- `Asia/Singapore` - Singapore Standard Time
- `Australia/Sydney` - AEST/AEDT
- `Pacific/Auckland` - NZST/NZDT

## ⚙️ Advanced Configuration

### Custom Email Search

```yaml
email:
  search:
    keywords:
      - "itinerary"
      - "confirmation"
      - "booking"
      - "reservation"
      - "travel"
      - "flight"
      - "hotel"
    max_pdf_size_mb: 10
```

## 🔍 Configuration Validation

### Test Configuration

```bash
python3 -c "
from travelbot.daemon import TravelBotDaemon
try:
    daemon = TravelBotDaemon()
    print('✓ Configuration loaded successfully')
    print(f'✓ Email: {daemon.config[\"email\"][\"imap\"][\"username\"]}')
    print(f'✓ Model: {daemon.config[\"openai\"][\"model\"]}')
except Exception as e:
    print(f'✗ Configuration error: {e}')
"
```

### Validate Email Connection

```bash
python3 -c "
from travelbot.daemon import TravelBotDaemon
daemon = TravelBotDaemon()
success = daemon.connect_to_mailbox()
print('✓ Email connection successful' if success else '✗ Email connection failed')
if success:
    daemon.email_client.logout()
"
```

### Validate Azure OpenAI

```bash
python3 -c "
import requests, yaml
with open('travelbot/config.yaml') as f:
    config = yaml.safe_load(f)
    
response = requests.post(
    config['openai']['endpoint'],
    headers={'api-key': config['openai']['api_key']},
    json={
        'messages': [{'role': 'user', 'content': 'Hello'}],
        'max_tokens': 5
    },
    timeout=10
)

if response.status_code == 200:
    print('✓ Azure OpenAI connection successful')
else:
    print(f'✗ Azure OpenAI error: {response.status_code} - {response.text}')
"
```

## 📝 Configuration Templates

### Minimal Configuration

```yaml
# Minimal working configuration
openai:
  api_key: "your-azure-openai-key"
  endpoint: "https://your-resource.openai.azure.com/openai/deployments/your-model-name/chat/completions?api-version=2024-02-15-preview"
  model: "your-model-name"

smtp:
  host: "smtp.gmail.com"
  port: 587
  user: "your-email@gmail.com"
  password: "your-app-password"

email:
  imap:
    host: "imap.gmail.com"
    port: 993
    username: "your-email@gmail.com"
    password: "your-app-password"

processing:
  timezone: "America/New_York"
  default_reply_to: "your-personal-email@gmail.com"
```

### Production Configuration

```yaml
# Production configuration with all options
openai:
  provider: "azure"
  api_key: "${TRAVELBOT_OPENAI_KEY}"
  model: "your-model-deployment"
  endpoint: "https://your-company-resource.openai.azure.com/openai/deployments/your-model-deployment/chat/completions?api-version=2024-02-15-preview"
  api_version: "2024-02-15-preview"
  deployment: "your-model-deployment"

smtp:
  host: "smtp.company.com"
  port: 587
  user: "travelbot@company.com"
  password: "${TRAVELBOT_EMAIL_PASSWORD}"

email:
  imap:
    host: "imap.company.com"
    port: 993
    username: "travelbot@company.com"
    password: "${TRAVELBOT_EMAIL_PASSWORD}"
  search:
    keywords: ["itinerary", "confirmation", "travel", "booking", "reservation"]
    max_pdf_size_mb: 15

processing:
  download_folder: "/var/travelbot/attachments"
  timezone: "America/New_York"
  default_reply_to: "travel-admin@company.com"
```

## 🚨 Troubleshooting Configuration

### Common Configuration Errors

**1. YAML Syntax Errors**
```
yaml.scanner.ScannerError: while scanning for the next token
```
- Check for proper indentation (use spaces, not tabs)
- Verify quotes are properly closed
- Ensure colons have spaces after them

**2. Missing Required Fields**
```
KeyError: 'api_key'
```
- Check all required fields are present
- Verify field names match exactly (case-sensitive)

**3. Invalid Timezone**
```
ValueError: Invalid timezone: America/New_York_Invalid
```
- Use valid timezone identifiers from the reference above
- Check spelling and capitalization

**4. Connection Timeouts**
```
TimeoutError: Connection timed out
```
- Verify server hostnames and ports
- Check firewall/network connectivity
- Test credentials manually

### Configuration Backup

Always backup your configuration before making changes:

```bash
cp travelbot/config.yaml travelbot/config.yaml.backup.$(date +%Y%m%d_%H%M%S)
```

---

For operational procedures, see [operations.md](operations.md).
For API documentation, see [api.md](api.md).
