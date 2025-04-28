# 1. Install Libraries (if running in Colab/Jupyter)
# !pip install -U -q google google-generativeai pypdf

import os
import time
import google.generativeai as genai
from google.generativeai import types
from pypdf import PdfReader, PdfWriter
import sys # Import sys for flushing output

from dotenv import load_dotenv


# --- Configuration ---
load_dotenv()  # Load environment variables from .env file


# --- API Keys ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # Or GEMINI_API_KEY if that's your .env name


# --- Colab Specific Setup ---
# (Keep the Colab setup block as it was, or adapt if needed)
# try:
#     # ... Colab setup ...
# except (ImportError, ModuleNotFoundError, ValueError) as e:
#     # --- Local Environment Setup ---
#     print("Not running in Colab or Colab setup failed. Assuming local environment.")
#     # ... (rest of the local setup block) ...
#     if "GEMINI_API_KEY" not in os.environ:
#         raise ValueError("GEMINI_API_KEY environment variable not set.")
#     WORKING_DIR = os.path.dirname(os.path.abspath(__file__))
#     os.chdir(WORKING_DIR)
#     print(f"Running locally. Working directory set to: {WORKING_DIR}")
# --- End Setup ---

# Configuration
INPUT_PDF_FILENAME = "output_cropped_upper.pdf"
OUTPUT_TEXT_FILENAME = "ocr_output_upper.txt"
# State file to track progress
STATE_FILENAME = ".ocr_progress_state.txt" # Hidden file to store last completed page
# Use a model that supports vision/PDF processing well
MODEL_NAME = "gemini-1.5-flash-latest"
# Delay between page processing to avoid hitting API rate limits (in seconds)
PAGE_DELAY = 2

def save_progress(page_num):
    """Saves the last successfully processed page number."""
    try:
        with open(STATE_FILENAME, 'w') as f:
            f.write(str(page_num))
    except IOError as e:
        print(f"Warning: Could not save progress state to {STATE_FILENAME}: {e}")

def load_progress():
    """Loads the last successfully processed page number. Returns 0 if no state."""
    if not os.path.exists(STATE_FILENAME):
        return 0
    try:
        with open(STATE_FILENAME, 'r') as f:
            content = f.read().strip()
            if content:
                return int(content)
            else:
                return 0 # File exists but is empty
    except (IOError, ValueError) as e:
        print(f"Warning: Could not read or parse progress state from {STATE_FILENAME}: {e}. Starting from beginning.")
        # Optionally delete corrupted state file here
        # try: os.remove(STATE_FILENAME) except OSError: pass
        return 0

def delete_progress_state():
    """Deletes the progress state file upon successful completion."""
    try:
        if os.path.exists(STATE_FILENAME):
            os.remove(STATE_FILENAME)
            print(f"Deleted progress state file: {STATE_FILENAME}")
    except OSError as e:
        print(f"Warning: Could not delete progress state file {STATE_FILENAME}: {e}")


