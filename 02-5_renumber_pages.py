import re
import os

# --- Configuration ---
input_filename = "ocr_output.txt"
output_filename = "ocr_output_renumbered.txt" # Save to a new file for safety

# Calculate the offset based on the example: Original 22 becomes New 1
# offset = original_start_page - new_start_page
offset = 22 - 1

# --- Get File Paths ---
# Assumes the script is in the same directory as the input file
script_dir = os.path.dirname(os.path.abspath(__file__))
input_filepath = os.path.join(script_dir, input_filename)
output_filepath = os.path.join(script_dir, output_filename)

# --- Regular Expression ---
# Matches the start of the line (^), the literal "--- Page ",
# captures one or more digits (\d+), matches " ---", and the end of the line ($)
page_marker_regex = re.compile(r"^--- Page (\d+) ---$")

print(f"Reading from: {input_filepath}")
print(f"Writing to:   {output_filepath}")
print(f"Applying offset: Subtracting {offset} from original page numbers.")

lines_processed = 0
lines_changed = 0

try:
    with open(input_filepath, 'r', encoding='utf-8') as infile, \
         open(output_filepath, 'w', encoding='utf-8') as outfile:

        for line in infile:
            lines_processed += 1
            # Strip potential leading/trailing whitespace before matching
            stripped_line = line.strip()
            match = page_marker_regex.match(stripped_line)

            if match:
                try:
                    original_page_str = match.group(1)
                    original_page_num = int(original_page_str)

                    # Calculate the new page number
                    new_page_num = original_page_num - offset

                    # Only create markers for new page numbers >= 1
                    if new_page_num >= 1:
                        # Format the new page number with zero-padding (e.g., 01, 02, 10)
                        formatted_new_page = f"{new_page_num:02d}"
                        new_line = f"--- Page {formatted_new_page} ---\n"
                        outfile.write(new_line)
                        lines_changed += 1
                        # Optional: print change for verification during run
                        # print(f"Changed '{stripped_line}' to '--- Page {formatted_new_page} ---'")
                    else:
                        # If new page number < 1, write the original line back
                        # You could also choose to skip these lines or add a comment
                        outfile.write(line)
                        print(f"Warning: Original page {original_page_num} resulted in new page {new_page_num} (< 1). Kept original line: '{stripped_line}'")

                except ValueError:
                    # This should not happen if regex matches \d+, but good practice
                    print(f"Warning: Could not parse number in line: '{stripped_line}'. Kept original line.")
                    outfile.write(line) # Write original line if conversion fails
            else:
                # Line doesn't match the page marker pattern, write it unchanged
                outfile.write(line)

    print(f"\nProcessing complete.")
    print(f"Total lines processed: {lines_processed}")
    print(f"Page markers renumbered (where new page >= 1): {lines_changed}")
    print(f"Output saved to: {output_filepath}")

except FileNotFoundError:
    print(f"Error: Input file not found at '{input_filepath}'")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
