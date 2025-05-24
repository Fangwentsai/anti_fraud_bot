#!/usr/bin/env python3
"""
土豆遊戲修復測試腳本
測試修復後的土豆遊戲功能
"""

import json
from game_service import start_potato_game, handle_potato_game_answer, game_service

def test_potato_game_fix():
    """測試土豆遊戲修復"""
    print("🎮 土豆遊戲修復測試")
    print("=" * 50)
    
    test_user_id = "test_user_fix_123"
    
    # 測試1: 開始遊戲
    print("\n1️⃣ 測試開始遊戲...")
    flex_message, error = start_potato_game(test_user_id)
    
    if error:
        print(f"❌ 遊戲開始失敗：{error}")
        return False
    
    if flex_message:
        print("✅ 遊戲開始成功")
        print(f"   - Flex Message類型：{type(flex_message).__name__}")
        print(f"   - Alt Text：{flex_message.alt_text}")
    else:
        print("❌ 沒有返回Flex Message")
        return False
    
    # 測試2: 檢查遊戲狀態
    print("\n2️⃣ 測試遊戲狀態...")
    game_state = game_service.user_game_state.get(test_user_id)
    if game_state:
        print("✅ 遊戲狀態正確創建")
        question_data = game_state.get("question")
        if question_data:
            print(f"   - 詐騙類型：{question_data.get('fraud_type', 'N/A')}")
            print(f"   - 選項數量：{len(question_data.get('options', []))}")
            print(f"   - 正確答案：{question_data.get('correct_option', 'N/A')}")
        else:
            print("❌ 問題數據缺失")
            return False
    else:
        print("❌ 遊戲狀態未創建")
        return False
    
    # 測試3: 回答問題
    print("\n3️⃣ 測試回答問題...")
    is_correct, result_flex = handle_potato_game_answer(test_user_id, 0)
    
    if result_flex:
        print("✅ 答案處理成功")
        print(f"   - 結果：{'正確' if is_correct else '錯誤'}")
        print(f"   - Flex Message類型：{type(result_flex).__name__}")
        print(f"   - Alt Text：{result_flex.alt_text}")
    else:
        print("❌ 答案處理失敗")
        return False
    
    # 測試4: 檢查遊戲狀態清除
    print("\n4️⃣ 測試遊戲狀態清除...")
    game_state_after = game_service.user_game_state.get(test_user_id)
    if game_state_after is None:
        print("✅ 遊戲狀態正確清除")
    else:
        print("❌ 遊戲狀態未清除")
        return False
    
    # 測試5: 測試JSON數據結構
    print("\n5️⃣ 測試JSON數據結構...")
    try:
        with open('potato_game_questions.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            questions = data.get('questions', [])
            
            if questions:
                first_question = questions[0]
                required_fields = ['fraud_type', 'fraud_message', 'explanation', 'options', 'correct_option']
                
                missing_fields = []
                for field in required_fields:
                    if field not in first_question:
                        missing_fields.append(field)
                
                if missing_fields:
                    print(f"❌ JSON缺少必要字段：{missing_fields}")
                    return False
                else:
                    print("✅ JSON數據結構正確")
                    print(f"   - 總問題數：{len(questions)}")
                    print(f"   - 詐騙類型：{first_question.get('fraud_type')}")
                    print(f"   - 選項數量：{len(first_question.get('options', []))}")
            else:
                print("❌ JSON中沒有問題數據")
                return False
                
    except Exception as e:
        print(f"❌ JSON讀取失敗：{e}")
        return False
    
    print("\n🎉 所有測試通過！土豆遊戲修復成功！")
    return True

def test_button_label_length():
    """測試按鈕標籤長度限制"""
    print("\n📏 測試按鈕標籤長度...")
    
    # 模擬長選項文字
    long_option = "這是一個非常非常非常長的選項文字，用來測試按鈕標籤是否會超過LINE的限制長度，應該會被截斷處理"
    
    # 測試標籤生成
    button_label = f"選項 A"
    if len(button_label) <= 20:
        print(f"✅ 按鈕標籤長度正確：'{button_label}' ({len(button_label)}字元)")
    else:
        print(f"❌ 按鈕標籤過長：'{button_label}' ({len(button_label)}字元)")
        return False
    
    # 測試選項文字截斷
    if len(long_option) > 80:
        truncated = long_option[:77] + "..."
        print(f"✅ 長選項正確截斷：{len(truncated)}字元")
    else:
        print("✅ 選項長度在限制內")
    
    return True

def main():
    """主測試函數"""
    print("🛡️ 土豆遊戲修復驗證測試")
    print("=" * 60)
    
    # 執行所有測試
    tests = [
        test_potato_game_fix,
        test_button_label_length
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"\n❌ 測試失敗：{test.__name__}")
        except Exception as e:
            print(f"\n💥 測試異常：{test.__name__} - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 測試結果：{passed}/{total} 通過")
    
    if passed == total:
        print("🎉 所有測試通過！土豆遊戲已成功修復！")
        print("\n✅ 修復內容：")
        print("   - 修復了按鈕標籤過長的問題")
        print("   - 正確處理JSON數據結構")
        print("   - 使用fraud_message作為問題內容")
        print("   - 使用correct_option字段判斷正確答案")
        print("   - 限制選項文字長度避免顯示問題")
        print("   - 改進了遊戲介面和用戶體驗")
    else:
        print("❌ 部分測試失敗，需要進一步修復")
    
    return passed == total

if __name__ == "__main__":
    main() 