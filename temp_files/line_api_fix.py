#!/usr/bin/env python3
"""
LINE API v3 修復腳本
本腳本修復 anti_fraud_clean_app.py 中的所有 v3_messaging_api.reply_message 調用，
添加適當的 ReplyMessageRequest 包裝。
"""

import re
import sys
import os
import shutil
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_line_api_calls(file_path):
    """
    修復 v3_messaging_api.reply_message 調用
    """
    # 備份原始文件
    backup_path = file_path + '.bak'
    shutil.copy2(file_path, backup_path)
    logger.info(f"已創建備份文件: {backup_path}")
    
    # 讀取文件內容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 尋找所有未使用 ReplyMessageRequest 的 v3_messaging_api.reply_message 調用
    pattern = r'(v3_messaging_api\.reply_message\(\s*?)(?!ReplyMessageRequest)(reply_token=[^,]+,\s*?messages=\[[^\]]+\]\s*?\))'
    
    # 檢查是否有匹配
    matches = re.findall(pattern, content)
    if not matches:
        logger.info("沒有找到需要修復的 API 調用。")
        return False
    
    # 進行替換
    fixed_content = re.sub(pattern, r'\1ReplyMessageRequest(\n                \2\n            )', content)
    
    # 添加必要的 import
    if 'from linebot.v3.messaging import ReplyMessageRequest' not in fixed_content:
        # 尋找適當的導入位置
        import_pattern = r'from linebot\.v3\.messaging import .*?TextMessage as V3TextMessage'
        if re.search(import_pattern, fixed_content):
            fixed_content = re.sub(
                import_pattern,
                r'from linebot.v3.messaging import ReplyMessageRequest, TextMessage as V3TextMessage',
                fixed_content
            )
        else:
            # 如果找不到適當的導入位置，在文件頂部添加
            fixed_content = 'from linebot.v3.messaging import ReplyMessageRequest\n' + fixed_content
    
    # 寫入修改後的內容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    logger.info(f"已修復 {len(matches)} 處 v3_messaging_api.reply_message 調用")
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
    
    # 修復 LINE API 調用
    success = fix_line_api_calls(file_path)
    
    if success:
        logger.info(f"已成功修復 {file_path} 中的 LINE API 調用")
        logger.info(f"如果有問題，可以還原備份文件: {file_path}.bak")
    else:
        logger.info(f"沒有需要修復的內容或修復失敗")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 