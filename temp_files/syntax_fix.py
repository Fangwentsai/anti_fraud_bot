#!/usr/bin/env python3
"""
語法錯誤修復腳本
修復 anti_fraud_clean_app.py 中的語法錯誤
"""

import re
import sys
import os
import shutil
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_syntax_errors(file_path):
    """
    修復語法錯誤
    """
    # 備份原始文件
    backup_path = file_path + '.syntax_fix.bak'
    shutil.copy2(file_path, backup_path)
    logger.info(f"已創建備份文件: {backup_path}")
    
    # 讀取文件內容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修復1: return# 處理天氣查詢 -> return\n        # 處理天氣查詢
    content = re.sub(r'return# 處理天氣查詢', r'return\n        \n        # 處理天氣查詢', content)
    logger.info("已修復 return# 處理天氣查詢 語法錯誤")
    
    # 修復2: returnexcept Exception as e: -> return\n            except Exception as e:
    content = re.sub(r'returnexcept Exception as e:', r'return\n            except Exception as e:', content)
    logger.info("已修復 returnexcept Exception as e: 語法錯誤")
    
    # 修復3: return# 一般聊天回應 -> return\n        # 一般聊天回應
    content = re.sub(r'return# 一般聊天回應', r'return\n        \n        # 一般聊天回應', content)
    logger.info("已修復 return# 一般聊天回應 語法錯誤")
    
    # 修復4: 移除函數外部的 return 語句
    # 尋找圖片分析邏輯後的錯誤 return
    pattern = r'(\s+line_bot_api\.reply_message\(reply_token,\s+TextSendMessage\(text=reply_text\)\s+\)\s+)return(\s+@handler\.add\(PostbackEvent\))'
    content = re.sub(pattern, r'\1\2', content)
    logger.info("已移除函數外部的 return 語句")
    
    # 修復5: 修復 try-except 結構
    # 確保 try 語句有對應的 except
    try_pattern = r'(\s+try:\s+# 檢查是否指定了城市.*?)(\s+return\s+except Exception as e:)'
    replacement = r'\1\n            except Exception as e:'
    content = re.sub(try_pattern, replacement, content, flags=re.DOTALL)
    logger.info("已修復 try-except 結構")
    
    # 修復6: 修復縮排問題
    # 修復 reply_token=reply_token 的縮排
    content = re.sub(r'(\s+v3_messaging_api\.reply_message\(\s+ReplyMessageRequest\(\s+)reply_token=reply_token,', 
                     r'\1reply_token=reply_token,', content)
    
    # 修復 messages 的縮排
    content = re.sub(r'(\s+ReplyMessageRequest\(\s+reply_token=reply_token,\s+)messages=', 
                     r'\1messages=', content)
    
    # 修復 ) 的縮排
    content = re.sub(r'(\s+messages=\[[^\]]+\]\s+)\s+\)', r'\1)', content)
    
    logger.info("已修復縮排問題")
    
    # 寫入修改後的內容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info("語法錯誤修復完成")
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
    
    # 修復語法錯誤
    success = fix_syntax_errors(file_path)
    
    if success:
        logger.info(f"已成功修復 {file_path} 中的語法錯誤")
        logger.info(f"如果有問題，可以還原備份文件: {file_path}.syntax_fix.bak")
    else:
        logger.info(f"修復失敗")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 