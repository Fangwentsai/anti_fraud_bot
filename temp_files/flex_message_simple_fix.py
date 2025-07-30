#!/usr/bin/env python3
"""
LINE Bot SDK v3 Flex Message 簡單修復腳本
直接替換圖片分析回覆邏輯，使用舊版 API
"""

import sys
import os
import shutil
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_flex_message_simple(file_path):
    """
    簡單修復 Flex Message 問題
    直接替換圖片分析回覆邏輯
    """
    # 備份原始文件
    backup_path = file_path + '.simple_fix.bak'
    shutil.copy2(file_path, backup_path)
    logger.info(f"已創建備份文件: {backup_path}")
    
    # 讀取文件內容
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 找到圖片分析回覆的開始位置
    start_line = -1
    end_line = -1
    
    for i, line in enumerate(lines):
        if "# 回覆分析結果" in line and "if flex_message:" in lines[i+1]:
            start_line = i
            logger.info(f"找到圖片分析回覆開始位置: 第 {i+1} 行")
            break
    
    if start_line == -1:
        logger.error("找不到圖片分析回覆的開始位置")
        return False
    
    # 找到結束位置（下一個 except 或 else 語句）
    for i in range(start_line + 1, len(lines)):
        if lines[i].strip().startswith("except LineBotApiError as e:"):
            end_line = i
            logger.info(f"找到圖片分析回覆結束位置: 第 {i+1} 行")
            break
    
    if end_line == -1:
        logger.error("找不到圖片分析回覆的結束位置")
        return False
    
    # 創建新的回覆邏輯
    new_logic = [
        "            # 回覆分析結果\n",
        "            if flex_message:\n",
        "                # 對於 FlexSendMessage，直接使用舊版 API 以確保兼容性\n",
        "                try:\n",
        "                    if line_bot_api:\n",
        "                        line_bot_api.reply_message(reply_token, flex_message)\n",
        "                        logger.info(f\"使用舊版 API 回覆圖片分析成功: {user_id}\")\n",
        "                    else:\n",
        "                        logger.error(\"LINE Bot API 未初始化\")\n",
        "                except LineBotApiError as e:\n",
        "                    logger.error(f\"使用LINE API回覆圖片分析時發生錯誤: {e}\")\n",
        "                    if \"Invalid reply token\" in str(e):\n",
        "                        # 如果是無效的回覆令牌，嘗試使用push_message作為備用\n",
        "                        try:\n",
        "                            if line_bot_api:\n",
        "                                line_bot_api.push_message(user_id, flex_message)\n",
        "                                logger.info(f\"圖片分析回覆令牌無效，改用push_message成功: {user_id}\")\n",
        "                            else:\n",
        "                                logger.error(\"LINE Bot API 未初始化\")\n",
        "                        except Exception as push_error:\n",
        "                            logger.error(f\"圖片分析使用push_message也失敗: {push_error}\")\n"
    ]
    
    # 替換內容
    new_lines = lines[:start_line] + new_logic + lines[end_line:]
    
    # 寫入修改後的內容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    logger.info("Flex Message 簡單修復完成")
    return True

def main():
    """主函數"""
    # 檢查參數
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = 'anti_fraud_clean_app.py'  # 默認檔案名
    
    # 檢查文件是否存在
    if not os.path.isfile(file_path):
        logger.error(f"文件不存在: {file_path}")
        return 1
    
    # 修復文件
    success = fix_flex_message_simple(file_path)
    
    if success:
        logger.info(f"已成功修復 {file_path}")
        logger.info(f"如果有問題，可以還原備份文件: {file_path}.simple_fix.bak")
    else:
        logger.info(f"修復失敗")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 