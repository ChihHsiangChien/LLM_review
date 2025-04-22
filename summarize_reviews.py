# -*- coding: utf-8 -*-
import os
import csv
import time
import re # Needed for parsing Markdown and chunk IDs
from dotenv import load_dotenv
import argparse
from openai import OpenAI # xAI uses OpenAI-compatible API

# --- Configuration ---
load_dotenv()  # Load environment variables from .env file

# --- API Keys ---
XAI_API_KEY = os.getenv("XAI_API_KEY")

# --- LLM Model Settings ---
XAI_MODEL = "grok-3-mini-latest" # Or "grok-1.5-pro" or another suitable model

# --- Input/Output Files ---
DEFAULT_INPUT_CSV = "llm_review_output_merge.csv"
DEFAULT_OUTPUT_MD = "grok_summary_review.md"

# --- xAI Prompt Template ---
SUMMARY_PROMPT_TEMPLATE = """
作為一位資深的書籍總編輯，你的任務是整合來自多位 AI 審閱者對同一段文字的修改建議與原因。

請仔細閱讀以下的「原始文本」以及由不同 AI 提供的「審閱意見」。

你的目標是：
1.  綜合所有 AI 的建議和原因。
2.  提出一個最終的、整合性的「建議修改後的文字」。
3.  提出一個最終的、整合性的「修改的原因」，解釋為何需要這樣修改，並說明你是如何權衡不同 AI 的意見的。
4.  如果多數或所有 AI 認為無需修改，或者你綜合判斷後認為原文最佳，請在「建議修改後的文字」中回答「無需修改」，並在「修改的原因」中說明理由（例如：綜合多方意見，原文無需調整，各 AI 提出的細微問題不影響整體表達）。
5.  如果 AI 意見分歧很大，請權衡後給出你認為最恰當的單一建議和原因。
6.  請用以下格式回覆，確保包含 '最終建議修改後的文字:' 和 '最終修改的原因:' 這兩個標籤：

最終建議修改後的文字: [這裡填寫你整合後的建議修改文字，或填寫 '無需修改']
最終修改的原因: [這裡填寫你整合後的修改原因，或說明無需修改的理由]

--- 原始文本 ---
{original_text}
--- 審閱意見 ---
{combined_reviews}
---
"""

# --- Initialize xAI Client ---
xai_client = None
if not XAI_API_KEY:
    print("錯誤：未在 .env 檔案中找到 XAI_API_KEY。請確保 .env 檔案存在且包含有效的金鑰。")
    # Allow script to run without client if only checking processed IDs
    # exit(1)
else:
    try:
        xai_client = OpenAI(
            api_key=XAI_API_KEY,
            base_url="https://api.x.ai/v1",
        )
        print("xAI Grok 客戶端初始化成功。")
    except Exception as e:
        print(f"警告：無法初始化 xAI Grok 客戶端: {e}。如果僅檢查已處理 ID，可忽略此警告。")
        # Don't exit, allow checking processed IDs
        # exit(1)

# --- Helper Functions ---

def parse_grok_summary_response(response_text):
    """Parses Grok's summary response to extract suggestion and reason."""
    suggestion = "無法解析 Grok 回應"
    reason = "無法解析 Grok 回應"
    try:
        suggestion_marker = "最終建議修改後的文字:"
        reason_marker = "最終修改的原因:"
        suggestion_start = response_text.find(suggestion_marker)
        reason_start = response_text.find(reason_marker)

        if suggestion_start != -1 and reason_start != -1:
            if suggestion_start < reason_start:
                suggestion = response_text[suggestion_start + len(suggestion_marker):reason_start].strip()
                reason = response_text[reason_start + len(reason_marker):].strip()
            else:
                 reason = response_text[reason_start + len(reason_marker):suggestion_start].strip()
                 suggestion = response_text[suggestion_start + len(suggestion_marker):].strip()
        elif suggestion_start != -1:
             suggestion = response_text[suggestion_start + len(suggestion_marker):].strip()
             reason = "Grok 未提供原因標籤"
        elif reason_start != -1:
             suggestion = "Grok 未提供建議標籤"
             reason = response_text[reason_start + len(reason_marker):].strip()
        else:
            suggestion = response_text.strip() # Fallback
            reason = "Grok 回應格式不符，未找到指定標籤"

    except Exception as e:
        print(f"解析 Grok 回應時出錯: {e}\n原始回應: {response_text[:500]}...")
        suggestion = f"解析錯誤: {e}"
        reason = f"解析錯誤: {e}"

    suggestion = suggestion if suggestion is not None else "解析結果為 None"
    reason = reason if reason is not None else "解析結果為 None"
    return suggestion, reason

