import os
import csv
import re
import argparse # For command-line arguments

# --- Configuration ---
# MAX_CHUNK_CHARS is no longer needed for the primary chunking logic
# if each page is one chunk. We can remove or ignore it.
# MAX_CHUNK_CHARS = 2000 # Removed/Commented out

# Output filename for the processed chunks
DEFAULT_CHUNK_OUTPUT_FILE = "book_chunks.csv"

# --- Helper Functions ---

def clean_page_footer(lines):
    """
    Attempts to remove common footer elements like page numbers
    or 'Author Name \n Page Number' from the end of a page's text lines.
    This is heuristic and might need adjustment based on the book format.
    """
    cleaned_lines = list(lines) # Make a mutable copy
    if not cleaned_lines:
        return cleaned_lines

    # Rule 1: Remove last line if it's just a number
    last_line = cleaned_lines[-1].strip()
    if last_line.isdigit():
        # print(f"    Cleaning footer (Rule 1): '{last_line}'")
        cleaned_lines.pop()
        if not cleaned_lines:
            return cleaned_lines

    # Rule 2: Remove last two lines if they match "Name\nNumber" pattern
    # (Check if there are at least 2 lines left)
    if len(cleaned_lines) >= 2:
        second_last_line = cleaned_lines[-2].strip()
        last_line_again = cleaned_lines[-1].strip() # Re-check last line after potential pop
        # Check if last line is number and second last is non-empty text
        if last_line_again.isdigit() and second_last_line and not second_last_line.isdigit():
             # A simple check, could be more specific (e.g., check for author name patterns)
             # print(f"    Cleaning footer (Rule 2): '{second_last_line}\\n{last_line_again}'")
             cleaned_lines.pop() # Remove number
             cleaned_lines.pop() # Remove name line

    return cleaned_lines


def chunk_text_by_page_and_para(filename, content):
    """
    Splits text by page markers ("--- Page X ---").
    Each page's content becomes a single chunk.
    Assigns unique IDs like 'filename_PageX'.
    """
    base_filename = os.path.splitext(os.path.basename(filename))[0]
    chunks = []
    current_pos = 0
    page_counter = 0 # For text before the first marker or if no markers exist

    # Regex to find page markers like "--- Page X ---"
    page_marker_pattern = re.compile(r'--- Page (\d+) ---')

    matches = list(page_marker_pattern.finditer(content))

    if not matches:
        # No page markers found, treat the whole file as one "page" (Page 0)
        print("警告：在檔案中未找到 '--- Page X ---' 標記，將整個檔案視為單一區塊 (Page 0) 處理。") # Modified warning slightly
        page_content = content
        page_num_str = "0" # Assign page 0
        process_page_content(page_content, base_filename, page_num_str, chunks) # Call the modified processor
    else:
        # Process text before the first marker (if any) as Page 0
        first_match_start = matches[0].start()
        if first_match_start > 0:
            page_content = content[current_pos:first_match_start].strip()
            if page_content:
                 page_num_str = "0" # Assign page 0 to content before first marker
                 print(f"  處理第一個標記前的內容 (頁碼 {page_num_str})...")
                 process_page_content(page_content, base_filename, page_num_str, chunks)
            # current_pos = matches[0].end() # No need to track end if processing whole page

        # Process content between markers (or from marker to end)
        for i, match in enumerate(matches):
            page_num_str = match.group(1)
            print(f"  處理頁碼 {page_num_str}...")

            # Find the start of the next marker, or end of file
            next_marker_start = matches[i+1].start() if i + 1 < len(matches) else len(content)

            # Extract content for the current page (between end of current marker and start of next)
            # Or from start of marker if we want the marker itself included? Let's stick to between.
            page_content = content[match.end():next_marker_start].strip()
            # current_pos = next_marker_start # No longer needed for this logic

            if page_content:
                process_page_content(page_content, base_filename, page_num_str, chunks)

    return chunks

# --- MODIFIED FUNCTION ---
def process_page_content(page_content, base_filename, page_num_str, all_chunks):
    """
    Helper to process the content of a single page.
    Cleans footers and treats the entire page content as one chunk.
    """
    lines = page_content.splitlines()
    cleaned_lines = clean_page_footer(lines)
    cleaned_page_content = "\n".join(cleaned_lines).strip()

    if not cleaned_page_content:
        print(f"    頁碼 {page_num_str} 清理後無內容，跳過。")
        return

    # --- Removed paragraph splitting and MAX_CHUNK_CHARS logic ---
    # paragraphs = re.split(r'\n\s*\n', cleaned_page_content)
    # block_counter = 1
    # for para in paragraphs:
    #    ... (splitting logic removed) ...

    # Treat the entire cleaned page content as a single chunk
    chunk_id = f"{base_filename}_Page{page_num_str}" # Simplified chunk ID
    all_chunks.append({"chunk_id": chunk_id, "original_text": cleaned_page_content})
    # print(f"    頁碼 {page_num_str} 已作為單一區塊加入。") # Optional: Add confirmation

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preprocess a book TXT file into chunks based on page markers (one chunk per page).") # Updated description
    parser.add_argument("input_file", help="Path to the input TXT file.")
    parser.add_argument("-o", "--output", default=DEFAULT_CHUNK_OUTPUT_FILE,
                        help=f"Path to the output CSV file for chunks (default: {DEFAULT_CHUNK_OUTPUT_FILE})")
    args = parser.parse_args()

    input_filepath = args.input_file
    output_filepath = args.output

    if not os.path.exists(input_filepath):
        print(f"錯誤：找不到輸入檔案 '{input_filepath}'")
        exit(1)

    print(f"--- 開始預處理檔案: {input_filepath} ---")
    print(f"--- 分塊邏輯：每個頁面 ('--- Page X ---'之間) 作為一個區塊 ---") # Added clarification

    try:
        # It's often safer to specify encoding, especially if files might come from different OS
        with open(input_filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"錯誤：無法讀取檔案 {input_filepath}: {e}")
        exit(1)

    # Perform chunking using the modified logic
    processed_chunks = chunk_text_by_page_and_para(input_filepath, content)

    if not processed_chunks:
        print("錯誤：未能從檔案中提取任何文字區塊。")
        exit(1)

    print(f"\n--- 處理完成，共生成 {len(processed_chunks)} 個區塊 (每個區塊代表一頁) ---") # Updated summary

    # Write chunks to CSV
    try:
        with open(output_filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['chunk_id', 'original_text']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(processed_chunks)
        print(f"區塊已成功寫入到: {output_filepath}")
    except Exception as e:
        print(f"錯誤：無法寫入區塊 CSV 檔案 {output_filepath}: {e}")
        exit(1)

