# LLM 書籍審閱工具 (LLMrivised)

這是一個使用多個大型語言模型（LLM）來審閱書籍文字內容的專案，旨在找出科學錯誤、過時資訊或與當代社會價值觀不符的表述。

整個流程分為兩個主要步驟，由兩個獨立的 Python 腳本執行：

1.  **`preprocess_book.py`**: 負責讀取原始 `.txt` 檔案，根據檔案內的頁碼標記 (`--- Page X ---`) 將每一頁的內容切割成一個區塊，並清理可能的頁尾資訊，最後將切割後的區塊保存到一個中間 CSV 檔案 (`book_chunks.csv`)。**此步驟生成的 `chunk_id` (格式如 `檔名_PageX`) 對於 `review_chunks.py` 的頁碼範圍功能至關重要。**
2.  **`review_chunks.py`**: 負責讀取 `book_chunks.csv` 檔案，將每個文本區塊（即每一頁的內容）發送給已啟用的大型語言模型進行審閱，解析模型的返回結果，並將最終的審閱意見（包含原文、各模型建議、各模型原因）附加到最終的輸出 CSV 檔案 (`llm_review_output.csv`)。此腳本支援斷點續傳、處理數量限制以及**指定頁碼範圍處理**。

## 主要功能

*   **多 LLM 支援**: 同時利用 OpenAI GPT 系列、Google Gemini 和 xAI Grok 的能力進行審閱。
*   **內容審定**: 基於科學知識和社會近況檢查事實錯誤、過時資訊、爭議性或歧視性內容。
*   **頁面級文本切割**: `preprocess_book.py` 根據檔案內的 `--- Page X ---` 標記進行切割。
*   **頁尾清理**: `preprocess_book.py` 自動嘗試移除頁碼等頁尾干擾資訊。
*   **API 金鑰管理**: 使用標準的 `.env` 檔案安全地管理各個平台的 API 金鑰。
*   **斷點續傳**: `review_chunks.py` 可以從上次中斷的地方繼續執行，避免重複處理和浪費 API 額度。
*   **範圍處理**: `review_chunks.py` 可使用 `--start-page` 和 `--end-page` 參數僅處理指定頁碼範圍內的區塊。
*   **測試限制**: `review_chunks.py` 可使用 `--limit` 參數限制單次運行處理的**新**區塊數量（可在指定範圍內生效）。
*   **可配置性**: 可以輕鬆在 `review_chunks.py` 中啟用或禁用特定的 LLM，並配置使用的模型。
*   **結構化輸出**: 審閱結果以 CSV 格式清晰呈現，方便後續分析和使用。

## 環境要求

*   Python 3.8 或更高版本。
*   安裝必要的 Python 函式庫：
    ```bash
    pip install openai google-generativeai python-dotenv pandas
    ```

## 設定環境變數

本專案需要使用 API Keys 來與大型語言模型互動。請依照以下步驟設定：

1.  複製 `.env.example` 檔案並重新命名為 `.env`：
    ```bash
    cp .env.example .env
    ```
2.  編輯 `.env` 檔案，填入你自己的 API Keys。
    ```dotenv
    OPENAI_API_KEY=填入你的OpenAI API Key
    GOOGLE_API_KEY=填入你的Google API Key
    XAI_API_KEY=填入你的xAI API Key
    ANTHROPIC_API_KEY=填入你的Anthropic API Key
    ```
3.  `.env` 檔案已被加入 `.gitignore`，不會被同步到版本控制中，請妥善保管。


## 設定步驟

1.  **克隆倉庫 (Clone Repository) 或下載檔案:**
    將 `preprocess_book.py` 和 `review_chunks.py` 檔案下載到您的工作目錄。

2.  **安裝依賴:**
    開啟終端機，切換到您的工作目錄，然後執行：
    ```bash
    pip install openai google-generativeai python-dotenv pandas
    ```

3.  **創建 `.env` 檔案:**
    *   在專案的根目錄（與 `.py` 檔案同級）建立一個名為 `.env` 的文字檔案。
    *   在 `.env` 檔案中，按照以下格式填入您的 API 金鑰：
        ```dotenv
        # .env
        OPENAI_API_KEY="sk-你的OpenAI金鑰"
        GOOGLE_API_KEY="你的Google Gemini金鑰"
        XAI_API_KEY="你的xAI Grok API金鑰"
        ```
    *   **請務必將 `"..."` 中的內容替換為您自己的有效 API 金鑰。** 只需填寫你計劃使用的 LLM 的 API Key。

4.  **準備書籍檔案 (.txt):**
    *   **格式要求**:
        *   確保您的書籍文字檔是 `.txt` 格式。
        *   檔案應使用 **UTF-8** 編碼儲存，以避免中文亂碼。
        *   檔案內容中**必須**包含清晰的頁碼標記，格式為 `--- Page X ---` （其中 `X` 是頁碼數字），每個標記應單獨佔一行或易於被正則表達式 `r'--- Page (\d+) ---'` 匹配。`preprocess_book.py` 會以此標記作為頁面分割的**唯一**依據，並生成格式為 `檔名_PageX` 的 `chunk_id`。如果找不到標記，整個檔案會被視為一個區塊 (Page 0)。
    *   **放置檔案**: 將準備好的 `.txt` 檔案放置在與 Python 腳本相同的目錄下。

