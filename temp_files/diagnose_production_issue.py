#!/usr/bin/env python3
"""
診斷生產環境土豆遊戲問題
模擬完整的遊戲流程來找出問題所在
"""

import json
from game_service import start_potato_game

def diagnose_production_issue():
    """診斷生產環境問題"""
    print("🔍 診斷生產環境土豆遊戲問題")
    print("=" * 50)
    
    # 模擬生產環境的用戶ID
    user_id = "Ua0cb4a29292e6b683b14327daa75df63"
    
    print(f"📱 模擬用戶: {user_id}")
    print("💬 觸發訊息: 選哪顆土豆")
    
    try:
        # 啟動遊戲
        print("\n1️⃣ 啟動遊戲...")
        flex_message, error = start_potato_game(user_id)
        
        if error:
            print(f"❌ 遊戲啟動失敗: {error}")
            return False
        
        if not flex_message:
            print("❌ 沒有返回Flex Message")
            return False
        
        print("✅ 遊戲啟動成功")
        
        # 轉換為JSON檢查結構
        print("\n2️⃣ 檢查Flex Message結構...")
        flex_dict = flex_message.as_json_dict()
        
        # 檢查基本結構
        print(f"   - 類型: {flex_dict.get('type')}")
        print(f"   - Alt Text: {flex_dict.get('altText')}")
        
        contents = flex_dict.get('contents', {})
        if not contents:
            print("❌ 缺少contents")
            return False
        
        # 檢查footer和按鈕
        footer = contents.get('footer', {})
        if not footer:
            print("❌ 缺少footer")
            return False
        
        footer_contents = footer.get('contents', [])
        print(f"   - 按鈕數量: {len(footer_contents)}")
        
        # 詳細檢查每個按鈕
        print("\n3️⃣ 詳細檢查按鈕...")
        for i, button in enumerate(footer_contents):
            if button.get('type') != 'button':
                print(f"❌ 按鈕 {i} 類型錯誤: {button.get('type')}")
                return False
            
            action = button.get('action', {})
            if not action:
                print(f"❌ 按鈕 {i} 缺少action")
                return False
            
            label = action.get('label', '')
            data = action.get('data', '')
            
            print(f"   - 按鈕 {i}:")
            print(f"     * 標籤: 「{label}」 (長度: {len(label)})")
            print(f"     * 數據: {data}")
            print(f"     * 類型: {action.get('type')}")
            
            # 檢查標籤長度
            if len(label) > 20:
                print(f"     ❌ 標籤過長！超過20字符限制")
                return False
            
            if not label:
                print(f"     ❌ 標籤為空！")
                return False
            
            # 檢查是否有特殊字符
            if any(ord(c) > 127 for c in label if c not in '選項 ABCD'):
                print(f"     ⚠️ 標籤包含特殊字符")
        
        # 檢查JSON序列化
        print("\n4️⃣ 檢查JSON序列化...")
        try:
            json_str = json.dumps(flex_dict, ensure_ascii=False)
            print(f"   - JSON長度: {len(json_str)}")
            
            # 檢查是否有問題字符
            if '\u00a0' in json_str:
                print("   ⚠️ 發現不間斷空格字符")
            
            if '"label":""' in json_str:
                print("   ❌ 發現空標籤")
                return False
            
            # 檢查標籤格式
            import re
            label_matches = re.findall(r'"label":"([^"]*)"', json_str)
            print(f"   - 找到 {len(label_matches)} 個標籤")
            for i, label in enumerate(label_matches):
                if len(label) > 20:
                    print(f"   ❌ 標籤 {i} 過長: 「{label}」 ({len(label)})")
                    return False
            
        except Exception as e:
            print(f"   ❌ JSON序列化失敗: {e}")
            return False
        
        # 輸出完整的JSON供檢查
        print("\n5️⃣ 完整JSON結構:")
        print(json.dumps(flex_dict, ensure_ascii=False, indent=2))
        
        print("\n✅ 所有檢查都通過！")
        return True
        
    except Exception as e:
        print(f"❌ 診斷過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_line_sdk_compatibility():
    """檢查LINE SDK兼容性"""
    print("\n🔧 檢查LINE SDK兼容性...")
    
    try:
        from linebot.models import FlexSendMessage, BubbleContainer, BoxComponent, TextComponent, ButtonComponent, PostbackAction
        print("✅ LINE SDK模組導入成功")
        
        # 測試創建簡單的Flex Message
        bubble = BubbleContainer(
            body=BoxComponent(
                layout='vertical',
                contents=[
                    TextComponent(text="測試")
                ]
            ),
            footer=BoxComponent(
                layout='vertical',
                contents=[
                    ButtonComponent(
                        action=PostbackAction(
                            label="選項 A",
                            data="test"
                        )
                    )
                ]
            )
        )
        
        flex_message = FlexSendMessage(alt_text="測試", contents=bubble)
        flex_dict = flex_message.as_json_dict()
        
        print("✅ Flex Message創建成功")
        print(f"   - 按鈕標籤: {flex_dict['contents']['footer']['contents'][0]['action']['label']}")
        
        return True
        
    except Exception as e:
        print(f"❌ LINE SDK兼容性檢查失敗: {e}")
        return False

def main():
    """主診斷函數"""
    print("🩺 生產環境問題診斷")
    print("=" * 60)
    
    # 執行診斷
    sdk_ok = check_line_sdk_compatibility()
    game_ok = diagnose_production_issue()
    
    print("\n" + "=" * 60)
    print("📊 診斷結果:")
    print(f"   - LINE SDK兼容性: {'✅ 正常' if sdk_ok else '❌ 異常'}")
    print(f"   - 遊戲功能: {'✅ 正常' if game_ok else '❌ 異常'}")
    
    if sdk_ok and game_ok:
        print("\n🎉 本地環境完全正常！")
        print("💡 建議檢查生產環境:")
        print("   1. 確認代碼版本是否為最新")
        print("   2. 檢查環境變數設定")
        print("   3. 重新部署應用程式")
        print("   4. 檢查LINE SDK版本")
    else:
        print("\n❌ 發現問題，需要進一步修復")
    
    return sdk_ok and game_ok

if __name__ == "__main__":
    main() 