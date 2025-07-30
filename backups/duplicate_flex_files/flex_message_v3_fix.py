#!/usr/bin/env python3
"""
LINE Bot SDK v3 Flex Message 修復腳本
修復 Flex Message 在 v3 API 中的格式問題
"""

import re
import sys
import os
import shutil
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_flex_message_v3(file_path):
    """
    修復 Flex Message 在 v3 API 中的格式問題
    """
    # 備份原始文件
    backup_path = file_path + '.flex_v3_fix.bak'
    shutil.copy2(file_path, backup_path)
    logger.info(f"已創建備份文件: {backup_path}")
    
    # 讀取文件內容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修復1: 圖片分析回覆的 Flex Message 格式
    # 找到圖片分析回覆的程式碼
    pattern1 = r'(if flex_message:\s+# 使用新版 API 回覆\s+try:\s+if v3_messaging_api:\s+from linebot\.v3\.messaging import ReplyMessageRequest\s+v3_messaging_api\.reply_message\(\s+ReplyMessageRequest\(\s+reply_token=reply_token,\s+messages=\[flex_message\]\s+\)\s+\))'
    
    replacement1 = '''if flex_message:
                # 使用新版 API 回覆
                try:
                    if v3_messaging_api:
                        from linebot.v3.messaging import ReplyMessageRequest
                        from linebot.v3.messaging import FlexMessage as V3FlexMessage
                        
                        # 將 FlexSendMessage 轉換為 v3 格式
                        if hasattr(flex_message, 'contents'):
                            v3_flex_message = V3FlexMessage(
                                alt_text=flex_message.alt_text,
                                contents=flex_message.contents
                            )
                        else:
                            # 如果已經是 v3 格式，直接使用
                            v3_flex_message = flex_message
                        
                        v3_messaging_api.reply_message(
                            ReplyMessageRequest(
                                reply_token=reply_token,
                                messages=[v3_flex_message]
                           )
                        )'''
    
    # 執行第一個替換
    content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)
    logger.info("已修復圖片分析回覆的 Flex Message 格式")
    
    # 修復2: push_message 中的 Flex Message 格式
    pattern2 = r'(v3_messaging_api\.push_message\(\s+PushMessageRequest\(\s+to=user_id,\s+messages=\[flex_message\]\s+\)\s+\))'
    
    replacement2 = '''# 將 FlexSendMessage 轉換為 v3 格式
                                if hasattr(flex_message, 'contents'):
                                    v3_flex_message = V3FlexMessage(
                                        alt_text=flex_message.alt_text,
                                        contents=flex_message.contents
                                    )
                                else:
                                    v3_flex_message = flex_message
                                
                                v3_messaging_api.push_message(
                                    PushMessageRequest(
                                        to=user_id,
                                        messages=[v3_flex_message]
                                   )
                                )'''
    
    # 執行第二個替換
    content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)
    logger.info("已修復 push_message 中的 Flex Message 格式")
    
    # 修復3: 確保導入 V3FlexMessage
    # 在文件開頭添加必要的導入
    import_pattern = r'(from linebot\.v3\.messaging import.*?)\n'
    
    # 檢查是否已經有 FlexMessage 的導入
    if 'from linebot.v3.messaging import FlexMessage' not in content:
        # 在現有的 v3 導入後添加 FlexMessage 導入
        v3_import_pattern = r'(from linebot\.v3\.messaging import [^\\n]+)'
        
        def add_flex_import(match):
            existing_import = match.group(1)
            if 'FlexMessage' not in existing_import:
                return existing_import + ', FlexMessage'
            return existing_import
        
        content = re.sub(v3_import_pattern, add_flex_import, content)
        logger.info("已添加 FlexMessage 導入")
    
    # 寫入修改後的內容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info("Flex Message v3 格式修復完成")
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
    success = fix_flex_message_v3(file_path)
    
    if success:
        logger.info(f"已成功修復 {file_path}")
        logger.info(f"如果有問題，可以還原備份文件: {file_path}.flex_v3_fix.bak")
    else:
        logger.info(f"修復失敗")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 