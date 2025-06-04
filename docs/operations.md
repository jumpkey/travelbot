# TravelBot v1.0 Operations Guide

This guide covers deployment, monitoring, and operational procedures for TravelBot v1.0, including IMAP IDLE functionality and real-time email processing.

## 🚀 Deployment

### System Requirements

- **Operating System**: Linux (tested on Ubuntu 20.04+), macOS, or Windows
- **Python**: 3.8 or higher
- **Memory**: Minimum 512MB RAM, recommended 1GB+
- **Disk Space**: 100MB for application, additional space for logs
- **Network**: Outbound HTTPS (443) for Azure OpenAI, IMAP/SMTP ports for email

### Pre-Deployment Checklist

1. **Azure OpenAI Access**:
   - Valid Azure OpenAI subscription
   - GPT-4o-e2 model deployment
   - API key and endpoint URL

2. **Email Server Access**:
   - IMAP server credentials for reading emails
   - SMTP server credentials for sending responses
   - Test connectivity to both servers

3. **Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Installation Steps

1. **Clone and Setup**:
   ```bash
   git clone <repository-url>
   cd travelbot
   pip install -r requirements.txt
   ```

2. **Configure System**:
   ```bash
   cp travelbot/config.yaml.example travelbot/config.yaml
   # Edit config.yaml with your credentials
   ```

3. **Test Configuration**:
   ```bash
   python3 -c "from travelbot.daemon import TravelBotDaemon; d = TravelBotDaemon(); print('Config loaded successfully')"
   ```

4. **Run Initial Test**:
   ```bash
   python3 scripts/start_travelbot.py --poll-interval 60
   # Let it run for a few cycles, then Ctrl+C
   ```

## 🔧 Production Deployment

### Daemon Startup

**Foreground (Testing)**:
```bash
python3 scripts/start_travelbot.py
```

**Background (Production)**:
```bash
nohup python3 scripts/start_travelbot.py > travelbot.log 2>&1 &
```

**With Custom Settings**:
```bash
nohup python3 scripts/start_travelbot.py --poll-interval 60 > travelbot.log 2>&1 &
```

**Note**: Logging is automatically unbuffered for real-time output under nohup - no additional flags required.

### Systemd Service (Linux)

Create `/etc/systemd/system/travelbot.service`:

```ini
[Unit]
Description=TravelBot Email Processing Daemon
After=network.target

[Service]
Type=simple
User=travelbot
Group=travelbot
WorkingDirectory=/opt/travelbot
ExecStart=/usr/bin/python3 scripts/start_travelbot.py --poll-interval 30
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable travelbot
sudo systemctl start travelbot
sudo systemctl status travelbot
```

## 📊 Monitoring

### Log Analysis

**View Live Logs**:
```bash
tail -f travelbot.log
```

**Search for Errors**:
```bash
grep "ERROR" travelbot.log
grep "✗" travelbot.log
```

**Check Processing Stats**:
```bash
grep "✅ Successfully processed" travelbot.log | wc -l  # Success count
grep "✗.*processing error" travelbot.log | wc -l        # Error count
```

### Log Format

TravelBot uses structured logging with timestamps and emoji indicators:

```
[2025-05-30 15:47:41] [INFO] 🚀 TravelBot Daemon starting...
[2025-05-30 15:47:41] [INFO] ✓ Successfully connected to mailbox
[2025-05-30 15:47:41] [INFO] 🔍 Checking mailbox...
[2025-05-30 15:47:41] [INFO] 💤 No unread emails found
[2025-05-30 15:48:15] [INFO] 📬 Found 1 unread email(s): ['4']
[2025-05-30 15:48:15] [INFO] 🔄 Processing email UID 4
[2025-05-30 15:48:15] [INFO] 📧 Subject: Travel Itinerary for June Trip...
[2025-05-30 15:48:15] [INFO] 🧠 Calling Azure OpenAI (gpt-4o-e2)...
[2025-05-30 15:48:20] [INFO] ✓ Received 3542 characters from LLM
[2025-05-30 15:48:20] [INFO] ✅ Response sent to user@example.com
[2025-05-30 15:48:20] [INFO] ✅ Successfully processed UID 4
```

### Key Indicators

- **🚀** Daemon startup
- **✓** Successful operations
- **✗** Errors
- **📬** New emails found
- **🔄** Processing started
- **🧠** LLM API calls
- **✅** Successful completion
- **💥** Fatal errors
- **🛑** Shutdown signals

### Health Checks

**Process Status**:
```bash
ps aux | grep start_travelbot
```

**Connection Test**:
```bash
python3 -c "
from travelbot.email_client import EmailClient
from travelbot.daemon import TravelBotDaemon
daemon = TravelBotDaemon()
if daemon.connect_to_mailbox():
    print('✓ Email connection successful')
    daemon.email_client.logout()
else:
    print('✗ Email connection failed')
"
```

