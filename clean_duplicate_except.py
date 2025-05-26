#!/usr/bin/env python3
"""
清理重複的 except 區塊
"""

import sys
import os
import shutil
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_duplicate_except(file_path):
    """清理重複的 except 區塊"""
    # 備份原始文件
    backup_path = file_path + '.clean_except.bak'
    shutil.copy2(file_path, backup_path)
    logger.info(f"已創建備份文件: {backup_path}")
    
    # 讀取文件內容
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 找到重複的 except LineBotApiError 區塊並移除
    new_lines = []
    skip_lines = False
    skip_count = 0
    
    for i, line in enumerate(lines):
        # 檢查是否是重複的 except LineBotApiError
        if (line.strip().startswith("except LineBotApiError as e:") and 
            i > 1350 and  # 在圖片處理區域
            "使用LINE API回覆圖片分析時發生錯誤" in lines[i+1]):
            
            # 檢查前面是否已經有相同的 except 區塊
            found_duplicate = False
            for j in range(max(0, i-20), i):
                if (lines[j].strip().startswith("except LineBotApiError as e:") and
                    j < i and "使用LINE API回覆圖片分析時發生錯誤" in lines[j+1]):
                    found_duplicate = True
                    break
            
            if found_duplicate:
                skip_lines = True
                skip_count = 0
                logger.info(f"找到重複的 except 區塊，開始跳過第 {i+1} 行")
                continue
        
        if skip_lines:
            skip_count += 1
            # 跳過整個重複的 except 區塊，直到找到下一個主要結構
            if (line.strip().startswith("else:") or 
                line.strip().startswith("except Exception as e:") or
                line.strip().startswith("def ") or
                skip_count > 30):  # 安全機制，避免跳過太多行
                skip_lines = False
                logger.info(f"重複 except 區塊結束於第 {i+1} 行")
            else:
                continue
        
        new_lines.append(line)
    
    # 寫入修改後的內容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    logger.info("清理重複 except 區塊完成")
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
    
    # 清理文件
    success = clean_duplicate_except(file_path)
    
    if success:
        logger.info(f"已成功清理 {file_path}")
        logger.info(f"如果有問題，可以還原備份文件: {file_path}.clean_except.bak")
    else:
        logger.info(f"清理失敗")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 