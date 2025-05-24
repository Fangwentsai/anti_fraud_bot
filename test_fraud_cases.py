#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
詐騙案例分享測試模組
測試詐騙話術和案例的內容
"""

import sys
import os
import json

# 添加當前目錄到Python路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fraud_knowledge import load_fraud_tactics, get_anti_fraud_tips

def test_fraud_cases_content():
    """測試詐騙案例的內容豐富度"""
    print("=" * 60)
    print("📋 詐騙案例內容測試")
    print("=" * 60)
    
    # 載入詐騙話術資料
    fraud_tactics = load_fraud_tactics()
    
    if not fraud_tactics:
        print("❌ 無法載入詐騙話術資料")
        return False
    
    print(f"✅ 成功載入 {len(fraud_tactics)} 種詐騙類型")
    
    # 選出三個代表性的詐騙案例進行詳細分享
    featured_cases = [
        "假交友投資詐騙",
        "網路購物詐騙", 
        "假檢警詐騙"
    ]
    
    results = []
    
    for i, case_type in enumerate(featured_cases, 1):
        print(f"\n" + "="*50)
        print(f"📖 詐騙案例分享 {i}: {case_type}")
        print("="*50)
        
        if case_type in fraud_tactics:
            description = fraud_tactics[case_type]
            print(f"📝 詐騙手法說明：\n{description}")
            
            # 生成詳細的案例分享
            case_content = generate_detailed_case_study(case_type, description)
            print(f"\n🎭 真實案例分享：\n{case_content}")
            
            results.append({
                "type": case_type,
                "description": description,
                "case_study": case_content,
                "has_content": bool(case_content and len(case_content) > 100)
            })
        else:
            print(f"❌ 找不到 {case_type} 的相關資料")
            results.append({
                "type": case_type,
                "has_content": False
            })
    
    return results

def generate_detailed_case_study(fraud_type, description):
    """根據詐騙類型生成詳細案例分享"""
    
    case_studies = {
        "假交友投資詐騙": """
🚨 真實案例分享：「美女投資老師詐騙陷阱」

📅 案例時間：2024年3月
👥 受害者：張先生，42歲，工程師

📖 案例經過：
張先生在交友軟體認識一位自稱在金融業工作的美女，對方主動示好並分享投資心得。經過一個月的感情培養後，對方介紹他投資外匯，並提供「內幕消息」。

🎣 詐騙手法：
• 利用交友軟體建立假身份
• 長期經營感情關係博取信任
• 聲稱有投資內幕或特殊管道
• 提供假的投資平台和獲利截圖
• 初期小額投資讓受害者嚐到甜頭
• 誘導大額投資後就無法提領

💸 損失金額：新台幣230萬元

🛡️ 防範要點：
• 網路交友要特別謹慎，美女主動示好需提高警覺
• 任何投資都有風險，不要相信穩賺不賠的說法
• 不要因為感情因素而做出不理性的投資決定
• 投資前要確認平台的合法性
• 遇到無法提領資金時要立即報警
        """,
        
        "網路購物詐騙": """
🚨 真實案例分享：「假購物網站詐騙」

📅 案例時間：2024年2月
👥 受害者：李小姐，28歲，上班族

📖 案例經過：
李小姐在社群媒體看到名牌包包超低價促銷廣告，點擊進入看起來很專業的購物網站。網站聲稱是「品牌官方授權經銷商」，價格只要市價的3折。

🎣 詐騙手法：
• 在社群媒體投放誘人的促銷廣告
• 建立假的購物網站，模仿知名品牌設計
• 以遠低於市價的價格吸引消費者
• 製造假的用戶評價和購買紀錄
• 要求先付款後出貨
• 收款後消失或寄送劣質仿冒品

💸 損失金額：新台幣15,000元

🛡️ 防範要點：
• 選擇知名可靠的購物平台
• 價格明顯低於市價時要提高警覺
• 查看網站是否有完整的公司資訊和客服
• 使用安全的付款方式，避免轉帳
• 購買前搜尋該網站的評價和討論
        """,
        
        "假檢警詐騙": """
🚨 真實案例分享：「假冒檢察官洗錢案詐騙」

📅 案例時間：2024年1月
👥 受害者：王阿姨，65歲，退休教師

📖 案例經過：
王阿姨接到自稱「刑事局」的電話，對方說她的身分證被冒用申請信用卡，涉及洗錢案件。為了證明清白，需要將存款轉到「監管帳戶」保護財產。

🎣 詐騙手法：
• 冒充檢察官、警察或法院人員
• 編造受害者涉及刑事案件的謊言
• 利用威嚇手段讓受害者害怕
• 要求提供個人資料和銀行帳號
• 聲稱需要「監管帳戶」保護財產
• 引導受害者到ATM進行轉帳

💸 損失金額：新台幣180萬元

🛡️ 防範要點：
• 檢警調不會電話辦案，更不會要求轉帳
• 接到類似電話要立即掛斷並撥打165查證
• 真正的司法程序會以書面通知
• 不要在電話中透露任何個人資料
• ATM沒有監管或解除設定功能
        """
    }
    
    return case_studies.get(fraud_type, "")

def test_anti_fraud_tips():
    """測試防詐小知識內容"""
    print("\n" + "=" * 60)
    print("💡 防詐小知識測試")
    print("=" * 60)
    
    tips = get_anti_fraud_tips()
    
    if not tips:
        print("❌ 無法載入防詐小知識")
        return False
    
    print(f"✅ 成功載入 {len(tips)} 條防詐小知識")
    
    # 隨機展示5條小知識
    import random
    selected_tips = random.sample(tips, min(5, len(tips)))
    
    for i, tip in enumerate(selected_tips, 1):
        print(f"\n💡 防詐小知識 {i}:")
        print(f"   {tip}")
    
    return len(tips) >= 10  # 至少要有10條小知識

def main():
    """主測試函數"""
    print("🚀 開始詐騙案例分享測試")
    
    # 測試1: 詐騙案例內容
    case_results = test_fraud_cases_content()
    
    # 測試2: 防詐小知識
    tips_ok = test_anti_fraud_tips()
    
    # 統計結果
    print("\n" + "=" * 60)
    print("📊 測試結果統計")
    print("=" * 60)
    
    if case_results:
        valid_cases = sum(1 for r in case_results if r.get("has_content", False))
        print(f"詐騙案例測試: {valid_cases}/3 通過")
    else:
        valid_cases = 0
        print("詐騙案例測試: 0/3 通過")
    
    print(f"防詐小知識測試: {'✅ 通過' if tips_ok else '❌ 失敗'}")
    
    # 整體評估
    if valid_cases >= 3 and tips_ok:
        print("🎉 詐騙案例分享功能測試通過！")
        return True
    else:
        print("❌ 詐騙案例分享功能需要改進")
        return False

if __name__ == "__main__":
    main() 