def call_grok_for_summary(original_text, combined_reviews):
    """Calls the xAI Grok API to get a summarized review."""
    if not xai_client:
        print("錯誤：xAI 客戶端未初始化，無法調用 API。")
        return "xAI 客戶端未初始化", "xAI 客戶端未初始化"

    prompt = SUMMARY_PROMPT_TEMPLATE.format(
        original_text=original_text,
        combined_reviews=combined_reviews
    )
    max_retries = 3
    retry_delay = 5 # seconds

    for attempt in range(max_retries):
        try:
            response = xai_client.chat.completions.create(
                model=XAI_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=2000,
            )
            response_text = response.choices[0].message.content
            return parse_grok_summary_response(response_text)

        except Exception as e:
            print(f"錯誤：調用 xAI API 失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
            if 'rate limit' in str(e).lower() and attempt < max_retries - 1:
                 current_delay = retry_delay * (2 ** attempt)
                 print(f"遇到速率限制，等待 {current_delay} 秒後重試...")
                 time.sleep(current_delay)
            elif attempt < max_retries - 1:
                print(f"等待 {retry_delay} 秒後重試...")
                time.sleep(retry_delay)
            else:
                error_message = f"xAI API 調用失敗: {e}"
                return error_message, error_message # Return error after max retries

    return "xAI API 調用失敗 (已達最大重試次數)", "xAI API 調用失敗 (已達最大重試次數)" # Fallback

def get_page_number_from_id(chunk_id):
    """
    Extracts the page number from a chunk_id (e.g., 'filename_Page123').
    Returns int or None.
    NOTE: This function is kept for displaying page number in output,
          but is NO LONGER USED FOR FILTERING rows.
    """
    match = re.search(r'_Page(\d+)$', str(chunk_id))
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None # Should not happen with \d+ but good practice
    # Fallback for IDs without _PageX but ending in digits
    match_simple = re.search(r'(\d+)$', str(chunk_id))
    if match_simple:
        try:
            # Be careful with this fallback, might not be a page number
            # Consider if this fallback is truly desired or should return None
            return int(match_simple.group(1))
        except ValueError:
            return None
    return None # Return None if no number found

def load_processed_summary_ids(markdown_filepath):
    """Loads already summarized chunk IDs from the output Markdown file."""
    processed_ids = set()
    if not os.path.exists(markdown_filepath):
        return processed_ids # File doesn't exist yet

    # Regex to find the chunk ID in the header: ## 區塊 ID: [ID_VALUE] (頁碼: ...)
    # Making it flexible for potential variations in spacing or content
    id_pattern = re.compile(r"^\s*##\s+區塊\s+ID:\s*([^(\s]+)") # Capture non-space, non-( chars after colon

    try:
        with open(markdown_filepath, 'r', encoding='utf-8') as mdfile:
            for line in mdfile:
                match = id_pattern.match(line)
                if match:
                    processed_ids.add(match.group(1).strip())
        print(f"從 {markdown_filepath} 載入 {len(processed_ids)} 個已彙整的區塊 ID。")
    except FileNotFoundError:
        pass # Should be caught by os.path.exists, but good practice
    except Exception as e:
        print(f"讀取現有 Markdown 輸出檔案 {markdown_filepath} 時發生錯誤: {e}。將假設沒有已處理的 ID。")
        return set()

    return processed_ids

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize LLM reviews using xAI Grok and output to Markdown.")
    parser.add_argument("input_csv", nargs='?', default=DEFAULT_INPUT_CSV,
                        help=f"Path to the input CSV file with merged LLM reviews (default: {DEFAULT_INPUT_CSV})")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_MD,
                        help=f"Path to the output Markdown file for Grok summaries (default: {DEFAULT_OUTPUT_MD})")
    parser.add_argument("-l", "--limit", type=int, default=None,
                        help="限制本次運行處理的 *新* 區塊數量 (用於測試，在指定範圍內生效)")
    # --- MODIFICATION START: Changed page arguments to row arguments ---
    parser.add_argument("--start-row", type=int, default=None,
                        help="指定開始處理的 CSV 資料行號 (包含此行，從 1 開始計算)")
    parser.add_argument("--end-row", type=int, default=None,
                        help="指定結束處理的 CSV 資料行號 (包含此行，從 1 開始計算)")
    # --- MODIFICATION END ---

    args = parser.parse_args()

    input_filepath = args.input_csv
    output_filepath = args.output
    process_limit = args.limit
    # --- MODIFICATION START: Use row arguments ---
    start_row = args.start_row
    end_row = args.end_row
    # --- MODIFICATION END ---

    # --- MODIFICATION START: Validate row arguments ---
    if start_row is not None and start_row <= 0:
        print(f"錯誤：開始行號 (--start-row) 必須是正整數。")
        exit(1)
    if end_row is not None and end_row <= 0:
        print(f"錯誤：結束行號 (--end-row) 必須是正整數。")
        exit(1)
    if start_row is not None and end_row is not None and start_row > end_row:
        print(f"錯誤：開始行號 ({start_row}) 不能大於結束行號 ({end_row})。")
        exit(1)
    # --- MODIFICATION END ---

    if not os.path.exists(input_filepath):
        print(f"錯誤：找不到輸入的 CSV 檔案 '{input_filepath}'。")
        exit(1)

    print(f"--- 開始使用 xAI Grok 彙整審閱意見 ---")
    print(f"讀取審閱來源: {input_filepath}")
    print(f"寫入/附加彙整結果至: {output_filepath}")

    # --- MODIFICATION START: Update range info message ---
    range_info = []
    if start_row is not None:
        range_info.append(f"從第 {start_row} 行開始")
    if end_row is not None:
        range_info.append(f"到第 {end_row} 行結束")
    if range_info:
        print(f"*** 行號範圍限制：僅考慮 CSV 中 {' '.join(range_info)} 的區塊 ***")
    # --- MODIFICATION END ---
    if process_limit is not None:
        print(f"*** 數量限制：本次運行最多處理 {process_limit} 個 *新* 區塊 (在指定範圍內) ***")

    # Define expected columns for suggestions and reasons
    review_columns = {
        "OpenAI": ("OpenAI 建議修改", "OpenAI 原因"),
        "Gemini": ("Gemini 建議修改", "Gemini 原因"),
        "xAI Grok": ("xAI Grok 建議修改", "xAI Grok 原因"), # Original Grok review
        "Anthropic": ("Anthropic 建議修改", "Anthropic 原因"),
    }

    # Load IDs already processed in the *output Markdown* file
    processed_summary_ids = load_processed_summary_ids(output_filepath)

    # Read all chunks from input CSV first
    all_chunks = []
    try:
        with open(input_filepath, 'r', newline='', encoding='utf-8-sig') as infile:
            reader = csv.DictReader(infile)
            # Check for required columns in the header
            required_cols = ['chunk_id', 'original_text']
            header = reader.fieldnames
            if not header:
                 print(f"錯誤：無法讀取 CSV 檔案 '{input_filepath}' 的標頭。檔案可能為空或格式錯誤。")
                 exit(1)
            if not all(col in header for col in required_cols):
                missing = [col for col in required_cols if col not in header]
                print(f"錯誤：輸入 CSV 檔案 '{input_filepath}' 缺少必要欄位: {', '.join(missing)}")
                exit(1)
            all_chunks = list(reader)
        print(f"從 '{input_filepath}' 讀取了 {len(all_chunks)} 個區塊記錄 (資料行)。")
    except FileNotFoundError:
        print(f"錯誤：找不到輸入的 CSV 檔案 '{input_filepath}'。")
        exit(1)
    except Exception as e:
        print(f"讀取輸入 CSV 檔案 '{input_filepath}' 時發生錯誤: {e}")
        exit(1)

    # --- MODIFICATION START: Filter chunks based on row number ---
    chunks_in_range = []
    skipped_count_range = 0
    if start_row is None and end_row is None:
        chunks_in_range = all_chunks
        print("未指定行號範圍，將考慮所有區塊。")
    else:
        print("正在根據行號範圍篩選區塊...")
        # Use enumerate to get the 0-based index (i) along with the row data
        for i, row in enumerate(all_chunks):
            # Calculate 1-based row number (for user comparison)
            # Note: This assumes the first data row after the header is row 1
            row_num = i + 1

            in_range = True
            if start_row is not None and row_num < start_row:
                in_range = False
            if end_row is not None and row_num > end_row:
                in_range = False

            if in_range:
                chunks_in_range.append(row)
            else:
                skipped_count_range += 1
        print(f"行號範圍篩選完成。共有 {len(chunks_in_range)} 個區塊在指定行號範圍內。因範圍限制跳過了 {skipped_count_range} 個區塊。")
    # --- MODIFICATION END ---

    # Process the filtered chunks
    processed_count_this_run = 0
    skipped_already_done = 0
    total_chunks_to_consider = len(chunks_in_range)

    try:
        # Open output file in append mode
        with open(output_filepath, 'a', encoding='utf-8') as outfile:
            # Write header only if the file is new/empty
            if outfile.tell() == 0:
                outfile.write(f"# LLM 審閱意見彙整報告 (由 xAI Grok 產生)\n\n")
                outfile.write(f"來源檔案: `{input_filepath}`\n\n")
                outfile.write("---\n\n") # Add initial separator
                print("輸出檔案為空，已寫入 Markdown 標頭。")

            # --- MODIFICATION START: Iterate through chunks_in_range (already filtered) ---
            # Use enumerate again to track progress within the filtered list if needed,
            # but the primary filtering by row number is already done.
            for idx, row in enumerate(chunks_in_range):
            # --- MODIFICATION END ---
                try:
                    chunk_id = row['chunk_id']
                    original_text = row['original_text']
                    # Still get page number for display, but don't use it for filtering
                    page_num_str = str(get_page_number_from_id(chunk_id) or "N/A")
                except KeyError as e:
                    print(f"警告：處理範圍內區塊時發現缺少必要欄位 '{e}'，跳過此行 ({row.get('chunk_id', '未知ID')})。")
                    continue

                # --- Resumability Check ---
                if chunk_id in processed_summary_ids:
                    skipped_already_done += 1
                    # print(f"區塊 {chunk_id} 已在輸出檔案中，跳過。") # Optional: Verbose logging
                    continue

                # --- Limit Check ---
                if process_limit is not None and processed_count_this_run >= process_limit:
                    print(f"\n已達到本次運行的 *新* 區塊處理上限 ({process_limit} 個)，停止處理。")
                    break

                # --- MODIFICATION START: Update progress message ---
                # Display the index within the *filtered* list (idx)
                print(f"\n--- 處理新區塊 {chunk_id} (Page: {page_num_str}) ---")
                print(f"    (範圍內第 {idx+1}/{total_chunks_to_consider} 個，本次運行第 {processed_count_this_run + 1} 個新區塊)")
                # --- MODIFICATION END ---

                # --- Combine Reviews ---
                combined_reviews_text = ""
                has_valid_review = False
                valid_review_sources = []
                for llm_name, (sug_col, rea_col) in review_columns.items():
                    
                    # Get the raw values first
                    suggestion_raw = row.get(sug_col) # Get value, could be None, "", or string
                    reason_raw = row.get(rea_col)     # Get value, could be None, "", or string

                    # Strip only if the value is not None, otherwise use an empty string
                    suggestion = suggestion_raw.strip() if suggestion_raw is not None else ""
                    reason = reason_raw.strip() if reason_raw is not None else ""

                    
                    is_meaningful = suggestion and suggestion not in ["未啟用", "API 調用失敗", "無法解析回應", "因安全設置被阻擋", "解析錯誤", "解析結果為 None", "xAI 客戶端未初始化", "Gemini 未返回內容"] # Add more negative keywords if needed

                    if is_meaningful:
                        combined_reviews_text += f"**{llm_name} 意見:**\n"
                        combined_reviews_text += f"  建議修改: {suggestion}\n"
                        combined_reviews_text += f"  原因: {reason}\n\n"
                        has_valid_review = True
                        valid_review_sources.append(llm_name)
                    elif sug_col in row:
                        pass # Ignore empty/placeholder reviews silently

                if not has_valid_review:
                    print(f"    區塊 {chunk_id} 沒有找到任何有效的 AI 審閱意見，跳過 Grok 彙整。")
                    # Write a note to the Markdown file for this skipped chunk
                    outfile.write(f"## 區塊 ID: {chunk_id} (頁碼: {page_num_str})\n\n")
                    outfile.write(f"**原始文本:**\n```\n{original_text}\n```\n\n")
                    outfile.write(f"**Grok 彙整建議修改:**\n```\n無有效來源意見可供彙整\n```\n\n")
                    outfile.write(f"**Grok 彙整修改原因:**\n```\n無有效來源意見可供彙整\n```\n\n")
                    outfile.write("---\n\n")
                    outfile.flush()
                    processed_count_this_run += 1 # Count as processed for limit purposes
                    processed_summary_ids.add(chunk_id) # Add to set to prevent reprocessing if limit hit
                    continue

                print(f"    收集到來自 {valid_review_sources} 的有效意見，發送給 Grok...")

                # --- Call Grok for summary ---
                if not xai_client:
                    print("    錯誤：xAI 客戶端未初始化，無法執行彙整。")
                    grok_suggestion, grok_reason = "xAI 客戶端未初始化", "xAI 客戶端未初始化"
                else:
                    grok_suggestion, grok_reason = call_grok_for_summary(original_text, combined_reviews_text.strip())
                    print(f"    Grok 彙整建議: {grok_suggestion[:100]}...")
                    print(f"    Grok 彙整原因: {grok_reason[:100]}...")

                # --- Write to Markdown ---
                outfile.write(f"## 區塊 ID: {chunk_id} (頁碼: {page_num_str})\n\n") # Still display page number if available
                outfile.write(f"**原始文本:**\n```\n{original_text}\n```\n\n")
                outfile.write(f"**Grok 彙整建議修改:**\n```\n{grok_suggestion}\n```\n\n")
                outfile.write(f"**Grok 彙整修改原因:**\n```\n{grok_reason}\n```\n\n")
                # Optionally include the source reviews for comparison
                # outfile.write(f"**參考來源意見:**\n\n{combined_reviews_text}\n")
                outfile.write("---\n\n")
                outfile.flush() # Ensure data is written periodically

                processed_count_this_run += 1
                processed_summary_ids.add(chunk_id) # Add to set immediately after writing
                time.sleep(1) # Add a small delay between API calls

    except Exception as e:
        print(f"\n處理過程中發生未預期的錯誤: {e}")
        print("請檢查輸入檔案格式和 API 連接。")
        # Don't exit here, report summary below

    print(f"\n--- 審閱意見彙整流程結束 ---")
    if skipped_already_done > 0:
        print(f"跳過了 {skipped_already_done} 個已存在於輸出檔案中的區塊。")
    print(f"本次運行共處理並寫入了 {processed_count_this_run} 個 *新* 區塊的彙整結果。")
    if process_limit is not None and processed_count_this_run >= process_limit:
         print(f"由於設定了 --limit={process_limit}，處理可能已提前終止。")
    # --- MODIFICATION START: Update completion message ---
    elif start_row is not None or end_row is not None:
         print(f"處理已完成指定行號範圍內所有需要處理的新區塊。")
    # --- MODIFICATION END ---
    else:
         print(f"已處理完所有需要處理的新區塊。")
    print(f"彙整結果已寫入/附加到 Markdown 檔案: {output_filepath}")
