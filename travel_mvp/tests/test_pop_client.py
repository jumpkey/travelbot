import unittest
import sys 
import os 
import shutil # For robust folder cleanup

# Adjust the Python path to include the src directory for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pop_client import POPClient 

class TestPOPClient(unittest.TestCase):
    # Test-specific download folder
    DOWNLOAD_FOLDER_POP = "test_attachments_output_pop"

    @classmethod
    def setUpClass(cls):
        # Clean up test folder once before all tests in the class
        if os.path.exists(cls.DOWNLOAD_FOLDER_POP):
            shutil.rmtree(cls.DOWNLOAD_FOLDER_POP)
        # Re-create it empty for the test run
        os.makedirs(cls.DOWNLOAD_FOLDER_POP, exist_ok=True)

    def setUp(self):
        self.pop_client = POPClient()
        # For tests other than invalid host, we set up a connection.
        # The first test (invalid host) will create its own client.
        if self.id().endswith("test_00_connect_pop_invalid_credentials_or_host"):
             # This specific test does not need a pre-established connection from setUp
            pass
        else:
            self.DREAMHOST_POP_HOST = "pop.dreamhost.com"
            self.DREAMHOST_POP_PORT = 995
            self.DREAMHOST_USERNAME = "travelbot@jumpkey.com"
            self.DREAMHOST_PASSWORD = "MadTravel2025@@"
            
            print(f"\nConnecting to {self.DREAMHOST_POP_HOST} for POP3 test setup ({self.id()})...")
            self.pop_client.connect_pop(
                self.DREAMHOST_POP_HOST,
                self.DREAMHOST_POP_PORT,
                self.DREAMHOST_USERNAME,
                self.DREAMHOST_PASSWORD
            )
            self.assertTrue(self.pop_client.connection is not None, 
                            f"Failed to connect to DreamHost POP3 for testing in {self.id()}")

    def tearDown(self):
        if self.pop_client and self.pop_client.connection:
            print(f"Logging out from POP3 in tearDown ({self.id()})...")
            self.pop_client.disconnect_pop()

    @classmethod
    def tearDownClass(cls):
        # Clean up test folder once after all tests in the class
        print(f"\nCleaning up POP test attachment folder in tearDownClass: {cls.DOWNLOAD_FOLDER_POP}")
        if os.path.exists(cls.DOWNLOAD_FOLDER_POP):
            shutil.rmtree(cls.DOWNLOAD_FOLDER_POP)
            print(f"Removed folder: {cls.DOWNLOAD_FOLDER_POP}")

    # This test runs first and does its own client setup/teardown
    def test_00_connect_pop_invalid_credentials_or_host(self):
        print("\nRunning test_00_connect_pop_invalid_credentials_or_host...")
        local_pop_client = POPClient() # Use a local client for this specific test
        conn = local_pop_client.connect_pop(
            hostname="invalid.hostname.that.does.not.exist", 
            port=995, 
            username="testuser", 
            password="wrongpassword"
        )
        self.assertIsNone(conn, "Connection should fail with invalid hostname/credentials and return None")
        self.assertIsNone(local_pop_client.connection, "POPClient's connection attribute should be None after failed connection")

    # Subsequent tests use the connection from setUp
    def test_01_list_and_retrieve_pop_messages(self):
        print("\nRunning test_01_list_and_retrieve_pop_messages...")
        self.assertTrue(self.pop_client.connection is not None, "POP3 connection not available.")
        resp, messages_info = self.pop_client.list_messages()
        
        self.assertIsNotNone(resp, "LIST command should get a response from server.")
        # poplib responses are bytes
        self.assertTrue(resp.startswith(b'+OK'), f"LIST command response should be +OK, got: {resp}")
        self.assertIsNotNone(messages_info, "list_messages should return a list of message info.")
        
        # Expecting 2 messages based on previous IMAP reset and confirmation
        self.assertEqual(len(messages_info), 2, f"Expected 2 messages in the POP3 mailbox, found {len(messages_info)}.")
        print(f"Found {len(messages_info)} messages: {messages_info}")

        if messages_info:
            first_msg_num_info = messages_info[0]
            self.assertIn('msg_num', first_msg_num_info, "Message info dict missing 'msg_num'")
            first_msg_num = first_msg_num_info['msg_num']
            
            print(f"Attempting to retrieve message number {first_msg_num}...")
            raw_email_bytes = self.pop_client.retrieve_email_message(first_msg_num)
            self.assertIsNotNone(raw_email_bytes, f"Should retrieve raw email bytes for message {first_msg_num}.")
            if raw_email_bytes is not None: # Check to satisfy type checker for len()
                 self.assertTrue(len(raw_email_bytes) > 0, f"Retrieved email for message {first_msg_num} should not be empty.")
                 print(f"Successfully retrieved message {first_msg_num}, size: {len(raw_email_bytes)} bytes.")

    def test_02_download_pdf_attachments_pop_live(self):
        print("\nRunning test_02_download_pdf_attachments_pop_live...")
        self.assertTrue(self.pop_client.connection is not None, "POP3 connection not available.")
        
        resp, messages_info = self.pop_client.list_messages()
        self.assertTrue(resp is not None and resp.startswith(b'+OK'), "Failed to list messages before PDF download test.")
        self.assertEqual(len(messages_info), 2, "Expected 2 messages for POP3 PDF download test based on current mailbox state.")

        downloaded_files_count = 0
        for i, msg_info in enumerate(messages_info):
            msg_num = msg_info['msg_num']
            print(f"Attempting to download PDF from POP message number {msg_num} into {TestPOPClient.DOWNLOAD_FOLDER_POP}...")
            filepath = self.pop_client.download_pdf_attachments_pop(msg_num, download_folder=TestPOPClient.DOWNLOAD_FOLDER_POP)
            
            self.assertIsNotNone(filepath, f"download_pdf_attachments_pop should return a filepath for msg {msg_num}, but got None.")
            if filepath:
                downloaded_files_count += 1
                self.assertTrue(os.path.exists(filepath), f"Downloaded PDF file should exist at {filepath}")
                self.assertTrue(os.path.getsize(filepath) > 0, f"Downloaded PDF file {filepath} should not be empty.")
                print(f"PDF attachment from POP msg {msg_num} successfully downloaded to: {filepath}")

                try:
                    with open(filepath, 'rb') as f_pdf:
                        magic_bytes = f_pdf.read(4)
                    self.assertEqual(magic_bytes, b'%PDF', 
                                     f"The downloaded file {filepath} (from POP msg {msg_num}) does not start with PDF magic number '%PDF'.")
                    print(f"PDF magic number check passed for {filepath}.")
                except Exception as e_read:
                    self.fail(f"Could not read downloaded file {filepath} (from POP msg {msg_num}) to check magic number: {e_read}")
        
        self.assertEqual(downloaded_files_count, len(messages_info),
                         f"Expected to download {len(messages_info)} PDFs via POP3, but only got {downloaded_files_count}.")

    # This test was originally for IMAP, keeping a skipped version for POP if needed later.
    @unittest.skip("Skipping live POP3 test for specific app password unless explicitly running diagnostics.")
    def test_connect_pop_live_outlook_app_password(self):
        print("\nRunning test_connect_pop_live_outlook_app_password (SKIPPED)...")
        pass


if __name__ == '__main__':
    unittest.main()
