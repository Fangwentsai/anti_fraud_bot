#!/usr/bin/env python3
"""
Reply Token 修復腳本
修復 anti_fraud_clean_app.py 中的 reply token 重複使用問題
"""

import re
import sys
import os
import shutil
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_reply_token_issues(file_path):
    """
    修復 reply token 重複使用問題
    """
    # 備份原始文件
    backup_path = file_path + '.reply_token_fix.bak'
    shutil.copy2(file_path, backup_path)
    logger.info(f"已創建備份文件: {backup_path}")
    
    # 讀取文件內容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修復1: 在圖片分析處理邏輯前添加 return 語句
    # 尋找圖片分析處理邏輯的位置
    image_analysis_pattern = r'(\s+# 添加圖片分析命令處理\s+if "分析圖片" in cleaned_message or "檢查圖片" in cleaned_message:)'
    
    # 在圖片分析邏輯前添加 return，並將圖片分析邏輯移到適當的位置
    replacement = r'''
        # 處理詐騙分析完成後直接返回，避免繼續執行其他邏輯
        return

    # 添加圖片分析命令處理
    if "分析圖片" in cleaned_message or "檢查圖片" in cleaned_message:'''
    
    # 檢查是否找到匹配
    if re.search(image_analysis_pattern, content):
        content = re.sub(image_analysis_pattern, replacement, content)
        logger.info("已修復圖片分析邏輯的 return 語句問題")
    else:
        logger.warning("未找到圖片分析邏輯，可能已經修復或結構已改變")
    
    # 修復2: 在所有主要處理邏輯後添加 return 語句，確保不會執行到圖片分析
    # 尋找詐騙分析邏輯的結束位置
    fraud_analysis_end_pattern = r'(\s+# 詐騙分析完成，直接返回，不繼續執行其他邏輯\s*$)'
    
    if re.search(fraud_analysis_end_pattern, content, re.MULTILINE):
        content = re.sub(fraud_analysis_end_pattern, r'\1\n            return', content, flags=re.MULTILINE)
        logger.info("已在詐騙分析結束後添加 return 語句")
    
    # 修復3: 在功能查詢處理後添加 return
    function_inquiry_pattern = r'(\s+# 統一發送彩色的Flex Message按鈕（群組和個人聊天都一樣）.*?logger\.error\(f"發送統一按鈕時發生未知錯誤: \{e\}"\)\s*)'
    
    if re.search(function_inquiry_pattern, content, re.DOTALL):
        content = re.sub(function_inquiry_pattern, r'\1\n            return', content, flags=re.DOTALL)
        logger.info("已在功能查詢處理後添加 return 語句")
    
    # 修復4: 在天氣查詢處理後添加 return
    weather_query_pattern = r'(\s+# 使用新版 API 回覆.*?line_bot_api\.reply_message\(reply_token, TextSendMessage\(text=error_text\)\)\s*)'
    
    if re.search(weather_query_pattern, content, re.DOTALL):
        content = re.sub(weather_query_pattern, r'\1\n            return', content, flags=re.DOTALL)
        logger.info("已在天氣查詢處理後添加 return 語句")
    
    # 修復5: 確保圖片分析邏輯使用 reply_token 變數而不是 event.reply_token
    event_reply_token_pattern = r'line_bot_api\.reply_message\(\s*event\.reply_token,'
    content = re.sub(event_reply_token_pattern, 'line_bot_api.reply_message(reply_token,', content)
    
    # 修復6: 在圖片分析邏輯後添加 return
    image_analysis_end_pattern = r'(\s+line_bot_api\.reply_message\(\s*reply_token,\s*TextSendMessage\(text=reply_text\)\s*\))'
    
    if re.search(image_analysis_end_pattern, content):
        content = re.sub(image_analysis_end_pattern, r'\1\n            return', content)
        logger.info("已在圖片分析邏輯後添加 return 語句")
    
    # 寫入修改後的內容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info("Reply token 修復完成")
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
    
    # 修復 reply token 問題
    success = fix_reply_token_issues(file_path)
    
    if success:
        logger.info(f"已成功修復 {file_path} 中的 reply token 問題")
        logger.info(f"如果有問題，可以還原備份文件: {file_path}.reply_token_fix.bak")
    else:
        logger.info(f"修復失敗或沒有需要修復的內容")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 