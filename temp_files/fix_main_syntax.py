#!/usr/bin/env python3
"""
修復 anti_fraud_clean_app.py 中的主要語法錯誤
"""

import re

def fix_syntax_errors():
    """修復主程式中的語法錯誤"""
    
    print("🔧 開始修復 anti_fraud_clean_app.py 中的語法錯誤...")
    
    # 讀取原始文件
    try:
        with open('anti_fraud_clean_app.py', 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print("❌ 找不到 anti_fraud_clean_app.py 文件")
        return False
    
    # 記錄原始行數
    original_lines = len(content.split('\n'))
    print(f"📄 原始文件有 {original_lines} 行")
    
    # 修復常見的語法錯誤
    fixes_applied = []
    
    # 1. 修復缺少縮排的 else 語句
    if "                    else:\n                    # 如果Flex消息創建失敗" in content:
        content = content.replace(
            "                    else:\n                    # 如果Flex消息創建失敗",
            "            else:\n                # 如果Flex消息創建失敗"
        )
        fixes_applied.append("修復 else 語句縮排")
    
    # 2. 修復不完整的 try-except 結構
    # 查找並修復缺少 except 的 try 語句
    try_pattern = r'(\s+)try:\s*\n(\s+if v3_messaging_api:.*?\n.*?\)\s*\n\s*else:\s*\n.*?line_bot_api\.reply_message.*?\n)(?!\s*except)'
    
    def fix_try_except(match):
        indent = match.group(1)
        try_block = match.group(2)
        return f"{indent}try:\n{try_block}{indent}except Exception as e:\n{indent}    logger.error(f'發送訊息時發生錯誤: {{e}}')\n"
    
    content = re.sub(try_pattern, fix_try_except, content, flags=re.DOTALL)
    fixes_applied.append("修復不完整的 try-except 結構")
    
    # 3. 修復錯位的 except 語句
    content = re.sub(
        r'(\s+)except (LineBotApiError|Exception) as (\w+):\s*\n(?!\s+)',
        r'\1except \2 as \3:\n\1    ',
        content
    )
    fixes_applied.append("修復錯位的 except 語句")
    
    # 4. 修復重複的 return 語句
    content = re.sub(r'\n\s*return\s*\n\s*# 重要：直接返回.*?\n\s*return\s*\n', '\n            return\n\n', content)
    fixes_applied.append("移除重複的 return 語句")
    
    # 5. 修復縮排不一致的問題
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # 檢查是否是錯誤的縮排
        if line.strip().startswith('line_bot_api.reply_message') and not line.startswith('                '):
            # 修復縮排
            fixed_line = '                ' + line.strip()
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    fixes_applied.append("修復縮排不一致問題")
    
    # 寫入修復後的文件
    try:
        with open('anti_fraud_clean_app_fixed.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        fixed_lines = len(content.split('\n'))
        print(f"✅ 修復完成！修復後文件有 {fixed_lines} 行")
        print(f"📝 應用的修復：")
        for fix in fixes_applied:
            print(f"   • {fix}")
        
        print(f"\n💾 修復後的文件已保存為: anti_fraud_clean_app_fixed.py")
        print(f"🔍 請檢查修復結果，確認無誤後可以替換原文件")
        
        return True
        
    except Exception as e:
        print(f"❌ 寫入修復文件時發生錯誤: {e}")
        return False

def validate_syntax():
    """驗證修復後的語法"""
    print("\n🔍 驗證修復後的語法...")
    
    try:
        import ast
        with open('anti_fraud_clean_app_fixed.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 嘗試解析語法
        ast.parse(content)
        print("✅ 語法驗證通過！")
        return True
        
    except SyntaxError as e:
        print(f"❌ 語法錯誤仍然存在: {e}")
        print(f"   行號: {e.lineno}")
        print(f"   錯誤: {e.msg}")
        return False
    except FileNotFoundError:
        print("❌ 找不到修復後的文件")
        return False
    except Exception as e:
        print(f"❌ 驗證過程中發生錯誤: {e}")
        return False

if __name__ == "__main__":
    print("=== 語法錯誤修復工具 ===\n")
    
    if fix_syntax_errors():
        validate_syntax()
    else:
        print("❌ 修復失敗") 