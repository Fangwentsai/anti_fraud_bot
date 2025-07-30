#!/usr/bin/env python3
"""
LINE Bot SDK v3 Flex Message 最終修復腳本
直接使用字典格式，避免 to_dict() 方法的兼容性問題
"""

import re
import sys
import os
import shutil
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_flex_message_v3_final(file_path):
    """
    最終修復 Flex Message 在 v3 API 中的格式問題
    使用更簡單直接的方法：直接使用舊版 API 作為備用
    """
    # 備份原始文件
    backup_path = file_path + '.flex_v3_fix_final.bak'
    shutil.copy2(file_path, backup_path)
    logger.info(f"已創建備份文件: {backup_path}")
    
    # 讀取文件內容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修復策略：直接使用舊版 API 處理 FlexSendMessage
    # 找到圖片分析回覆的程式碼段
    pattern = r'(# 回覆分析結果\s+if flex_message:\s+# 使用新版 API 回覆\s+try:\s+if v3_messaging_api:.*?logger\.info\(f"使用v3 API回覆圖片分析成功: \{user_id\}"\)\s+else:\s+# 舊版 API 作為備用\s+line_bot_api\.reply_message\(reply_token, flex_message\))'
    
    replacement = '''# 回覆分析結果
            if flex_message:
                # 對於 FlexSendMessage，直接使用舊版 API 以確保兼容性
                try:
                    if line_bot_api:
                        line_bot_api.reply_message(reply_token, flex_message)
                        logger.info(f"使用舊版 API 回覆圖片分析成功: {user_id}")
                    else:
                        logger.error("LINE Bot API 未初始化")
                except Exception as api_error:
                    logger.error(f"使用舊版 API 回覆圖片分析失敗: {api_error}")'''
    
    # 執行替換
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    logger.info("已修復圖片分析回覆的 Flex Message 格式")
    
    # 修復 push_message 中的 Flex Message 格式
    pattern2 = r'(# 如果是無效的回覆令牌，嘗試使用push_message作為備用\s+try:\s+if v3_messaging_api:.*?logger\.info\(f"圖片分析回覆令牌無效，改用push_message成功: \{user_id\}"\)\s+except Exception as push_error:\s+logger\.error\(f"圖片分析使用push_message也失敗: \{push_error\}"))'
    
    replacement2 = '''# 如果是無效的回覆令牌，嘗試使用push_message作為備用
                        try:
                            if line_bot_api:
                                line_bot_api.push_message(user_id, flex_message)
                                logger.info(f"圖片分析回覆令牌無效，改用push_message成功: {user_id}")
                            else:
                                logger.error("LINE Bot API 未初始化")
                        except Exception as push_error:
                            logger.error(f"圖片分析使用push_message也失敗: {push_error}")'''
    
    # 執行第二個替換
    content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)
    logger.info("已修復 push_message 中的 Flex Message 格式")
    
    # 寫入修改後的內容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info("Flex Message v3 格式修復完成 (最終版)")
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
    success = fix_flex_message_v3_final(file_path)
    
    if success:
        logger.info(f"已成功修復 {file_path}")
        logger.info(f"如果有問題，可以還原備份文件: {file_path}.flex_v3_fix_final.bak")
    else:
        logger.info(f"修復失敗")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 