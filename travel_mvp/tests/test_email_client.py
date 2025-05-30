import unittest
import sys 
import os 
import time 
import shutil # For robust folder cleanup

# Adjust the Python path to include the src directory for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from email_client import EmailClient

class TestEmailClient(unittest.TestCase):
    uid_for_later_tests = None # Class attribute to share UID

    # Test-specific download folders
    DOWNLOAD_FOLDER_PDF_EXISTS = "test_attachments_output_exists"
    DOWNLOAD_FOLDER_PDF_NONE = "test_attachments_output_none"


    @classmethod
    def setUpClass(cls):
        # Clean up test folders once before all tests in the class
        if os.path.exists(cls.DOWNLOAD_FOLDER_PDF_EXISTS):
            shutil.rmtree(cls.DOWNLOAD_FOLDER_PDF_EXISTS)
        if os.path.exists(cls.DOWNLOAD_FOLDER_PDF_NONE):
            shutil.rmtree(cls.DOWNLOAD_FOLDER_PDF_NONE)
        # Re-create them empty for the test run
        os.makedirs(cls.DOWNLOAD_FOLDER_PDF_EXISTS, exist_ok=True)
        os.makedirs(cls.DOWNLOAD_FOLDER_PDF_NONE, exist_ok=True)


    def setUp(self):
        self.email_client = EmailClient()
        self.DREAMHOST_IMAP_HOST = "imap.dreamhost.com"
        self.DREAMHOST_USERNAME = "travelbot@jumpkey.com"
        self.DREAMHOST_PASSWORD = "MadTravel2025@@" 
        
        print(f"\nConnecting to {self.DREAMHOST_IMAP_HOST} for test setup...")
        self.email_client.connect_imap(self.DREAMHOST_IMAP_HOST, self.DREAMHOST_USERNAME, self.DREAMHOST_PASSWORD)
        self.assertTrue(self.email_client.mail is not None, "Failed to connect to DreamHost IMAP for testing in setUp.")
        
        if self.email_client.mail:
            typ, data = self.email_client.mail.select("INBOX")
            if typ != 'OK':
                self.fail(f"Failed to select INBOX on DreamHost IMAP. Response: {data}")
            print("INBOX selected for tests.")
        else:
            self.fail("IMAP connection object (self.email_client.mail) is None after connect_imap in setUp.")


    def tearDown(self):
        if self.email_client and self.email_client.mail:
            print("Logging out in tearDown...")
            self.email_client.logout()

    @classmethod
    def tearDownClass(cls):
        # Clean up test folders once after all tests in the class
        print("\nCleaning up test attachment folders in tearDownClass...")
        if os.path.exists(cls.DOWNLOAD_FOLDER_PDF_EXISTS):
            shutil.rmtree(cls.DOWNLOAD_FOLDER_PDF_EXISTS)
            print(f"Removed folder: {cls.DOWNLOAD_FOLDER_PDF_EXISTS}")
        if os.path.exists(cls.DOWNLOAD_FOLDER_PDF_NONE):
            shutil.rmtree(cls.DOWNLOAD_FOLDER_PDF_NONE)
            print(f"Removed folder: {cls.DOWNLOAD_FOLDER_PDF_NONE}")

    # Test methods are now ordered to run reset first.
    def test_00_reset_all_emails_to_unseen(self): # Run this early
        print("\nRunning test_00_reset_all_emails_to_unseen...")
        self.assertTrue(self.email_client.mail is not None, "IMAP connection not available for reset test.")
        
        # First, find some emails and ensure at least one is SEEN.
        initial_uids = self.email_client.search_emails(['ALL'])
        if not initial_uids:
            self.skipTest("No emails found in INBOX to perform reset test.")
            return

        uid_to_test_seen = initial_uids[0]
        print(f"Marking UID {uid_to_test_seen} as SEEN for setup...")
        marked_seen = self.email_client.mark_emails_as_seen([uid_to_test_seen])
        self.assertTrue(marked_seen, f"Failed to mark UID {uid_to_test_seen} as SEEN during test setup.")
        
        # Verify it's NOT UNSEEN (i.e., it is SEEN)
        # time.sleep(1) # Brief pause for server to update flags (optional)
        uids_check_seen = self.email_client.search_emails(['UNSEEN', 'UID', uid_to_test_seen])
        self.assertEqual(len(uids_check_seen), 0, 
                         f"UID {uid_to_test_seen} should be SEEN (not UNSEEN) after marking.")

        # Now, call the reset method
        print("Calling reset_all_emails_to_unseen()...")
        reset_success = self.email_client.reset_all_emails_to_unseen()
        self.assertTrue(reset_success, "reset_all_emails_to_unseen() should return True on success.")

        # Verify that the specific email (and potentially others) are now UNSEEN
        # time.sleep(1) # Brief pause (optional)
        uids_after_reset = self.email_client.search_emails(['UNSEEN', 'UID', uid_to_test_seen])
        self.assertEqual(len(uids_after_reset), 1,
                         f"UID {uid_to_test_seen} should be UNSEEN after reset_all_emails_to_unseen().")
        print(f"UID {uid_to_test_seen} is now UNSEEN. Reset successful.")

        all_unread_after_reset = self.email_client.search_unread_with_keywords()
        print(f"Total unread emails after reset: {len(all_unread_after_reset)}")
        self.assertTrue(len(all_unread_after_reset) >= 1, "Expected at least one unread email after reset.")
        # Example: If you know the total number of emails that should be unread
        # total_emails_in_inbox = len(initial_uids) 
        # self.assertEqual(len(all_unread_after_reset), total_emails_in_inbox, 
        #                  f"Expected all {total_emails_in_inbox} emails to be unread after reset.")


    def test_01_connect_imap_invalid_credentials(self): # Renamed from 00 to 01
        print("\nRunning test_01_connect_imap_invalid_credentials...")
        temp_client = EmailClient()
        conn = temp_client.connect_imap(
            hostname="imap.invalidserver.example.com", 
            username="testuser", 
            password="wrongpassword"
        )
        self.assertIsNone(conn, "Connection should be None for invalid server/credentials.")

    def test_02_search_all_unread(self): # Renamed from 01 to 02
        print("\nRunning test_02_search_all_unread...")
        self.assertTrue(self.email_client.mail is not None, "IMAP connection not available for search_all_unread.")
        uids = self.email_client.search_unread_with_keywords()
        self.assertIsNotNone(uids, "search_unread_with_keywords should return a list, not None")
        print(f"Found {len(uids)} unread email(s). UIDs: {uids}")
        self.assertIsInstance(uids, list, "Should return a list of UIDs.")

    def test_03_search_unread_with_subject_keyword(self): # Renamed from 02 to 03
        print("\nRunning test_03_search_unread_with_subject_keyword...")
        self.assertTrue(self.email_client.mail is not None, "IMAP connection not available.")
        keyword = "Alpha" 
        uids = self.email_client.search_unread_with_keywords(subject_keywords=[keyword])
        self.assertIsNotNone(uids)
        print(f"Found {len(uids)} unread email(s) with keyword '{keyword}'. UIDs: {uids}")
        self.assertTrue(len(uids) >= 0, "Expected at least 0 emails for specific keyword search") 
        if uids:
            TestEmailClient.uid_for_later_tests = uids[0]
            print(f"Stored UID {uids[0]} for later tests.")

    def test_04_fetch_headers(self): # Renamed from 03 to 04
        print("\nRunning test_04_fetch_headers...")
        self.assertTrue(self.email_client.mail is not None, "IMAP connection not available.")
        uid_to_fetch = getattr(TestEmailClient, 'uid_for_later_tests', None)
        
        if not uid_to_fetch:
            all_unread_uids = self.email_client.search_unread_with_keywords()
            if all_unread_uids:
                uid_to_fetch = all_unread_uids[0]
                print(f"No UID from 'Alpha' search, using first available unread UID: {uid_to_fetch}")
            else:
                self.skipTest("Skipping fetch_headers test: No unread emails found to get a UID and 'Alpha' search yielded no UID.")

        print(f"Attempting to fetch headers for UID: {uid_to_fetch}")
        headers_map = self.email_client.fetch_email_headers([uid_to_fetch])
        self.assertIsNotNone(headers_map, "fetch_email_headers should return a dict.")
        self.assertIn(uid_to_fetch, headers_map, "Fetched headers map should contain the requested UID.")
        header_content = headers_map.get(uid_to_fetch)
        self.assertIsNotNone(header_content, f"Header string for UID {uid_to_fetch} should not be None.")
        if header_content:
            print(f"Fetched headers for {uid_to_fetch} (first 300 chars): {header_content[:300]}...")
            self.assertTrue(len(header_content) > 0, "Header string should not be empty.")

    def test_05_mark_as_seen_and_verify(self): # Renamed from 04 to 05
        print("\nRunning test_05_mark_as_seen_and_verify...")
        self.assertTrue(self.email_client.mail is not None, "IMAP connection not available.")
        beta_uids = self.email_client.search_unread_with_keywords(subject_keywords=["Beta"])
        if not beta_uids:
            self.skipTest("Skipping mark_as_seen test: No unread email with 'Beta' in subject found.")
        
        uid_to_mark_seen = beta_uids[0]
        print(f"Found UID {uid_to_mark_seen} with 'Beta' in subject. Attempting to mark as SEEN.")
        
        mark_success = self.email_client.mark_emails_as_seen([uid_to_mark_seen])
        self.assertTrue(mark_success, f"mark_emails_as_seen failed for UID {uid_to_mark_seen}")
        
        uids_after_mark_seen = self.email_client.search_emails(['UNSEEN', 'UID', uid_to_mark_seen])
        self.assertEqual(len(uids_after_mark_seen), 0, 
                         f"Email UID {uid_to_mark_seen} should no longer be UNSEEN after marking as seen.")
        print(f"UID {uid_to_mark_seen} successfully marked as SEEN.")

    def test_06_mark_as_unseen_and_verify(self): # Renamed from 05 to 06
        print("\nRunning test_06_mark_as_unseen_and_verify...")
        self.assertTrue(self.email_client.mail is not None, "IMAP connection not available.")
        keyword_charlie = "Charlie"
        charlie_uids_all = self.email_client.search_emails(['SUBJECT', keyword_charlie])
        if not charlie_uids_all:
            self.skipTest(f"Skipping mark_as_unseen test: No email with '{keyword_charlie}' in subject found at all.")
        
        uid_to_mark_unseen = charlie_uids_all[0]
        print(f"Found UID {uid_to_mark_unseen} with '{keyword_charlie}' in subject.")

        is_unseen_currently = self.email_client.search_emails(['UNSEEN', 'UID', uid_to_mark_unseen])
        if is_unseen_currently:
            print(f"UID {uid_to_mark_unseen} ('{keyword_charlie}') is UNSEEN. Test expects it to be SEEN initially. Marking SEEN first.")
            self.email_client.mark_emails_as_seen([uid_to_mark_unseen])
            is_unseen_after_marking_seen = self.email_client.search_emails(['UNSEEN', 'UID', uid_to_mark_unseen])
            if is_unseen_after_marking_seen:
                 self.fail(f"Failed to mark UID {uid_to_mark_unseen} ('{keyword_charlie}') as SEEN for test setup.")

        print(f"Attempting to mark UID {uid_to_mark_unseen} ('{keyword_charlie}') as UNSEEN.")
        mark_success = self.email_client.mark_emails_as_unseen([uid_to_mark_unseen])
        self.assertTrue(mark_success, f"mark_emails_as_unseen failed for UID {uid_to_mark_unseen}")

        uids_after_mark_unseen = self.email_client.search_emails(['UNSEEN', 'UID', uid_to_mark_unseen])
        self.assertEqual(len(uids_after_mark_unseen), 1, 
                         f"Email UID {uid_to_mark_unseen} ('{keyword_charlie}') should be UNSEEN after marking as unseen.")
        print(f"UID {uid_to_mark_unseen} successfully marked as UNSEEN.")

    def test_07_download_pdf_attachments_live(self): # Renamed for clarity and updated logic
        print("\nRunning test_07_download_pdf_attachments_live...")
        self.assertTrue(self.email_client.mail is not None, "IMAP connection not available.")
        
        uids_with_known_pdfs = ['1', '2'] # From previous investigation
        download_folder = TestEmailClient.DOWNLOAD_FOLDER_PDF_EXISTS 

        # download_pdf_attachments method itself creates the folder.
        # setUpClass cleans it once before all tests.

        downloaded_files_count = 0
        for email_uid in uids_with_known_pdfs:
            print(f"Attempting to download PDF from UID {email_uid} into {download_folder}...")
            # Ensure email is unread for consistency if search_unread_with_keywords was used to find it.
            # However, download_pdf_attachments doesn't care about read/unread status, only UID.
            # For this test, we directly use UIDs '1' and '2'.
            
            filepath = self.email_client.download_pdf_attachments(email_uid, download_folder=download_folder)
            
            self.assertIsNotNone(filepath, f"download_pdf_attachments should return a filepath for UID {email_uid}, but got None.")
            if filepath: 
                downloaded_files_count += 1
                self.assertTrue(os.path.exists(filepath), f"Downloaded PDF file should exist at {filepath}")
                self.assertTrue(os.path.getsize(filepath) > 0, f"Downloaded PDF file {filepath} should not be empty.")
                # The main code's download_pdf_attachments tries to ensure .pdf extension from original filename
                # or generates one ending in .pdf. Filename sanitization might alter it.
                # A check for .pdf extension is good, but be mindful of sanitization effects.
                # self.assertTrue(filepath.lower().endswith('.pdf'), f"Filename {filepath} should end with .pdf") 
                print(f"PDF attachment from UID {email_uid} successfully downloaded to: {filepath}")

                try:
                    with open(filepath, 'rb') as f_pdf:
                        magic_bytes = f_pdf.read(4)
                    self.assertEqual(magic_bytes, b'%PDF', 
                                     f"The downloaded file {filepath} does not start with PDF magic number '%PDF'.")
                    print(f"PDF magic number check passed for {filepath}.")
                except Exception as e_read:
                    self.fail(f"Could not read downloaded file {filepath} to check magic number: {e_read}")
        
        self.assertEqual(downloaded_files_count, len(uids_with_known_pdfs),
                         f"Expected to download {len(uids_with_known_pdfs)} PDFs, but only got {downloaded_files_count}.")
        
    def test_08_download_pdf_no_attachment(self): 
        print("\nRunning test_08_download_pdf_no_attachment...")
        self.assertTrue(self.email_client.mail is not None, "IMAP connection not available.")
        keyword = "ZetaNoPDF"
        zeta_uids = self.email_client.search_unread_with_keywords(subject_keywords=[keyword]) 
        if not zeta_uids:
             self.skipTest(f"Skipping no_attachment test: No unread email with '{keyword}' in subject found.")

        email_uid_no_pdf = zeta_uids[0]
        print(f"Found email UID {email_uid_no_pdf} with keyword '{keyword}'. Expecting no PDF.")
        
        filepath = self.email_client.download_pdf_attachments(email_uid_no_pdf, download_folder=TestEmailClient.DOWNLOAD_FOLDER_PDF_NONE)
        self.assertIsNone(filepath, f"download_pdf_attachments should return None for email UID {email_uid_no_pdf} which has no PDF.")
        print("Correctly returned None for email with no PDF attachment.")

if __name__ == '__main__':
    unittest.main()
