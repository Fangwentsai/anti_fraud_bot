import os
import json
import logging
import datetime
from typing import Dict, List, Any, Optional
import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)

class FirebaseManager:
    """
    管理Firebase連接和數據操作的類
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """
        獲取FirebaseManager的單例實例
        """
        if cls._instance is None:
            cls._instance = FirebaseManager()
        return cls._instance
    
    def __init__(self):
        """
        初始化Firebase連接
        """
        self.app = None
        self.db = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """
        初始化Firebase連接
        
        有兩種方式初始化:
        1. 使用本地的服務賬號密鑰文件
        2. 使用環境變量中的Firebase憑證
        """
        try:
            # 檢查是否有服務賬號密鑰文件
            service_account_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_PATH', 'firebase-key.json')
            
            if os.path.exists(service_account_path):
                # 使用服務賬號密鑰文件
                cred = credentials.Certificate(service_account_path)
                self.app = firebase_admin.initialize_app(cred)
            else:
                # 嘗試使用環境變量中的Firebase憑證
                firebase_credentials = os.environ.get('FIREBASE_CREDENTIALS')
                if firebase_credentials:
                    try:
                        cred_dict = json.loads(firebase_credentials)
                        cred = credentials.Certificate(cred_dict)
                        self.app = firebase_admin.initialize_app(cred)
                    except json.JSONDecodeError:
                        logger.error("無法解析環境變量中的Firebase憑證JSON")
                        return
                else:
                    logger.error("找不到Firebase憑證。請提供服務賬號密鑰文件或設置FIREBASE_CREDENTIALS環境變量")
                    return
            
            # 初始化Firestore
            self.db = firestore.client()
            logger.info("Firebase初始化成功")
        
        except Exception as e:
            logger.error(f"Firebase初始化失敗: {e}")
    
    def save_user_interaction(self, user_id: str, display_name: str, message: str, 
                             response: str, is_fraud_related: bool = False, 
                             fraud_type: Optional[str] = None, risk_level: Optional[str] = None) -> bool:
        """
        保存用戶互動記錄
        
        Args:
            user_id: Line用戶ID
            display_name: 用戶顯示名稱
            message: 用戶消息內容
            response: 機器人響應內容
            is_fraud_related: 是否與詐騙相關
            fraud_type: 詐騙類型 (可選)
            risk_level: 風險等級 (可選)
            
        Returns:
            是否成功保存
        """
        if not self.db:
            logger.error("Firebase未初始化，無法保存數據")
            return False
        
        try:
            # 更新或創建用戶記錄
            user_ref = self.db.collection('users').document(user_id)
            user_ref.set({
                'display_name': display_name,
                'last_interaction': datetime.datetime.now(),
                'interaction_count': firestore.Increment(1)
            }, merge=True)
            
            # 添加互動記錄
            interaction_data = {
                'user_id': user_id,
                'display_name': display_name,
                'message': message,
                'response': response,
                'timestamp': datetime.datetime.now(),
                'is_fraud_related': is_fraud_related
            }
            
            # 添加詐騙相關資訊（如果有）
            if is_fraud_related:
                interaction_data['fraud_type'] = fraud_type
                interaction_data['risk_level'] = risk_level
            
            # 保存互動記錄
            self.db.collection('interactions').add(interaction_data)
            
            # 如果是詐騙相關，額外保存到詐騙記錄集合
            if is_fraud_related and fraud_type:
                fraud_data = {
                    'user_id': user_id,
                    'display_name': display_name,
                    'message': message,
                    'fraud_type': fraud_type,
                    'risk_level': risk_level,
                    'timestamp': datetime.datetime.now()
                }
                self.db.collection('fraud_reports').add(fraud_data)
            
            return True
        
        except Exception as e:
            logger.error(f"保存用戶互動記錄失敗: {e}")
            return False
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        獲取用戶個人資料
        
        Args:
            user_id: Line用戶ID
            
        Returns:
            用戶個人資料字典
        """
        if not self.db:
            logger.error("Firebase未初始化，無法獲取數據")
            return {}
        
        try:
            user_doc = self.db.collection('users').document(user_id).get()
            if user_doc.exists:
                return user_doc.to_dict()
            return {}
        
        except Exception as e:
            logger.error(f"獲取用戶個人資料失敗: {e}")
            return {}
    
    def get_user_fraud_reports(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        獲取用戶的詐騙報告歷史
        
        Args:
            user_id: Line用戶ID
            limit: 最大返回記錄數
            
        Returns:
            詐騙報告列表
        """
        if not self.db:
            logger.error("Firebase未初始化，無法獲取數據")
            return []
        
        try:
            query = (self.db.collection('fraud_reports')
                    .where('user_id', '==', user_id)
                    .order_by('timestamp', direction=firestore.Query.DESCENDING)
                    .limit(limit))
            
            results = []
            for doc in query.stream():
                report = doc.to_dict()
                # 將timestamp轉換為字符串以便序列化
                if 'timestamp' in report:
                    report['timestamp'] = report['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                results.append(report)
            
            return results
        
        except Exception as e:
            logger.error(f"獲取用戶詐騙報告失敗: {e}")
            return []
    
    def get_fraud_statistics(self) -> Dict[str, Any]:
        """
        獲取詐騙統計數據
        
        Returns:
            詐騙統計數據字典
        """
        if not self.db:
            logger.error("Firebase未初始化，無法獲取數據")
            return {}
        
        try:
            # 獲取所有詐騙報告
            reports = self.db.collection('fraud_reports').stream()
            
            # 統計各類型詐騙數量
            fraud_types = {}
            risk_levels = {'高': 0, '中': 0, '低': 0}
            total_reports = 0
            
            for doc in reports:
                report = doc.to_dict()
                total_reports += 1
                
                # 詐騙類型統計
                fraud_type = report.get('fraud_type', '未分類')
                if fraud_type not in fraud_types:
                    fraud_types[fraud_type] = 0
                fraud_types[fraud_type] += 1
                
                # 風險等級統計
                risk_level = report.get('risk_level', '未評估')
                if risk_level in risk_levels:
                    risk_levels[risk_level] += 1
            
            return {
                'total_reports': total_reports,
                'fraud_types': fraud_types,
                'risk_levels': risk_levels
            }
        
        except Exception as e:
            logger.error(f"獲取詐騙統計數據失敗: {e}")
            return {} 