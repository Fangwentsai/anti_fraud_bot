#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
防詐遊戲測試模組
測試防詐騙遊戲的題目內容和邏輯
"""

import sys
import os
import json
import random

# 添加當前目錄到Python路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 設置環境變數
os.environ['CWB_API_KEY'] = 'CWA-E3034BF2-AE4B-4D55-B6AA-1BDC01372CF7'
os.environ['LINE_CHANNEL_ACCESS_TOKEN'] = 'test_token'
os.environ['LINE_CHANNEL_SECRET'] = 'test_secret'
os.environ['OPENAI_API_KEY'] = 'test_openai_key'

from game_service import start_potato_game, handle_potato_game_answer, is_game_trigger

def test_game_trigger():
    """測試遊戲觸發功能"""
    print("=" * 60)
    print("🎮 防詐遊戲觸發測試")
    print("=" * 60)
    
    # 測試觸發關鍵詞
    trigger_phrases = [
        "防詐騙測試",
        "開始防詐遊戲",
        "詐騙遊戲",
        "防詐測驗",
        "防詐小遊戲"
    ]
    
    results = []
    for phrase in trigger_phrases:
        is_triggered = is_game_trigger(phrase)
        print(f"📝 測試觸發詞: '{phrase}' -> {'✅ 觸發' if is_triggered else '❌ 未觸發'}")
        results.append(is_triggered)
    
    # 測試不應該觸發的詞
    non_trigger_phrases = [
        "詐騙案例",
        "分析詐騙",
        "天氣如何",
        "你好"
    ]
    
    for phrase in non_trigger_phrases:
        is_triggered = is_game_trigger(phrase)
        print(f"📝 測試非觸發詞: '{phrase}' -> {'✅ 正確(未觸發)' if not is_triggered else '❌ 錯誤(意外觸發)'}")
        results.append(not is_triggered)  # 反向，因為這些不應該觸發
    
    success_count = sum(results)
    total_count = len(results)
    print(f"\n🎯 觸發測試結果: {success_count}/{total_count} 正確")
    
    return success_count == total_count

def test_game_questions():
    """測試防詐遊戲題目"""
    print("\n" + "=" * 60)
    print("📚 防詐遊戲題目測試")
    print("=" * 60)
    
    # 載入題目檔案
    try:
        with open('fraud_detection_questions.json', 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
        
        questions = questions_data.get('questions', [])
        print(f"✅ 成功載入 {len(questions)} 道防詐題目")
        
        if len(questions) < 5:
            print("❌ 題目數量不足5道")
            return False
        
        # 隨機選擇5道題目進行測試
        selected_questions = random.sample(questions, 5)
        
        test_results = []
        
        for i, question in enumerate(selected_questions, 1):
            print(f"\n" + "="*50)
            print(f"🎲 測試題目 {i}")
            print("="*50)
            
            # 檢查題目結構 - 適應現有格式
            required_fields = ['id', 'fraud_type', 'fraud_message', 'options', 'correct_option', 'explanation']
            has_all_fields = all(field in question for field in required_fields)
            
            if not has_all_fields:
                missing_fields = [field for field in required_fields if field not in question]
                print(f"❌ 題目結構不完整: {question.get('id', '未知')}, 缺少: {missing_fields}")
                test_results.append(False)
                continue
            
            print(f"📝 題目ID: {question['id']}")
            print(f"📖 詐騙類型: {question['fraud_type']}")
            print(f"🎭 詐騙訊息: {question['fraud_message'][:100]}...")
            
            # 檢查選項
            options = question['options']
            if len(options) < 2:
                print("❌ 選項數量不足")
                test_results.append(False)
                continue
            
            print(f"📋 選項數量: {len(options)}")
            for j, option in enumerate(options):
                option_text = option.get('text', '') if isinstance(option, dict) else str(option)
                print(f"   {option.get('id', j+1)}. {option_text[:50]}...")
            
            # 檢查正確答案
            correct_answer = question['correct_option']
            if not correct_answer:
                print(f"❌ 正確答案未設定: {correct_answer}")
                test_results.append(False)
                continue
            
            print(f"✅ 正確答案: 選項 {correct_answer}")
            
            # 檢查解釋
            explanation = question['explanation']
            if not explanation or len(explanation) < 20:
                print("❌ 解釋內容不足")
                test_results.append(False)
                continue
            
            print(f"💡 解釋: {explanation[:100]}...")
            print("✅ 題目結構完整")
            test_results.append(True)
        
        success_count = sum(test_results)
        print(f"\n🎯 題目測試結果: {success_count}/5 通過")
        
        return success_count >= 4  # 至少4/5通過
        
    except FileNotFoundError:
        print("❌ 找不到 fraud_detection_questions.json 檔案")
        return False
    except json.JSONDecodeError:
        print("❌ JSON檔案格式錯誤")
        return False
    except Exception as e:
        print(f"❌ 載入題目時發生錯誤: {e}")
        return False

def test_game_flow():
    """測試遊戲流程"""
    print("\n" + "=" * 60)
    print("🔄 防詐遊戲流程測試")
    print("=" * 60)
    
    # 測試開始遊戲
    test_user_id = "test_user_123"
    print(f"📱 測試用戶ID: {test_user_id}")
    
    try:
        # 開始遊戲
        flex_message, error_message = start_potato_game(test_user_id)
        
        if error_message:
            print(f"❌ 開始遊戲失敗: {error_message}")
            return False
        
        if not flex_message:
            print("❌ 未生成Flex訊息")
            return False
        
        print("✅ 成功開始遊戲並生成Flex訊息")
        
        # 測試回答遊戲
        # 隨機選擇一個答案進行測試
        test_answers = [0, 1, 2]  # 測試不同的答案選項
        answer_results = []
        
        for answer in test_answers:
            print(f"\n📝 測試回答選項: {answer}")
            try:
                is_correct, result_flex = handle_potato_game_answer(test_user_id, answer)
                
                if result_flex:
                    print(f"✅ 成功處理答案: {'正確' if is_correct else '錯誤'}")
                    answer_results.append(True)
                else:
                    print("❌ 未生成結果Flex訊息")
                    answer_results.append(False)
                    
                # 重新開始遊戲以測試下一個答案
                start_potato_game(test_user_id)
                
            except Exception as e:
                print(f"❌ 處理答案時發生錯誤: {e}")
                answer_results.append(False)
        
        success_count = sum(answer_results)
        print(f"\n🎯 遊戲流程測試結果: {success_count}/{len(test_answers)} 成功")
        
        return success_count >= 2  # 至少2/3成功
        
    except Exception as e:
        print(f"❌ 遊戲流程測試發生錯誤: {e}")
        return False

def test_game_content_quality():
    """測試遊戲內容品質"""
    print("\n" + "=" * 60)
    print("🎨 防詐遊戲內容品質測試")
    print("=" * 60)
    
    try:
        with open('fraud_detection_questions.json', 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
        
        questions = questions_data.get('questions', [])
        
        # 檢查題目覆蓋的詐騙類型
        fraud_types_covered = set()
        fraud_messages_length = []
        explanations_length = []
        
        for question in questions[:20]:  # 檢查前20道題目
            fraud_message = question.get('fraud_message', '')
            explanation = question.get('explanation', '')
            fraud_type = question.get('fraud_type', '')
            
            fraud_messages_length.append(len(fraud_message))
            explanations_length.append(len(explanation))
            
            # 收集詐騙類型
            if fraud_type:
                fraud_types_covered.add(fraud_type)
        
        print(f"✅ 涵蓋詐騙類型: {len(fraud_types_covered)} 種")
        for fraud_type in sorted(fraud_types_covered):
            print(f"   - {fraud_type}")
        
        avg_message_length = sum(fraud_messages_length) / len(fraud_messages_length) if fraud_messages_length else 0
        avg_explanation_length = sum(explanations_length) / len(explanations_length) if explanations_length else 0
        
        print(f"📊 平均詐騙訊息長度: {avg_message_length:.0f} 字")
        print(f"📊 平均解釋長度: {avg_explanation_length:.0f} 字")
        
        # 品質評估
        quality_score = 0
        if len(fraud_types_covered) >= 5:
            quality_score += 1
            print("✅ 詐騙類型覆蓋度: 良好")
        else:
            print("❌ 詐騙類型覆蓋度: 不足")
        
        if avg_message_length >= 50:
            quality_score += 1
            print("✅ 詐騙訊息豐富度: 良好")
        else:
            print("❌ 詐騙訊息豐富度: 不足")
        
        if avg_explanation_length >= 30:
            quality_score += 1
            print("✅ 解釋詳細度: 良好")
        else:
            print("❌ 解釋詳細度: 不足")
        
        print(f"\n🎯 內容品質評分: {quality_score}/3")
        
        return quality_score >= 2
        
    except Exception as e:
        print(f"❌ 內容品質測試發生錯誤: {e}")
        return False

def main():
    """主測試函數"""
    print("🚀 開始防詐遊戲測試")
    
    # 測試1: 遊戲觸發
    trigger_ok = test_game_trigger()
    
    # 測試2: 遊戲題目
    questions_ok = test_game_questions()
    
    # 測試3: 遊戲流程
    flow_ok = test_game_flow()
    
    # 測試4: 內容品質
    quality_ok = test_game_content_quality()
    
    # 統計結果
    print("\n" + "=" * 60)
    print("📊 測試結果統計")
    print("=" * 60)
    
    tests = [
        ("遊戲觸發", trigger_ok),
        ("遊戲題目", questions_ok),
        ("遊戲流程", flow_ok),
        ("內容品質", quality_ok)
    ]
    
    passed_tests = sum(1 for _, result in tests if result)
    total_tests = len(tests)
    
    for test_name, result in tests:
        print(f"{test_name}: {'✅ 通過' if result else '❌ 失敗'}")
    
    print(f"\n總通過率: {passed_tests}/{total_tests}")
    
    if passed_tests >= 3:
        print("🎉 防詐遊戲功能測試通過！")
        return True
    else:
        print("❌ 防詐遊戲功能需要改進")
        return False

if __name__ == "__main__":
    main() 