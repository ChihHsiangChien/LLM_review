import re
import os

def replace_page_numbers(input_filepath, output_filepath):
    # Regex to match the target line and capture the page number
    # Handles potential variations in spacing and ensures both numbers match
    regex = re.compile(r"^(## 區塊 ID: .*?_Page)(\d+)( \(頁碼: )\2(\))$")
    # 區塊換頁碼加上多少數字？
    subtraction_value = 13
    lines_changed = 0

    try:
        with open(input_filepath, 'r', encoding='utf-8') as infile, \
             open(output_filepath, 'w', encoding='utf-8') as outfile:

            for line in infile:
                match = regex.match(line)
                if match:
                    try:
                        original_page_number = int(match.group(2))
                        new_page_number = original_page_number - subtraction_value
                        # Construct the new line
                        new_line = f"## {new_page_number}\n"
                        outfile.write(new_line)
                        lines_changed += 1
                        print(f"Replaced: '{line.strip()}' with '{new_line.strip()}'")
                    except ValueError:
                        # If the captured number isn't a valid integer, write original line
                        outfile.write(line)
                        print(f"Warning: Could not convert page number in line: {line.strip()}")
                    except Exception as e:
                        outfile.write(line)
                        print(f"Error processing line: {line.strip()} - {e}")
                else:
                    # If the line doesn't match, write it as is
                    outfile.write(line)

        print(f"\nProcessing complete. {lines_changed} lines replaced.")
        print(f"Output saved to: {output_filepath}")

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_filepath}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# --- Configuration ---
input_file = r"c:\Users\User\Documents\GitHub\LLM_review\grok_summary_review copy.md" # 您的輸入檔案路徑
output_file = r"c:\Users\User\Documents\GitHub\LLM_review\grok_summary_review_modified.md" # 輸出的新檔案路徑

# --- Run the replacement ---
# **重要：執行前請確保輸入檔案路徑正確，並建議先備份原始檔案！**
replace_page_numbers(input_file, output_file)

# --- (Optional) Post-processing ---
# 如果確認輸出檔案正確無誤，您可以取消註解以下程式碼來取代原始檔案
# import shutil
# try:
#     shutil.move(output_file, input_file)
#     print(f"Successfully replaced original file with modified version.")
# except Exception as e:
#     print(f"Error replacing original file: {e}")
