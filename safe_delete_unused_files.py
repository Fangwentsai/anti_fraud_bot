#!/usr/bin/env python3
"""
安全刪除未使用檔案的腳本
"""

import os
import shutil
from pathlib import Path

def safe_delete_files():
    """安全刪除未使用的檔案"""
    
    # 要刪除的檔案列表
    files_to_delete = [
        # 備份檔案
        "anti_fraud_clean_app_backup.py",
        "anti_fraud_clean_app_emergency_backup.py", 
        "anti_fraud_clean_app_fixed.py",
        "anti_fraud_clean_app_syntax_fixed.py",
        "anti_fraud_clean_app_v0525.py",
        "anti_fraud_clean_app_v05262026.py",
        "app_backup.py",
        
        # .bak 備份檔案
        "anti_fraud_clean_app.py.bak",
        "anti_fraud_clean_app.py.clean_except.bak",
        "anti_fraud_clean_app.py.final_fix.bak",
        "anti_fraud_clean_app.py.final_solution.bak",
        "anti_fraud_clean_app.py.flex_v3_fix_final.bak",
        "anti_fraud_clean_app.py.flex_v3_fix_v2.bak",
        "anti_fraud_clean_app.py.flex_v3_fix.bak",
        "anti_fraud_clean_app.py.image_analysis_fix.bak",
        "anti_fraud_clean_app.py.precise_fix.bak",
        "anti_fraud_clean_app.py.reply_token_fix.bak",
        "anti_fraud_clean_app.py.simple_fallback.bak",
        "anti_fraud_clean_app.py.simple_fix.bak",
        "anti_fraud_clean_app.py.syntax_fix.bak",
        
        # 修復腳本
        "fix_flex_message_empty_text.py",
        "fix_json.py",
        "fix_json_final.py", 
        "fix_json_simple.py",
        "fix_main_syntax.py",
        "fix_syntax_errors.py",
        "fix_trigger_conflicts.py",
        "fix_weather_bug.py",
        "flex_fix.py",
        "flex_message_simple_fix.py",
        "flex_message_v3_fix.py",
        "flex_message_v3_fix_final.py",
        "flex_message_v3_fix_v2.py",
        "flex_message_final_solution.py",
        "flex_message_precise_fix.py",
        "manual_cleanup.py",
        "manual_fix.py",
        "manual_fix_syntax.py",
        "simple_fix.py",
        "simple_fallback_fix.py",
        "syntax_fix.py",
        "reply_token_fix.py",
        "indent_fix.py",
        "line_api_fix.py",
        "image_analysis_fix.py",
        "emergency_weather_fix.py",
        "final_fix.py",
        "final_fix2.py",
        "final_repair.py",
        "clean_duplicate_except.py",
        
        # 臨時檔案
        "anti_fraud_clean_app.py-e",
        "temp.json",
        
        # 其他未使用的檔案
        "core_functions_backup.py",
        "check_files.py",
        "project_stats.py",
        "protect_core_functions.py",
        "extract_health_product.py",
        "diagnose_production_issue.py",
        "comprehensive_test.py",
        "comprehensive_test_report.py",
        "image_analysis_demo.py",
        "weather_integration_example.py",
        "city_selector.py",
        "calendar_weather_service.py",
        "calendar_weather_config.example",
        "requirements_calendar_weather.txt",
        "gunicorn.conf.py",
        "keep_alive_service.py",
        "manage_beauty_health_whitelist.py",
        "manage_safe_domains.py",
        "beauty_health_whitelist.json",
        "protection_snapshot.json",
        "final_fixed.json",
        "final_fixed2.json",
        "fixed_part.txt",
        "easter_egg_return.txt",
        "test_report_20250524_153027.txt",
        "final_system_summary.md",
        "final_trigger_keywords_summary.md",
        "trigger_keywords_analysis.md",
        "updated_trigger_keywords_summary.md",
        "summary.md",
        "總結.md",
        "語法錯誤修復總結.md",
        "郵件檢測邏輯修正說明.md",
        "修改天氣Flex訊息設計說明.md",
        "問題修復完成報告.md",
        "天氣API修復說明.md",
        "天氣功能修復及優化說明.md",
        "天氣功能修復說明.md",
        "推薦行為檢測改進說明.md",
        "服務功能總結.md",
        "短網址分析報告.md",
        "短網址分析總結報告.md",
        "RENDER_PERFORMANCE_FIX.md",
        "deploy_with_api_key.md",
        "DEPLOYMENT_FIX.md",
        "DEPLOYMENT.md",
        "PRODUCTION_DEPLOYMENT_GUIDE.md",
        "PRODUCTION_DEPLOYMENT.md",
        "MODEL_UPGRADE.md",
        "MODULARIZATION_PROGRESS.md",
        "POTATO_GAME_FIX_REPORT.md",
        "POTATO_GAME_FIX_SUMMARY.md",
        "POTATO_GAME_TRIGGER_FIX_REPORT.md",
        "RECOVERY_GUIDE.md",
        "RENDER_PERFORMANCE_FIX.md",
        "SECURITY_FIX_DOMAIN_SPOOFING.md",
        "URL_EXTRACTION_FIX_SUMMARY.md",
        "DOMAIN_SPOOFING_FIX_REPORT.md",
        "DOMAIN_SPOOFING_TEST_RESULTS.md",
        "FINAL_DOMAIN_SPOOFING_ANALYSIS.md",
        "README_calendar_weather.md",
        "CWB_API_SETUP.md",
        "GITHUB_SETUP.md",
        "INSTRUCTIONS.md",
        "integration_guide.md",
        "image_url_analysis_feature.md",
        "weather_implementation_guide.md",
        "CORE_PROTECTION_README.md",
        "bug_fix_report.md",
        "bsms_短鏈結實現報告.md"
    ]
    
    deleted_count = 0
    not_found_count = 0
    
    print("🗑️ 開始安全刪除未使用的檔案...")
    print("=" * 50)
    
    for filename in files_to_delete:
        file_path = Path(filename)
        if file_path.exists():
            try:
                # 先備份到 temp_files 目錄
                backup_dir = Path("temp_files")
                backup_dir.mkdir(exist_ok=True)
                backup_path = backup_dir / filename
                
                # 如果備份檔案已存在，添加時間戳
                if backup_path.exists():
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    name_parts = filename.rsplit('.', 1)
                    if len(name_parts) > 1:
                        backup_path = backup_dir / f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                    else:
                        backup_path = backup_dir / f"{filename}_{timestamp}"
                
                shutil.copy2(file_path, backup_path)
                file_path.unlink()
                print(f"✅ 已刪除並備份: {filename}")
                deleted_count += 1
                
            except Exception as e:
                print(f"❌ 刪除失敗 {filename}: {e}")
        else:
            print(f"⚠️ 檔案不存在: {filename}")
            not_found_count += 1
    
    print("=" * 50)
    print(f"📊 刪除統計:")
    print(f"  成功刪除: {deleted_count} 個檔案")
    print(f"  檔案不存在: {not_found_count} 個")
    print(f"  備份位置: temp_files/ 目錄")
    print(f"\n💡 如果發現誤刪，可以從 temp_files/ 目錄恢復")

if __name__ == "__main__":
    # 顯示預覽
    print("🔍 預覽要刪除的檔案:")
    print("這些檔案都是備份、修復腳本或臨時檔案，可以安全刪除")
    print("=" * 50)
    
    response = input("是否繼續執行刪除？(y/N): ").strip().lower()
    if response in ['y', 'yes']:
        safe_delete_files()
    else:
        print("❌ 取消刪除") 