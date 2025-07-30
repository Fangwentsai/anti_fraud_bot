#!/usr/bin/env python3
"""
LINE Bot SDK v3 Flex Message 最終解決方案
使用 as_json_dict() 方法正確轉換 BubbleContainer
"""

import re
import sys
import os
import shutil
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_flex_message_final_solution(file_path):
    """
    最終解決 Flex Message 在 v3 API 中的格式問題
    使用 as_json_dict() 方法
    """
    # 備份原始文件
    backup_path = file_path + '.final_solution.bak'
    shutil.copy2(file_path, backup_path)
    logger.info(f"已創建備份文件: {backup_path}")
    
    # 讀取文件內容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修復1: 替換 to_dict() 為 as_json_dict()
    # 找到並替換第一個位置
    pattern1 = r'if hasattr\(flex_message\.contents, \'to_dict\'\):\s+# 如果是 LINE SDK 對象，轉換為字典\s+contents_dict = flex_message\.contents\.to_dict\(\)'
    
    replacement1 = '''if hasattr(flex_message.contents, 'as_json_dict'):
                                # 如果是 LINE SDK 對象，使用 as_json_dict() 轉換為字典
                                contents_dict = flex_message.contents.as_json_dict()'''
    
    content = re.sub(pattern1, replacement1, content)
    logger.info("已修復第一個 to_dict() 調用")
    
    # 修復2: 替換第二個 to_dict() 調用
    pattern2 = r'if hasattr\(flex_message\.contents, \'to_dict\'\):\s+# 如果是 LINE SDK 對象，轉換為字典\s+contents_dict = flex_message\.contents\.to_dict\(\)'
    
    replacement2 = '''if hasattr(flex_message.contents, 'as_json_dict'):
                                        # 如果是 LINE SDK 對象，使用 as_json_dict() 轉換為字典
                                        contents_dict = flex_message.contents.as_json_dict()'''
    
    content = re.sub(pattern2, replacement2, content)
    logger.info("已修復第二個 to_dict() 調用")
    
    # 修復3: 更新檢查條件的註釋
    content = content.replace(
        '# 檢查 contents 是否為 BubbleContainer 或其他 Flex 容器',
        '# 檢查 contents 是否為 BubbleContainer 或其他 Flex 容器，使用 as_json_dict() 方法'
    )
    
    # 寫入修改後的內容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info("Flex Message 最終解決方案修復完成")
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
    success = fix_flex_message_final_solution(file_path)
    
    if success:
        logger.info(f"已成功修復 {file_path}")
        logger.info(f"如果有問題，可以還原備份文件: {file_path}.final_solution.bak")
        logger.info("現在 FlexSendMessage 將使用 as_json_dict() 方法正確轉換為 v3 格式")
    else:
        logger.info(f"修復失敗")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 