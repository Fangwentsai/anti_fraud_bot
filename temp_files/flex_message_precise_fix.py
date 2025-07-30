#!/usr/bin/env python3
"""
LINE Bot SDK v3 Flex Message 精確修復腳本
只替換 to_dict() 為 as_json_dict()，不改變其他結構
"""

import sys
import os
import shutil
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_flex_message_precise(file_path):
    """
    精確修復 Flex Message 問題
    只替換 to_dict() 為 as_json_dict()
    """
    # 備份原始文件
    backup_path = file_path + '.precise_fix.bak'
    shutil.copy2(file_path, backup_path)
    logger.info(f"已創建備份文件: {backup_path}")
    
    # 讀取文件內容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修復1: 替換 to_dict() 為 as_json_dict()
    content = content.replace("hasattr(flex_message.contents, 'to_dict')", "hasattr(flex_message.contents, 'as_json_dict')")
    content = content.replace("flex_message.contents.to_dict()", "flex_message.contents.as_json_dict()")
    
    logger.info("已替換所有 to_dict() 為 as_json_dict()")
    
    # 寫入修改後的內容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info("Flex Message 精確修復完成")
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
    success = fix_flex_message_precise(file_path)
    
    if success:
        logger.info(f"已成功修復 {file_path}")
        logger.info(f"如果有問題，可以還原備份文件: {file_path}.precise_fix.bak")
    else:
        logger.info(f"修復失敗")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 