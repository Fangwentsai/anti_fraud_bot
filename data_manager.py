import json
import os
from typing import Dict, List, Any

class FraudDataManager:
    """
    管理詐騙類型、案例和處理SOP的數據管理類
    """
    
    def __init__(self, data_file: str = 'fraud_data.json'):
        """
        初始化數據管理器
        
        Args:
            data_file: 存儲數據的JSON文件路徑
        """
        self.data_file = data_file
        self.fraud_types = self._load_data()
        
    def _load_data(self) -> Dict[str, Any]:
        """
        從JSON文件加載數據，如果文件不存在則創建默認數據
        
        Returns:
            詐騙類型數據字典
        """
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"警告：數據文件 {self.data_file} 格式錯誤，使用默認數據")
                return self._create_default_data()
        else:
            return self._create_default_data()
    
    def _create_default_data(self) -> Dict[str, Any]:
        """
        創建默認的詐騙類型數據
        
        Returns:
            默認詐騙類型數據字典
        """
        return {
            "網路購物": {
                "description": "涉及假冒購物網站、虛假商品或不實廣告的詐騙",
                "examples": [],
                "sop": []
            },
            "假冒身份": {
                "description": "冒充親友、官方人員或企業代表的詐騙",
                "examples": [],
                "sop": []
            },
            "投資理財": {
                "description": "高報酬投資、假冒投資平台的詐騙",
                "examples": [],
                "sop": []
            },
            "個資盜用": {
                "description": "竊取個人資料以進行的詐騙",
                "examples": [],
                "sop": []
            }
        }
    
    def save_data(self) -> None:
        """
        保存數據到JSON文件
        """
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.fraud_types, f, ensure_ascii=False, indent=2)
    
    def get_fraud_types(self) -> Dict[str, Any]:
        """
        獲取所有詐騙類型數據
        
        Returns:
            所有詐騙類型數據
        """
        return self.fraud_types
    
    def add_fraud_type(self, name: str, description: str) -> bool:
        """
        添加新的詐騙類型
        
        Args:
            name: 詐騙類型名稱
            description: 詐騙類型描述
            
        Returns:
            是否成功添加
        """
        if name in self.fraud_types:
            return False
        
        self.fraud_types[name] = {
            "description": description,
            "examples": [],
            "sop": []
        }
        self.save_data()
        return True
    
    def add_example(self, fraud_type: str, example: str) -> bool:
        """
        添加詐騙案例
        
        Args:
            fraud_type: 詐騙類型名稱
            example: 案例描述
            
        Returns:
            是否成功添加
        """
        if fraud_type not in self.fraud_types:
            return False
        
        if example not in self.fraud_types[fraud_type]["examples"]:
            self.fraud_types[fraud_type]["examples"].append(example)
            self.save_data()
        
        return True
    
    def add_sop_step(self, fraud_type: str, step: str) -> bool:
        """
        添加處理SOP步驟
        
        Args:
            fraud_type: 詐騙類型名稱
            step: SOP步驟描述
            
        Returns:
            是否成功添加
        """
        if fraud_type not in self.fraud_types:
            return False
        
        if step not in self.fraud_types[fraud_type]["sop"]:
            self.fraud_types[fraud_type]["sop"].append(step)
            self.save_data()
        
        return True
    
    def remove_fraud_type(self, fraud_type: str) -> bool:
        """
        刪除詐騙類型
        
        Args:
            fraud_type: 詐騙類型名稱
            
        Returns:
            是否成功刪除
        """
        if fraud_type not in self.fraud_types:
            return False
        
        del self.fraud_types[fraud_type]
        self.save_data()
        return True
    
    def update_description(self, fraud_type: str, description: str) -> bool:
        """
        更新詐騙類型描述
        
        Args:
            fraud_type: 詐騙類型名稱
            description: 新的描述
            
        Returns:
            是否成功更新
        """
        if fraud_type not in self.fraud_types:
            return False
        
        self.fraud_types[fraud_type]["description"] = description
        self.save_data()
        return True 