def ocr_pdf_batched(pdf_path, output_txt_path):
    """
    Performs OCR on a PDF page by page using Gemini, saves to a text file,
    and supports resuming from the last completed page.

    Args:
        pdf_path (str): Path to the input PDF file.
        output_txt_path (str): Path to save the extracted text.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: Input PDF not found at {pdf_path}")
        return

    # --- State Loading ---
    last_completed_page = load_progress()
    start_page = last_completed_page + 1
    # --- End State Loading ---

    print(f"Starting OCR process for: {pdf_path}")
    print(f"Output will be saved to: {output_txt_path}")

    # Determine file mode: 'w' (write) if starting fresh, 'a' (append) if resuming
    file_mode = 'a' if start_page > 1 else 'w'
    if start_page > 1:
        print(f"Resuming process from page {start_page}.")
    else:
        print("Starting process from the beginning.")


    client = None
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("Error: GOOGLE_API_KEY environment variable is not set")
            return
        if not api_key.startswith("AI"):
            print("Warning: GOOGLE_API_KEY format looks incorrect. Should start with 'AI'")

            
        print(f"Attempting to configure Gemini with API key: {api_key[:4]}...")
        genai.configure(api_key=api_key) # Use the correct key here
        client = genai.GenerativeModel(model_name=MODEL_NAME)
        print("Gemini client configured successfully.")
    except Exception as e:
        print(f"Critical error configuring Gemini client: {str(e)}")
        import traceback
        print("Full error details:")
        print(traceback.format_exc())
        return

    try:
        reader = PdfReader(pdf_path)
        num_pages = len(reader.pages)
        print(f"PDF has {num_pages} total pages.")

        if start_page > num_pages:
            print("All pages seem to have been processed already based on state file.")
            return

        # Open output file in appropriate mode (append or write)
        with open(output_txt_path, file_mode, encoding='utf-8') as outfile:
            # Add a separator if appending
            if file_mode == 'a':
                 outfile.write(f"\n--- Resuming process at page {start_page} ---\n\n")

            # Loop starting from the page after the last completed one
            for i in range(start_page - 1, num_pages):
                page_num = i + 1
                temp_pdf_path = f"temp_page_{page_num}.pdf"

                try:
                    # --- Progress Output ---
                    progress_percent = (page_num / num_pages) * 100
                    print(f"\n--- Processing Page {page_num}/{num_pages} ({progress_percent:.1f}%) ---", flush=True)

                    # 1. Create temp page PDF
                    writer = PdfWriter()
                    writer.add_page(reader.pages[i])
                    with open(temp_pdf_path, "wb") as temp_pdf_file:
                        writer.write(temp_pdf_file)
                    print(f"Created temporary file: {temp_pdf_path}", flush=True)

                    # 2. Read the PDF file as binary
                    with open(temp_pdf_path, 'rb') as f:
                        pdf_content = f.read()

                    # 3. Prepare prompt and content
                    prompt = "Extract all text content from this PDF page accurately. Preserve original line breaks where possible."
                    
                    # Create generation config to handle potential longer responses
                    generation_config = {
                        "temperature": 0.1,
                        "top_p": 1,
                        "top_k": 1,
                        "max_output_tokens": 2048,
                    }

                    # 4. Call Gemini API with image content
                    response = client.generate_content(
                        contents=[prompt, {"mime_type": "application/pdf", "data": pdf_content}],
                        generation_config=generation_config
                    )

                    # 5. Extract and save text
                    page_text = response.text.strip()
                    print(f"Extracted text (first 100 chars): {page_text[:100]}...", flush=True)
                    outfile.write(f"--- Page {page_num} ---\n")
                    outfile.write(page_text)
                    outfile.write("\n\n")
                    outfile.flush()

                    # --- Save Progress State ---
                    save_progress(page_num)

                    print(f"Successfully processed and saved page {page_num}.", flush=True)

                except Exception as e:
                    print(f"Error processing page {page_num}: {e}", flush=True)
                    outfile.write(f"--- Page {page_num} ---\n")
                    outfile.write(f"[Error processing page: {e}]\n\n")
                    outfile.flush()
                    print(f"Skipping to next page due to error on page {page_num}.", flush=True)

                finally:
                    # 6. Clean up local temp file
                    if os.path.exists(temp_pdf_path):
                        try:
                            os.remove(temp_pdf_path)
                            print(f"Deleted temporary file: {temp_pdf_path}", flush=True)
                        except OSError as oe:
                             print(f"Warning: Could not delete temporary file {temp_pdf_path}: {oe}", flush=True)
                    
                    # 7. Delay
                    if page_num < num_pages: # No need to delay after the last page
                        print(f"Waiting for {PAGE_DELAY} seconds...", flush=True)
                        time.sleep(PAGE_DELAY)

            print(f"\nFinished processing all pages up to {num_pages}.")
            delete_progress_state()

    except Exception as e:
        print(f"\nAn critical error occurred during the main PDF processing: {e}")
        print("Progress up to the last successfully completed page (if any) is saved.")
        print("You can try running the script again to resume.")


if __name__ == "__main__":
    # Ensure WORKING_DIR is defined (copying setup logic is safer)
    try:
        # Attempt to get WORKING_DIR from the setup block logic
        if 'WORKING_DIR' not in locals() and 'WORKING_DIR' not in globals():
             # Fallback for local execution if setup block wasn't fully run in context
             if 'google.colab' not in sys.modules: # Basic check if not in Colab
                 WORKING_DIR = os.path.dirname(os.path.abspath(__file__))
                 print(f"Warning: WORKING_DIR not set, defaulting to script directory: {WORKING_DIR}")
                 os.chdir(WORKING_DIR)
             else:
                 # Handle case where it's Colab but WORKING_DIR wasn't set (shouldn't happen with full script run)
                 print("Error: Could not determine WORKING_DIR in Colab environment.")
                 sys.exit(1) # Exit if working directory is critical and unknown

        input_pdf_full_path = os.path.join(WORKING_DIR, INPUT_PDF_FILENAME)
        output_txt_full_path = os.path.join(WORKING_DIR, OUTPUT_TEXT_FILENAME)
        ocr_pdf_batched(input_pdf_full_path, output_txt_full_path)
    except NameError:
         print("Error: WORKING_DIR was not defined. Ensure the setup block runs correctly.")
         sys.exit(1)
    except Exception as main_exec_error:
         print(f"An unexpected error occurred in the main execution block: {main_exec_error}")
         sys.exit(1)

