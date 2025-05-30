# PDF Processor Guide

## Purpose

The `pdf_processor` module provides utilities for processing PDF files, primarily focusing on text extraction. It uses the `pdfplumber` library to achieve this.

## Functions

### `extract_text_from_pdf(pdf_filepath)`
Extracts all text content from the pages of a given PDF file.

-   **Parameters:**
    -   `pdf_filepath` (str): The full path to the PDF file from which text needs to be extracted.
-   **Returns:**
    -   `str`: A single string containing all extracted text, with text from different pages joined by newline characters (`\n`).
    -   Returns an empty string (`""`) if:
        -   The specified `pdf_filepath` does not exist.
        -   The file is not a valid PDF or is corrupted (e.g., `pdfplumber.exceptions.PDFSyntaxError` or other `pdfplumber` related errors occur).
        -   The PDF contains no pages or no extractable text.
        -   Any other unexpected error occurs during processing.
-   **Error Handling:**
    -   Prints error messages to standard output if the file is not found, if it's not a valid PDF, or if other exceptions occur during processing.
    -   Prints a warning if a page contains no extractable text.

## Basic Usage Scenario

```python
from src.pdf_processor import extract_text_from_pdf
import os

# Assuming you have a PDF file, for example, one downloaded by EmailClient or POPClient:
# Example PDF path (replace with an actual path to a PDF file for testing)
# This path might come from a previous step where a PDF was downloaded.
# For instance, if EmailClient downloaded 'itinerary.pdf' into 'downloaded_pdfs':
# pdf_file_path = os.path.join("downloaded_pdfs", "itinerary.pdf")

# For this example, let's assume a PDF exists at 'tests/data/itinerary_sample_1.pdf'
# (as established in previous development steps)
pdf_file_path = os.path.join("tests", "data", "itinerary_sample_1.pdf") # Adjust path as needed relative to your script

if not os.path.exists(pdf_file_path):
    print(f"Error: Sample PDF not found at {pdf_file_path}. Cannot demonstrate usage.")
else:
    print(f"Attempting to extract text from: {pdf_file_path}")
    extracted_text = extract_text_from_pdf(pdf_file_path)

    if extracted_text:
        print(f"Successfully extracted {len(extracted_text)} characters.")
        print("\n--- Extracted Text (first 500 characters) ---")
        print(extracted_text[:500])
        print("\n---------------------------------------------")
        
        # You can now use this text for further processing, e.g., with an LLM.
        # For example, saving it to a file:
        # with open("extracted_output.txt", "w", encoding="utf-8") as f:
        #     f.write(extracted_text)
        # print("Full extracted text saved to extracted_output.txt")
    else:
        print("No text was extracted, or an error occurred during extraction.")

```

## Dependencies

-   `pdfplumber`: This module relies on the `pdfplumber` library, which should be listed in `requirements.txt`.
-   `os`: Used for checking file existence (`os.path.exists`) and getting basename (`os.path.basename`).

```
