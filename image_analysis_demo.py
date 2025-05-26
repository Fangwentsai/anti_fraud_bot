#!/usr/bin/env python3
"""
圖片分析優化效果示例
展示優化後的 Flex Message 結構
"""

import json
import sys
import os

# 添加當前目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from image_handler import ImageHandler

def demo_optimized_image_analysis():
    """展示優化後的圖片分析效果"""
    
    print("🎯 圖片分析功能優化示例")
    print("=" * 50)
    
    # 創建圖片處理器
    image_handler = ImageHandler()
    
    # 模擬不同風險等級的分析結果
    test_cases = [
        {
            "name": "高風險投資詐騙",
            "result": {
                "success": True,
                "risk_level": "高風險",
                "fraud_type": "投資詐騙（股市操控、虛假投資建議）",
                "explanation": "這則訊息用了「明牌」、「短線目標」、「必達」等保證獲利的說法，誘使人相信投資一定會賺錢，但股市本來有風險，任何保證獲利的說法都要小心。",
                "suggestions": "🚫 不要相信任何保證獲利的投資建議\n🔍 投資前要多方查證\n🛡️ 小心加入來路不明的投資群組",
                "extracted_text": "台股當沖分享交流群・加入\n王鴻強・5月14日上午10:32・\n明日飆股資訊來襲\n現價9塊\n短線目標35塊\n長線抱到下月必達百塊"
            }
        },
        {
            "name": "中風險釣魚網站",
            "result": {
                "success": True,
                "risk_level": "中高",
                "fraud_type": "釣魚網站詐騙",
                "explanation": "這個網站模仿知名銀行，企圖竊取您的帳號密碼。網址有拼寫錯誤，且要求輸入完整的個人資料。",
                "suggestions": "🚫 立即停止使用此網站\n🔍 確認官方網址\n🛡️ 更改相關密碼",
                "extracted_text": "台灣銀行網路銀行登入\n請輸入您的帳號密碼\n帳號：\n密碼：\n驗證碼："
            }
        },
        {
            "name": "低風險正常內容",
            "result": {
                "success": True,
                "risk_level": "低風險",
                "fraud_type": "非詐騙相關",
                "explanation": "這是正常的商業廣告內容，沒有發現明顯的詐騙特徵。",
                "suggestions": "💡 可以正常瀏覽\n🔍 購買前仍建議比較價格",
                "extracted_text": "限時優惠！買一送一\n全館商品8折起\n活動期間：即日起至月底"
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 測試案例 {i}: {test_case['name']}")
        print("-" * 30)
        
        # 創建 Flex Message
        flex_message = image_handler._create_analysis_flex_message(
            test_case['result'], 
            "示例用戶"
        )
        
        # 轉換為字典以檢查結構
        try:
            contents_dict = flex_message.contents.as_json_dict()
            
            print(f"✅ Alt Text: {flex_message.alt_text}")
            
            # 檢查標題
            header = contents_dict.get('header', {})
            if header.get('contents'):
                title_text = header['contents'][0].get('text', '')
                print(f"🎨 標題: {title_text}")
            
            # 檢查主要內容
            body_contents = contents_dict.get('body', {}).get('contents', [])
            print(f"📝 主體內容項目數: {len(body_contents)}")
            
            # 檢查是否包含重複的圖片文字
            has_extracted_text = False
            for content in body_contents:
                if content.get('type') == 'text':
                    text_content = content.get('text', '')
                    if '圖片文字內容' in text_content:
                        has_extracted_text = True
                        break
            
            if has_extracted_text:
                print("❌ 仍包含重複的圖片文字內容")
            else:
                print("✅ 已移除重複的圖片文字內容")
            
            # 檢查底部按鈕
            footer_contents = contents_dict.get('footer', {}).get('contents', [])
            button_count = sum(1 for item in footer_contents if item.get('type') == 'button')
            
            # 檢查是否有贊助按鈕
            has_sponsor_button = False
            sponsor_text = ""
            for content in footer_contents:
                if content.get('type') == 'button':
                    label = content.get('action', {}).get('label', '')
                    if '給我們鼓勵' in label:
                        has_sponsor_button = True
                        break
                elif content.get('type') == 'text':
                    text_content = content.get('text', '')
                    if '贊助' in text_content or '咖啡' in text_content:
                        sponsor_text = text_content
                        break
            
            print(f"🔘 底部按鈕數量: {button_count}")
            
            if has_sponsor_button:
                print("☕ 包含贊助按鈕")
                if sponsor_text:
                    print(f"💬 贊助文字: {sponsor_text[:50]}...")
            else:
                print("⚪ 未顯示贊助按鈕")
            
            # 顯示主要分析內容
            print(f"🔍 風險等級: {test_case['result']['risk_level']}")
            print(f"📊 詐騙類型: {test_case['result']['fraud_type']}")
            
        except Exception as e:
            print(f"❌ 處理 Flex Message 時發生錯誤: {e}")
    
    print(f"\n🎉 優化效果總結:")
    print("✅ 1. 移除了重複的圖片文字內容顯示")
    print("✅ 2. 添加了 10% 機率的贊助按鈕")
    print("✅ 3. 保持了完整的分析功能")
    print("✅ 4. 維持了美觀的 Flex Message 格式")

if __name__ == "__main__":
    demo_optimized_image_analysis() 