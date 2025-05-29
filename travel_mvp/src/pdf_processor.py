import pdfplumber
import os

def extract_text_from_pdf(pdf_filepath):
    """
    Extracts all text from a given PDF file using pdfplumber.

    Args:
        pdf_filepath (str): The path to the PDF file.

    Returns:
        str: Concatenated text from all pages. Returns an empty string on error
             (e.g., file not found, PDF processing error).
    """
    if not os.path.exists(pdf_filepath):
        print(f"Error: File not found at {pdf_filepath}")
        return ""

    full_text = []
    try:
        with pdfplumber.open(pdf_filepath) as pdf:
            if not pdf.pages:
                print(f"Warning: No pages found in PDF: {pdf_filepath}")
                return ""
            
            print(f"Extracting text from {len(pdf.pages)} page(s) in '{os.path.basename(pdf_filepath)}'...")
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    full_text.append(page_text)
                else:
                    print(f"Note: No text extracted from page {i+1} of '{os.path.basename(pdf_filepath)}'.")
            
            concatenated_text = "\n".join(full_text)
            text_length = len(concatenated_text)
            print(f"Successfully extracted text from '{os.path.basename(pdf_filepath)}'. Total length: {text_length} chars.")
            return concatenated_text
            
    except pdfplumber.utils.exceptions.PdfminerException as e_pdf_related: # Catching PdfminerException
        print(f"Error: PDF processing error in '{pdf_filepath}': {e_pdf_related}")
        return ""
    except Exception as e:
        print(f"Error processing PDF file '{pdf_filepath}': {e}")
        return ""

if __name__ == '__main__':
    pass