**Azure OpenAI Test**:
```bash
python3 -c "
import requests, yaml
with open('travelbot/config.yaml') as f:
    config = yaml.safe_load(f)
response = requests.post(config['openai']['endpoint'], 
    headers={'api-key': config['openai']['api_key']},
    json={'messages': [{'role': 'user', 'content': 'test'}], 'max_tokens': 10})
print('✓ Azure OpenAI connection successful' if response.status_code == 200 else f'✗ Error: {response.status_code}')
"
```

## 🔄 Maintenance

### Log Rotation

**Manual Rotation**:
```bash
mv travelbot.log travelbot.log.$(date +%Y%m%d)
# Restart daemon to create new log file
```

**Logrotate Configuration** (`/etc/logrotate.d/travelbot`):
```
/opt/travelbot/travelbot.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 travelbot travelbot
    postrotate
        systemctl reload travelbot
    endscript
}
```

### Backup Procedures

**Configuration Backup**:
```bash
cp travelbot/config.yaml config.yaml.backup.$(date +%Y%m%d)
```

**Log Archive**:
```bash
tar -czf travelbot-logs-$(date +%Y%m%d).tar.gz *.log
```

### Updates

1. **Stop the daemon**:
   ```bash
   pkill -f start_travelbot.py
   # or: sudo systemctl stop travelbot
   ```

2. **Update code**:
   ```bash
   git pull origin main
   ```

3. **Update dependencies**:
   ```bash
   pip install -r requirements.txt --upgrade
   ```

4. **Test configuration**:
   ```bash
   python3 -c "from travelbot.daemon import TravelBotDaemon; TravelBotDaemon()"
   ```

5. **Restart daemon**:
   ```bash
   nohup python3 scripts/start_travelbot.py > travelbot.log 2>&1 &
   # or: sudo systemctl start travelbot
   ```

## 🚨 Troubleshooting

### Common Issues

**1. Connection Failures**
```
[ERROR] ✗ Connection error: [Errno 111] Connection refused
```
- Check IMAP/SMTP server settings
- Verify network connectivity
- Check firewall rules

**2. Authentication Errors**
```
[ERROR] ✗ Login failed for user@domain.com
```
- Verify email credentials
- Check if 2FA/app-specific passwords required
- Test credentials manually

**3. LLM API Errors**
```
[ERROR] ✗ LLM error: 401 Unauthorized
```
- Check Azure OpenAI API key
- Verify endpoint URL format
- Check API quota/limits

**4. Processing Errors**
```
[ERROR] ✗ JSON parse error: Expecting value
```
- Usually temporary LLM response formatting issues
- Check for API rate limiting
- Verify prompt length not exceeding limits

### Recovery Procedures

**Daemon Crash Recovery**:
```bash
# Check for hung processes
ps aux | grep start_travelbot

# Kill if necessary
pkill -f start_travelbot.py

# Restart
nohup python3 scripts/start_travelbot.py > travelbot.log 2>&1 &
```

**Connection Recovery**:
- Daemon automatically attempts reconnection after 5 consecutive errors
- Manual restart may be needed for persistent issues

**Email Queue Issues**:
```bash
# Reset all emails to unread (use carefully!)
python3 -c "
from travelbot.email_client import EmailClient
from travelbot.daemon import TravelBotDaemon
daemon = TravelBotDaemon()
daemon.connect_to_mailbox()
daemon.email_client.reset_all_emails_to_unseen()
daemon.email_client.logout()
"
```

## 📈 Performance Optimization

### Polling Interval

- **High Volume**: 15-30 seconds
- **Medium Volume**: 30-60 seconds  
- **Low Volume**: 60-300 seconds

### Resource Usage

- **Memory**: ~50MB base + ~10MB per concurrent email
- **CPU**: Minimal except during LLM API calls
- **Network**: ~1KB per email check, ~50KB per LLM call

### Scaling Considerations

For high-volume deployments:
- Consider multiple daemon instances with different mailboxes
- Implement database logging for analytics
- Add monitoring dashboards (Grafana, etc.)
- Consider message queue for email processing

## 🔐 Security

### File Permissions

```bash
chmod 600 travelbot/config.yaml  # Protect sensitive config
chmod 700 travelbot/            # Restrict package access
chmod +x scripts/start_travelbot.py
```

### Network Security

- Use TLS/SSL for all email connections
- Consider VPN for Azure OpenAI access
- Implement firewall rules for outbound connections only

### Data Protection

- Configuration file contains sensitive credentials
- Email content is processed by Azure OpenAI
- Generated calendar files may contain personal information
- Implement data retention policies for logs

---

For additional support, see [configuration.md](configuration.md) and [api.md](api.md).
