#!/usr/bin/env python3
"""
縮排修復腳本
修復圖片分析邏輯的縮排問題
"""

import re
import sys
import os
import shutil
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_indentation(file_path):
    """
    修復縮排問題
    """
    # 備份原始文件
    backup_path = file_path + '.indent_fix.bak'
    shutil.copy2(file_path, backup_path)
    logger.info(f"已創建備份文件: {backup_path}")
    
    # 讀取文件內容
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 修復圖片分析邏輯的縮排
    in_image_analysis = False
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # 檢查是否進入圖片分析邏輯
        if "# 添加圖片分析命令處理" in line:
            in_image_analysis = True
            fixed_lines.append(line)
            continue
        
        # 檢查是否離開圖片分析邏輯
        if in_image_analysis and line.strip().startswith("@handler.add(PostbackEvent)"):
            in_image_analysis = False
            fixed_lines.append(line)
            continue
        
        # 如果在圖片分析邏輯中，修復縮排
        if in_image_analysis:
            # 如果是 if 語句，應該有4個空格縮排
            if line.strip().startswith('if "分析圖片"'):
                fixed_lines.append("        " + line.strip() + "\n")
            # 如果是 if 語句內的內容，應該有8個空格縮排
            elif line.strip() and not line.startswith("    # 添加圖片分析命令處理"):
                # 檢查當前縮排
                current_indent = len(line) - len(line.lstrip())
                if current_indent > 8:
                    # 已經有正確的縮排，保持不變
                    fixed_lines.append(line)
                else:
                    # 需要修復縮排
                    fixed_lines.append("        " + line.strip() + "\n")
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    # 寫入修改後的內容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    logger.info("縮排修復完成")
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
    
    # 修復縮排
    success = fix_indentation(file_path)
    
    if success:
        logger.info(f"已成功修復 {file_path} 中的縮排問題")
        logger.info(f"如果有問題，可以還原備份文件: {file_path}.indent_fix.bak")
    else:
        logger.info(f"修復失敗")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 