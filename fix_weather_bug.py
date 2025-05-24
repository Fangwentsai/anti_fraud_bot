#!/usr/bin/env python3
"""
天氣查詢功能修復腳本
修復問題：anti_fraud_clean_app.py中 weather_result["success"] 錯誤
"""

import os
import re
import logging
import sys

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_weather_query_bug():
    """修復天氣查詢功能bug"""
    try:
        # 備份文件
        target_file = "anti_fraud_clean_app.py"
        backup_file = "anti_fraud_clean_app_backup_before_weather_fix.py"
        
        # 檢查文件是否存在
        if not os.path.exists(target_file):
            logger.error(f"目標文件不存在: {target_file}")
            return False
        
        # 創建備份
        import shutil
        shutil.copy2(target_file, backup_file)
        logger.info(f"已創建備份文件: {backup_file}")
        
        # 讀取文件內容
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 檢查是否包含錯誤代碼
        if 'weather_result["success"]' in content:
            # 使用正則表達式查找並替換錯誤代碼段
            pattern = r'if\s+weather_result\["success"\]:'
            replacement = 'if weather_data.get("success"):'
            
            # 計算替換前的匹配數量
            matches_before = len(re.findall(pattern, content))
            
            # 進行替換
            modified_content = re.sub(pattern, replacement, content)
            
            # 計算替換後的匹配數量
            matches_after = len(re.findall(pattern, modified_content))
            
            # 只有在確實進行了替換時才寫入文件
            if matches_before > matches_after:
                with open(target_file, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                logger.info(f"成功修復 {matches_before - matches_after} 處天氣查詢錯誤")
                return True
            else:
                logger.warning("未找到需要修復的錯誤代碼")
                return False
        else:
            # 檢查是否使用了 weather_result 但沒有直接訪問 ["success"]
            if 'weather_result' in content:
                logger.warning("檢測到 weather_result 變量，但未找到具體錯誤模式")
                
                # 手動檢查天氣處理部分
                weather_handling_section = re.search(r'# 處理天氣查詢.*?return', content, re.DOTALL)
                if weather_handling_section:
                    logger.info("找到天氣處理部分，正在分析...")
                    section_text = weather_handling_section.group(0)
                    logger.info(f"天氣處理部分前100個字符: {section_text[:100]}...")
                    
                    # 提取所有的變量使用情況
                    variable_uses = re.findall(r'(\w+)(?:\[|\.|=)', section_text)
                    logger.info(f"天氣處理部分使用的變量: {set(variable_uses)}")
                else:
                    logger.warning("無法找到天氣處理部分")
            
            logger.info("文件已經是最新版本，不需要修復")
            return True
    
    except Exception as e:
        logger.error(f"修復過程中發生錯誤: {e}")
        return False

def main():
    """主函數"""
    logger.info("開始修復天氣查詢功能...")
    
    if fix_weather_query_bug():
        logger.info("修復完成！請重新啟動服務以應用更改")
    else:
        logger.error("修復失敗！請手動檢查並修復問題")
        sys.exit(1)

if __name__ == "__main__":
    main() 