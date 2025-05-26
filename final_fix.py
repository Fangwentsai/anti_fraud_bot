#!/usr/bin/env python3
"""
最終修復腳本
解決所有剩餘的語法和結構問題
"""

import re
import sys
import os
import shutil
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def final_fix(file_path):
    """
    最終修復
    """
    # 備份原始文件
    backup_path = file_path + '.final_fix.bak'
    shutil.copy2(file_path, backup_path)
    logger.info(f"已創建備份文件: {backup_path}")
    
    # 讀取文件內容
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 找到需要修復的區域
    fixed_lines = []
    skip_lines = False
    
    for i, line in enumerate(lines):
        # 檢查是否到達函數外部的圖片分析邏輯
        if line.strip() == "# 添加圖片分析命令處理" and not line.startswith("        "):
            # 開始跳過函數外部的圖片分析邏輯
            skip_lines = True
            logger.info(f"開始跳過函數外部的圖片分析邏輯，行號: {i+1}")
            continue
        
        # 檢查是否到達 @handler.add(PostbackEvent)
        if skip_lines and line.strip().startswith("@handler.add(PostbackEvent)"):
            # 停止跳過
            skip_lines = False
            logger.info(f"停止跳過，到達 PostbackEvent handler，行號: {i+1}")
            fixed_lines.append(line)
            continue
        
        # 如果不在跳過模式，添加行
        if not skip_lines:
            fixed_lines.append(line)
    
    # 寫入修改後的內容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    logger.info("最終修復完成")
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
    
    # 最終修復
    success = final_fix(file_path)
    
    if success:
        logger.info(f"已成功完成最終修復 {file_path}")
        logger.info(f"如果有問題，可以還原備份文件: {file_path}.final_fix.bak")
    else:
        logger.info(f"修復失敗")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 