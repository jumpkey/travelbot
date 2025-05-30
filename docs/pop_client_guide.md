# POPClient Guide

## Purpose

The `POPClient` class provides functionalities to connect to a POP3 email server, list messages, retrieve full email messages, and download PDF attachments from these messages. It uses username/password authentication with POP3_SSL.

## Initialization

The client is initialized without any parameters:

```python
from src.pop_client import POPClient

client = POPClient()
```
The POP3 connection object is stored in `client.connection` after a successful connection.

## Methods

### `connect_pop(self, hostname, port, username, password)`
Connects to the specified POP3 server using SSL.

-   **Parameters:**
    -   `hostname` (str): The POP3 server hostname (e.g., "pop.dreamhost.com").
    -   `port` (int): The POP3 server port (e.g., 995 for SSL).
    -   `username` (str): The email account username.
    -   `password` (str): The email account password (or app password).
-   **Returns:**
    -   The `poplib.POP3_SSL` connection object on success.
    -   `None` on failure.
-   **Usage:**
    ```python
    conn = client.connect_pop("pop.example.com", 995, "user@example.com", "password")
    if conn:
        print("Successfully connected to POP3 server!")
    ```

### `list_messages(self)`
Lists all messages currently in the mailbox. POP3 typically provides message numbers and their sizes.

-   **Parameters:** None.
-   **Returns:**
    -   A tuple `(response, message_info_list, octets)`:
        -   `response` (bytes): The raw server response to the LIST command.
        -   `message_info_list` (list): A list of dictionaries, where each dictionary is `{'msg_num': int, 'size': int}`.
        -   `octets` (int): Total size of maildrop in octets (may not be used by all servers).
    -   Returns `(None, [])` on error or if not connected.
-   **Usage:**
    ```python
    resp, msg_infos = client.list_messages()
    if resp and resp.startswith(b'+OK'):
        for info in msg_infos:
            print(f"Message Number: {info['msg_num']}, Size: {info['size']} bytes")
    ```

### `retrieve_email_message(self, message_num)`
Retrieves the full raw content of a specific email message by its number.

-   **Parameters:**
    -   `message_num` (int or str): The number of the message to retrieve.
-   **Returns:**
    -   The raw email message as `bytes` on success.
    -   `None` on failure.
-   **Usage:**
    ```python
    if msg_infos:
        first_msg_num = msg_infos[0]['msg_num']
        raw_email = client.retrieve_email_message(first_msg_num)
        if raw_email:
            print(f"Retrieved message {first_msg_num}, {len(raw_email)} bytes.")
            # To parse:
            # import email
            # email_message = email.message_from_bytes(raw_email)
            # print(f"Subject: {email_message.get('Subject')}")
    ```

### `download_pdf_attachments_pop(self, message_num, download_folder="attachments_pop")`
Retrieves a specific email message, then finds and downloads the first PDF attachment.

-   **Parameters:**
    -   `message_num` (int or str): The number of the email message to process.
    -   `download_folder` (str, optional): The folder where the PDF should be saved. Defaults to "attachments_pop". Will be created if it doesn't exist.
-   **Returns:**
    -   The full `filepath` (str) of the saved PDF on success.
    -   `None` if no PDF attachment is found or an error occurs.
-   **Usage:**
    ```python
    if msg_infos:
        msg_num_to_process = msg_infos[0]['msg_num'] # Example: process the first message
        filepath = client.download_pdf_attachments_pop(msg_num_to_process, download_folder="my_pop_downloads")
        if filepath:
            print(f"PDF from POP message {msg_num_to_process} downloaded to: {filepath}")
    ```

### `disconnect_pop(self)`
Closes the connection to the POP3 server.

-   **Usage:**
    ```python
    client.disconnect_pop()
    ```

## Basic Usage Scenario

```python
from src.pop_client import POPClient
import os
import email # For parsing the retrieved message if needed

# --- Configuration ---
POP_HOST = "pop.dreamhost.com"
POP_PORT = 995
POP_USERNAME = "travelbot@jumpkey.com"
POP_PASSWORD = "MadTravel2025@@" # Ideally, use environment variables or a config file
DOWNLOAD_DIR = "downloaded_itineraries_pop"

# --- Initialize Client ---
client = POPClient()

# --- Connect to Server ---
if not client.connect_pop(POP_HOST, POP_PORT, POP_USERNAME, POP_PASSWORD):
    print("Failed to connect to POP3 server. Exiting.")
    exit()

try:
    # --- List Messages ---
    print("Listing messages from POP3 server...")
    resp, msg_infos = client.list_messages()

    if not (resp and resp.startswith(b'+OK') and msg_infos):
        print("No messages found or error listing messages.")
    else:
        print(f"Found {len(msg_infos)} message(s).")
        # Example: Process the first message if available
        msg_to_process_info = msg_infos[0]
        msg_num = msg_to_process_info['msg_num']
        print(f"Processing message number {msg_num} (Size: {msg_to_process_info['size']})...")

        # --- Retrieve a specific message (optional, as download_pdf_attachments_pop does this) ---
        # raw_email_content = client.retrieve_email_message(msg_num)
        # if raw_email_content:
        #     email_obj = email.message_from_bytes(raw_email_content)
        #     print(f"Subject of message {msg_num}: {email_obj.get('Subject')}")
        # else:
        #     print(f"Could not retrieve message {msg_num}.")

        # --- Download PDF from the message ---
        print(f"Attempting to download PDF from message {msg_num}...")
        pdf_filepath = client.download_pdf_attachments_pop(msg_num, download_folder=DOWNLOAD_DIR)

        if pdf_filepath:
            print(f"PDF from message {msg_num} successfully downloaded to: {pdf_filepath}")
            # Here, you would typically pass pdf_filepath to the pdf_processor
            # from src.pdf_processor import extract_text_from_pdf
            # text_content = extract_text_from_pdf(pdf_filepath)
            # print(f"Extracted text (first 100 chars): {text_content[:100]}...")
        else:
            print(f"No PDF found or error downloading for message {msg_num}.")

finally:
    # --- Disconnect ---
    print("Disconnecting from POP3 server...")
    client.disconnect_pop()

```
