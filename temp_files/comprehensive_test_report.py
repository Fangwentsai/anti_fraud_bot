#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
防詐騙機器人綜合測試報告
運行所有四項功能測試並生成最終報告
"""

import sys
import os
import subprocess
from datetime import datetime

# 添加當前目錄到Python路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_test_module(test_file):
    """運行測試模組並獲取結果"""
    try:
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=True, text=True, 
                              cwd=os.path.dirname(os.path.abspath(__file__)))
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.stderr else None
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e)
        }

def extract_test_results(output, test_name):
    """從測試輸出中提取關鍵結果"""
    lines = output.split('\n')
    results = {
        "test_name": test_name,
        "status": "❌ 失敗",
        "details": "",
        "success_rate": "0%"
    }
    
    if test_name == "網站風險評估":
        for line in lines:
            if "準確率:" in line:
                accuracy = line.split("準確率:")[1].strip()
                results["success_rate"] = accuracy
            if "網站風險評估功能測試通過" in line:
                results["status"] = "✅ 通過"
            if "正確識別:" in line:
                results["details"] = line.strip()
    
    elif test_name == "詐騙案例分享":
        for line in lines:
            if "詐騙案例分享功能測試通過" in line:
                results["status"] = "✅ 通過"
            if "詐騙案例測試:" in line:
                results["details"] = line.strip()
            if "成功載入" in line and "種詐騙類型" in line:
                results["success_rate"] = "100%"
    
    elif test_name == "防詐遊戲":
        for line in lines:
            if "防詐遊戲功能測試通過" in line:
                results["status"] = "✅ 通過"
            if "總通過率:" in line:
                rate = line.split("總通過率:")[1].strip()
                results["success_rate"] = rate
            if "成功載入" in line and "道防詐題目" in line:
                results["details"] = line.strip()
    
    elif test_name == "天氣查詢":
        for line in lines:
            if "天氣查詢功能測試通過" in line:
                results["status"] = "✅ 通過"
            if "總通過率:" in line:
                rate = line.split("總通過率:")[1].strip()
                results["success_rate"] = rate
            if "城市查詢成功率:" in line:
                results["details"] = line.strip()
    
    return results

def generate_summary_report(test_results):
    """生成綜合測試報告"""
    report = []
    report.append("=" * 80)
    report.append("🚀 防詐騙機器人功能測試綜合報告")
    report.append("=" * 80)
    report.append(f"📅 測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"🖥️  測試環境: macOS")
    report.append("")
    
    # 測試結果概覽
    report.append("📊 測試結果概覽")
    report.append("-" * 40)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for result in test_results:
        status_symbol = "✅" if result["status"] == "✅ 通過" else "❌"
        report.append(f"{status_symbol} {result['test_name']}: {result['status']} ({result['success_rate']})")
        if result["status"] == "✅ 通過":
            passed_tests += 1
    
    report.append("")
    overall_success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    report.append(f"🎯 整體通過率: {passed_tests}/{total_tests} ({overall_success_rate:.1f}%)")
    
    # 詳細測試結果
    report.append("")
    report.append("📋 詳細測試結果")
    report.append("=" * 80)
    
    for i, result in enumerate(test_results, 1):
        report.append(f"\n{i}. {result['test_name']} {result['status']}")
        report.append("-" * 50)
        if result["details"]:
            report.append(f"📈 測試詳情: {result['details']}")
        report.append(f"📊 成功率: {result['success_rate']}")
        
        # 根據測試類型添加具體描述
        if result["test_name"] == "網站風險評估":
            report.append("🔍 測試內容: 隨機可疑網域、safe_domains變異、合法網域識別")
        elif result["test_name"] == "詐騙案例分享":
            report.append("📖 測試內容: 詐騙案例生成、防詐小知識載入")
        elif result["test_name"] == "防詐遊戲":
            report.append("🎮 測試內容: 遊戲觸發、題目載入、流程測試、內容品質")
        elif result["test_name"] == "天氣查詢":
            report.append("☁️ 測試內容: 台北、宜蘭、嘉義、高雄、屏東天氣預報")
    
    # 功能完整性評估
    report.append("")
    report.append("🏆 功能完整性評估")
    report.append("=" * 80)
    
    if passed_tests >= 4:
        report.append("🎉 恭喜！所有核心功能測試通過")
        report.append("✨ 系統已準備好發布到GitHub")
        deployment_status = "✅ 準備發布"
    elif passed_tests >= 3:
        report.append("👍 大部分功能正常，建議修復後發布")
        deployment_status = "⚠️ 建議修復"
    else:
        report.append("❌ 需要大幅改善才能發布")
        deployment_status = "❌ 需要修復"
    
    report.append(f"📦 發布狀態: {deployment_status}")
    
    # 建議改進項目
    report.append("")
    report.append("💡 建議改進項目")
    report.append("-" * 40)
    
    failed_tests = [r for r in test_results if r["status"] != "✅ 通過"]
    if failed_tests:
        for test in failed_tests:
            report.append(f"• 修復{test['test_name']}功能")
    else:
        report.append("• 已達到發布標準，無需額外修復")
        report.append("• 可考慮增加更多詐騙類型的測試案例")
        report.append("• 可考慮添加用戶反饋機制")
    
    # 下一步行動
    report.append("")
    report.append("🚀 下一步行動")
    report.append("-" * 40)
    if passed_tests >= 3:
        report.append("1. 準備GitHub發布材料")
        report.append("2. 撰寫README.md文檔")
        report.append("3. 檢查程式碼品質")
        report.append("4. 創建發布版本")
    else:
        report.append("1. 修復失敗的測試項目")
        report.append("2. 重新運行測試")
        report.append("3. 確保所有功能正常後再發布")
    
    report.append("")
    report.append("=" * 80)
    report.append("📝 測試報告結束")
    report.append("=" * 80)
    
    return "\n".join(report)

def main():
    """主測試函數"""
    print("🚀 開始運行防詐騙機器人綜合功能測試")
    print("=" * 80)
    
    # 定義測試模組
    test_modules = [
        ("test_website_risk_assessment.py", "網站風險評估"),
        ("test_fraud_cases.py", "詐騙案例分享"), 
        ("test_fraud_game.py", "防詐遊戲"),
        ("test_weather_query.py", "天氣查詢")
    ]
    
    test_results = []
    
    # 運行每個測試模組
    for test_file, test_name in test_modules:
        print(f"\n🔍 正在測試: {test_name}")
        print("-" * 50)
        
        if not os.path.exists(test_file):
            print(f"❌ 測試文件不存在: {test_file}")
            test_results.append({
                "test_name": test_name,
                "status": "❌ 失敗",
                "details": "測試文件不存在",
                "success_rate": "0%"
            })
            continue
        
        result = run_test_module(test_file)
        
        if result["success"]:
            print(f"✅ {test_name} 測試完成")
            extracted_result = extract_test_results(result["output"], test_name)
        else:
            print(f"❌ {test_name} 測試失敗")
            if result["error"]:
                print(f"錯誤信息: {result['error']}")
            extracted_result = {
                "test_name": test_name,
                "status": "❌ 失敗",
                "details": f"執行錯誤: {result['error']}" if result["error"] else "未知錯誤",
                "success_rate": "0%"
            }
        
        test_results.append(extracted_result)
    
    # 生成綜合報告
    print("\n📋 生成綜合測試報告...")
    report = generate_summary_report(test_results)
    
    # 保存報告到文件
    report_filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 顯示報告
    print(report)
    print(f"\n📄 完整報告已保存至: {report_filename}")

if __name__ == "__main__":
    main() 