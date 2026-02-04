#!/usr/bin/env python3
"""
TravelBot Production Email Processing Daemon

This daemon continuously monitors the configured mailbox for new travel emails,
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
from .auto_reply_filter import should_skip_auto_reply, ReplyRateLimiter
import re
import json
import email
from icalendar import Calendar

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
        
        # Rate limiter for reply loop prevention (max 3 replies per address per hour)
        self.reply_rate_limiter = ReplyRateLimiter(max_replies=3, window_seconds=3600)
        
        # Failure tracking for poison email prevention (Issue 001)
        # Maps email UID -> failure count
        self.email_failure_counts = {}
        self.max_failures_per_email = 3
        
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

MESSAGE CLASSIFICATION (IMPORTANT - DO THIS FIRST):
Before processing, classify this email into one of these categories:
- "TRAVEL_ITINERARY": Contains travel bookings, reservations, or event information that should be processed
- "AUTO_REPLY": Out-of-office reply, vacation auto-response, or automatic acknowledgment
- "BOUNCE": Delivery failure notification, undeliverable mail, or system error message
- "NON_TRAVEL": Regular email without travel/event information (but not an auto-reply or bounce)

Signs of AUTO_REPLY: phrases like "I am out of the office", "automatic reply", "away from my desk", "on vacation until", "will respond when I return"
Signs of BOUNCE: phrases like "delivery failed", "undeliverable", "mailbox full", "user unknown", "could not be delivered"

OUTPUT FORMAT:
Return ONLY a valid JSON object with these fields:

{
  "message_type": "TRAVEL_ITINERARY | AUTO_REPLY | BOUNCE | NON_TRAVEL",
  "message_type_reason": "[Brief explanation of why you classified it this way]",
  "ics_content": "[Complete .ics file with VTIMEZONE definitions and all travel events - empty VCALENDAR if not TRAVEL_ITINERARY]",
  "email_summary": "[Professional travel digest OR brief explanation if not travel-related]"
}

If message_type is AUTO_REPLY or BOUNCE: set ics_content to empty VCALENDAR headers only, and email_summary should briefly explain why no processing was done.
If message_type is NON_TRAVEL: still process any date/time/event information found (meetings, appointments, etc.) and generate appropriate ICS content.
If message_type is TRAVEL_ITINERARY: process normally with full ICS and summary.
"""
        
        return prompt
    
    def _extract_json_from_llm_response(self, content):
        """Extract JSON from LLM response, handling various formats (Issue 003)."""
        original_content = content
        
        # Strip leading/trailing whitespace
        content = content.strip()
        
        # Handle markdown code blocks with various fence styles
        # Pattern: ```json ... ``` or ``` ... ``` or ~~~ ... ~~~
        fence_patterns = [
            (r'```json\s*\n?', r'\n?```'),
            (r'```\s*\n?', r'\n?```'),
            (r'~~~json\s*\n?', r'\n?~~~'),
            (r'~~~\s*\n?', r'\n?~~~'),
        ]
        
        for start_pattern, end_pattern in fence_patterns:
            start_match = re.match(start_pattern, content, re.IGNORECASE)
            if start_match:
                # Remove start fence
                content = content[start_match.end():]
                # Remove end fence if present
                end_match = re.search(end_pattern + r'\s*$', content)
                if end_match:
                    content = content[:end_match.start()]
                content = content.strip()
                break
        
        # Try direct JSON parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Find first { and last } to extract JSON object
        first_brace = content.find('{')
        last_brace = content.rfind('}')
        
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            json_substring = content[first_brace:last_brace + 1]
            try:
                return json.loads(json_substring)
            except json.JSONDecodeError:
                pass
        
        # Log the problematic content for debugging (avoid logging full potentially sensitive content)
        self.log_with_timestamp(
            f"✗ Could not extract JSON from LLM response (length: {len(original_content)})",
            "ERROR",
        )
        # Only log a short, truncated snippet to avoid exposing PII/travel details
        snippet = original_content[:100]
        self.log_with_timestamp(
            f"✗ Response snippet (truncated to 100 chars): {snippet!r}",
            "ERROR",
        )
        
        raise ValueError("Could not extract valid JSON from LLM response")

    def get_comprehensive_response_from_llm(self, prompt):
        """Get structured JSON response with both .ics content and email summary.
        
        Includes timeout and retry logic (Issue 002) and robust JSON parsing (Issue 003).
        """
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

        # Retry configuration (Issue 002)
        max_retries = 3
        base_delay = 2  # seconds
        timeout = (10, 120)  # (connect timeout, read timeout) in seconds
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                self.log_with_timestamp(f"🧠 Calling Azure OpenAI ({model})... (attempt {attempt + 1}/{max_retries})")
                response = requests.post(endpoint, headers=headers, json=data, timeout=timeout)
                response.raise_for_status()
                rj = response.json()

                if "choices" in rj and "message" in rj["choices"][0]:
                    content = rj["choices"][0]["message"]["content"]
                else:
                    raise ValueError("Unexpected LLM response format")
                    
                self.log_with_timestamp(f"✓ Received {len(content)} characters from LLM")
                
                # Parse JSON response using robust extraction (Issue 003)
                parsed_response = self._extract_json_from_llm_response(content)
                
                if "ics_content" in parsed_response and "email_summary" in parsed_response:
                    # Ensure message_type exists (default to TRAVEL_ITINERARY for backward compatibility)
                    if "message_type" not in parsed_response:
                        parsed_response["message_type"] = "TRAVEL_ITINERARY"
                        parsed_response["message_type_reason"] = "No classification provided, assuming travel itinerary"
                    return parsed_response
                else:
                    raise ValueError("Response missing required fields (ics_content, email_summary)")
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                self.log_with_timestamp(f"✗ LLM request timeout (attempt {attempt + 1}): {e}", "ERROR")
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                self.log_with_timestamp(f"✗ LLM connection error (attempt {attempt + 1}): {e}", "ERROR")
            except requests.exceptions.HTTPError as e:
                last_exception = e
                # Retry on 5xx server errors, but not on 4xx client errors
                if response.status_code >= 500:
                    self.log_with_timestamp(f"✗ LLM server error {response.status_code} (attempt {attempt + 1}): {e}", "ERROR")
                else:
                    self.log_with_timestamp(f"✗ LLM client error {response.status_code}: {e}", "ERROR")
                    raise  # Don't retry client errors
            except ValueError as e:
                # JSON parsing or response format errors - don't retry
                self.log_with_timestamp(f"✗ LLM response error: {e}", "ERROR")
                raise
            except Exception as e:
                last_exception = e
                self.log_with_timestamp(f"✗ LLM unexpected error (attempt {attempt + 1}): {e}", "ERROR")
            
            # Exponential backoff before retry
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                self.log_with_timestamp(f"⏳ Retrying in {delay} seconds...")
                time.sleep(delay)
        
        # All retries exhausted
        self.log_with_timestamp(f"✗ LLM call failed after {max_retries} attempts", "ERROR")
        raise last_exception or Exception("LLM call failed after all retries")

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

    def _validate_ics_content(self, ics_content):
        """Validate ICS content using icalendar library (Issue 005).
        
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        try:
            cal = Calendar.from_ical(ics_content)
            # Check that it has at least the basic calendar structure
            if cal.name != 'VCALENDAR':
                return False, "ICS content is not a valid VCALENDAR"
            return True, None
        except Exception as e:
            return False, str(e)

    def _send_email_with_retry(self, msg, reply_to):
        """Send email with timeout and retry logic (Issue 004).
        
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        max_retries = 3
        base_delay = 2  # seconds
        smtp_timeout = 30  # seconds
        
        for attempt in range(max_retries):
            try:
                self.log_with_timestamp(f"📤 Sending email to {reply_to}... (attempt {attempt + 1}/{max_retries})")
                with smtplib.SMTP(self.config['smtp']['host'], self.config['smtp']['port'], timeout=smtp_timeout) as smtp:
                    smtp.starttls()
                    smtp.login(self.config['smtp']['user'], self.config['smtp']['password'])
                    smtp.send_message(msg)
                
                self.log_with_timestamp(f"✅ Response sent to {reply_to}")
                return True
                
            except smtplib.SMTPServerDisconnected as e:
                self.log_with_timestamp(f"✗ SMTP server disconnected (attempt {attempt + 1}): {e}", "ERROR")
            except smtplib.SMTPConnectError as e:
                self.log_with_timestamp(f"✗ SMTP connection error (attempt {attempt + 1}): {e}", "ERROR")
            except smtplib.SMTPAuthenticationError as e:
                # Don't retry authentication errors
                self.log_with_timestamp(f"✗ SMTP authentication error: {e}", "ERROR")
                return False
            except smtplib.SMTPRecipientsRefused as e:
                # Don't retry recipient errors
                self.log_with_timestamp(f"✗ SMTP recipients refused: {e}", "ERROR")
                return False
            except TimeoutError as e:
                self.log_with_timestamp(f"✗ SMTP timeout (attempt {attempt + 1}): {e}", "ERROR")
            except OSError as e:
                # Network-related errors
                self.log_with_timestamp(f"✗ SMTP network error (attempt {attempt + 1}): {e}", "ERROR")
            except Exception as e:
                self.log_with_timestamp(f"✗ SMTP unexpected error (attempt {attempt + 1}): {e}", "ERROR")
            
            # Exponential backoff before retry
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                self.log_with_timestamp(f"⏳ Retrying SMTP in {delay} seconds...")
                time.sleep(delay)
        
        self.log_with_timestamp(f"✗ Email send failed after {max_retries} attempts", "ERROR")
        return False

    def send_comprehensive_response_email(self, original_email, ics_content, email_summary):
        """Send response email with tailored content and calendar attachment.
        
        Includes ICS validation (Issue 005) and SMTP timeout/retry (Issue 004).
        """
        
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
        
        # Validate ICS content before attaching (Issue 005)
        ics_valid, ics_error = self._validate_ics_content(ics_content)
        
        if ics_valid:
            # Use LLM-generated email summary as main body with calendar attachment
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
        else:
            # ICS validation failed - send email without calendar attachment
            self.log_with_timestamp(f"⚠️  ICS validation failed: {ics_error}", "WARN")
            body = f"""Your travel itinerary has been processed!

{email_summary}

⚠️ CALENDAR NOTE:
We were unable to generate a valid calendar attachment for this itinerary. Please add the events to your calendar manually using the information above.

Best regards,
TravelBot Production Processing System
"""
        
        msg.set_content(body)
        
        # Generate unique ICS filename and save to work directory
        ics_filepath = self.generate_unique_ics_filename(original_email['uid'])
        
        if ics_valid:
            with open(ics_filepath, 'w', encoding='utf-8') as f:
                f.write(ics_content)
            
            # Read ICS file for email attachment
            with open(ics_filepath, 'rb') as f:
                ics_data = f.read()
            msg.add_attachment(ics_data, maintype="text", subtype="calendar", 
                             filename=f"travel_itinerary_{original_email['uid']}.ics")
        else:
            # Only write invalid ICS for debugging if retain_files is enabled
            if self.retain_files:
                invalid_filepath = ics_filepath + '.invalid'
                with open(invalid_filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# ICS VALIDATION ERROR: {ics_error}\n\n{ics_content}")
                self.log_with_timestamp(f"📝 Invalid ICS saved for debugging: {invalid_filepath}")
            ics_filepath = None  # Don't return invalid file path
        
        # Send email with retry logic (Issue 004)
        success = self._send_email_with_retry(msg, reply_to)
        return success, ics_filepath

    def _handle_poison_email(self, email_uid, email_content=None):
        """Handle a poison email that has exceeded max failures (Issue 001).
        
        Marks the email as seen and optionally sends a fallback error notification.
        """
        self.log_with_timestamp(f"☠️  Email UID {email_uid} exceeded max failures ({self.max_failures_per_email}), marking as poison", "WARN")
        
        # Mark as seen to stop retrying
        self.email_client.mark_emails_as_seen([email_uid])
        
        # Clear from failure tracking
        if email_uid in self.email_failure_counts:
            del self.email_failure_counts[email_uid]
        
        # Try to send a fallback error notification if we have email content
        if email_content:
            try:
                reply_to = self.determine_reply_address(email_content)
                if reply_to:
                    self._send_fallback_error_email(email_content, reply_to)
            except Exception as e:
                self.log_with_timestamp(f"⚠️  Could not send fallback error email: {e}", "WARN")
        
        self.log_with_timestamp(f"✅ Marked poison email UID {email_uid} as seen (no further retries)")

    def _send_fallback_error_email(self, original_email, reply_to):
        """Send a fallback error notification when processing fails permanently."""
        msg = EmailMessage()
        
        clean_subject = original_email['subject'].replace('\n', ' ').replace('\r', ' ').strip()
        clean_subject = ' '.join(clean_subject.split())
        
        msg['Subject'] = f"Re: {clean_subject[:100]} - Processing Error"
        msg['From'] = self.config['smtp']['user']
        msg['To'] = reply_to
        
        body = """We received your travel-related email but encountered an error while processing it.

Unfortunately, we were unable to extract the travel information and generate a calendar attachment for this email.

WHAT YOU CAN DO:
- Forward the email again if you believe it was a temporary issue
- Manually add the travel events to your calendar using the original email

We apologize for the inconvenience.

Best regards,
TravelBot Production Processing System
"""
        msg.set_content(body)
        
        # Single attempt with timeout (no retry for fallback - best effort only)
        try:
            with smtplib.SMTP(self.config['smtp']['host'], self.config['smtp']['port'], timeout=30) as smtp:
                smtp.starttls()
                smtp.login(self.config['smtp']['user'], self.config['smtp']['password'])
                smtp.send_message(msg)
            self.log_with_timestamp(f"📤 Sent fallback error notification to {reply_to}")
        except Exception as e:
            self.log_with_timestamp(f"⚠️  Failed to send fallback error email: {e}", "WARN")

    def _record_email_failure(self, email_uid):
        """Record a failure for an email and check if it's now a poison email (Issue 001).
        
        Returns:
            bool: True if the email has exceeded max failures and should be treated as poison
        """
        current_count = self.email_failure_counts.get(email_uid, 0) + 1
        self.email_failure_counts[email_uid] = current_count
        
        self.log_with_timestamp(f"📊 Email UID {email_uid} failure count: {current_count}/{self.max_failures_per_email}")
        
        return current_count >= self.max_failures_per_email

    def _clear_email_failure(self, email_uid):
        """Clear failure tracking for an email after successful processing."""
        if email_uid in self.email_failure_counts:
            del self.email_failure_counts[email_uid]

    def process_single_email(self, email_uid):
        """Process a single email with comprehensive travel detection and loop prevention.
        
        Includes poison email handling (Issue 001) to prevent infinite retry loops.
        """
        self.log_with_timestamp(f"🔄 Processing email UID {email_uid}")
        
        # Check if this email has already exceeded max failures
        if self.email_failure_counts.get(email_uid, 0) >= self.max_failures_per_email:
            self.log_with_timestamp(f"⏭️  Skipping poison email UID {email_uid} (already at max failures)")
            self._handle_poison_email(email_uid)
            return True  # Return True to indicate it's been handled
        
        ics_filepath = None
        email_content = None
        try:
            # Extract complete email content using new attachments directory
            email_content = self.email_client.get_complete_email_content(email_uid, self.attachments_dir)
            if not email_content:
                self.log_with_timestamp(f"✗ Failed to extract content for UID {email_uid}", "ERROR")
                if self._record_email_failure(email_uid):
                    self._handle_poison_email(email_uid)
                    return True
                return False
            
            self.log_with_timestamp(f"📧 Subject: {email_content['subject'][:100]}...")
            self.log_with_timestamp(f"📧 From: {email_content['from']}")
            self.log_with_timestamp(f"📧 Body: {len(email_content['body_text'])} chars")
            if email_content['pdf_text']:
                self.log_with_timestamp(f"📎 PDF: {len(email_content['pdf_text'])} chars")
            
            # === LAYER 1: Heuristic-based auto-reply detection (before LLM call) ===
            # Fetch raw message to check headers
            raw_msg = self._fetch_raw_message(email_uid)
            if raw_msg:
                smtp_user = self.config['smtp']['user']
                skip, skip_reason = should_skip_auto_reply(raw_msg, email_content, smtp_user)
                if skip:
                    self.log_with_timestamp(f"🚫 Skipping auto-reply/bounce: {skip_reason}")
                    # Mark as seen to prevent infinite retry, but don't send response
                    self.email_client.mark_emails_as_seen([email_uid])
                    self._clear_email_failure(email_uid)
                    self.log_with_timestamp(f"✅ Marked UID {email_uid} as seen (no reply sent)")
                    return True
            
            # === LAYER 2: Rate limiting check ===
            reply_to = self.determine_reply_address(email_content)
            if reply_to:
                can_send, rate_reason = self.reply_rate_limiter.can_send(reply_to)
                if not can_send:
                    self.log_with_timestamp(f"🚫 Rate limit exceeded for {reply_to}: {rate_reason}")
                    # Mark as seen to prevent infinite retry
                    self.email_client.mark_emails_as_seen([email_uid])
                    self._clear_email_failure(email_uid)
                    self.log_with_timestamp(f"✅ Marked UID {email_uid} as seen (rate limited)")
                    return True
            
            # Build comprehensive travel prompt
            prompt = self.build_comprehensive_travel_prompt(email_content)
            self.log_with_timestamp(f"📝 Built prompt: {len(prompt)} characters")
            
            # Get structured response from LLM
            llm_response = self.get_comprehensive_response_from_llm(prompt)
            
            # === LAYER 3: LLM-based message classification ===
            message_type = llm_response.get('message_type', 'TRAVEL_ITINERARY')
            message_type_reason = llm_response.get('message_type_reason', '')
            
            self.log_with_timestamp(f"🏷️  LLM classified as: {message_type} ({message_type_reason})")
            
            # Skip sending response for auto-replies and bounces detected by LLM
            if message_type in ('AUTO_REPLY', 'BOUNCE'):
                self.log_with_timestamp(f"🚫 LLM detected {message_type}, skipping reply")
                # Mark as seen to prevent infinite retry
                self.email_client.mark_emails_as_seen([email_uid])
                self._clear_email_failure(email_uid)
                self.log_with_timestamp(f"✅ Marked UID {email_uid} as seen (LLM: {message_type})")
                return True
            
            ics_content = llm_response['ics_content']
            email_summary = llm_response['email_summary']
            
            self.log_with_timestamp(f"📅 Generated .ics: {len(ics_content)} chars")
            self.log_with_timestamp(f"📧 Generated summary: {len(email_summary)} chars")
            
            # Send comprehensive response email
            success, ics_filepath = self.send_comprehensive_response_email(email_content, ics_content, email_summary)
            
            if success:
                # Record reply for rate limiting
                if reply_to:
                    self.reply_rate_limiter.record_reply(reply_to)
                
                # Mark original email as read
                self.email_client.mark_emails_as_seen([email_uid])
                
                # Clear failure tracking on success
                self._clear_email_failure(email_uid)
                
                # Clean up work files after successful processing
                self.cleanup_work_files(email_content, ics_filepath)
                
                self.log_with_timestamp(f"✅ Successfully processed UID {email_uid}")
                return True
            else:
                self.log_with_timestamp(f"✗ Failed to send response for UID {email_uid}", "ERROR")
                # Clean up even on failure to avoid accumulating files
                if not self.retain_files:
                    self.cleanup_work_files(email_content, ics_filepath)
                
                # Record failure and check if poison
                if self._record_email_failure(email_uid):
                    self._handle_poison_email(email_uid, email_content)
                    return True
                return False
                
        except Exception as e:
            self.log_with_timestamp(f"✗ Processing error for UID {email_uid}: {e}", "ERROR")
            # Clean up on error to avoid accumulating files
            if not self.retain_files and ics_filepath:
                self.cleanup_work_files({}, ics_filepath)
            
            # Record failure and check if poison (Issue 001)
            if self._record_email_failure(email_uid):
                self._handle_poison_email(email_uid, email_content)
                return True
            return False
    
    def _fetch_raw_message(self, email_uid):
        """Fetch raw email message to access headers for auto-reply detection."""
        try:
            if not self.email_client.mail:
                return None
            typ, data = self.email_client.mail.uid('fetch', email_uid, '(RFC822)')
            if typ != 'OK' or not data or not data[0]:
                return None
            # Validate IMAP response structure before accessing
            if not isinstance(data[0], tuple) or len(data[0]) < 2:
                self.log_with_timestamp(f"⚠️  Unexpected IMAP response structure for UID {email_uid}", "WARN")
                return None
            raw_email_bytes = data[0][1]
            if not raw_email_bytes:
                return None
            return email.message_from_bytes(raw_email_bytes)
        except Exception as e:
            self.log_with_timestamp(f"⚠️  Could not fetch raw message for header check: {e}", "WARN")
            return None
    
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
