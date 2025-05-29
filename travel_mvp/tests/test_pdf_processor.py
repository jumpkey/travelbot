import unittest
import os
import sys

# Adjust the Python path to include the src directory for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pdf_processor import extract_text_from_pdf 

class TestPDFProcessor(unittest.TestCase):

    def setUp(self):
        self.base_dir = os.path.dirname(__file__)
        self.data_dir = os.path.join(self.base_dir, "data")
        self.sample_pdf_path = os.path.join(self.data_dir, "sample_itinerary.pdf")
        # self.output_dir = os.path.join(self.base_dir, "output") # If creating output files
        # os.makedirs(self.output_dir, exist_ok=True) # Ensure output dir exists if used

        # Ensure data directory exists for not_a_pdf.txt creation
        os.makedirs(self.data_dir, exist_ok=True)


    def test_extract_text_from_sample_pdf(self):
        print(f"\nRunning test_extract_text_from_sample_pdf on: {self.sample_pdf_path}...")
        
        if not os.path.exists(self.sample_pdf_path):
            self.skipTest(f"Sample PDF not found at {self.sample_pdf_path}. Cannot run text extraction test.")
            return

        extracted_text = extract_text_from_pdf(self.sample_pdf_path)
        
        self.assertIsNotNone(extracted_text, "Extracted text should not be None.")
        self.assertTrue(len(extracted_text) > 0, "Extracted text should not be empty for a valid PDF with text.")
        
        print(f"Successfully extracted {len(extracted_text)} characters.")
        # Limit printing for very long texts to keep logs concise
        print(f"First 200 chars of extracted text: '{extracted_text[:200]}...'")

        # Assertions for the dummy PDF content
        self.assertIn("This is a test PDF document.", extracted_text, 
                      "Expected text not found in dummy PDF.")

    def test_extract_text_from_nonexistent_pdf(self):
        print("\nRunning test_extract_text_from_nonexistent_pdf...")
        non_existent_path = os.path.join(self.data_dir, "non_existent.pdf")
        extracted_text = extract_text_from_pdf(non_existent_path)
        self.assertEqual(extracted_text, "", "Should return an empty string for a non-existent file.")

    def test_extract_text_from_not_a_pdf(self):
        print("\nRunning test_extract_text_from_not_a_pdf...")
        not_a_pdf_path = os.path.join(self.data_dir, "not_a_pdf.txt")
        try:
            with open(not_a_pdf_path, "w") as f:
                f.write("This is not a PDF file.")
            
            extracted_text = extract_text_from_pdf(not_a_pdf_path)
            self.assertEqual(extracted_text, "", "Should return an empty string for a non-PDF file.")
        finally:
            if os.path.exists(not_a_pdf_path):
                os.remove(not_a_pdf_path) # Clean up dummy file

if __name__ == '__main__':
    unittest.main()
