# Setup and Configuration Guide

This guide provides instructions on how to set up the `travel_mvp` project environment, install dependencies, and run the included tests.

## Prerequisites

-   **Python:** Python 3.8 or newer is recommended. You can check your Python version by running `python --version` or `python3 --version`.
-   **Git:** Required for cloning the repository.

## Setup Instructions

### 1. Clone the Repository
If you haven't already, clone the project repository to your local machine.
```bash
# Replace with the actual repository URL
# git clone https://github.com/yourusername/travel_mvp.git
# cd travel_mvp
```

### 2. Create a Virtual Environment
It is highly recommended to use a virtual environment to manage project dependencies and avoid conflicts with system-wide packages.

-   **Using `venv` (built-in with Python 3):**
    ```bash
    # Navigate to the project root directory (e.g., travel_mvp)
    python3 -m venv venv 
    ```
    This creates a directory named `venv` within your project folder.

-   **Activate the Virtual Environment:**
    -   On macOS and Linux:
        ```bash
        source venv/bin/activate
        ```
    -   On Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    Your command prompt should now indicate that you are in the virtual environment (e.g., `(venv) Your-Computer:travel_mvp user$`).

### 3. Install Dependencies
Once the virtual environment is activated, install the required Python packages using the `requirements.txt` file:
```bash
pip install -r requirements.txt
```
This will install `pdfplumber` and any other libraries specified in the file.

## Running Tests

The project includes unit tests to verify the functionality of its components.

-   **Navigate to the project root directory** (e.g., `travel_mvp`) if you are not already there.
-   **Ensure your virtual environment is activated.**
-   **Run tests using `unittest`'s discovery feature:**
    ```bash
    python -m unittest discover -s tests
    ```
    Or, to run a specific test file:
    ```bash
    python -m unittest tests.test_email_client 
    # (or tests.test_pop_client, tests.test_pdf_processor)
    ```
    The tests will output their results to the console. Live tests (e.g., for email connection) will attempt to connect to the configured DreamHost server if not skipped.

## Email Account Configuration for Testing

Some tests (particularly in `test_email_client.py` and `test_pop_client.py`) are designed to interact with a live email server to verify connection, fetching, and downloading functionalities.

-   **Test Account:** The current live tests are configured to use the following DreamHost account:
    -   **IMAP Host:** `imap.dreamhost.com` (Port 993, SSL)
    -   **POP3 Host:** `pop.dreamhost.com` (Port 995, SSL)
    -   **Username:** `travelbot@jumpkey.com`
    -   **Password:** `MadTravel2025@@`

-   **Caution:** These credentials are for testing purposes. Avoid using personal or sensitive email accounts directly in test configurations if possible. For production systems, credentials should be managed securely (e.g., environment variables, secrets management tools), not hardcoded.

-   **Setting up Test Emails:** For tests involving email content (e.g., searching by subject, downloading attachments), you may need to manually place emails with specific characteristics (subjects, attachments) into the test account's INBOX and ensure they are in the correct state (e.g., UNSEEN/unread) for the tests to pass as expected. The `EmailClient.reset_all_emails_to_unseen()` method can be used to mark all emails in the INBOX as unread.

## Project Structure (Overview)

```
travel_mvp/
├── docs/                     # Documentation files (guides)
│   ├── email_client_guide.md
│   ├── pop_client_guide.md
│   ├── pdf_processor_guide.md
│   └── setup_guide.md
├── src/                      # Source code
│   ├── __init__.py
│   ├── email_client.py       # IMAP email functionalities
│   ├── pop_client.py         # POP3 email functionalities
│   ├── pdf_processor.py      # PDF text extraction
│   ├── main.py               # Main application entry point (to be developed)
│   └── config.py             # Configuration loading (to be developed)
├── tests/                    # Test files
│   ├── __init__.py
│   ├── data/                 # Test data (e.g., sample PDFs)
│   │   ├── MDWAZL_itinerary.pdf
│   │   ├── MAKEUX_itinerary.pdf
│   │   ├── MDWAZL_extracted_text.txt
│   │   ├── MAKEUX_extracted_text.txt
│   │   └── sample_itinerary.pdf (dummy PDF for basic pdfplumber test)
│   ├── test_email_client.py
│   ├── test_pop_client.py
│   └── test_pdf_processor.py
├── requirements.txt          # Python package dependencies
├── README.md                 # Project overview and MVP plan
└── ...                       # Other project files (e.g., .gitignore, LICENSE)
```
This guide should help another developer get started with understanding, setting up, and testing the existing codebase.

```
