import poplib
import socket
import os
import email # For parsing email messages
import time # For generating unique filenames

class POPClient:
    def __init__(self):
        self.connection = None

    def connect_pop(self, hostname, port, username, password):
        print(f"Attempting POP3 SSL connection to {hostname}:{port} as {username}...")
        try:
            self.connection = poplib.POP3_SSL(host=hostname, port=port)
            # Set debug level to 1 for standard command/response logging
            self.connection.set_debuglevel(1) 
            
            print("POP3 SSL connection established.")
            
            # User Authentication
            print(f"Sending USER {username}...")
            user_resp = self.connection.user(username)
            print(f"Server response to USER: {user_resp}")
            if not user_resp.startswith(b'+OK'):
                print(f"POP3 USER command failed: {user_resp}")
                self.disconnect_pop()
                return None

            print(f"Sending PASS {'*' * len(password)}...")
            pass_resp = self.connection.pass_(password)
            print(f"Server response to PASS: {pass_resp}")
            if not pass_resp.startswith(b'+OK'):
                print(f"POP3 PASS command failed: {pass_resp}")
                self.disconnect_pop()
                return None

            print("POP3 authentication successful.")
            num_messages, total_size = self.connection.stat()
            print(f"Mailbox contains {num_messages} messages, total size {total_size} bytes.")
            
            return self.connection
            
        except poplib.error_proto as e:
            print(f"POP3 protocol error: {e}")
            if self.connection:
                try:
                    self.connection.quit()
                except: # nosec
                    pass 
                self.connection = None
            return None
        except socket.error as e:
            print(f"Socket error during POP3 connection: {e}")
            self.connection = None 
            return None
        except Exception as e:
            print(f"An unexpected error occurred during POP3 connection: {e}")
            if self.connection: 
                try:
                    self.connection.quit()
                except: # nosec
                    pass
                self.connection = None
            return None

    def list_messages(self):
        if not self.connection:
            print("Not connected to POP3 server.")
            return None, [] 
        
        try:
            print("Listing messages from server...")
            # Note: poplib debuglevel output will show raw command
            resp, mail_list_raw, octets = self.connection.list()
            
            # Response from server is bytes, decode for printing
            decoded_resp = resp.decode('utf-8', 'replace') if isinstance(resp, bytes) else str(resp)
            print(f"LIST command response: {decoded_resp}")
            
            processed_mail_list = []
            if decoded_resp.startswith('+OK'):
                for item_bytes in mail_list_raw:
                    item_str = item_bytes.decode('utf-8', 'replace')
                    parts = item_str.split(' ')
                    if len(parts) == 2:
                        try:
                            processed_mail_list.append({'msg_num': int(parts[0]), 'size': int(parts[1])})
                        except ValueError:
                            print(f"Warning: Could not parse message info: {item_str}")
                print(f"Found {len(processed_mail_list)} messages.")
            else:
                print(f"LIST command failed: {decoded_resp}")
            
            return resp, processed_mail_list # Return original response and processed list
        except poplib.error_proto as e:
            print(f"POP3 error during LIST: {e}")
            return None, []
        except Exception as e_list:
            print(f"Unexpected error during list_messages: {e_list}")
            import traceback
            traceback.print_exc()
            return None, []

    def retrieve_email_message(self, message_num):
        if not self.connection:
            print("Not connected to POP3 server.")
            return None
        
        try:
            print(f"Retrieving message number {message_num}...")
            # Ensure message_num is string for poplib
            resp, lines_bytes, octets = self.connection.retr(str(message_num)) 
            
            decoded_resp = resp.decode('utf-8', 'replace') if isinstance(resp, bytes) else str(resp)
            print(f"RETR command response: {decoded_resp}")

            if decoded_resp.startswith('+OK'):
                raw_email_bytes = b'\r\n'.join(lines_bytes)
                return raw_email_bytes
            else:
                print(f"Failed to retrieve message {message_num}: {decoded_resp}")
                return None
            
        except poplib.error_proto as e:
            print(f"POP3 error during RETR for message {message_num}: {e}")
            return None
        except Exception as e_retr:
            print(f"Unexpected error during retrieve_email_message for {message_num}: {e_retr}")
            import traceback
            traceback.print_exc()
            return None

    def download_pdf_attachments_pop(self, message_num, download_folder="attachments_pop"):
        if not self.connection: 
            print("Not connected to POP3 server for download_pdf_attachments_pop.")
            return None

        print(f"Attempting to download PDF attachments for POP message number {message_num}...")
        raw_email_bytes = self.retrieve_email_message(message_num)
        if not raw_email_bytes:
            print(f"Could not retrieve message {message_num}, cannot download attachments.")
            return None

        try:
            msg = email.message_from_bytes(raw_email_bytes)
            os.makedirs(download_folder, exist_ok=True)
            
            saved_filepath = None

            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                filename = part.get_filename()

                is_pdf_content_type = (content_type == 'application/pdf')
                is_octet_stream_with_pdf_extension = (
                    content_type == 'application/octet-stream' and 
                    filename and filename.lower().endswith('.pdf')
                )
                is_attachment = 'attachment' in content_disposition.lower()

                if is_pdf_content_type or (is_octet_stream_with_pdf_extension and is_attachment):
                    if not filename:
                        timestamp = int(time.time())
                        part_cid = part.get('Content-ID', '').strip('<>')
                        unique_suffix = part_cid.replace('@', '_').replace('.', '_') if part_cid else timestamp
                        filename = f"pop_msg_{message_num}_attachment_{unique_suffix}.pdf"
                    
                    filename = "".join(c if c.isalnum() or c in ['.', '-', '_'] else '_' for c in filename)
                    filename = filename[:200] if len(filename) > 200 else filename
                    
                    filepath = os.path.join(download_folder, filename)
                    
                    print(f"Found PDF attachment in POP msg {message_num}: '{filename}', Content-Type: {content_type}")
                    print(f"Attempting to save to: {filepath}")

                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            with open(filepath, 'wb') as f:
                                f.write(payload)
                            print(f"Successfully saved PDF attachment from POP msg {message_num} to {filepath}")
                            saved_filepath = filepath 
                            break # MVP: Download first PDF
                        else:
                            print(f"Could not decode payload for attachment '{filename}' from POP msg {message_num}. Skipping.")
                            
                    except Exception as e_save:
                        print(f"Error saving attachment '{filename}' from POP msg {message_num}: {e_save}")
            
            if saved_filepath:
                return saved_filepath
            else:
                print(f"No PDF attachments found (or successfully saved) for POP message {message_num}.")
                return None
            
        except Exception as e_main:
            print(f"An unexpected error occurred processing POP message {message_num} for attachments: {e_main}")
            import traceback
            traceback.print_exc()
            return None

    def disconnect_pop(self):
        if self.connection:
            print("Disconnecting from POP3 server...")
            try:
                quit_resp_bytes = self.connection.quit()
                # quit_resp is bytes, decode for printing
                quit_resp = quit_resp_bytes.decode('utf-8', 'replace') if isinstance(quit_resp_bytes, bytes) else str(quit_resp_bytes)
                print(f"Server response to QUIT: {quit_resp}")
            except poplib.error_proto as e:
                print(f"POP3 error during QUIT: {e}")
            except Exception as e: # nosec
                print(f"Unexpected error during QUIT: {e}")
            finally:
                self.connection = None
        else:
            print("No active POP3 connection to disconnect.")

# Example Usage (will not be run by subtask, for context only)
# if __name__ == '__main__':
#     client = POPClient()
#     # Replace with actual Outlook POP3 details and app password if testing locally
#     # conn = client.connect_pop("outlook.office365.com", 995, "your_email@example.com", "your_app_password")
#     # if conn:
#     #     # List messages (optional)
#     #     # resp, mails, octets = conn.list()
#     #     # print(f"LIST response: {resp}, {len(mails)} messages.")
#     #     # for i, mail_info in enumerate(mails[:5]): # Print info for first 5 messages
#     #     #     print(f"Message {i+1}: {mail_info}")
#     #     client.disconnect_pop()
