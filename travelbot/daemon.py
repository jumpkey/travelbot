#!/usr/bin/env python3
"""
TravelBot Production Email Processing Daemon

This daemon continuously monitors the travelbot@jumpkey.com mailbox for new travel emails,
processes them with comprehensive travel service detection, and sends back personalized
calendar responses with timezone intelligence.

Usage:
    python3 travelbot_daemon.py [--poll-interval SECONDS]
    
For background operation:
    nohup python3 travelbot_daemon.py > travelbot.log 2>&1 &
"""

import sys
import os
import time
import argparse
from datetime import datetime
import uuid

import yaml
import requests
import smtplib
from email.message import EmailMessage
from .email_client import EmailClient
import re
import json

class TravelBotDaemon:
    def __init__(self, config_path="config.yaml", poll_interval=30, retain_files=False, verbose=False):
        self.config_path = config_path
        self.poll_interval = poll_interval
        self.retain_files = retain_files
        self.verbose = verbose
        self.config = self.load_config()
        self.email_client = EmailClient()
        self.running = False
        
        # IDLE-related attributes
        self.idle_enabled = False
        self.idle_client = None
        self.idle_thread = None
        
        # Ensure work directories exist
        self.work_dir = "work"
        self.attachments_dir = os.path.join(self.work_dir, "attachments")
        self.ics_dir = os.path.join(self.work_dir, "ics_files")
        os.makedirs(self.attachments_dir, exist_ok=True)
        os.makedirs(self.ics_dir, exist_ok=True)
        
        print(f"🤖 TravelBot Daemon v1.0 Initialized", flush=True)
        print(f"📧 Monitoring: {self.config['email']['imap']['username']}", flush=True)
        print(f"⏱️  Poll interval: {poll_interval} seconds", flush=True)
        print(f"🎯 LLM Model: {self.config['openai']['model']}", flush=True)
        
        # Check IDLE capability
        self.check_server_capabilities()
        print("=" * 80, flush=True)
        
    def load_config(self):
        config_file = os.path.join(os.path.dirname(__file__), self.config_path)
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def log_with_timestamp(self, message, level="INFO"):
        """Log message with timestamp and immediate flush."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}", flush=True)
    
    def check_server_capabilities(self):
        """Check server IDLE capability and configure accordingly."""
        try:
            # Temporarily connect to check capabilities
            imap_config = self.config['email']['imap']
            temp_client = self.email_client
            
            if temp_client.connect_imap(imap_config['host'], imap_config['username'], imap_config['password']):
                idle_supported = temp_client.check_idle_support()
                idle_config_enabled = imap_config.get('idle_enabled', True)
                
                self.idle_enabled = idle_supported and idle_config_enabled
                
                if self.idle_enabled:
                    print(f"⚡ IDLE Mode: ENABLED (Real-time email processing)", flush=True)
                    print(f"⏰ IDLE timeout: {imap_config.get('idle_timeout', 1740)}s", flush=True)
                else:
                    if not idle_supported:
                        print(f"📡 IDLE Mode: DISABLED (Server does not support IDLE)", flush=True)
                    elif not idle_config_enabled:
                        print(f"📡 IDLE Mode: DISABLED (Disabled in configuration)", flush=True)
                    print(f"🔄 Falling back to polling mode", flush=True)
                
                temp_client.logout()
            else:
                print(f"⚠️  Could not check IDLE capabilities - connection failed", flush=True)
                self.idle_enabled = False
                
        except Exception as e:
            print(f"⚠️  Error checking server capabilities: {e}", flush=True)
            self.idle_enabled = False

    def setup_idle_mode(self):
        """Setup IDLE connection and monitoring."""
        if not self.idle_enabled:
            return False
            
        try:
            imap_config = self.config['email']['imap']
            self.log_with_timestamp("🔌 Setting up IDLE connection...")
            
            # Setup dedicated IDLE connection
            self.idle_client = self.email_client.setup_idle_connection(
                imap_config['host'],
                imap_config['username'], 
                imap_config['password']
            )
            
            if self.idle_client:
                self.log_with_timestamp("✓ IDLE connection established")
                return True
            else:
                self.log_with_timestamp("✗ Failed to setup IDLE connection", "ERROR")
                return False
                
        except Exception as e:
            self.log_with_timestamp(f"✗ IDLE setup error: {e}", "ERROR")
            return False

    def set_idle_notification_flag(self, response):
        """Simple callback to set notification flag without processing."""
        try:
            parsed_response = self.email_client.handle_idle_response(response)
            if parsed_response['type'] == 'new_message':
                self.log_with_timestamp("🔔 IDLE notification flag set")
                self.idle_notification_received = True
                return True
            return False
        except Exception as e:
            self.log_with_timestamp(f"✗ Error in IDLE callback: {e}", "ERROR")
            return False
    
    def check_and_process_emails(self, reason="check", idle_triggered=False):
        """Safely check and process emails with proper error handling."""
        try:
            self.log_with_timestamp(f"🔍 Checking for unread emails ({reason})...")
            
            # CRITICAL: If this was triggered by IDLE, refresh the mailbox state
            # because IDLE uses a separate connection
            if idle_triggered:
                self.log_with_timestamp("🔄 IDLE triggered - refreshing mailbox state...")
                try:
                    # Re-select INBOX to refresh mailbox state
                    typ, data = self.email_client.mail.select("INBOX")
                    if typ == 'OK':
                        self.log_with_timestamp("✓ Mailbox state refreshed after IDLE notification")
                    else:
                        self.log_with_timestamp(f"⚠️  Mailbox refresh failed: {data}", "WARN")
                        # Try to reconnect
                        self.connect_to_mailbox()
                except Exception as refresh_e:
                    self.log_with_timestamp(f"⚠️  Error refreshing mailbox: {refresh_e}", "WARN")
                    # Try to reconnect
                    self.connect_to_mailbox()
                
                # Add small delay to ensure email is fully committed
                import time
                time.sleep(1)
            
            # Search for unread emails
            unread_uids = self.search_for_unread_emails()
            
            if unread_uids:
                self.log_with_timestamp(f"📬 Found {len(unread_uids)} unread email(s) - processing...")
                processed = self.process_emails_batch(unread_uids)
                self.log_with_timestamp(f"✅ Processed {processed}/{len(unread_uids)} email(s) successfully")
                
                # CRITICAL: Check again after processing in case new emails arrived
                # during processing (emails can arrive while we're busy)
                self.log_with_timestamp("🔄 Checking for additional emails that arrived during processing...")
                additional_uids = self.search_for_unread_emails()
                if additional_uids:
                    additional_processed = self.process_emails_batch(additional_uids)
                    self.log_with_timestamp(f"📬 Processed {additional_processed} additional email(s)")
            else:
                self.log_with_timestamp("📭 No unread emails found")
                # If IDLE triggered but no emails found, log for debugging
                if idle_triggered:
                    self.log_with_timestamp("🤔 IDLE notification received but no unread emails found - possible timing issue", "WARN")
                
        except Exception as e:
            self.log_with_timestamp(f"✗ Error during email check ({reason}): {e}", "ERROR")
            import traceback
            traceback.print_exc()
            # Don't re-raise - continue with IDLE monitoring

    def fallback_to_polling(self, reason):
        """Switch to polling mode when IDLE fails."""
        self.log_with_timestamp(f"🔄 Falling back to polling mode: {reason}", "WARN")
        self.idle_enabled = False
        
        # Cleanup IDLE connection
        if self.idle_client:
            try:
                self.email_client.idle_cleanup(self.idle_client)
            except:
                pass
            self.idle_client = None
            
        # Start polling loop
        return self.run_polling_loop()

    def run_idle_loop(self):
        """Main IDLE event loop with robust error handling and periodic fallback."""
        self.running = True
        self.log_with_timestamp("⚡ TravelBot IDLE mode starting...")
        
        # Setup IDLE connection
        if not self.setup_idle_mode():
            return self.fallback_to_polling("IDLE setup failed")
        
        # Also maintain regular IMAP connection for operations
        if not self.connect_to_mailbox():
            self.log_with_timestamp("💥 Failed to connect to mailbox. Exiting.", "ERROR")
            return
        
        # IMPORTANT: Check for existing unread emails at startup
        self.log_with_timestamp("🔍 Checking for existing unread emails at startup...")
        self.check_and_process_emails("startup")
        
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        # Shared state for IDLE callback communication
        self.idle_notification_received = False
        
        try:
            while self.running:
                try:
                    if self.verbose:
                        self.log_with_timestamp("👂 Starting IDLE monitoring cycle...")
                    
                    # Get IDLE configuration
                    imap_config = self.config['email']['imap']
                    idle_timeout = imap_config.get('idle_timeout', 1740)  # 29 minutes
                    check_interval = 300  # Check every 5 minutes instead of full timeout
                    
                    # Use shorter intervals for better responsiveness
                    actual_timeout = min(idle_timeout, check_interval)
                    
                    # Reset notification flag
                    self.idle_notification_received = False
                    
                    # Start IDLE monitoring
                    idle_thread = self.email_client.start_idle_monitoring(
                        self.idle_client,
                        self.set_idle_notification_flag,
                        timeout=actual_timeout,
                        verbose=self.verbose
                    )
                    
                    # Wait for IDLE thread to complete or notification
                    idle_thread.join()
                    
                    # Check if we received a notification or timeout occurred
                    if self.idle_notification_received:
                        self.log_with_timestamp("📬 IDLE notification received - checking for new emails")
                        self.check_and_process_emails("IDLE notification", idle_triggered=True)
                    else:
                        self.log_with_timestamp("⏰ IDLE timeout - performing periodic email check")
                        self.check_and_process_emails("periodic check")
                    
                    # Reset error counter on successful cycle
                    consecutive_errors = 0
                    
                    # Brief pause before next IDLE cycle
                    time.sleep(2)
                    
                except Exception as e:
                    consecutive_errors += 1
                    self.log_with_timestamp(f"✗ IDLE cycle error ({consecutive_errors}/{max_consecutive_errors}): {e}", "ERROR")
                    import traceback
                    traceback.print_exc()
                    
                    if consecutive_errors >= max_consecutive_errors:
                        return self.fallback_to_polling("Too many consecutive IDLE errors")
                        
                    # Wait before retry, with exponential backoff
                    wait_time = min(60, 5 * consecutive_errors)
                    self.log_with_timestamp(f"⏳ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    
        except KeyboardInterrupt:
            self.log_with_timestamp("🛑 Received interrupt signal. Shutting down...")
        except Exception as e:
            self.log_with_timestamp(f"💥 Fatal IDLE error: {e}", "ERROR")
            import traceback
            traceback.print_exc()
        finally:
            self.running = False
            if self.idle_client:
                self.email_client.idle_cleanup(self.idle_client)
            self.email_client.logout()
            self.log_with_timestamp("🏁 TravelBot IDLE mode stopped")

    def run_main_loop(self):
        """Unified entry point for IDLE or polling mode."""
        if self.idle_enabled:
            try:
                return self.run_idle_loop()
            except Exception as e:
                self.log_with_timestamp(f"IDLE mode failed: {e}, falling back to polling", "ERROR")
                return self.fallback_to_polling("IDLE mode exception")
        else:
            return self.run_polling_loop()

    def connect_to_mailbox(self):
        """Connect to the email server with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                imap_config = self.config['email']['imap']
                connected = self.email_client.connect_imap(
                    imap_config['host'], 
                    imap_config['username'], 
                    imap_config['password']
                )
                
                if connected:
                    # Select INBOX
                    typ, data = self.email_client.mail.select("INBOX")
                    if typ == 'OK':
                        self.log_with_timestamp("✓ Successfully connected to mailbox")
                        return True
                    else:
                        self.log_with_timestamp(f"✗ Failed to select INBOX: {data}", "ERROR")
                        return False
                else:
                    self.log_with_timestamp(f"✗ Connection attempt {attempt + 1} failed", "WARN")
                    
            except Exception as e:
                self.log_with_timestamp(f"✗ Connection error (attempt {attempt + 1}): {e}", "ERROR")
                
            if attempt < max_retries - 1:
                time.sleep(5)  # Wait 5 seconds before retry
                
        return False
    
    def search_for_unread_emails(self):
        """Search for unread emails in the mailbox with enhanced error handling."""
        try:
            search_result = self.email_client.search_emails(['UNSEEN'])
            
            # Handle new structured response format
            if isinstance(search_result, dict):
                if search_result['success']:
                    unread_uids = search_result['uids']
                    if unread_uids:
                        self.log_with_timestamp(f"📬 Found {len(unread_uids)} unread email(s): {unread_uids}")
                    else:
                        if self.verbose:
                            self.log_with_timestamp("📭 No unread emails found")
                    return unread_uids
                else:
                    # Search failed - this is the key improvement for distinguishing errors
                    error_msg = search_result.get('error', 'Unknown search error')
                    self.log_with_timestamp(f"✗ Email search failed: {error_msg}", "ERROR")
                    
                    # If it's a connection error, attempt reconnection
                    if 'connection' in error_msg.lower() or 'eof' in error_msg.lower() or 'auth' in error_msg.lower():
                        self.log_with_timestamp("🔌 Connection issue detected, attempting to reconnect...", "WARN")
                        if self.connect_to_mailbox():
                            self.log_with_timestamp("✓ Reconnection successful, retrying search...")
                            # Retry search once after reconnection
                            retry_result = self.email_client.search_emails(['UNSEEN'])
                            if isinstance(retry_result, dict) and retry_result['success']:
                                return retry_result['uids']
                        self.log_with_timestamp("✗ Reconnection failed or retry unsuccessful", "ERROR")
                    
                    return []
            else:
                # Fallback for old format (shouldn't happen with new code)
                self.log_with_timestamp("⚠️  Received old search format, converting...", "WARN")
                return search_result if search_result else []
                
        except Exception as e:
            self.log_with_timestamp(f"✗ Unexpected error during email search: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return []
    
    def build_comprehensive_travel_prompt(self, email_content):
        """Build comprehensive prompt that captures ALL travel-related services."""
        
        prompt = f"""You are a professional travel itinerary processing assistant with expertise in detecting ALL types of travel-related services and appointments.

EMAIL METADATA:
Subject: {email_content['subject']}
From: {email_content['from']}
Date: {email_content['date']}

EMAIL BODY CONTENT:
{email_content['body_text']}
"""

        if email_content['pdf_text'] and len(email_content['pdf_text']) > 50:
            prompt += f"""

PDF ATTACHMENT CONTENT:
{email_content['pdf_text']}
"""

        prompt += """

TASK: Extract ALL travel-related events and services, then output a JSON object with two fields: timezone-aware .ics calendar content and a professional email summary.

COMPREHENSIVE TRAVEL SERVICE DETECTION:
Look for ANY scheduled travel-related services including but not limited to:

TRANSPORTATION:
- Flights (commercial airlines, private jets, charter flights)
- Ground transportation (rental cars, car services, rideshares, taxis)
- Rail travel (trains, subways, metro)
- Marine transport (ferries, cruises, water taxis)
- Transfers (airport shuttles, hotel shuttles, private drivers)

ACCOMMODATION:
- Hotels, motels, resorts, bed & breakfasts
- Vacation rentals (Airbnb, VRBO, etc.)
- Corporate housing, extended stays
- Hostels, lodges, camps

SERVICES & APPOINTMENTS:
- Restaurant reservations with specific times
- Tour bookings and guided excursions
- Meeting locations and conference venues
- Spa appointments, golf tee times
- Entertainment bookings (shows, concerts, events)
- Business meetings at specific venues
- Airport lounge access with times
- Baggage services, concierge services
- Travel insurance appointments
- Visa/passport appointments
- Any service with a scheduled time and location

CRITICAL TIMEZONE REQUIREMENTS:
1. Identify airport/location timezones (BOS=America/New_York, DFW=America/Chicago, etc.)
2. Generate proper VTIMEZONE definitions for each unique timezone
3. Use TZID references for all timed events (DTSTART;TZID=America/New_York:20250602T080000)
4. Departure times use origin timezone, arrival times use destination timezone

CATEGORY MAPPING FOR .ICS:
- Flights: CATEGORIES:TRAVEL,FLIGHT (TRANSP:OPAQUE - busy time)
- Hotels: CATEGORIES:TRAVEL,HOTEL (TRANSP:TRANSPARENT - free time)
- Car rentals: CATEGORIES:TRAVEL,CAR_RENTAL (TRANSP:TRANSPARENT - free time)
- Ground transport: CATEGORIES:TRAVEL,TRANSPORT (TRANSP:OPAQUE - busy time)
- Restaurants: CATEGORIES:TRAVEL,DINING (TRANSP:OPAQUE - busy time)
- Tours/Activities: CATEGORIES:TRAVEL,ACTIVITY (TRANSP:OPAQUE - busy time)
- Business meetings: CATEGORIES:TRAVEL,MEETING (TRANSP:OPAQUE - busy time)
- General travel services: CATEGORIES:TRAVEL,SERVICE (TRANSP:TRANSPARENT - free time)
- Entertainment: CATEGORIES:TRAVEL,ENTERTAINMENT (TRANSP:OPAQUE - busy time)
- Events: CATEGORIES:TRAVEL,EVENT (TRANSP:OPAQUE - busy time)
- Other travel services: CATEGORIES:TRAVEL,OTHER (TRANSP:TRANSPARENT - free time)

EMAIL SUMMARY FORMATTING:
Create a professional travel digest with appropriate emoji categories:
✈️ FLIGHTS & TRANSPORTATION
🏨 ACCOMMODATION  
🍽️ DINING & RESERVATIONS
🎯 ACTIVITIES & TOURS
🤝 MEETINGS & APPOINTMENTS
🚗 GROUND TRANSPORTATION
🎫 ENTERTAINMENT & EVENTS
📋 OTHER TRAVEL SERVICES

FORMAT REQUIREMENTS:
- For multiple flights, use a BULLET LIST ENTRY PER FLIGHT LEG with all key details on separate lines per leg!
- Use format: "Day Date: FlightNumber Origin→Destination (Departure Time TZ → Arrival Time TZ) | Seat | Confirmation" for each bullet entry
- DO NOT combine multiple flight legs on one bullet entry
- Keep hotel, car rental, and other services concise but complete
- Use consistent timezone abbreviations (CT, ET, PT, MT, etc.)

OUTPUT FORMAT:
Return ONLY a valid JSON object with exactly these two fields:

{
  "ics_content": "[Complete .ics file with VTIMEZONE definitions and all travel events]",
  "email_summary": "[Professional travel digest with all services organized by category, using local timezones and emoji headers]"
}

If no travel information is found, return empty ics_content with VCALENDAR headers only and email_summary explaining no travel events were detected.
"""
        
        return prompt
    
    def get_comprehensive_response_from_llm(self, prompt):
        """Get structured JSON response with both .ics content and email summary."""
        api_key = self.config['openai']['api_key']
        endpoint = self.config['openai']['endpoint']
        model = self.config['openai'].get('model', 'gpt-4o-e2')

        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,
            "max_tokens": 8000
        }

        try:
            self.log_with_timestamp(f"🧠 Calling Azure OpenAI ({model})...")
            response = requests.post(endpoint, headers=headers, json=data)
            response.raise_for_status()
            rj = response.json()

            if "choices" in rj and "message" in rj["choices"][0]:
                content = rj["choices"][0]["message"]["content"]
            else:
                raise ValueError("Unexpected LLM response format")

            # Clean up markdown code blocks if present
            if content.startswith("```json") and content.endswith("```"):
                content = content[7:-3].strip()
            elif content.startswith("```") and content.endswith("```"):
                content = content[3:-3].strip()
                
            self.log_with_timestamp(f"✓ Received {len(content)} characters from LLM")
            
            # Parse JSON response
            try:
                parsed_response = json.loads(content)
                if "ics_content" in parsed_response and "email_summary" in parsed_response:
                    return parsed_response
                else:
                    raise ValueError("Response missing required fields")
            except json.JSONDecodeError as e:
                self.log_with_timestamp(f"✗ JSON parse error: {e}", "ERROR")
                raise ValueError("LLM returned invalid JSON")
            
        except Exception as e:
            self.log_with_timestamp(f"✗ LLM error: {e}", "ERROR")
            raise

    def determine_reply_address(self, original_email):
        """Determine appropriate reply address with default reply-to policy."""
        from_addr = original_email['from'].lower()
        subject = original_email['subject'].lower()
        body = original_email['body_text'].lower()
        
        # Check for do-not-reply indicators
        do_not_reply_indicators = [
            'noreply', 'no-reply', 'do-not-reply', 'donotreply',
            'auto-confirm', 'automated', 'system', 'notification'
        ]
        
        is_do_not_reply = any(indicator in from_addr for indicator in do_not_reply_indicators)
        
        # Check for airline/system emails
        airline_domains = [
            'american.airlines', 'delta.com', 'united.com', 'southwest.com',
            'jetblue.com', 'aa.com', 'ual.com', 'expedia.com', 'travelocity.com',
            'info.email.aa.com', 'email.aa.com'
        ]
        
        is_airline_system = any(domain in from_addr for domain in airline_domains)
        
        if is_do_not_reply or is_airline_system:
            # Check if forwarded
            forwarding_indicators = ['fw:', 'fwd:', 'forwarded']
            if any(indicator in subject for indicator in forwarding_indicators):
                if 'from:' in body and '@' in body:
                    lines = original_email['body_text'].split('\n')
                    for line in lines[:10]:
                        if 'from:' in line.lower() and '@' in line:
                            email_match = re.search(r'[\w\.-]+@[\w\.-]+', line)
                            if email_match:
                                forwarder_email = email_match.group(0)
                                self.log_with_timestamp(f"📤 Forwarded email detected, replying to: {forwarder_email}")
                                return forwarder_email
            
            # Use default reply-to address
            default_reply = self.config['processing'].get('default_reply_to')
            if default_reply:
                self.log_with_timestamp(f"📤 Do-not-reply detected, using default: {default_reply}")
                return default_reply
            else:
                self.log_with_timestamp("⚠️  Do-not-reply detected, no default configured", "WARN")
                return None
        
        return original_email['from']

    def generate_unique_ics_filename(self, email_uid):
        """Generate a unique ICS filename with filesystem check."""
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        
        # Base filename using email UID (should be unique, but add extra safety)
        base_filename = f"itinerary_{timestamp}_{unique_id}_{email_uid}.ics"
        ics_filepath = os.path.join(self.ics_dir, base_filename)
        
        # Filesystem uniqueness check
        counter = 1
        while os.path.exists(ics_filepath):
            name_part = f"itinerary_{timestamp}_{unique_id}_{email_uid}_{counter}"
            test_filename = f"{name_part}.ics"
            ics_filepath = os.path.join(self.ics_dir, test_filename)
            counter += 1
            
        return ics_filepath

    def cleanup_work_files(self, email_content, ics_filepath):
        """Clean up work files after successful processing."""
        if self.retain_files:
            self.log_with_timestamp(f"🔒 Retaining work files (--retain-files enabled)")
            return
            
        files_to_cleanup = []
        
        # Add PDF attachment if exists
        if email_content.get('pdf_filepath') and os.path.exists(email_content['pdf_filepath']):
            files_to_cleanup.append(email_content['pdf_filepath'])
            
        # Add ICS file if exists
        if ics_filepath and os.path.exists(ics_filepath):
            files_to_cleanup.append(ics_filepath)
            
        # Remove files
        cleaned_count = 0
        for filepath in files_to_cleanup:
            try:
                os.remove(filepath)
                cleaned_count += 1
                self.log_with_timestamp(f"🗑️  Cleaned up: {os.path.basename(filepath)}")
            except Exception as e:
                self.log_with_timestamp(f"⚠️  Failed to cleanup {filepath}: {e}", "WARN")
                
        if cleaned_count > 0:
            self.log_with_timestamp(f"✨ Cleaned up {cleaned_count} work file(s)")

    def send_comprehensive_response_email(self, original_email, ics_content, email_summary):
        """Send response email with tailored content and calendar attachment."""
        
        reply_to = self.determine_reply_address(original_email)
        if not reply_to:
            self.log_with_timestamp("⏭️  Skipping reply - no valid address")
            return True, None
        
        msg = EmailMessage()
        
        # Clean subject line
        clean_subject = original_email['subject'].replace('\n', ' ').replace('\r', ' ').strip()
        clean_subject = ' '.join(clean_subject.split())
        
        msg['Subject'] = f"Re: {clean_subject[:100]} - Complete Travel Itinerary"
        msg['From'] = self.config['smtp']['user']
        msg['To'] = reply_to
        
        # Use LLM-generated email summary as main body
        body = f"""Your travel itinerary has been processed successfully!

{email_summary}

📅 CALENDAR ATTACHMENT:
The attached .ics file contains all your travel events with proper timezone handling. Simply double-click the attachment to add all events to your Outlook or Google calendar.

✅ TIMEZONE INTELLIGENCE:
- Flight times show in local airport timezones
- Hotel times display in destination timezone  
- Your calendar adjusts correctly when traveling
- International events handled properly

Best regards,
TravelBot Production Processing System
"""
        msg.set_content(body)
        
        # Generate unique ICS filename and save to work directory
        ics_filepath = self.generate_unique_ics_filename(original_email['uid'])
        with open(ics_filepath, 'w', encoding='utf-8') as f:
            f.write(ics_content)
        
        # Read ICS file for email attachment
        with open(ics_filepath, 'rb') as f:
            ics_data = f.read()
        msg.add_attachment(ics_data, maintype="text", subtype="calendar", 
                         filename=f"travel_itinerary_{original_email['uid']}.ics")
        
        # Send email
        try:
            with smtplib.SMTP(self.config['smtp']['host'], self.config['smtp']['port']) as smtp:
                smtp.starttls()
                smtp.login(self.config['smtp']['user'], self.config['smtp']['password'])
                smtp.send_message(msg)
            
            self.log_with_timestamp(f"✅ Response sent to {reply_to}")
            return True, ics_filepath
            
        except Exception as e:
            self.log_with_timestamp(f"✗ Email send failed: {e}", "ERROR")
            return False, ics_filepath

    def process_single_email(self, email_uid):
        """Process a single email with comprehensive travel detection."""
        self.log_with_timestamp(f"🔄 Processing email UID {email_uid}")
        
        ics_filepath = None
        try:
            # Extract complete email content using new attachments directory
            email_content = self.email_client.get_complete_email_content(email_uid, self.attachments_dir)
            if not email_content:
                self.log_with_timestamp(f"✗ Failed to extract content for UID {email_uid}", "ERROR")
                return False
            
            self.log_with_timestamp(f"📧 Subject: {email_content['subject'][:100]}...")
            self.log_with_timestamp(f"📧 From: {email_content['from']}")
            self.log_with_timestamp(f"📧 Body: {len(email_content['body_text'])} chars")
            if email_content['pdf_text']:
                self.log_with_timestamp(f"📎 PDF: {len(email_content['pdf_text'])} chars")
            
            # Build comprehensive travel prompt
            prompt = self.build_comprehensive_travel_prompt(email_content)
            self.log_with_timestamp(f"📝 Built prompt: {len(prompt)} characters")
            
            # Get structured response from LLM
            llm_response = self.get_comprehensive_response_from_llm(prompt)
            
            ics_content = llm_response['ics_content']
            email_summary = llm_response['email_summary']
            
            self.log_with_timestamp(f"📅 Generated .ics: {len(ics_content)} chars")
            self.log_with_timestamp(f"📧 Generated summary: {len(email_summary)} chars")
            
            # Send comprehensive response email
            success, ics_filepath = self.send_comprehensive_response_email(email_content, ics_content, email_summary)
            
            if success:
                # Mark original email as read
                self.email_client.mark_emails_as_seen([email_uid])
                
                # Clean up work files after successful processing
                self.cleanup_work_files(email_content, ics_filepath)
                
                self.log_with_timestamp(f"✅ Successfully processed UID {email_uid}")
                return True
            else:
                self.log_with_timestamp(f"✗ Failed to send response for UID {email_uid}", "ERROR")
                # Clean up even on failure to avoid accumulating files
                if not self.retain_files:
                    self.cleanup_work_files(email_content, ics_filepath)
                return False
                
        except Exception as e:
            self.log_with_timestamp(f"✗ Processing error for UID {email_uid}: {e}", "ERROR")
            # Clean up on error to avoid accumulating files
            if not self.retain_files and ics_filepath:
                self.cleanup_work_files({}, ics_filepath)
            return False
    
    def process_emails_batch(self, email_uids):
        """Process a batch of emails."""
        success_count = 0
        total_count = len(email_uids)
        
        self.log_with_timestamp(f"📦 Processing batch of {total_count} email(s)")
        
        for uid in email_uids:
            try:
                if self.process_single_email(uid):
                    success_count += 1
                time.sleep(1)  # Brief pause between emails
            except Exception as e:
                self.log_with_timestamp(f"✗ Batch processing error for UID {uid}: {e}", "ERROR")
        
        self.log_with_timestamp(f"📊 Batch complete: {success_count}/{total_count} successful")
        return success_count
    
    def run_polling_loop(self):
        """Main polling loop for the daemon."""
        self.running = True
        self.log_with_timestamp("🚀 TravelBot Daemon starting...")
        
        # Initial connection
        if not self.connect_to_mailbox():
            self.log_with_timestamp("💥 Failed to connect to mailbox. Exiting.", "ERROR")
            return
        
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        try:
            while self.running:
                cycle_start = datetime.now()
                self.log_with_timestamp(f"🔍 Checking mailbox...")
                
                try:
                    # Search for unread emails
                    unread_uids = self.search_for_unread_emails()
                    
                    if unread_uids:
                        # Process emails
                        processed = self.process_emails_batch(unread_uids)
                        self.log_with_timestamp(f"✨ Cycle complete: {processed} email(s) processed")
                    else:
                        self.log_with_timestamp("💤 No unread emails found")
                    
                    consecutive_errors = 0  # Reset error counter on success
                    
                except Exception as e:
                    consecutive_errors += 1
                    self.log_with_timestamp(f"✗ Cycle error ({consecutive_errors}/{max_consecutive_errors}): {e}", "ERROR")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        self.log_with_timestamp("💥 Too many consecutive errors. Attempting reconnection...", "ERROR")
                        self.email_client.logout()
                        time.sleep(30)  # Wait before reconnection
                        if not self.connect_to_mailbox():
                            self.log_with_timestamp("💥 Reconnection failed. Exiting.", "ERROR")
                            break
                        consecutive_errors = 0
                
                # Calculate sleep time
                cycle_duration = (datetime.now() - cycle_start).total_seconds()
                sleep_time = max(0, self.poll_interval - cycle_duration)
                
                if sleep_time > 0:
                    self.log_with_timestamp(f"😴 Sleeping {sleep_time:.1f}s until next check...")
                    time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            self.log_with_timestamp("🛑 Received interrupt signal. Shutting down...")
        except Exception as e:
            self.log_with_timestamp(f"💥 Fatal error: {e}", "ERROR")
        finally:
            self.running = False
            self.email_client.logout()
            self.log_with_timestamp("🏁 TravelBot Daemon stopped")

def main():
    parser = argparse.ArgumentParser(description='TravelBot Production Email Processing Daemon')
    parser.add_argument('--poll-interval', type=int, default=30, 
                       help='Email polling interval in seconds (default: 30)')
    parser.add_argument('--retain-files', action='store_true',
                       help='Retain work files (attachments and ICS files) after processing for debugging')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging (shows all IDLE monitoring details)')
    
    args = parser.parse_args()
    
    daemon = TravelBotDaemon(poll_interval=args.poll_interval, retain_files=args.retain_files, verbose=args.verbose)
    daemon.run_main_loop()

if __name__ == '__main__':
    main()
