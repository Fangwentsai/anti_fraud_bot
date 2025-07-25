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
            # 檢查用戶是否存在，若不存在則創建並初始化次數
            user_ref = self.db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                # 確保用戶有analysis_credits欄位
                if 'analysis_credits' not in user_data:
                    user_ref.set({
                        'display_name': display_name,
                        'last_interaction': datetime.datetime.now(),
                        'interaction_count': firestore.Increment(1),
                        'analysis_credits': 5  # 初始化分析次數
                    }, merge=True)
                    logger.info(f"用戶 {user_id} 初始化分析次數為5")
                else:
                    # 更新用戶記錄
                    user_ref.set({
                        'display_name': display_name,
                        'last_interaction': datetime.datetime.now(),
                        'interaction_count': firestore.Increment(1)
                    }, merge=True)
            else:
                # 創建新用戶記錄，包括analysis_credits欄位
                user_ref.set({
                    'display_name': display_name,
                    'last_interaction': datetime.datetime.now(),
                    'interaction_count': 1,
                    'analysis_credits': 5  # 初始化分析次數
                })
                logger.info(f"創建新用戶 {user_id} 並初始化分析次數為5")
            
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
            valid_reports_for_game = []
            generic_fraud_types = ['未知', '未知類型', '非詐騙相關', '不確定']
            min_message_length = 10  # 訊息最小長度
            
            # 使用簡單查詢，避免需要複合索引
            try:
                # 先嘗試簡單查詢，只獲取最近的報告，然後在應用層過濾
                simple_query = (
                    self.db.collection('fraud_reports')
                    .order_by('timestamp', direction=firestore.Query.DESCENDING)
                    .limit(200)
                )
                reports_stream = simple_query.stream()
                
                for doc in reports_stream:
                    report = doc.to_dict()
                    message_text = report.get('message')
                    fraud_type = report.get('fraud_type')
                    risk_level = report.get('risk_level')
                    
                    # 在應用層進行過濾
                    if (message_text and 
                        isinstance(message_text, str) and 
                        len(message_text.strip()) > min_message_length and
                        fraud_type and
                        fraud_type not in generic_fraud_types and
                        risk_level in ['中', '高']):
                        valid_reports_for_game.append({
                            'message': message_text,
                            'fraud_type': fraud_type
                        })
                        if len(valid_reports_for_game) >= 50:  # 找到足夠多的候選就停止
                            break
            
            except Exception as e:
                logger.warning(f"使用簡單查詢獲取遊戲題目時出錯: {e}")
                # 繼續執行，嘗試備選方案
            
            if not valid_reports_for_game:
                logger.warning("未找到符合遊戲條件的詐騙報告 (風險中/高)。嘗試放寬條件。")
                # 如果沒有中高風險的，就放寬條件，不限風險等級
                backup_query = (
                    self.db.collection('fraud_reports')
                    .order_by('timestamp', direction=firestore.Query.DESCENDING)
                    .limit(300)
                )
                backup_reports_stream = backup_query.stream()
                
                for doc in backup_reports_stream:
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
                        if len(valid_reports_for_game) >= 50:  # 避免過多候選
                            break
            
            if not valid_reports_for_game:
                # 最後備選：如果還是找不到，返回幾個預設的詐騙示例
                logger.warning("在數據庫中找不到合適的遊戲題目，使用預設題目")
                default_examples = [
                    {
                        'message': "您好，我是蝦皮官方客服。您的訂單有問題需要退款，請加入我們的LINE群組處理：@shipping123",
                        'fraud_type': "網購詐騙"
                    },
                    {
                        'message': "恭喜您獲得iPhone 15抽獎資格！請點擊連結填寫收件資料：https://bit.ly/claim-prize",
                        'fraud_type': "網路釣魚"
                    },
                    {
                        'message': "您的包裹無法投遞，請至以下網址確認您的地址：https://delivery-check.site/verify",
                        'fraud_type': "物流詐騙"
                    }
                ]
                return random.choice(default_examples)
            
            selected_report = random.choice(valid_reports_for_game)
            logger.info(f"為遊戲選取的詐騙報告: fraud_type='{selected_report['fraud_type']}', message='{selected_report['message'][:30]}...'" )
            return selected_report

        except Exception as e:
            logger.error(f"為遊戲獲取隨機詐騙報告失敗: {e}")
            # 發生錯誤時，返回預設題目
            default_example = {
                'message': "您好，我是蝦皮官方客服。您的訂單有問題需要退款，請加入我們的LINE群組處理：@shipping123",
                'fraud_type': "網購詐騙"
            }
            logger.info("由於錯誤，返回預設詐騙題目")
            return default_example

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

    def get_recent_interactions(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        獲取用戶最近的對話歷史記錄
        
        Args:
            user_id: Line用戶ID
            limit: 最大返回記錄數
            
        Returns:
            最近對話記錄列表，按時間從舊到新排序
        """
        if not self.db:
            logger.error("Firebase未初始化，無法獲取數據")
            return []
        
        try:
            # 嘗試使用複合查詢
            try:
                query = (self.db.collection('interactions')
                        .where('user_id', '==', user_id)
                        .order_by('timestamp', direction=firestore.Query.DESCENDING)
                        .limit(limit))
                
                results = []
                for doc in query.stream():
                    interaction = doc.to_dict()
                    # 將timestamp轉換為字符串以便序列化
                    if 'timestamp' in interaction:
                        interaction['timestamp'] = interaction['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    results.append(interaction)
                
                # 返回按時間從舊到新排序的結果，便於構建對話歷史
                results.reverse()
                
                return results
                
            except Exception as query_error:
                # 如果是索引錯誤，記錄下來並嘗試使用替代方案
                if "index" in str(query_error).lower():
                    logger.warning(f"索引錯誤，嘗試使用替代方案獲取用戶對話歷史: {query_error}")
                    
                    # 備選方案：只獲取用戶ID，不排序 (這可能不需要索引)
                    try:
                        alt_query = (self.db.collection('interactions')
                                    .where('user_id', '==', user_id)
                                    .limit(limit*2))  # 獲取稍多一些，以防丟失最近數據
                        
                        alt_results = []
                        for doc in alt_query.stream():
                            interaction = doc.to_dict()
                            if 'timestamp' in interaction:
                                # 保存timestamp以便後續排序
                                try:
                                    if isinstance(interaction['timestamp'], datetime.datetime):
                                        alt_results.append(interaction)
                                except Exception:
                                    # 忽略時間格式錯誤的記錄
                                    pass
                        
                        # 在Python中進行排序
                        if alt_results:
                            alt_results.sort(key=lambda x: x['timestamp'], reverse=True)
                            # 只保留limit數量的記錄
                            alt_results = alt_results[:limit]
                            # 將時間戳轉換為字符串
                            for item in alt_results:
                                if isinstance(item['timestamp'], datetime.datetime):
                                    item['timestamp'] = item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                            # 反轉順序，從舊到新
                            alt_results.reverse()
                            
                            logger.info(f"使用替代方案成功獲取了 {len(alt_results)} 條用戶對話記錄")
                            return alt_results
                    except Exception as alt_error:
                        logger.error(f"替代方案也失敗了: {alt_error}")
                        # 繼續到最終異常處理
                
                # 如果不是索引錯誤或備選方案也失敗，則抛出原始異常
                raise query_error
                
        except Exception as e:
            logger.error(f"獲取用戶對話歷史失敗: {e}")
            logger.info("由於無法獲取對話歷史，機器人將在無記憶模式下運行")
            return []

    def set_user_state(self, user_id: str, state_data: Dict[str, Any]) -> bool:
        """
        設置用戶狀態數據
        
        Args:
            user_id: 用戶ID
            state_data: 狀態數據字典
            
        Returns:
            操作是否成功
        """
        if not self.db:
            logger.error("Firebase未初始化，無法設置用戶狀態")
            return False
        
        try:
            user_ref = self.db.collection('users').document(user_id)
            
            # 添加用戶狀態
            user_ref.set({
                'state': state_data,
                'state_updated_at': datetime.datetime.now()
            }, merge=True)
            
            logger.info(f"成功設置用戶 {user_id} 狀態: {state_data}")
            return True
        except Exception as e:
            logger.error(f"設置用戶狀態失敗: {e}")
            return False
    
    def get_user_state(self, user_id: str) -> Dict[str, Any]:
        """
        獲取用戶狀態數據
        
        Args:
            user_id: 用戶ID
            
        Returns:
            用戶狀態數據，如果不存在或出錯則返回空字典
        """
        if not self.db:
            logger.error("Firebase未初始化，無法獲取用戶狀態")
            return {}
        
        try:
            user_doc = self.db.collection('users').document(user_id).get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                if 'state' in user_data:
                    return user_data['state']
            
            return {}
        except Exception as e:
            logger.error(f"獲取用戶狀態失敗: {e}")
            return {}
    
    def get_user_analysis_credits(self, user_id: str) -> int:
        """
        获取用户剩余的分析次数
        
        Args:
            user_id: 用户ID
            
        Returns:
            剩余分析次数，如果用户不存在则返回初始值5
        """
        if not self.db:
            logger.error("Firebase未初始化，无法获取用户分析次数")
            return 5
        
        try:
            logger.info(f"嘗試獲取用戶 {user_id} 的分析次數")
            user_doc = self.db.collection('users').document(user_id).get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                logger.info(f"用戶文檔存在，數據：{user_data}")
                
                # 如果用户存在但没有分析次数字段，则添加初始值
                if 'analysis_credits' not in user_data:
                    logger.info(f"用戶 {user_id} 沒有 analysis_credits 字段，設置為初始值 5")
                    try:
                        update_result = self.db.collection('users').document(user_id).set({
                            'analysis_credits': 5
                        }, merge=True)
                        logger.info(f"更新用戶 analysis_credits 結果：{update_result}")
                    except Exception as update_error:
                        logger.error(f"更新用戶 analysis_credits 失敗：{update_error}")
                    return 5
                
                credits = user_data.get('analysis_credits', 0)
                logger.info(f"用戶 {user_id} 的分析次數：{credits}")
                return credits
            else:
                # 如果用户不存在，创建新用户并设置初始分析次数
                logger.info(f"用戶 {user_id} 不存在，創建新用戶")
                try:
                    create_result = self.db.collection('users').document(user_id).set({
                        'display_name': 'New User',
                        'analysis_credits': 5,
                        'last_interaction': datetime.datetime.now(),
                        'interaction_count': 1
                    })
                    logger.info(f"創建新用戶結果：{create_result}")
                except Exception as create_error:
                    logger.error(f"創建新用戶失敗：{create_error}")
                return 5
        
        except Exception as e:
            logger.error(f"获取用户分析次数失败，詳細錯誤: {str(e)}")
            import traceback
            logger.error(f"錯誤堆棧: {traceback.format_exc()}")
            return 0
    
    def decrease_user_analysis_credits(self, user_id: str) -> bool:
        """
        减少用户的分析次数
        
        Args:
            user_id: 用户ID
            
        Returns:
            操作是否成功
        """
        if not self.db:
            logger.error("Firebase未初始化，无法更新用户分析次数")
            return False
        
        try:
            # 获取当前用户分析次数
            current_credits = self.get_user_analysis_credits(user_id)
            
            if current_credits <= 0:
                return False
            
            # 减少分析次数
            self.db.collection('users').document(user_id).update({
                'analysis_credits': firestore.Increment(-1)
            })
            
            return True
        
        except Exception as e:
            logger.error(f"减少用户分析次数失败: {e}")
            return False
    
    def increase_user_analysis_credits(self, user_id: str, amount: int = 1) -> bool:
        """
        增加用户的分析次数
        
        Args:
            user_id: 用户ID
            amount: 增加的次数，默认为1
            
        Returns:
            操作是否成功
        """
        if not self.db:
            logger.error("Firebase未初始化，无法更新用户分析次数")
            return False
        
        try:
            # 增加分析次数
            self.db.collection('users').document(user_id).update({
                'analysis_credits': firestore.Increment(amount)
            })
            
            return True
        
        except Exception as e:
            logger.error(f"增加用户分析次数失败: {e}")
            return False
    
    def record_ad_view(self, user_id: str, ad_type: str) -> bool:
        """
        记录用户观看广告的历史
        
        Args:
            user_id: 用户ID
            ad_type: 广告类型
            
        Returns:
            操作是否成功
        """
        if not self.db:
            logger.error("Firebase未初始化，无法记录广告观看")
            return False
        
        try:
            # 记录广告观看历史
            self.db.collection('ad_views').add({
                'user_id': user_id,
                'ad_type': ad_type,
                'timestamp': datetime.datetime.now()
            })
            
            return True
        
        except Exception as e:
            logger.error(f"记录广告观看失败: {e}")
            return False 