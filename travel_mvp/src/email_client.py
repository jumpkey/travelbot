import imaplib
import ssl
import os
import email # For parsing email messages
import time # For generating unique filenames

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

    def search_emails(self, criteria, charset='UTF-8'):
        if not self.mail:
            print("Not connected to IMAP server. Call connect_imap first.")
            return []
        try:
            print(f"Searching with criteria: {criteria} using charset: {charset}")
            typ, data = self.mail.uid('search', None, *criteria) 
            
            if typ == 'OK':
                uids_string = data[0].decode('utf-8') if isinstance(data[0], bytes) else data[0]
                if uids_string: 
                    uids_list = uids_string.split(' ')
                    print(f"Found {len(uids_list)} email(s) matching criteria: {uids_list}")
                    return uids_list
                else:
                    print("No emails found matching criteria.")
                    return []
            else:
                error_detail = data[0].decode('utf-8') if isinstance(data[0], bytes) and data[0] else str(data)
                print(f"IMAP search command failed: Response type {typ}, Data: {error_detail}")
                return []
        except imaplib.IMAP4.error as e:
            print(f"IMAP error during search: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error during search_emails: {e}")
            import traceback
            traceback.print_exc() 
            return []

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
        return self.search_emails(criteria)

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

    def download_pdf_attachments(self, email_uid, download_folder="attachments"):
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
                    
                    # Basic filename sanitization
                    filename = "".join(c if c.isalnum() or c in ['.', '-', '_'] else '_' for c in filename)
                    # Prevent excessively long filenames (truncate if necessary)
                    filename = filename[:200] if len(filename) > 200 else filename

                    filepath = os.path.join(download_folder, filename)
                    
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

            # search_emails already prints messages and returns a list of UIDs
            all_uids = self.search_emails(['ALL']) 
            
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

pass
