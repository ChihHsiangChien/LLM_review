import os
import csv
import time
import re # Import regex module
from dotenv import load_dotenv
import pandas as pd # Still useful for reading the processed IDs easily
import argparse

# --- LLM Client Libraries ---
from openai import OpenAI # Used for both OpenAI and xAI Grok
import google.generativeai as genai
import anthropic # Added for Anthropic Claude

# --- Configuration ---
load_dotenv()  # Load environment variables from .env file


# --- API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
XAI_API_KEY  = os.getenv("XAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") # Added Anthropic Key

# --- LLM Model Settings ---
OPENAI_MODEL = "gpt-4o-mini" # Or "gpt-4-turbo", "gpt-3.5-turbo"
GEMINI_MODEL = "gemini-1.5-flash-latest" # Or "gemini-1.5-pro-latest"
XAI_MODEL = "grok-3-mini-latest" # Or "grok-1.5-pro" grok-beta
ANTHROPIC_MODEL = "claude-3-5-haiku-20241022" # Or "claude-3-opus-20240229", "claude-3-haiku-20240307"

# --- Enable/Disable LLMs ---
ENABLE_OPENAI = True
ENABLE_GEMINI = True
ENABLE_XAI = True
ENABLE_ANTHROPIC = True # Added Anthropic Toggle

# --- Input/Output Files ---
DEFAULT_CHUNK_INPUT_FILE = "book_chunks.csv" # Must match output of preprocess_book.py
DEFAULT_REVIEW_OUTPUT_FILE = "llm_review_output.csv"

# --- CSV Header for Output ---
CSV_HEADER = [
    "chunk_id", "original_text", # Include original text for context
    "OpenAI 建議修改", "OpenAI 原因",
    "Gemini 建議修改", "Gemini 原因",
    "xAI Grok 建議修改", "xAI Grok 原因",
    "Anthropic 建議修改", "Anthropic 原因" # Added Anthropic Columns
]

# --- LLM Prompt Template ---
# This template should work for Anthropic as well
REVIEW_PROMPT_TEMPLATE = """
作為一個專業的書籍審閱編輯，請基於最新的科學知識和當前的社會價值觀與狀況，審閱以下文字段落。
你的任務是：
1.  檢查內容是否有科學上的錯誤、過時的資訊或與當前普遍接受的科學觀點不符之處。
2.  檢查內容是否包含可能引起爭議、歧視、刻板印象或與當代社會包容性價值觀不符的表述。
3.  如果發現需要修改的地方，請明確提出「建議修改後的文字」。
4.  請清楚說明「修改的原因」，解釋為何原文不妥以及修改的依據（科學知識或社會近況）。
5.  如果文字段落沒有問題，請在「建議修改後的文字」欄位回答「無需修改」，並在「修改的原因」欄位說明「內容在科學與社會層面均屬恰當」。
6.  請用以下格式回覆，確保包含 '建議修改後的文字:' 和 '修改的原因:' 這兩個標籤：

建議修改後的文字: [這裡填寫建議修改後的文字，或填寫 '無需修改']
修改的原因: [這裡填寫修改的原因，或填寫 '內容在科學與社會層面均屬恰當']

待審閱的文字段落如下：
---
{text_chunk}
---
"""

# --- Initialize LLM Clients ---
openai_client = None
gemini_model = None
xai_client = None
anthropic_client = None # Added Anthropic Client variable

if ENABLE_OPENAI:
    if not OPENAI_API_KEY:
        print("警告：未找到 OPENAI_API_KEY，將禁用 OpenAI。")
        ENABLE_OPENAI = False
    else:
        try:
            openai_client = OpenAI(api_key=OPENAI_API_KEY)
            print("OpenAI 客戶端初始化成功。")
        except Exception as e:
            print(f"警告：無法初始化 OpenAI 客戶端: {e}")
            ENABLE_OPENAI = False

if ENABLE_GEMINI:
    if not GOOGLE_API_KEY:
        print("警告：未找到 GOOGLE_API_KEY，將禁用 Gemini。")
        ENABLE_GEMINI = False
    else:
        try:
            genai.configure(api_key=GOOGLE_API_KEY)
            gemini_model = genai.GenerativeModel(GEMINI_MODEL)
            print("Google Gemini 客戶端初始化成功。")
        except Exception as e:
            print(f"警告：無法初始化 Google Gemini 客戶端: {e}")
            ENABLE_GEMINI = False

