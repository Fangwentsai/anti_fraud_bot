import os
import json
import logging
import datetime
from typing import Dict, List, Any, Optional
import firebase_admin
from firebase_admin import credentials, firestore
import random

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
            fraud_types_stats = {} # Renamed to avoid conflict
            risk_levels_stats = {'高': 0, '中': 0, '低': 0, '無風險': 0, '不確定': 0} # Added more risk levels
            total_reports = 0
            
            for doc in reports:
                report = doc.to_dict()
                total_reports += 1
                
                # 詐騙類型統計
                fraud_type_report = report.get('fraud_type', '未分類') # Renamed to avoid conflict
                if fraud_type_report not in fraud_types_stats:
                    fraud_types_stats[fraud_type_report] = 0
                fraud_types_stats[fraud_type_report] += 1
                
                # 風險等級統計
                risk_level_report = report.get('risk_level', '未評估') # Renamed to avoid conflict
                if risk_level_report in risk_levels_stats:
                    risk_levels_stats[risk_level_report] += 1
            
            return {
                'total_reports': total_reports,
                'fraud_types': fraud_types_stats,
                'risk_levels': risk_levels_stats
            }
        
        except Exception as e:
            logger.error(f"獲取詐騙統計數據失敗: {e}")
            return {}

    def get_random_fraud_report_for_game(self) -> Optional[Dict[str, Any]]:
        """
        從 'fraud_reports' 隨機獲取一份報告用於遊戲題目
        """
        if not self.db:
            logger.error("Firebase未初始化，無法獲取遊戲題目")
            return None
        try:
            # 嘗試獲取風險等級為 '中' 或 '高' 的報告，增加獲取數量以提高篩選基數
            query = (
                self.db.collection('fraud_reports')
                .where('risk_level', 'in', ['中', '高'])
                .order_by('timestamp', direction=firestore.Query.DESCENDING)
                .limit(200) # 增加limit以獲取更多候選
            )
            reports_stream = query.stream()
            
            valid_reports_for_game = []
            generic_fraud_types = ['未知', '未知類型', '非詐騙相關', '不確定']
            min_message_length = 10 # 訊息最小長度

            for doc in reports_stream:
                report = doc.to_dict()
                message_text = report.get('message')
                fraud_type = report.get('fraud_type')
                risk_level = report.get('risk_level') # 確保也獲取risk_level來判斷

                # 嚴格的過濾條件
                if (message_text and 
                    isinstance(message_text, str) and 
                    len(message_text.strip()) > min_message_length and
                    fraud_type and
                    fraud_type not in generic_fraud_types and
                    risk_level in ['中', '高']): # 再次確認 risk_level
                    valid_reports_for_game.append({
                        'message': message_text,
                        'fraud_type': fraud_type
                    })
            
            if not valid_reports_for_game:
                logger.warning("在 'fraud_reports' 中未找到符合遊戲條件的詐騙報告 (風險中/高, 明確詐騙類型, 訊息長度 > 10)。嘗試放寬條件查詢所有報告。")
                # 如果嚴格條件下找不到，嘗試從所有報告中篩選，但仍應用基本過濾
                all_reports_stream = self.db.collection('fraud_reports').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(300).stream()
                for doc in all_reports_stream:
                    report = doc.to_dict()
                    message_text = report.get('message')
                    fraud_type = report.get('fraud_type')
                    # 放寬條件：至少訊息長度和詐騙類型需要有意義
                    if (message_text and 
                        isinstance(message_text, str) and 
                        len(message_text.strip()) > min_message_length and
                        fraud_type and
                        fraud_type not in generic_fraud_types):
                        valid_reports_for_game.append({
                            'message': message_text,
                            'fraud_type': fraud_type
                        })
                        if len(valid_reports_for_game) >= 50: # 避免過多候選
                            break 
            
            if not valid_reports_for_game:
                logger.error("即使放寬條件後，fraud_reports 中仍沒有符合遊戲條件的數據 (message長度>10, fraud_type非模糊)。遊戲可能無題目可出。")
                return None
            
            selected_report = random.choice(valid_reports_for_game)
            logger.info(f"為遊戲選取的詐騙報告: fraud_type='{selected_report['fraud_type']}', message='{selected_report['message'][:30]}...'" )
            return selected_report

        except Exception as e:
            logger.error(f"為遊戲獲取隨機詐騙報告失敗: {e}")
            return None

    def save_emerging_fraud_report(self, user_id: str, display_name: str, user_message: str,
                                   chatgpt_analysis: str, status: str = "pending_review") -> bool:
        """
        保存用戶回報的新興詐騙資訊
        """
        if not self.db:
            logger.error("Firebase未初始化，無法保存新興詐騙回報")
            return False
        
        try:
            report_data = {
                'user_id': user_id,
                'display_name': display_name,
                'user_message_description': user_message,
                'chatgpt_initial_analysis': chatgpt_analysis,
                'timestamp': datetime.datetime.now(),
                'status': status  # e.g., 'pending_review', 'categorized', 'rejected'
            }
            self.db.collection('emerging_fraud_reports').add(report_data)
            logger.info(f"成功保存新興詐騙回報 from {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"保存新興詐騙回報失敗: {e}")
            return False

    def get_pending_emerging_reports(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        獲取所有待審核 (pending_review) 的新興詐騙報告
        Args:
            limit: 最大返回報告數量
        Returns:
            待審核報告列表，每個報告包含ID和數據
        """
        if not self.db:
            logger.error("Firebase未初始化，無法獲取待審核報告")
            return []
        
        try:
            query = (self.db.collection('emerging_fraud_reports')
                     .where('status', '==', 'pending_review')
                     .order_by('timestamp', direction=firestore.Query.ASCENDING)
                     .limit(limit))
            
            reports = []
            for doc in query.stream():
                report_data = doc.to_dict()
                report_data['id'] = doc.id # 將文檔ID也加入到數據中
                if 'timestamp' in report_data and isinstance(report_data['timestamp'], datetime.datetime):
                    report_data['timestamp'] = report_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                reports.append(report_data)
            
            logger.info(f"獲取到 {len(reports)} 筆待審核的新興詐騙報告")
            return reports
        except Exception as e:
            logger.error(f"獲取待審核新興詐騙報告失敗: {e}")
            return []

    def update_emerging_report_status(self, report_id: str, new_status: str, processed_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        更新特定新興詐騙報告的狀態，並可選擇性存儲處理後的結構化數據
        Args:
            report_id: 要更新的報告文檔ID
            new_status: 新的狀態 (e.g., 'categorized', 'rejected', 'needs_more_info')
            processed_data: (可選) AI處理後的結構化詐騙資訊
        Returns:
            是否成功更新
        """
        if not self.db:
            logger.error("Firebase未初始化，無法更新報告狀態")
            return False
        
        try:
            report_ref = self.db.collection('emerging_fraud_reports').document(report_id)
            update_payload = {
                'status': new_status,
                'last_updated': datetime.datetime.now()
            }
            if processed_data:
                update_payload['processed_structured_info'] = processed_data
            
            report_ref.update(update_payload)
            logger.info(f"成功更新報告 {report_id} 狀態為 {new_status}")
            return True
        except Exception as e:
            logger.error(f"更新報告 {report_id} 狀態失敗: {e}")
            return False 