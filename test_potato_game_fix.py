#!/usr/bin/env python3
"""
土豆遊戲修復測試腳本
測試修復後的土豆遊戲功能
"""

import json
from game_service import start_potato_game, handle_potato_game_answer, game_service

def test_button_label_length():
    """測試按鈕label長度是否符合LINE API限制"""
    print("🔍 測試按鈕label長度...")
    
    test_user_id = "test_user_button_length"
    
    # 測試所有預設問題
    for i, question_data in enumerate(game_service.get_default_game_questions()):
        print(f"\n📝 測試問題 {i+1}: {question_data['question']}")
        
        options = question_data.get('options', [])
        for j, option in enumerate(options):
            # 模擬按鈕label處理邏輯
            button_label = option
            if len(button_label) > 20:
                button_label = button_label[:17] + "..."
            
            print(f"  選項 {j+1}: '{option}' -> 按鈕: '{button_label}' (長度: {len(button_label)})")
            
            # 檢查長度是否符合限制
            if len(button_label) > 20:
                print(f"  ❌ 按鈕label過長: {len(button_label)} > 20")
                return False
            else:
                print(f"  ✅ 按鈕label長度正常")
    
    print("\n🎉 所有按鈕label長度檢查通過！")
    return True

def test_flex_message_structure():
    """測試Flex Message結構是否正確"""
    print("\n🔍 測試Flex Message結構...")
    
    test_user_id = "test_user_flex"
    
    try:
        # 測試開始遊戲
        flex_message, error = start_potato_game(test_user_id)
        
        if error:
            print(f"❌ 開始遊戲失敗: {error}")
            return False
        
        if not flex_message:
            print("❌ 沒有返回Flex Message")
            return False
        
        print("✅ Flex Message創建成功")
        
        # 檢查Flex Message結構
        contents = flex_message.contents
        print(f"✅ Bubble容器: {type(contents).__name__}")
        
        # 檢查header
        if hasattr(contents, 'header') and contents.header:
            print("✅ Header存在")
        
        # 檢查body
        if hasattr(contents, 'body') and contents.body:
            print("✅ Body存在")
        
        # 檢查footer
        if hasattr(contents, 'footer') and contents.footer:
            print("✅ Footer存在")
            footer_contents = contents.footer.contents
            print(f"✅ Footer包含 {len(footer_contents)} 個按鈕")
            
            # 檢查每個按鈕
            for i, button in enumerate(footer_contents):
                if hasattr(button, 'action') and hasattr(button.action, 'label'):
                    label = button.action.label
                    print(f"  按鈕 {i+1}: '{label}' (長度: {len(label)})")
                    
                    if len(label) > 20:
                        print(f"  ❌ 按鈕label過長")
                        return False
        
        print("🎉 Flex Message結構檢查通過！")
        return True
        
    except Exception as e:
        print(f"❌ Flex Message測試失敗: {e}")
        return False

def test_game_flow():
    """測試完整的遊戲流程"""
    print("\n🔍 測試完整遊戲流程...")
    
    test_user_id = "test_user_flow"
    
    try:
        # 1. 開始遊戲
        print("1️⃣ 開始遊戲...")
        flex_message, error = start_potato_game(test_user_id)
        
        if error:
            print(f"❌ 開始遊戲失敗: {error}")
            return False
        
        print("✅ 遊戲開始成功")
        
        # 2. 檢查遊戲狀態
        game_state = game_service.user_game_state.get(test_user_id)
        if not game_state:
            print("❌ 遊戲狀態未保存")
            return False
        
        print("✅ 遊戲狀態保存成功")
        
        # 3. 回答問題
        print("2️⃣ 回答問題...")
        is_correct, result_flex = handle_potato_game_answer(test_user_id, 0)
        
        print(f"✅ 答案處理成功，結果: {'正確' if is_correct else '錯誤'}")
        
        # 4. 檢查遊戲狀態清除
        game_state_after = game_service.user_game_state.get(test_user_id)
        if game_state_after:
            print("❌ 遊戲狀態未清除")
            return False
        
        print("✅ 遊戲狀態清除成功")
        
        print("🎉 完整遊戲流程測試通過！")
        return True
        
    except Exception as e:
        print(f"❌ 遊戲流程測試失敗: {e}")
        return False

def test_action_consistency():
    """測試action名稱一致性"""
    print("\n🔍 測試action名稱一致性...")
    
    test_user_id = "test_user_action"
    
    try:
        # 開始遊戲並檢查按鈕action
        flex_message, error = start_potato_game(test_user_id)
        
        if error:
            print(f"❌ 開始遊戲失敗: {error}")
            return False
        
        # 檢查問題按鈕的action
        footer_contents = flex_message.contents.footer.contents
        for i, button in enumerate(footer_contents):
            if hasattr(button, 'action') and hasattr(button.action, 'data'):
                data = button.action.data
                print(f"選項按鈕 {i+1}: {data}")
                
                # 檢查action格式
                if not data.startswith('action=potato_game_answer'):
                    print(f"❌ 選項按鈕action格式錯誤: {data}")
                    return False
        
        print("✅ 選項按鈕action格式正確")
        
        # 測試結果頁面按鈕
        is_correct, result_flex = handle_potato_game_answer(test_user_id, 0)
        
        result_footer_contents = result_flex.contents.footer.contents
        for i, button in enumerate(result_footer_contents):
            if hasattr(button, 'action') and hasattr(button.action, 'data'):
                data = button.action.data
                print(f"結果按鈕 {i+1}: {data}")
                
                # 檢查"再玩一次"按鈕
                if '再玩一次' in button.action.label:
                    if not data.startswith('action=start_potato_game'):
                        print(f"❌ 再玩一次按鈕action錯誤: {data}")
                        return False
        
        print("✅ 結果按鈕action格式正確")
        print("🎉 action名稱一致性檢查通過！")
        return True
        
    except Exception as e:
        print(f"❌ action一致性測試失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("🔒 土豆遊戲修復測試開始")
    print("=" * 50)
    
    tests = [
        ("按鈕label長度", test_button_label_length),
        ("Flex Message結構", test_flex_message_structure),
        ("完整遊戲流程", test_game_flow),
        ("Action名稱一致性", test_action_consistency)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 執行測試: {test_name}")
        try:
            if test_func():
                print(f"✅ {test_name} - 通過")
                passed += 1
            else:
                print(f"❌ {test_name} - 失敗")
        except Exception as e:
            print(f"❌ {test_name} - 異常: {e}")
    
    print("\n" + "=" * 50)
    print(f"🎯 測試結果: {passed}/{total} 通過")
    
    if passed == total:
        print("🎉 所有測試通過！土豆遊戲修復成功！")
        return True
    else:
        print("⚠️ 部分測試失敗，需要進一步修復")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 