if ENABLE_XAI:
    if not XAI_API_KEY:
        print("警告：未找到 XAI_API_KEY，將禁用 xAI Grok。")
        ENABLE_XAI = False
    else:
        try:
            xai_client = OpenAI(
                api_key=XAI_API_KEY,
                base_url="https://api.x.ai/v1",
            )
            # Optional: Test connection (can be removed if causing issues)
            # try:
            #     test_response = xai_client.models.list()
            #     print("Successfully connected to xAI API and listed models")
            # except Exception as e:
            #     print(f"Failed to list models via xAI client: {e}")
            print("xAI Grok 客戶端初始化成功。")
        except Exception as e:
            print(f"警告：無法初始化 xAI Grok 客戶端: {e}")
            ENABLE_XAI = False

# --- Initialize Anthropic Client ---
if ENABLE_ANTHROPIC:
    if not ANTHROPIC_API_KEY:
        print("警告：未找到 ANTHROPIC_API_KEY，將禁用 Anthropic。")
        ENABLE_ANTHROPIC = False
    else:
        try:
            anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            # Optional: Add a simple test call if needed, e.g., list models (if API supports)
            # or just assume success if constructor doesn't raise error.
            print("Anthropic 客戶端初始化成功。")
        except Exception as e:
            print(f"警告：無法初始化 Anthropic 客戶端: {e}")
            ENABLE_ANTHROPIC = False


# --- Helper Functions ---

def parse_llm_response(response_text):
    """Parses LLM response to extract suggestion and reason."""
    suggestion = "無法解析回應"
    reason = "無法解析回應"
    try:
        suggestion_marker = "建議修改後的文字:"
        reason_marker = "修改的原因:"
        suggestion_start = response_text.find(suggestion_marker)
        reason_start = response_text.find(reason_marker)

        if suggestion_start != -1 and reason_start != -1:
            # Handle cases where markers might be in reverse order
            if suggestion_start < reason_start:
                suggestion = response_text[suggestion_start + len(suggestion_marker):reason_start].strip()
                reason = response_text[reason_start + len(reason_marker):].strip()
            else: # Reason marker appears before suggestion marker
                 reason = response_text[reason_start + len(reason_marker):suggestion_start].strip()
                 suggestion = response_text[suggestion_start + len(suggestion_marker):].strip()

        elif suggestion_start != -1:
             suggestion = response_text[suggestion_start + len(suggestion_marker):].strip()
             reason = "未提供原因標籤"
        elif reason_start != -1:
             suggestion = "未提供建議標籤"
             reason = response_text[reason_start + len(reason_marker):].strip()
        else:
            # Fallback if no markers found
            suggestion = response_text.strip()
            reason = "回應格式不符，未找到標籤"

    except Exception as e:
        print(f"解析回應時出錯: {e}\n原始回應: {response_text[:500]}...")
        suggestion = f"解析錯誤: {e}"
        reason = f"解析錯誤: {e}"

    # Ensure no None values are returned
    suggestion = suggestion if suggestion is not None else "解析結果為 None"
    reason = reason if reason is not None else "解析結果為 None"
    return suggestion, reason


