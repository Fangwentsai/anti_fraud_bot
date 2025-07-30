#!/usr/bin/env python3
"""
防詐騙機器人專案清理腳本
用於整理混亂的檔案結構
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path

class ProjectCleanup:
    def __init__(self):
        self.project_root = Path.cwd()
        self.backup_dir = self.project_root / "backups"
        self.temp_dir = self.project_root / "temp_files"
        self.test_dir = self.project_root / "tests"
        
    def create_directories(self):
        """創建必要的目錄"""
        directories = [self.backup_dir, self.temp_dir, self.test_dir]
        for directory in directories:
            directory.mkdir(exist_ok=True)
            print(f"✅ 創建目錄: {directory}")
    
    def identify_backup_files(self):
        """識別備份檔案"""
        backup_patterns = [
            "*.bak", "*.bak2", "*_backup.py", "*_backup.json",
            "*_emergency_backup.py", "*_backup_before_*.py"
        ]
        
        backup_files = []
        for pattern in backup_patterns:
            backup_files.extend(self.project_root.glob(pattern))
        
        return backup_files
    
    def identify_duplicate_flex_files(self):
        """識別重複的flex_message檔案"""
        flex_files = list(self.project_root.glob("flex_message_*.py"))
        
        # 按檔案大小排序，保留最大的（通常是最完整的）
        flex_files.sort(key=lambda x: x.stat().st_size, reverse=True)
        
        return flex_files
    
    def identify_test_files(self):
        """識別測試檔案"""
        test_files = list(self.project_root.glob("test_*.py"))
        return test_files
    
    def identify_temp_files(self):
        """識別臨時檔案"""
        temp_patterns = [
            "temp_*.py", "temp_*.json", "temp_*.txt",
            "fixed_*.json", "cleaned_*.json"
        ]
        
        temp_files = []
        for pattern in temp_patterns:
            temp_files.extend(self.project_root.glob(pattern))
        
        return temp_files
    
    def backup_files(self, files, category):
        """備份檔案到指定目錄"""
        if not files:
            return
        
        category_dir = self.backup_dir / category
        category_dir.mkdir(exist_ok=True)
        
        for file_path in files:
            if file_path.exists():
                backup_path = category_dir / file_path.name
                shutil.copy2(file_path, backup_path)
                print(f"📦 備份 {category}: {file_path.name}")
    
    def move_files(self, files, target_dir, category):
        """移動檔案到指定目錄"""
        if not files:
            return
        
        target_dir.mkdir(exist_ok=True)
        
        for file_path in files:
            if file_path.exists():
                target_path = target_dir / file_path.name
                if target_path.exists():
                    # 如果目標檔案已存在，添加時間戳
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    name_parts = file_path.stem, timestamp, file_path.suffix
                    target_path = target_dir / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
                
                shutil.move(str(file_path), str(target_path))
                print(f"📁 移動 {category}: {file_path.name} -> {target_dir.name}/")
    
    def generate_cleanup_report(self):
        """生成清理報告"""
        report = {
            "清理時間": datetime.now().isoformat(),
            "備份檔案數量": len(list(self.backup_dir.rglob("*"))),
            "測試檔案數量": len(list(self.test_dir.rglob("*.py"))),
            "臨時檔案數量": len(list(self.temp_dir.rglob("*"))),
            "建議": [
                "備份檔案已移至 backups/ 目錄",
                "測試檔案已移至 tests/ 目錄", 
                "臨時檔案已移至 temp_files/ 目錄",
                "建議定期清理 temp_files/ 目錄",
                "重要檔案已備份，可安全刪除重複檔案"
            ]
        }
        
        report_path = self.project_root / "cleanup_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"📊 清理報告已生成: {report_path}")
        return report
    
    def cleanup(self):
        """執行完整清理流程"""
        print("🧹 開始專案清理...")
        
        # 1. 創建目錄
        self.create_directories()
        
        # 2. 識別並處理備份檔案
        backup_files = self.identify_backup_files()
        if backup_files:
            print(f"\n📦 發現 {len(backup_files)} 個備份檔案")
            self.backup_files(backup_files, "backup_files")
        
        # 3. 識別並處理重複的flex檔案
        flex_files = self.identify_duplicate_flex_files()
        if len(flex_files) > 1:
            print(f"\n🔄 發現 {len(flex_files)} 個flex_message檔案")
            # 保留最大的檔案，移動其他的
            keep_file = flex_files[0]
            duplicate_files = flex_files[1:]
            print(f"保留: {keep_file.name}")
            self.backup_files(duplicate_files, "duplicate_flex_files")
        
        # 4. 移動測試檔案
        test_files = self.identify_test_files()
        if test_files:
            print(f"\n🧪 發現 {len(test_files)} 個測試檔案")
            self.move_files(test_files, self.test_dir, "測試檔案")
        
        # 5. 移動臨時檔案
        temp_files = self.identify_temp_files()
        if temp_files:
            print(f"\n🗂️ 發現 {len(temp_files)} 個臨時檔案")
            self.move_files(temp_files, self.temp_dir, "臨時檔案")
        
        # 6. 生成報告
        report = self.generate_cleanup_report()
        
        print(f"\n✅ 清理完成！")
        print(f"📊 清理報告: {report}")
        
        return report

def main():
    """主函數"""
    cleanup = ProjectCleanup()
    
    # 顯示清理預覽
    print("🔍 清理預覽:")
    print(f"備份檔案: {len(list(cleanup.identify_backup_files()))} 個")
    print(f"Flex檔案: {len(list(cleanup.identify_duplicate_flex_files()))} 個")
    print(f"測試檔案: {len(list(cleanup.identify_test_files()))} 個")
    print(f"臨時檔案: {len(list(cleanup.identify_temp_files()))} 個")
    
    # 詢問是否繼續
    response = input("\n是否繼續執行清理？(y/N): ").strip().lower()
    if response in ['y', 'yes']:
        cleanup.cleanup()
    else:
        print("❌ 取消清理")

if __name__ == "__main__":
    main() 