5.  **(可選) 配置 `review_chunks.py`:**
    你可以直接編輯 `review_chunks.py` 檔案來：
    *   修改 `ENABLE_OPENAI`, `ENABLE_GEMINI`, `ENABLE_XAI` (設置為 `True` 或 `False`) 來啟用或禁用特定的 LLM。
    *   修改 `OPENAI_MODEL`, `GEMINI_MODEL`, `XAI_MODEL` 來選擇不同的模型版本。
    *   修改 `DEFAULT_CHUNK_INPUT_FILE` 和 `DEFAULT_REVIEW_OUTPUT_FILE` 的預設檔案名稱。

## 使用說明

### 步驟一：預處理書籍檔案 (`preprocess_book.py`)

此步驟將書籍的 `.txt` 檔案根據頁碼標記分割成區塊（每頁一個區塊），並保存為 `book_chunks.csv` (或其他指定的名稱)。**生成的 `chunk_id` 對於步驟二的頁碼範圍功能很重要。**

1.  **開啟終端機**: 在您的作業系統中開啟終端機（命令提示字元、PowerShell、Terminal 等）。
2.  **切換目錄**: 使用 `cd` 指令切換到包含 Python 腳本和 `.txt` 檔案的專案目錄。
3.  **執行命令**:
    ```bash
    python preprocess_book.py <你的書檔名.txt> [-o <output_chunks.csv>]
    ```
    *   `<你的書檔名.txt>`: 你的書籍 TXT 檔案路徑。
    *   `-o <output_chunks.csv>`: (可選) 指定輸出的區塊 CSV 檔案名稱。預設為 `book_chunks.csv`。

    **範例:**
    ```bash
    # 使用預設輸出檔名 book_chunks.csv
    python preprocess_book.py "c:\path\to\my_book.txt"

    # 指定輸出檔名為 processed_my_book.csv
    python preprocess_book.py "my_book.txt" -o "processed_my_book.csv"
    ```
4.  **檢查輸出**: 腳本執行後，會在同目錄下生成一個 CSV 檔案。此檔案包含兩欄：`chunk_id`（唯一區塊標識符，格式為 `檔名_PageX`）和 `original_text`（切割後的文本區塊，即一整頁的內容）。

### 步驟二：使用 LLM 審閱區塊 (`review_chunks.py`)

此步驟讀取 `book_chunks.csv` (或上一步指定的輸出檔)，調用啟用的 LLM 進行審閱，並將結果附加到 `llm_review_output.csv` (或其他指定的名稱)。

1.  **執行命令**: 在同一個終端機視窗和目錄下，執行以下命令：

    **基本用法 (使用預設檔名，處理所有區塊):**
    ```bash
    python review_chunks.py
    ```

    **指定輸入和輸出檔案:**
    ```bash
    python review_chunks.py <input_chunks.csv> -o <output_review.csv>
    ```
    *   `<input_chunks.csv>`: (可選) `preprocess_book.py` 生成的區塊 CSV 檔案。預設為 `book_chunks.csv`。
    *   `-o <output_review.csv>`: (可選) 指定輸出的審閱結果 CSV 檔案名稱。預設為 `llm_review_output.csv`。

    **限制處理數量 (用於測試):**
    使用 `-l` 或 `--limit` 參數來限制本次運行處理的**新**區塊數量。
    ```bash
    # 只處理最多 10 個新區塊 (從頭開始或從上次中斷處繼續)
    python review_chunks.py -l 10
    ```

    **指定處理頁碼範圍:**
    使用 `--start-page` 和 `--end-page` 參數來指定要處理的頁碼範圍（包含起始和結束頁）。**這依賴於 `chunk_id` 中包含 `_PageX` 的格式。**
    ```bash
    # 只處理第 50 頁及之後的區塊
    python review_chunks.py --start-page 50

    # 只處理第 100 頁及之前的區塊
    python review_chunks.py --end-page 100

    # 只處理第 20 頁到第 30 頁之間的區塊 (包含 20 和 30)
    python review_chunks.py --start-page 20 --end-page 30
    ```

    **組合使用範圍和數量限制:**
    可以同時指定頁碼範圍和數量限制。`--limit` 會限制在指定範圍內處理的**新**區塊數量。
    ```bash
    # 處理第 50 頁到第 100 頁之間的區塊，但本次運行最多只處理 5 個新區塊
    python review_chunks.py --start-page 50 --end-page 100 --limit 5

    # 指定輸入輸出檔，處理第 10 頁之後的區塊，最多處理 20 個新區塊
    python review_chunks.py processed_my_book.csv -o reviews_part1.csv --start-page 10 --limit 20
    ```