def get_llm_review(client_type, text_chunk):
    """Calls the specified LLM API and handles retries."""
    prompt = REVIEW_PROMPT_TEMPLATE.format(text_chunk=text_chunk)
    suggestion = "未啟用或API調用失敗"
    reason = "未啟用或API調用失敗"
    max_retries = 3
    retry_delay = 5 # seconds

    client = None
    model_name = ""
    is_enabled = False
    system_prompt = "你是一位專業的書籍審閱編輯。" # Common system prompt

    if client_type == "openai":
        client = openai_client
        model_name = OPENAI_MODEL
        is_enabled = ENABLE_OPENAI
    elif client_type == "gemini":
        client = gemini_model
        # Gemini doesn't use a separate system prompt in the same way
        is_enabled = ENABLE_GEMINI
    elif client_type == "xai":
        client = xai_client
        model_name = XAI_MODEL
        is_enabled = ENABLE_XAI
    elif client_type == "anthropic": # Added Anthropic case
        client = anthropic_client
        model_name = ANTHROPIC_MODEL
        is_enabled = ENABLE_ANTHROPIC

    if not is_enabled or not client:
        return "未啟用", "未啟用"

    for attempt in range(max_retries):
        try:
            if client_type == "openai" or client_type == "xai":
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                    # Consider adding max_tokens if needed, e.g., max_tokens=1500
                )
                response_text = response.choices[0].message.content
                return parse_llm_response(response_text)

            elif client_type == "gemini":
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                ]
                # Gemini combines system-like instructions into the main prompt if needed,
                # or uses specific API features if available. Here, the main prompt contains the instructions.
                response = client.generate_content(prompt, safety_settings=safety_settings)

                if not response.parts:
                    block_reason = getattr(response.prompt_feedback, 'block_reason', None)
                    safety_ratings = getattr(response.prompt_feedback, 'safety_ratings', [])
                    if block_reason:
                        reason_text = f"Gemini 安全阻擋: {block_reason}"
                        print(f"警告: {reason_text} 對於文字塊: {text_chunk[:100]}...")
                        return "因安全設置被阻擋", reason_text
                    elif safety_ratings:
                         blocked_ratings = [r for r in safety_ratings if r.blocked]
                         if blocked_ratings:
                             reason_text = f"Gemini 安全阻擋 (基於評級): {blocked_ratings}"
                             print(f"警告: {reason_text} 對於文字塊: {text_chunk[:100]}...")
                             return "因安全設置被阻擋", reason_text
                    error_info = getattr(response, 'error', '未知原因')
                    return "Gemini 未返回內容", f"Gemini 錯誤或空回應: {error_info}"

                response_text = response.text
                return parse_llm_response(response_text)

            elif client_type == "anthropic": # Added Anthropic API call
                response = client.messages.create(
                    model=model_name,
                    system=system_prompt, # Use the system parameter for Anthropic
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1500, # Set a reasonable max token limit
                    temperature=0.5,
                )
                # Check if response content is valid
                if response.content and isinstance(response.content, list) and len(response.content) > 0:
                     # Assuming the first block is the text response
                     response_text = response.content[0].text
                     return parse_llm_response(response_text)
                else:
                     # Handle cases where response.content might be empty or unexpected format
                     print(f"警告: Anthropic 回應格式異常或為空。回應: {response}")
                     return "Anthropic 回應異常", f"Anthropic 回應格式異常或為空: {response.stop_reason or '未知原因'}"


        except Exception as e:
            # Check for specific Anthropic rate limit error if needed
            is_anthropic_rate_limit = isinstance(e, anthropic.RateLimitError)
            is_generic_rate_limit = ('rate limit' in str(e).lower() or
                                     (hasattr(e, 'status_code') and e.status_code == 429))

            print(f"錯誤：調用 {client_type.upper()} API 失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")

            if (is_generic_rate_limit or is_anthropic_rate_limit) and attempt < max_retries - 1:
                 current_delay = retry_delay * (2 ** attempt)
                 print(f"遇到速率限制，等待 {current_delay} 秒後重試...")
                 time.sleep(current_delay)
            elif attempt < max_retries - 1:
                print(f"等待 {retry_delay} 秒後重試...")
                time.sleep(retry_delay)
            else:
                suggestion = f"API 調用失敗 ({client_type.upper()}): {e}"
                reason = f"API 調用失敗 ({client_type.upper()}): {e}"
                # Add specific handling for Anthropic authentication error
                if isinstance(e, anthropic.AuthenticationError):
                    suggestion = f"API 調用失敗 ({client_type.upper()}): 認證錯誤，請檢查 API Key。"
                    reason = f"API 調用失敗 ({client_type.upper()}): 認證錯誤，請檢查 API Key。"
                return suggestion, reason # Return error after max retries

    return suggestion, reason # Fallback


def load_processed_ids(csv_filepath):
    """Loads already processed chunk IDs from the output CSV for resumability."""
    processed_ids = set()
    if not os.path.exists(csv_filepath):
        return processed_ids # File doesn't exist yet

    try:
        df = pd.read_csv(csv_filepath, usecols=['chunk_id'], low_memory=False)
        processed_ids = set(df['chunk_id'].astype(str).tolist())
        print(f"從 {csv_filepath} 載入 {len(processed_ids)} 個已處理的區塊 ID。")
    except FileNotFoundError:
        pass
    except (pd.errors.EmptyDataError, KeyError):
        print(f"警告：輸出檔案 {csv_filepath} 為空或缺少 'chunk_id' 欄，將從頭開始。")
    except Exception as e:
        print(f"讀取現有輸出 CSV 檔案 {csv_filepath} 時發生錯誤: {e}。將從頭開始。")
        return set()

    return processed_ids

