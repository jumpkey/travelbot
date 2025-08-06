import imaplib
import ssl
import os
import email # For parsing email messages
import time # For generating unique filenames
import uuid
import threading
import backoff
from html2text import html2text
import re
try:
    from imapclient import IMAPClient
    IMAPCLIENT_AVAILABLE = True
except ImportError:
    IMAPCLIENT_AVAILABLE = False
    print("Warning: IMAPClient not available. IDLE functionality disabled.")

class EmailClient:
    def __init__(self):
        """
        Initializes the EmailClient.
        """
        self.mail = None # To store the IMAP connection object

    def connect_imap(self, hostname, username, password):
        """
        Connects to an IMAP server using IMAP4_SSL and logs in with password.
        """
        print(f"Attempting to connect to {hostname} as {username}...")
        
        try:
            self.mail = imaplib.IMAP4_SSL(hostname)
            print(f"SSL connection object created for {hostname}. Attempting login for {username}...")
            
            response_status, response_data = self.mail.login(username, password)
            
            decoded_response_data = [data.decode() if isinstance(data, bytes) else str(data) for data in response_data]
            print(f"Login attempt response status: {response_status}, data: {decoded_response_data}")

            if response_status == 'OK':
                print(f"Successfully logged in as {username} to {hostname}.")
                # Store connection details for potential reconnection
                self._last_connection_details = (hostname, username, password)
                return self.mail
            else:
                print(f"Login failed for {username}. Server response status: {response_status}, data: {decoded_response_data}")
                try:
                    self.mail.shutdown()
                except Exception as e_shutdown: # nosec
                    print(f"Error during shutdown after failed login: {e_shutdown}")
                self.mail = None # Clear connection on failure
                return None
        except imaplib.IMAP4.error as e:
            print(f"IMAP4 error during connection/login for {username} to {hostname}: {e}")
            if self.mail:
                try:
                    self.mail.shutdown()
                except Exception as e_shutdown_inner: # nosec
                    print(f"Error during shutdown after IMAP4.error: {e_shutdown_inner}")
            self.mail = None
            return None
        except Exception as e:
            print(f"An unexpected error occurred connecting to {hostname} for {username}: {e}")
            if self.mail:
                try:
                    self.mail.shutdown()
                except Exception as e_shutdown_unexpected: # nosec
                    print(f"Error during shutdown after unexpected error: {e_shutdown_unexpected}")
            self.mail = None
            return None

    def validate_connection(self):
        """Test if the IMAP connection is still alive and responsive."""
        if not self.mail:
            return False
        try:
            # Simple NOOP command to test connection
            typ, data = self.mail.noop()
            if typ == 'OK':
                return True
            else:
                print(f"Connection validation failed: {typ} - {data}")
                return False
        except Exception as e:
            print(f"Connection validation error: {e}")
            return False

    def search_emails(self, criteria, charset='UTF-8', max_retries=3):
        """Enhanced search with connection recovery and retry logic."""
        if not self.mail:
            print("Not connected to IMAP server. Call connect_imap first.")
            return {'success': False, 'uids': [], 'error': 'Not connected'}
        
        # Store connection details for potential reconnection
        if not hasattr(self, '_last_connection_details'):
            print("Warning: No connection details stored for recovery")
            return self._perform_search(criteria, charset)
        
        for attempt in range(max_retries):
            try:
                # Validate connection before searching
                if not self.validate_connection():
                    print(f"Connection invalid on attempt {attempt + 1}, attempting to reconnect...")
                    if not self._reconnect():
                        print(f"Reconnection failed on attempt {attempt + 1}")
                        if attempt == max_retries - 1:
                            return {'success': False, 'uids': [], 'error': 'Connection failed after retries'}
                        continue
                
                # Perform the actual search
                result = self._perform_search(criteria, charset)
                if result['success']:
                    return result
                else:
                    # If search failed but connection seems OK, it might be a server issue
                    print(f"Search failed on attempt {attempt + 1}: {result['error']}")
                    if attempt < max_retries - 1:
                        import time
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        print(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    return result
                    
            except Exception as e:
                print(f"Search attempt {attempt + 1} failed with exception: {e}")
                if attempt < max_retries - 1:
                    import time
                    wait_time = 2 ** attempt
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    return {'success': False, 'uids': [], 'error': f'All retry attempts failed: {str(e)}'}
        
        return {'success': False, 'uids': [], 'error': 'Maximum retries exceeded'}

    def _perform_search(self, criteria, charset='UTF-8'):
        """Perform the actual IMAP search operation."""
        try:
            print(f"Searching with criteria: {criteria} using charset: {charset}")
            typ, data = self.mail.uid('search', None, *criteria) 
            
            if typ == 'OK':
                uids_string = data[0].decode('utf-8') if isinstance(data[0], bytes) else data[0]
                if uids_string: 
                    uids_list = uids_string.split(' ')
                    print(f"✓ Found {len(uids_list)} email(s) matching criteria: {uids_list}")
                    return {'success': True, 'uids': uids_list, 'error': None}
                else:
                    print("✓ Search successful - no emails found matching criteria")
                    return {'success': True, 'uids': [], 'error': None}
            else:
                error_detail = data[0].decode('utf-8') if isinstance(data[0], bytes) and data[0] else str(data)
                error_msg = f"IMAP search command failed: Response type {typ}, Data: {error_detail}"
                print(f"✗ {error_msg}")
                return {'success': False, 'uids': [], 'error': error_msg}
                
        except imaplib.IMAP4.error as e:
            error_msg = f"IMAP protocol error during search: {e}"
            print(f"✗ {error_msg}")
            return {'success': False, 'uids': [], 'error': error_msg}
        except Exception as e:
            error_msg = f"Unexpected error during search: {e}"
            print(f"✗ {error_msg}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'uids': [], 'error': error_msg}

    def _reconnect(self):
        """Attempt to reconnect using stored connection details."""
        try:
            if hasattr(self, '_last_connection_details'):
                print("🔌 Attempting to reconnect to IMAP server...")
                hostname, username, password = self._last_connection_details
                
                # Close existing connection if it exists
                if self.mail:
                    try:
                        self.mail.close()
                        self.mail.logout()
                    except:
                        pass
                    self.mail = None
                
                # Attempt new connection
                new_connection = self.connect_imap(hostname, username, password)
                if new_connection:
                    # CRITICAL: Select INBOX after reconnection
                    try:
                        typ, data = self.mail.select("INBOX")
                        if typ == 'OK':
                            print("✓ Successfully reconnected and selected INBOX")
                            return True
                        else:
                            print(f"✗ Failed to select INBOX after reconnection: {data}")
                            return False
                    except Exception as select_e:
                        print(f"✗ Error selecting INBOX after reconnection: {select_e}")
                        return False
                else:
                    print("✗ Failed to reconnect to IMAP server")
                    return False
            else:
                print("✗ No connection details available for reconnection")
                return False
        except Exception as e:
            print(f"✗ Error during reconnection: {e}")
            return False

    def search_unread_with_keywords(self, subject_keywords=None):
        if not self.mail:
            print("Not connected to IMAP server for search_unread_with_keywords. Call connect_imap first.")
            return []
            
        criteria = ['UNSEEN']
        if subject_keywords and isinstance(subject_keywords, list):
            for keyword in subject_keywords:
                criteria.append('SUBJECT')
                criteria.append(keyword) 
        
        print(f"Constructed search criteria for unread with keywords: {criteria}")
        
        # Handle new structured response format
        search_result = self.search_emails(criteria)
        if isinstance(search_result, dict):
            if search_result['success']:
                return search_result['uids']
            else:
                print(f"Search failed: {search_result['error']}")
                return []
        else:
            # Fallback for old format (shouldn't happen)
            return search_result if search_result else []

    def fetch_email_headers(self, email_uids):
        if not self.mail:
            print("Not connected. Call connect_imap first.")
            return {} 
        
        if isinstance(email_uids, str): 
            email_uids = [email_uids]
        if not isinstance(email_uids, list) or not all(isinstance(uid, str) for uid in email_uids):
            print("Invalid input: email_uids must be a string or a list of strings.")
            return {}

        headers_map = {}
        for uid in email_uids:
            try:
                print(f"Fetching headers for UID {uid}...")
                typ, data = self.mail.uid('fetch', uid, '(BODY[HEADER.FIELDS (SUBJECT FROM DATE)])')
                if typ == 'OK':
                    if data and data[0] and isinstance(data[0], tuple) and len(data[0]) == 2:
                        header_bytes = data[0][1]
                        header_string = header_bytes.decode('utf-8', errors='replace')
                        headers_map[uid] = header_string
                        print(f"Headers for UID {uid} (first 200 chars):\n{header_string[:200]}...")
                    else:
                        print(f"Unexpected data structure for UID {uid}: {data}")
                        headers_map[uid] = None
                else:
                    error_detail = data[0].decode('utf-8') if isinstance(data[0], bytes) and data[0] else str(data)
                    print(f"Failed to fetch headers for UID {uid}: {typ} - {error_detail}")
                    headers_map[uid] = None 
            except imaplib.IMAP4.error as e:
                print(f"IMAP error fetching headers for UID {uid}: {e}")
                headers_map[uid] = None
            except Exception as e:
                print(f"Unexpected error fetching headers for UID {uid}: {e}")
                import traceback
                traceback.print_exc()
                headers_map[uid] = None
        return headers_map

    def _store_flags(self, email_uids, command, flags):
        if not self.mail:
            print("Not connected. Call connect_imap first.")
            return False
        
        if isinstance(email_uids, str): 
            uids_string = email_uids
        elif isinstance(email_uids, list) and all(isinstance(uid, str) for uid in email_uids):
            if not email_uids: 
                print("No UIDs provided to store flags.")
                return False
            uids_string = ','.join(email_uids)
        else:
            print("Invalid input: email_uids must be a UID string or a list of UID strings.")
            return False
            
        try:
            print(f"Storing flags for UIDs {uids_string}: command='{command}', flags='{flags}'")
            typ, response = self.mail.uid('store', uids_string, command, flags)
            decoded_response = [item.decode() if isinstance(item, bytes) else str(item) for item in response] if response else []
            if typ == 'OK':
                print(f"Flags stored successfully. Server response: {decoded_response}")
                return True
            else:
                print(f"Failed to store flags. Server response: {typ} - {decoded_response}")
                return False
        except imaplib.IMAP4.error as e:
            print(f"IMAP error storing flags: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error storing flags: {e}")
            import traceback
            traceback.print_exc()
            return False

    def mark_emails_as_seen(self, email_uids):
        return self._store_flags(email_uids, '+FLAGS', '(\Seen)')

    def mark_emails_as_unseen(self, email_uids):
        return self._store_flags(email_uids, '-FLAGS', '(\Seen)')

    def check_idle_support(self):
        """Check if server supports IDLE extension."""
        if not IMAPCLIENT_AVAILABLE:
            print("IMAPClient not available. IDLE not supported.")
            return False
            
        if not self.mail:
            print("Not connected to IMAP server.")
            return False
            
        try:
            # Check if IDLE is in server capabilities
            typ, capabilities = self.mail.capability()
            if typ == 'OK':
                caps_str = ' '.join([cap.decode() if isinstance(cap, bytes) else str(cap) for cap in capabilities])
                idle_supported = 'IDLE' in caps_str
                print(f"Server capabilities: {caps_str}")
                print(f"IDLE support: {'Yes' if idle_supported else 'No'}")
                return idle_supported
            else:
                print(f"Failed to get server capabilities: {capabilities}")
                return False
        except Exception as e:
            print(f"Error checking IDLE support: {e}")
            return False

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def setup_idle_connection(self, hostname, username, password):
        """Setup dedicated IDLE connection with IMAPClient."""
        if not IMAPCLIENT_AVAILABLE:
            raise Exception("IMAPClient not available for IDLE connection")
        
        print(f"Setting up IDLE connection to {hostname}...")
        try:
            # Create new IMAPClient connection for IDLE
            idle_client = IMAPClient(hostname, use_uid=True, ssl=True)
            idle_client.login(username, password)
            idle_client.select_folder('INBOX')
            
            # Check IDLE capability
            if not idle_client.has_capability('IDLE'):
                raise Exception("Server does not support IDLE")
                
            print(f"✓ IDLE connection established to {hostname}")
            return idle_client
            
        except Exception as e:
            print(f"Failed to setup IDLE connection: {e}")
            raise

    def start_idle_monitoring(self, idle_client, callback, timeout=1740, verbose=False):
        """Start IDLE monitoring with callback for new messages."""
        if not idle_client:
            raise Exception("No IDLE client provided")
            
        if verbose:
            print(f"Starting IDLE monitoring (timeout: {timeout}s)...")
        
        def idle_thread():
            notification_received = False
            try:
                # Start IDLE
                idle_client.idle()
                print("✓ IDLE mode activated")
                
                # Wait for responses
                start_time = time.time()
                while time.time() - start_time < timeout and not notification_received:
                    try:
                        # Check for responses with 30 second timeout
                        responses = idle_client.idle_check(timeout=30)
                        
                        # Process all responses
                        if responses:
                            if verbose:
                                print(f"📨 Received {len(responses)} IDLE response(s)")
                            for response in responses:
                                # Only log non-keepalive responses, or all if verbose
                                response_str = str(response)
                                is_keepalive = 'Still here' in response_str or 'OK' in response_str
                                if verbose or not is_keepalive:
                                    print(f"IDLE response: {response}")
                                
                                # Check for various message events
                                response_bytes = response if isinstance(response, bytes) else str(response).encode()
                                
                                if (b'EXISTS' in response_bytes or 
                                    b'RECENT' in response_bytes):
                                    print("📬 New message detected via IDLE - ending IDLE session")
                                    try:
                                        result = callback(response)
                                        if result:  # Callback returns True for new messages
                                            notification_received = True
                                            break  # Exit response processing loop
                                    except Exception as cb_e:
                                        print(f"Error in IDLE callback: {cb_e}")
                                elif b'FETCH' in response_bytes:
                                    print("📬 Message update detected via IDLE")
                                    try:
                                        callback(response)
                                    except Exception as cb_e:
                                        print(f"Error in IDLE callback: {cb_e}")
                        else:
                            # No responses - this is normal for IDLE
                            if verbose:
                                print("👂 IDLE listening...")
                        
                        # Break out if we got a notification
                        if notification_received:
                            print("🔔 IDLE notification processed - ending session early")
                            break
                                
                    except Exception as e:
                        print(f"Error in IDLE check: {e}")
                        # Don't break immediately - try to continue
                        time.sleep(5)
                        continue
                        
                if not notification_received:
                    print("IDLE timeout reached, ending session")
                        
            except Exception as e:
                print(f"Error in IDLE monitoring: {e}")
                import traceback
                traceback.print_exc()
            finally:
                try:
                    idle_client.idle_done()
                    print("IDLE session ended")
                except Exception as e:
                    print(f"Error ending IDLE session: {e}")
        
        # Start IDLE in separate thread
        thread = threading.Thread(target=idle_thread, daemon=True)
        thread.start()
        return thread

    def handle_idle_response(self, response):
        """Process IDLE server responses."""
        try:
            response_str = response.decode() if isinstance(response, bytes) else str(response)
            print(f"Processing IDLE response: {response_str}")
            
            if 'EXISTS' in response_str:
                # Extract message count if available
                parts = response_str.split()
                if len(parts) >= 2 and parts[1] == 'EXISTS':
                    message_count = int(parts[0])
                    print(f"Mailbox now has {message_count} messages")
                    return {'type': 'new_message', 'count': message_count}
                else:
                    # Handle other EXISTS formats
                    return {'type': 'new_message', 'response': response_str}
                    
            elif 'RECENT' in response_str:
                return {'type': 'new_message', 'response': response_str}
                    
            elif 'EXPUNGE' in response_str:
                return {'type': 'message_deleted'}
                
            elif 'FETCH' in response_str:
                return {'type': 'message_updated'}
                
            return {'type': 'other', 'response': response_str}
            
        except Exception as e:
            print(f"Error processing IDLE response: {e}")
            return {'type': 'error', 'error': str(e)}

    def idle_cleanup(self, idle_client):
        """Clean up IDLE connection."""
        if idle_client:
            try:
                print("Cleaning up IDLE connection...")
                idle_client.idle_done()
                idle_client.logout()
                print("✓ IDLE connection cleaned up")
            except Exception as e:
                print(f"Error during IDLE cleanup: {e}")

    def generate_unique_filename(self, base_filename, directory):
        """Generate a unique filename by adding timestamp and UUID prefix."""
        # Extract file extension
        name, ext = os.path.splitext(base_filename)
        
        # Create timestamp prefix
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]  # First 8 chars of UUID
        
        # Sanitize the original name
        sanitized_name = "".join(c if c.isalnum() or c in ['.', '-', '_'] else '_' for c in name)
        sanitized_name = sanitized_name[:100]  # Limit length
        
        # Build filename with unique prefix
        unique_filename = f"{timestamp}_{unique_id}_{sanitized_name}{ext}"
        
        # Check if file exists and increment if needed
        counter = 1
        test_filename = unique_filename
        while os.path.exists(os.path.join(directory, test_filename)):
            name_part, ext_part = os.path.splitext(unique_filename)
            test_filename = f"{name_part}_{counter}{ext_part}"
            counter += 1
            
        return test_filename

    def download_pdf_attachments(self, email_uid, download_folder="work/attachments"):
        if not self.mail:
            print("Not connected. Call connect_imap first.")
            return None

        try:
            print(f"Attempting to fetch email UID {email_uid} for PDF attachments...")
            typ, data = self.mail.uid('fetch', email_uid, '(RFC822)')
            if typ != 'OK':
                error_detail = data[0].decode('utf-8') if isinstance(data[0], bytes) and data[0] else str(data)
                print(f"Failed to fetch email UID {email_uid}. Server response: {typ} - {error_detail}")
                return None

            # Ensure data[0] is a tuple and has at least two elements, data[0][1] being the email body
            if not (isinstance(data, list) and len(data) > 0 and isinstance(data[0], tuple) and len(data[0]) == 2):
                print(f"Unexpected data structure for RFC822 fetch of UID {email_uid}: {data}")
                return None
                
            raw_email_bytes = data[0][1]
            msg = email.message_from_bytes(raw_email_bytes)

            os.makedirs(download_folder, exist_ok=True)
            
            saved_filepath = None # To store the path of the first saved PDF

            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition")) 

                filename = part.get_filename()

                is_pdf_content_type = (content_type == 'application/pdf')
                is_octet_stream_with_pdf_extension = (
                    content_type == 'application/octet-stream' and 
                    filename and filename.lower().endswith('.pdf')
                )
                # Check if it's an attachment; 'attachment' in content_disposition is a good indicator
                is_attachment = 'attachment' in content_disposition.lower()

                if is_pdf_content_type or (is_octet_stream_with_pdf_extension and is_attachment):
                    if not filename: 
                        timestamp = int(time.time())
                        part_cid = part.get('Content-ID', '').strip('<>') # Use Content-ID if available
                        unique_suffix = part_cid.replace('@', '_').replace('.', '_') if part_cid else timestamp
                        filename = f"attachment_{email_uid}_{unique_suffix}.pdf"
                    
                    # Generate unique filename with timestamp and UUID prefix
                    unique_filename = self.generate_unique_filename(filename, download_folder)
                    filepath = os.path.join(download_folder, unique_filename)
                    
                    print(f"Found PDF attachment: '{filename}', Content-Type: {content_type}")
                    print(f"Attempting to save to: {filepath}")

                    try:
                        payload = part.get_payload(decode=True) 
                        if payload:
                            with open(filepath, 'wb') as f:
                                f.write(payload)
                            print(f"Successfully saved PDF attachment to {filepath}")
                            saved_filepath = filepath # Store path of first successfully saved PDF
                            break # MVP: Download first PDF attachment found and then stop
                        else:
                            print(f"Could not decode payload for attachment '{filename}'. Skipping.")
                            
                    except Exception as e_save:
                        print(f"Error saving attachment '{filename}': {e_save}")
                        # Continue to look for other PDF attachments if this one fails to save
            
            if saved_filepath:
                return saved_filepath # Return path of the first PDF successfully saved
            else:
                print(f"No PDF attachments found (or successfully saved) for email UID {email_uid}.")
                return None

        except imaplib.IMAP4.error as e:
            print(f"IMAP error downloading attachments for UID {email_uid}: {e}")
            return None
        except Exception as e_main:
            print(f"An unexpected error occurred downloading attachments for UID {email_uid}: {e_main}")
            import traceback
            traceback.print_exc()
            return None

    def logout(self): 
        if self.mail:
            print("Logging out from IMAP server...")
            try:
                self.mail.logout()
                print("Logout successful.")
            except imaplib.IMAP4.error as e:
                print(f"IMAP error during logout: {e}")
            except Exception as e: # nosec
                print(f"An unexpected error occurred during logout: {e}")
            finally:
                self.mail = None 
        else:
            print("No active IMAP connection to logout from.")

    def reset_all_emails_to_unseen(self, mailbox="INBOX"):
        if not self.mail:
            print("Not connected. Call connect_imap first.")
            return False
        
        try:
            print(f"Selecting mailbox: {mailbox}...")
            typ, data = self.mail.select(mailbox)
            if typ != 'OK':
                # Ensure data[0] is bytes before decoding, and handle if it's not
                error_msg = data[0].decode('utf-8', 'replace') if isinstance(data[0], bytes) else str(data[0])
                print(f"Failed to select mailbox {mailbox}: {error_msg}")
                return False
            print(f"Mailbox {mailbox} selected.")

            # Handle new structured response format from search_emails
            search_result = self.search_emails(['ALL'])
            
            if isinstance(search_result, dict):
                if search_result['success']:
                    all_uids = search_result['uids']
                else:
                    print(f"Search failed during reset: {search_result['error']}")
                    return False
            else:
                # Fallback for old format (shouldn't happen)
                all_uids = search_result if search_result else []
            
            if not all_uids: # Handles empty list from search_emails
                print(f"No emails found in mailbox {mailbox} to reset.")
                return True # No action needed, so operation is 'successful' in its goal

            print(f"Found {len(all_uids)} email(s) in {mailbox}. Marking all as UNSEEN.")
            # mark_emails_as_unseen handles printing success/failure of the store command
            return self.mark_emails_as_unseen(all_uids)
            
        except imaplib.IMAP4.error as e:
            print(f"IMAP error during reset_all_emails_to_unseen: {e}")
            return False
        except Exception as e_reset:
            print(f"Unexpected error during reset_all_emails_to_unseen: {e_reset}")
            import traceback
            traceback.print_exc()
            return False

    def extract_email_body(self, msg):
        """Extract email body text from email message, handling both HTML and plain text."""
        body_text = ""
        
        # If email is multipart, extract text from parts
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                    
                if content_type == "text/plain":
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        text = part.get_payload(decode=True).decode(charset, errors='replace')
                        body_text += text + "\n\n"
                    except Exception as e:
                        print(f"Error decoding plain text part: {e}")
                        
                elif content_type == "text/html":
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        html = part.get_payload(decode=True).decode(charset, errors='replace')
                        # Convert HTML to text
                        text = html2text(html)
                        body_text += text + "\n\n"
                    except Exception as e:
                        print(f"Error decoding HTML part: {e}")
        else:
            # Non-multipart email
            content_type = msg.get_content_type()
            charset = msg.get_content_charset() or 'utf-8'
            
            try:
                if content_type == "text/plain":
                    body_text = msg.get_payload(decode=True).decode(charset, errors='replace')
                elif content_type == "text/html":
                    html = msg.get_payload(decode=True).decode(charset, errors='replace')
                    body_text = html2text(html)
                else:
                    body_text = str(msg.get_payload())
            except Exception as e:
                print(f"Error decoding email body: {e}")
                body_text = str(msg.get_payload())
        
        return body_text.strip()

    def get_complete_email_content(self, email_uid, download_folder="attachments"):
        """Extract complete email content: headers, body, and PDF attachment text."""
        if not self.mail:
            print("Not connected. Call connect_imap first.")
            return None

        try:
            print(f"Fetching complete email content for UID {email_uid}...")
            typ, data = self.mail.uid('fetch', email_uid, '(RFC822)')
            if typ != 'OK':
                error_detail = data[0].decode('utf-8') if isinstance(data[0], bytes) and data[0] else str(data)
                print(f"Failed to fetch email UID {email_uid}. Server response: {typ} - {error_detail}")
                return None

            if not (isinstance(data, list) and len(data) > 0 and isinstance(data[0], tuple) and len(data[0]) == 2):
                print(f"Unexpected data structure for RFC822 fetch of UID {email_uid}: {data}")
                return None
                
            raw_email_bytes = data[0][1]
            msg = email.message_from_bytes(raw_email_bytes)

            # Extract email metadata
            email_content = {
                'uid': email_uid,
                'subject': msg.get('Subject', 'No Subject'),
                'from': msg.get('From', 'Unknown Sender'),
                'to': msg.get('To', ''),
                'date': msg.get('Date', ''),
                'body_text': self.extract_email_body(msg),
                'pdf_text': None,
                'pdf_filepath': None
            }

            # Try to download PDF attachment if present
            pdf_filepath = self.download_pdf_attachments(email_uid, download_folder)
            if pdf_filepath:
                email_content['pdf_filepath'] = pdf_filepath
                # Extract text from PDF
                try:
                    import sys
                    sys.path.append(os.path.dirname(__file__))
                    from pdf_processor import extract_text_from_pdf
                    pdf_text = extract_text_from_pdf(pdf_filepath)
                    email_content['pdf_text'] = pdf_text
                    print(f"Extracted {len(pdf_text)} characters from PDF attachment")
                except Exception as e:
                    print(f"Error extracting text from PDF {pdf_filepath}: {e}")
                    email_content['pdf_text'] = "Error extracting PDF text"

            print(f"Email content extracted:")
            print(f"  Subject: {email_content['subject'][:100]}...")
            print(f"  From: {email_content['from']}")
            print(f"  Body length: {len(email_content['body_text'])} characters")
            print(f"  PDF text length: {len(email_content['pdf_text']) if email_content['pdf_text'] else 0} characters")
            
            return email_content

        except Exception as e:
            print(f"Error extracting complete email content for UID {email_uid}: {e}")
            import traceback
            traceback.print_exc()
            return None

pass
