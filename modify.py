import os

def modify_app():
    # 讀取文件
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 確保有 import json
    if 'import json' not in content:
        content = content.replace('import re', 'import re\nimport json')
    
    # 添加修復代碼
    insertion_point = content.find('# 確保風險等級有值')
    if insertion_point > 0:
        new_code = '''
                # 修復JSON顯示問題
                try:
                    # 嘗試導入並使用修復函數
                    from fix_json_display import fix_url_analysis_result
                    analysis_result = fix_url_analysis_result(analysis_result)
                    logger.info("使用 fix_json_display 模塊處理了 URL 分析結果")
                except ImportError:
                    logger.warning("無法導入 fix_json_display 模塊")
                
                # 確保所有必要字段都有值
                if not analysis_result.get("reason"):
                    analysis_result["reason"] = "無具體原因說明"
                if not analysis_result.get("purpose"):
                    analysis_result["purpose"] = "未提供網站用途資訊"
                if not analysis_result.get("suggestion"):
                    analysis_result["suggestion"] = "請謹慎使用，如有疑慮請勿點擊"
                
'''
        content = content[:insertion_point] + new_code + content[insertion_point:]
    
    # 保存修改
    with open('app.py.bak', 'w', encoding='utf-8') as f:
        f.write(content)
    
    os.rename('app.py.bak', 'app.py')
    print('修改完成')

if __name__ == '__main__':
    modify_app() 