def get_page_number_from_id(chunk_id):
    """Extracts the page number from a chunk_id (e.g., 'filename_Page123')."""
    match = re.search(r'_Page(\d+)$', str(chunk_id))
    if match:
        return int(match.group(1))
    return None

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Review text chunks using multiple LLMs.")
    parser.add_argument("input_chunk_file", nargs='?', default=DEFAULT_CHUNK_INPUT_FILE,
                        help=f"Path to the input CSV file containing chunks (default: {DEFAULT_CHUNK_INPUT_FILE})")
    parser.add_argument("-o", "--output", default=DEFAULT_REVIEW_OUTPUT_FILE,
                        help=f"Path to the final output CSV file for reviews (default: {DEFAULT_REVIEW_OUTPUT_FILE})")
    parser.add_argument("-l", "--limit", type=int, default=None,
                        help="限制本次運行處理的 *新* 區塊數量 (用於測試)")
    parser.add_argument("--start-page", type=int, default=None,
                        help="指定開始處理的頁碼 (包含此頁，基於 chunk_id 的 _PageX)")
    parser.add_argument("--end-page", type=int, default=None,
                        help="指定結束處理的頁碼 (包含此頁，基於 chunk_id 的 _PageX)")

    args = parser.parse_args()

    input_filepath = args.input_chunk_file
    output_filepath = args.output
    process_limit = args.limit
    start_page = args.start_page
    end_page = args.end_page

    if start_page is not None and end_page is not None and start_page > end_page:
        print(f"錯誤：開始頁碼 ({start_page}) 不能大於結束頁碼 ({end_page})。")
        exit(1)

    # --- Pre-run Checks ---
    # Updated check to include Anthropic
    if not any([ENABLE_OPENAI, ENABLE_GEMINI, ENABLE_XAI, ENABLE_ANTHROPIC]):
        print("錯誤：沒有任何 LLM 被啟用或成功初始化。請檢查 .env 檔案和啟用設定。")
        exit(1)

    if not os.path.exists(input_filepath):
        print(f"錯誤：找不到輸入的區塊檔案 '{input_filepath}'。請先運行 preprocess_book.py。")
        exit(1)

    print(f"--- 開始使用 LLM 審閱區塊 ---")
    print(f"讀取區塊來源: {input_filepath}")
    print(f"寫入審閱結果至: {output_filepath}")
    # Updated print statement
    print(f"啟用 OpenAI: {ENABLE_OPENAI}, 啟用 Gemini: {ENABLE_GEMINI}, 啟用 xAI Grok: {ENABLE_XAI}, 啟用 Anthropic: {ENABLE_ANTHROPIC}")

    range_info = []
    if start_page is not None:
        range_info.append(f"從頁碼 {start_page} 開始")
    if end_page is not None:
        range_info.append(f"到頁碼 {end_page} 結束")
    if range_info:
        print(f"*** 範圍限制：僅處理 {' '.join(range_info)} 的區塊 ***")
    if process_limit is not None:
        print(f"*** 數量限制：本次運行最多處理 {process_limit} 個 *新* 區塊 (在指定範圍內) ***")

    processed_chunk_ids = load_processed_ids(output_filepath)

    try:
        with open(input_filepath, 'r', newline='', encoding='utf-8-sig') as infile, \
             open(output_filepath, 'a', newline='', encoding='utf-8-sig') as outfile:

            reader = csv.DictReader(infile)
            writer = csv.writer(outfile)

            if outfile.tell() == 0:
                writer.writerow(CSV_HEADER) # Use the updated header
                print("已寫入 CSV 表頭。")

            all_chunks = list(reader)
            total_chunks_in_file = len(all_chunks)
            print(f"檔案 '{input_filepath}' 中總共找到 {total_chunks_in_file} 個區塊。")

            chunks_to_process = []
            if start_page is None and end_page is None:
                chunks_to_process = all_chunks
                print("未指定頁碼範圍，將考慮所有區塊。")
            else:
                print("正在根據頁碼範圍篩選區塊...")
                skipped_count = 0
                for row in all_chunks:
                    chunk_id = row.get('chunk_id')
                    if not chunk_id:
                        print(f"警告：找到缺少 'chunk_id' 的行，跳過: {row}")
                        skipped_count += 1
                        continue

                    page_num = get_page_number_from_id(chunk_id)
                    if page_num is None:
                         print(f"警告：無法從 chunk_id '{chunk_id}' 提取頁碼，將跳過此區塊。")
                         skipped_count += 1
                         continue

                    in_range = True
                    if start_page is not None and page_num < start_page:
                        in_range = False
                    if end_page is not None and page_num > end_page:
                        in_range = False

                    if in_range:
                        chunks_to_process.append(row)
                    else:
                        skipped_count += 1
                print(f"篩選完成。共有 {len(chunks_to_process)} 個區塊在指定範圍內（或無範圍限制）。跳過了 {skipped_count} 個區塊。")

            total_chunks_to_consider = len(chunks_to_process)
            new_chunks_processed_this_run = 0

            for i, row in enumerate(chunks_to_process):
                try:
                    chunk_id = row['chunk_id']
                    original_text = row['original_text']
                except KeyError:
                    print(f"錯誤：輸入檔案 {input_filepath} 的某行缺少 'chunk_id' 或 'original_text' 欄，跳過此行。")
                    continue

                if chunk_id in processed_chunk_ids:
                    continue

                if process_limit is not None and new_chunks_processed_this_run >= process_limit:
                    print(f"\n已達到本次運行的新區塊處理上限 ({process_limit} 個)，停止處理。")
                    break

                print(f"\n--- 處理新區塊 {chunk_id} (範圍內第 {i+1}/{total_chunks_to_consider} 個) ---")
                print(f"原文: {original_text[:100]}...")

                # Initialize result dictionary - Added Anthropic keys
                result_data = {
                    "chunk_id": chunk_id,
                    "original_text": original_text,
                    "OpenAI 建議修改": "未啟用", "OpenAI 原因": "未啟用",
                    "Gemini 建議修改": "未啟用", "Gemini 原因": "未啟用",
                    "xAI Grok 建議修改": "未啟用", "xAI Grok 原因": "未啟用",
                    "Anthropic 建議修改": "未啟用", "Anthropic 原因": "未啟用" # Added
                }

                # Call enabled LLMs sequentially
                if ENABLE_OPENAI:
                    print("    調用 OpenAI...")
                    suggestion, reason = get_llm_review("openai", original_text)
                    result_data["OpenAI 建議修改"] = suggestion
                    result_data["OpenAI 原因"] = reason
                    time.sleep(0.5)

                if ENABLE_GEMINI:
                    print("    調用 Gemini...")
                    suggestion, reason = get_llm_review("gemini", original_text)
                    result_data["Gemini 建議修改"] = suggestion
                    result_data["Gemini 原因"] = reason
                    time.sleep(0.5)

                if ENABLE_XAI:
                    print("    調用 xAI Grok...")
                    suggestion, reason = get_llm_review("xai", original_text)
                    result_data["xAI Grok 建議修改"] = suggestion
                    result_data["xAI Grok 原因"] = reason
                    time.sleep(0.5)

                # Added Anthropic call
                if ENABLE_ANTHROPIC:
                    print("    調用 Anthropic...")
                    suggestion, reason = get_llm_review("anthropic", original_text)
                    result_data["Anthropic 建議修改"] = suggestion
                    result_data["Anthropic 原因"] = reason
                    time.sleep(0.5)

                # Write the completed row to the output CSV using the updated header order
                row_to_write = [result_data.get(col, "") for col in CSV_HEADER]
                writer.writerow(row_to_write)
                outfile.flush()
                print(f"  區塊 {chunk_id} 審閱完成並已寫入 CSV。")

                processed_chunk_ids.add(chunk_id)
                new_chunks_processed_this_run += 1

    except FileNotFoundError:
        print(f"錯誤：找不到輸入的區塊檔案 '{input_filepath}'。")
        exit(1)
    except Exception as e:
        print(f"\n處理過程中發生未預期的錯誤: {e}")
        # Consider adding more specific error type checks if needed
        if isinstance(e, anthropic.APIError):
             print(f"Anthropic API 錯誤詳情: {e.status_code}, {e.body}")
        print("請檢查輸入/輸出檔案和 API 連接。")
        exit(1)

    print(f"\n--- 區塊處理流程結束 ---")
    print(f"本次運行共處理了 {new_chunks_processed_this_run} 個新區塊。")

    if process_limit is not None and new_chunks_processed_this_run >= process_limit:
         print(f"由於設定了 --limit={process_limit}，處理可能已提前終止。")
    elif start_page is not None or end_page is not None:
         print(f"處理已完成指定頁碼範圍內的區塊。")
    else:
         print(f"已處理完所有需要處理的區塊。")

    print(f"完整審閱結果已附加到 {output_filepath}")
