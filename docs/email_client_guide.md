# EmailClient Guide

## Purpose

The `EmailClient` class provides functionalities to connect to an IMAP email server, search emails, fetch details, manage email flags (seen/unseen), and download attachments. It is designed to interact with standard IMAP servers using username/password authentication.

## Initialization

The client is initialized without any parameters:

```python
from src.email_client import EmailClient

client = EmailClient()
```
The IMAP connection object is stored in `client.mail` after a successful connection.

## Methods

### `connect_imap(self, hostname, username, password)`
Connects to the specified IMAP server using SSL.

-   **Parameters:**
    -   `hostname` (str): The IMAP server hostname (e.g., "imap.dreamhost.com").
    -   `username` (str): The email account username.
    -   `password` (str): The email account password (or app password).
-   **Returns:**
    -   The `imaplib.IMAP4_SSL` connection object on success.
    -   `None` on failure.
-   **Usage:**
    ```python
    conn = client.connect_imap("imap.example.com", "user@example.com", "password")
    if conn:
        print("Successfully connected!")
    ```

### `search_emails(self, criteria, charset='UTF-8')`
Performs a search in the currently selected mailbox based on given criteria.

-   **Parameters:**
    -   `criteria` (list): A list of IMAP search criteria strings (e.g., `['UNSEEN']`, `['SUBJECT', 'keyword']`, `['ALL']`).
    -   `charset` (str, optional): The charset for the search query. Defaults to 'UTF-8'. For most UID SEARCH operations with simple criteria, this is often not strictly needed or set to `None`. The method passes `None` as the charset argument to `imaplib.uid('search', None, *criteria)`.
-   **Returns:**
    -   A list of email UIDs (strings) matching the criteria.
    -   An empty list if no emails match or an error occurs.
-   **Usage:**
    ```python
    # Assuming INBOX is selected after connection
    # client.mail.select("INBOX") 
    uids_unseen = client.search_emails(['UNSEEN'])
    uids_with_subject = client.search_emails(['SUBJECT', 'Your Subject Keyword'])
    ```

### `search_unread_with_keywords(self, subject_keywords=None)`
A helper method to search for unread emails, optionally filtering by subject keywords.

-   **Parameters:**
    -   `subject_keywords` (list, optional): A list of keyword strings to search for in the subject. If provided, emails must contain all keywords (AND logic). If `None` or empty, searches for all unread emails.
-   **Returns:**
    -   A list of email UIDs (strings).
-   **Usage:**
    ```python
    # Search for all unread emails
    unread_uids = client.search_unread_with_keywords()
    # Search for unread emails with "invoice" and "report" in subject
    specific_unread_uids = client.search_unread_with_keywords(subject_keywords=["invoice", "report"])
    ```

### `fetch_email_headers(self, email_uids)`
Fetches specific headers (Subject, From, Date) for given email UIDs.

-   **Parameters:**
    -   `email_uids` (str or list): A single UID string or a list of UID strings.
-   **Returns:**
    -   A dictionary where keys are UIDs and values are the raw header strings for each email. If fetching fails for a UID, its value will be `None`. Returns an empty dictionary on major failure or if not connected.
-   **Usage:**
    ```python
    if uids:
        headers = client.fetch_email_headers(uids)
        for uid, header_text in headers.items():
            if header_text:
                print(f"UID: {uid}\nHeaders:\n{header_text[:200]}...")
    ```

### `mark_emails_as_seen(self, email_uids)`
Marks specified emails as SEEN (read).

-   **Parameters:**
    -   `email_uids` (str or list): A single UID string or a list of UID strings (comma-separated if providing as a single string direct to `imaplib.uid('store')`, but this method handles list conversion).
-   **Returns:**
    -   `True` on success, `False` on failure.
-   **Usage:**
    ```python
    if uids:
        client.mark_emails_as_seen(uids)
    ```

### `mark_emails_as_unseen(self, email_uids)`
Marks specified emails as UNSEEN (unread).

-   **Parameters:**
    -   `email_uids` (str or list): A single UID string or a list of UID strings.
-   **Returns:**
    -   `True` on success, `False` on failure.
-   **Usage:**
    ```python
    if uids:
        client.mark_emails_as_unseen(uids)
    ```

### `reset_all_emails_to_unseen(self, mailbox="INBOX")`
Resets all emails in the specified mailbox to UNSEEN.

