import re
import os

# --- 輸入設定 ---
# 定義來源 Markdown 檔案的路徑
input_file_path = r'c:\Users\User\Documents\GitHub\LLM_review\grok_summary_review.md'
# 定義要儲存結果的 TXT 檔案路徑
output_file_path = r'c:\Users\User\Documents\GitHub\LLM_review\extracted_grok_suggestions.txt'

# --- 正規表示式 ---
# - 匹配 "**Grok 彙整建議修改:**"
# - 匹配換行符 (\n)
# - 匹配程式碼區塊開始標記 ``` 和其後的換行符
# - 非貪婪地捕獲區塊內所有內容 (.*?)，包含換行符 (因為使用 re.DOTALL)
# - 匹配換行符和程式碼區塊結束標記 ```
pattern = r"\*\*Grok 彙整建議修改:\*\*\n```\n(.*?)\n```"

# --- 檔案處理 ---

# 檢查輸入檔案是否存在
if not os.path.exists(input_file_path):
    print(f"錯誤：找不到輸入檔案 {input_file_path}")
else:
    try:
        # 讀取 Markdown 檔案內容
        with open(input_file_path, 'r', encoding='utf-8') as infile:
            markdown_content = infile.read()

        # 使用 re.findall 查找所有匹配項 (re.DOTALL 使 '.' 匹配換行符)
        # re.findall 返回所有捕獲組 (括號內) 的內容列表
        matches = re.findall(pattern, markdown_content, re.DOTALL)

        # --- 處理與儲存結果 ---
        if matches:
            print(f"成功找到 {len(matches)} 個區塊內容。")

            # 開啟 (或建立) 輸出檔案，準備寫入 ('w' 模式會覆蓋舊檔案)
            with open(output_file_path, 'w', encoding='utf-8') as outfile:
                # 遍歷所有找到的內容
                for i, content in enumerate(matches):
                    # 寫入分隔標記 (可選，方便閱讀)
                    #outfile.write(f"--- 區塊 {i+1} ---\n")
                    # 寫入去除前後空白的內容，並在結尾加上換行符
                    outfile.write(content.strip() + "\n")
                    # 寫入區塊結束標記 (可選)
                    #outfile.write("--- 區塊結束 ---\n\n") # 增加一個空行分隔

            print(f"已將內容儲存至：{output_file_path}")

        else:
            print("找不到符合條件的區塊。")

    except FileNotFoundError:
        # 這個錯誤理論上會被上面的 os.path.exists 攔截，但保留以防萬一
        print(f"錯誤：找不到檔案 {input_file_path}")
    except IOError as e:
        print(f"讀取或寫入檔案時發生錯誤：{e}")
    except Exception as e:
        print(f"處理過程中發生未預期的錯誤：{e}")

