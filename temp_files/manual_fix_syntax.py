#!/usr/bin/env python3
"""
手動修復 anti_fraud_clean_app.py 中的語法錯誤
"""

def create_fixed_version():
    """創建手動修復的版本"""
    
    print("🔧 開始手動修復語法錯誤...")
    
    # 讀取原始文件
    try:
        with open('anti_fraud_clean_app.py', 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("❌ 找不到 anti_fraud_clean_app.py 文件")
        return False
    
    print(f"📄 原始文件有 {len(lines)} 行")
    
    # 手動修復關鍵的語法錯誤
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # 修復第1000行附近的問題
        if i >= 999 and i <= 1010:
            if 'except LineBotApiError as e:' in line and line.strip() == 'except LineBotApiError as e:':
                # 添加缺失的內容
                fixed_lines.append(line)
                fixed_lines.append('                logger.error(f"發送分析提示訊息時發生LINE API錯誤: {e}")\n')
                fixed_lines.append('                return\n')
                i += 1
                continue
            elif 'except Exception as e:' in line and line.strip() == 'except Exception as e:':
                # 添加缺失的內容
                fixed_lines.append(line)
                fixed_lines.append('                logger.error(f"發送分析提示訊息時發生未知錯誤: {e}")\n')
                i += 1
                continue
        
        # 修復第1118行的else語句縮排
        if 'else:' in line and '# 如果Flex消息創建失敗' in lines[i+1] if i+1 < len(lines) else False:
            if line.startswith('                    else:'):
                fixed_lines.append('            else:\n')
                i += 1
                continue
        
        # 修復第1134行的try語句
        if 'try:' in line and i > 1130 and i < 1140:
            if 'if v3_messaging_api:' in lines[i+1] if i+1 < len(lines) else False:
                # 確保try語句有正確的except
                fixed_lines.append(line)
                # 添加try塊內容
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('except'):
                    if 'else:' in lines[j] and 'line_bot_api.reply_message' in lines[j+1] if j+1 < len(lines) else False:
                        fixed_lines.append(lines[j])
                        fixed_lines.append(lines[j+1])
                        j += 2
                        break
                    else:
                        fixed_lines.append(lines[j])
                        j += 1
                
                # 添加except語句
                fixed_lines.append('            except Exception as error_send_error:\n')
                fixed_lines.append('                logger.error(f"發送等待分析錯誤訊息失敗: {error_send_error}")\n')
                i = j
                continue
        
        # 修復第1287行的try語句
        if 'try:' in line and i > 1280 and i < 1290:
            if 'if v3_messaging_api:' in lines[i+1] if i+1 < len(lines) else False:
                # 確保try語句有正確的except
                fixed_lines.append(line)
                # 添加try塊內容
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('except'):
                    if 'line_bot_api.reply_message' in lines[j] and not lines[j].startswith('                '):
                        # 修復縮排
                        fixed_lines.append('                ' + lines[j].strip() + '\n')
                        j += 1
                        break
                    else:
                        fixed_lines.append(lines[j])
                        j += 1
                
                # 添加except語句
                fixed_lines.append('                except LineBotApiError as e:\n')
                fixed_lines.append('                    logger.error(f"使用LINE API回覆時發生錯誤: {e}")\n')
                i = j
                continue
        
        # 默認情況：保持原行
        fixed_lines.append(line)
        i += 1
    
    # 寫入修復後的文件
    try:
        with open('anti_fraud_clean_app_manual_fixed.py', 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)
        
        print(f"✅ 手動修復完成！修復後文件有 {len(fixed_lines)} 行")
        print(f"💾 修復後的文件已保存為: anti_fraud_clean_app_manual_fixed.py")
        
        return True
        
    except Exception as e:
        print(f"❌ 寫入修復文件時發生錯誤: {e}")
        return False

def validate_syntax():
    """驗證修復後的語法"""
    print("\n🔍 驗證修復後的語法...")
    
    try:
        import ast
        with open('anti_fraud_clean_app_manual_fixed.py', 'r', encoding='utf-8') as f:
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
    print("=== 手動語法錯誤修復工具 ===\n")
    
    if create_fixed_version():
        validate_syntax()
    else:
        print("❌ 修復失敗") 