-   **Parameters:**
    -   `mailbox` (str, optional): The name of the mailbox to operate on. Defaults to "INBOX".
-   **Returns:**
    -   `True` if the operation was attempted (even if no emails were found or no flags needed changing).
    -   `False` if there was an error (e.g., selecting mailbox, IMAP error).
-   **Usage:**
    ```python
    client.reset_all_emails_to_unseen() 
    ```

### `download_pdf_attachments(self, email_uid, download_folder="attachments")`
Downloads the first PDF attachment found in the specified email.

-   **Parameters:**
    -   `email_uid` (str): The UID of the email to process.
    -   `download_folder` (str, optional): The folder where the PDF should be saved. Defaults to "attachments". Will be created if it doesn't exist.
-   **Returns:**
    -   The full `filepath` (str) of the saved PDF on success.
    -   `None` if no PDF attachment is found or an error occurs.
-   **Usage:**
    ```python
    if uids:
        filepath = client.download_pdf_attachments(uids[0], download_folder="my_downloaded_pdfs")
        if filepath:
            print(f"PDF downloaded to: {filepath}")
    ```

### `logout(self)`
Closes the connection to the IMAP server. Uses `self.mail`.

-   **Usage:**
    ```python
    client.logout()
    ```

## Basic Usage Scenario

```python
from src.email_client import EmailClient
import os

# --- Configuration ---
IMAP_HOST = "imap.dreamhost.com"
IMAP_USERNAME = "travelbot@jumpkey.com"
IMAP_PASSWORD = "MadTravel2025@@" # Ideally, use environment variables or a config file
DOWNLOAD_DIR = "downloaded_itineraries"

# --- Initialize Client ---
client = EmailClient()

# --- Connect to Server ---
if not client.connect_imap(IMAP_HOST, IMAP_USERNAME, IMAP_PASSWORD):
    print("Failed to connect to IMAP server. Exiting.")
    exit()

try:
    # --- Select Mailbox (Important for subsequent operations) ---
    # The EmailClient methods assume self.mail is an active connection.
    # Selecting mailbox is crucial before search.
    # For methods like reset_all_emails_to_unseen, mailbox selection is internal.
    # For searches, it's good practice to select INBOX explicitly if not done by default.
    print("Selecting INBOX...")
    status, data = client.mail.select("INBOX")
    if status != 'OK':
        print("Failed to select INBOX.")
        client.logout()
        exit()
    print("INBOX selected.")

    # --- Reset all emails to UNSEEN (for testing) ---
    print("Resetting emails to unseen...")
    client.reset_all_emails_to_unseen()

    # --- Search for Unread Itinerary Emails ---
    print("Searching for unread emails with 'Itinerary' in subject...")
    # Using a general keyword; specific keywords from README are "itinerary", "confirmation", "travel", "booking"
    itinerary_uids = client.search_unread_with_keywords(subject_keywords=["Itinerary"])

    if not itinerary_uids:
        print("No unread itinerary emails found.")
    else:
        print(f"Found {len(itinerary_uids)} unread itinerary email(s): {itinerary_uids}")

        # --- Process the first found itinerary email ---
        uid_to_process = itinerary_uids[0]
        
        print(f"Fetching headers for UID {uid_to_process}...")
        headers = client.fetch_email_headers(uid_to_process)
        if headers and headers.get(uid_to_process):
            print(f"Headers for {uid_to_process}:\n{headers[uid_to_process][:200]}...")

        print(f"Downloading PDF from UID {uid_to_process}...")
        pdf_filepath = client.download_pdf_attachments(uid_to_process, download_folder=DOWNLOAD_DIR)

        if pdf_filepath:
            print(f"PDF successfully downloaded to: {pdf_filepath}")
            # Here, you would typically pass pdf_filepath to the pdf_processor
            # from src.pdf_processor import extract_text_from_pdf
            # text_content = extract_text_from_pdf(pdf_filepath)
            # print(f"Extracted text (first 100 chars): {text_content[:100]}...")
            
            # --- Mark as Seen ---
            print(f"Marking UID {uid_to_process} as SEEN.")
            client.mark_emails_as_seen(uid_to_process)
        else:
            print(f"No PDF found or error downloading for UID {uid_to_process}.")

finally:
    # --- Logout ---
    print("Logging out...")
    client.logout()

```
