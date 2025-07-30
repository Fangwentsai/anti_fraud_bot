#!/usr/bin/env python3
"""
LINE Bot SDK v3 Flex Message 修復腳本 v2
修復 Flex Message 在 v3 API 中的格式問題 - 正確處理 BubbleContainer
"""

import re
import sys
import os
import shutil
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_flex_message_v3_v2(file_path):
    """
    修復 Flex Message 在 v3 API 中的格式問題 - v2版本
    正確處理 BubbleContainer 對象轉換
    """
    # 備份原始文件
    backup_path = file_path + '.flex_v3_fix_v2.bak'
    shutil.copy2(file_path, backup_path)
    logger.info(f"已創建備份文件: {backup_path}")
    
    # 讀取文件內容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修復1: 圖片分析回覆的 Flex Message 格式 - 更精確的處理
    pattern1 = r'(# 將 FlexSendMessage 轉換為 v3 格式\s+if hasattr\(flex_message, \'contents\'\):\s+v3_flex_message = V3FlexMessage\(\s+alt_text=flex_message\.alt_text,\s+contents=flex_message\.contents\s+\)\s+else:\s+# 如果已經是 v3 格式，直接使用\s+v3_flex_message = flex_message)'
    
    replacement1 = '''# 將 FlexSendMessage 轉換為 v3 格式
                        if hasattr(flex_message, 'contents') and hasattr(flex_message, 'alt_text'):
                            # 檢查 contents 是否為 BubbleContainer 或其他 Flex 容器
                            if hasattr(flex_message.contents, 'to_dict'):
                                # 如果是 LINE SDK 對象，轉換為字典
                                contents_dict = flex_message.contents.to_dict()
                            else:
                                # 如果已經是字典，直接使用
                                contents_dict = flex_message.contents
                            
                            v3_flex_message = V3FlexMessage(
                                alt_text=flex_message.alt_text,
                                contents=contents_dict
                            )
                        else:
                            # 如果已經是 v3 格式，直接使用
                            v3_flex_message = flex_message'''
    
    # 執行第一個替換
    content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)
    logger.info("已修復圖片分析回覆的 Flex Message 格式")
    
    # 修復2: push_message 中的 Flex Message 格式 - 更精確的處理
    pattern2 = r'(# 將 FlexSendMessage 轉換為 v3 格式\s+if hasattr\(flex_message, \'contents\'\):\s+v3_flex_message = V3FlexMessage\(\s+alt_text=flex_message\.alt_text,\s+contents=flex_message\.contents\s+\)\s+else:\s+v3_flex_message = flex_message)'
    
    replacement2 = '''# 將 FlexSendMessage 轉換為 v3 格式
                                if hasattr(flex_message, 'contents') and hasattr(flex_message, 'alt_text'):
                                    # 檢查 contents 是否為 BubbleContainer 或其他 Flex 容器
                                    if hasattr(flex_message.contents, 'to_dict'):
                                        # 如果是 LINE SDK 對象，轉換為字典
                                        contents_dict = flex_message.contents.to_dict()
                                    else:
                                        # 如果已經是字典，直接使用
                                        contents_dict = flex_message.contents
                                    
                                    v3_flex_message = V3FlexMessage(
                                        alt_text=flex_message.alt_text,
                                        contents=contents_dict
                                    )
                                else:
                                    # 如果已經是 v3 格式，直接使用
                                    v3_flex_message = flex_message'''
    
    # 執行第二個替換
    content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)
    logger.info("已修復 push_message 中的 Flex Message 格式")
    
    # 寫入修改後的內容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info("Flex Message v3 格式修復完成 (v2)")
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
    success = fix_flex_message_v3_v2(file_path)
    
    if success:
        logger.info(f"已成功修復 {file_path}")
        logger.info(f"如果有問題，可以還原備份文件: {file_path}.flex_v3_fix_v2.bak")
    else:
        logger.info(f"修復失敗")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 