2.  **監控進度**:
    *   腳本會首先讀取區塊檔案，並檢查最終輸出檔以確定哪些區塊已經處理過（實現斷點續傳）。
    *   如果指定了頁碼範圍，腳本會先篩選出符合範圍的區塊。
    *   接著，它會逐一處理尚未審閱的區塊（在指定範圍內），調用啟用的 LLM API。
    *   您會在終端機看到處理進度和 API 調用信息。
    *   **注意**: 此過程可能會非常耗時，具體取決於文本區塊的數量和 LLM 的回應速度。同時，這也會消耗您的 API 使用額度並可能產生費用。

3.  **中斷與恢復**: 您可以隨時使用 `Ctrl+C` 中斷 `review_chunks.py` 的執行。下次重新執行相同的命令（包括相同的範圍和限制參數）時，腳本會自動從上次停止的地方繼續處理（跳過已寫入輸出檔的區塊）。

4.  **查看結果**: 審閱結果會被**附加**到 `llm_review_output.csv` 檔案（或您使用 `-o` 選項指定的名稱）。

## 檔案說明

*   **`preprocess_book.py`**: 用於將 TXT 書籍檔案根據頁碼標記分割成區塊的腳本。
*   **`review_chunks.py`**: 用於調用 LLM 審閱區塊並記錄結果的腳本。
*   **`.env`**: (需自行創建) 存儲 API Keys 的檔案。
*   **`book_chunks.csv`**: (由 `preprocess_book.py` 生成) 包含 `chunk_id` (頁面 ID，格式通常為 `檔名_PageX`) 和 `original_text` (整頁內容) 的 CSV 檔案，作為 `review_chunks.py` 的輸入。
*   **`llm_review_output.csv`**: (由 `review_chunks.py` 生成/附加) 包含原始文本和各 LLM 審閱建議與原因的最終輸出 CSV 檔案。

## 配置選項

*   **啟用/禁用 LLM**:
    *   編輯 `review_chunks.py` 檔案。
    *   找到檔案開頭的 `ENABLE_OPENAI`, `ENABLE_GEMINI`, `ENABLE_XAI` 變數。
    *   將其值設置為 `True` (啟用) 或 `False` (禁用) 來控制是否調用對應的 LLM。
*   **選擇 LLM 模型**:
    *   編輯 `review_chunks.py` 檔案。
    *   修改 `OPENAI_MODEL`, `GEMINI_MODEL`, `XAI_MODEL` 的值來指定要使用的模型版本。

## 注意事項

*   **API 成本**: 使用 OpenAI, Google Cloud (Gemini), 和 xAI 的 API 通常需要付費。請注意您的 API 使用量和相關費用。
*   **API 速率限制**: 頻繁調用 API 可能會觸發服務提供商的速率限制。腳本內建了基本的重試和指數退避機制，但如果遇到持續的速率限制錯誤，可能需要調整 `retry_delay` 或增加 `time.sleep()` 的時間。
*   **錯誤處理**: 腳本包含對常見錯誤（如檔案找不到、API 金鑰無效、API 調用失敗）的基本處理，但可能無法涵蓋所有異常情況。請留意終端機輸出的錯誤訊息。
*   **頁碼範圍依賴**: `review_chunks.py` 的 `--start-page` 和 `--end-page` 功能依賴於 `preprocess_book.py` 生成的 `chunk_id` 包含 `_PageX` 格式。如果 `chunk_id` 格式不同，範圍篩選將無法正常工作。
*   **頁尾清理的局限性**: `preprocess_book.py` 中的 `clean_page_footer` 函數是基於常見模式的啟發式清理，對於格式特殊的書籍可能效果不佳或誤刪內容，您可能需要根據實際情況修改此函數的邏輯。
*   **記憶體使用**: 如果輸入的 `book_chunks.csv` 檔案非常巨大，`review_chunks.py` 在啟動時讀取所有區塊信息以進行篩選和檢查已處理 ID 可能會消耗較多記憶體。

## 輸出格式 (`llm_review_output.csv`)

最終的 CSV 檔案包含以下欄位：

*   `chunk_id`: 文本區塊的唯一標識符，格式通常為 `檔名_PageX`。
*   `original_text`: 從原始 `.txt` 檔案切割出來的文本區塊原文（整頁內容）。
*   `OpenAI 建議修改`: OpenAI 模型提供的修改建議文字，若無需修改則為 "無需修改"。
*   `OpenAI 原因`: OpenAI 模型提供的修改原因或說明。
*   `Gemini 建議修改`: Gemini 模型提供的修改建議文字。
*   `Gemini 原因`: Gemini 模型提供的修改原因或說明。
*   `xAI Grok 建議修改`: xAI Grok 模型提供的修改建議文字。
*   `xAI Grok 原因`: xAI Grok 模型提供的修改原因或說明。

*注意：如果某個 LLM 在 `review_chunks.py` 中被禁用（例如 `ENABLE_OPENAI = False`），則對應的建議和原因欄位會顯示 "未啟用"。如果 API 調用失敗或解析出錯，欄位中會顯示錯誤訊息。*
