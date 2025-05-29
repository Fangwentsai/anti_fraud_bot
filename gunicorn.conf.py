#!/usr/bin/env python3
"""
Gunicorn 配置文件
用於生產環境的 WSGI 伺服器配置
"""

import os
import multiprocessing

# 伺服器設定
port = os.environ.get('PORT', 8080)
bind = f"0.0.0.0:{port}"
# 減少 worker 數量以加快啟動速度（免費方案資源有限）
workers = min(multiprocessing.cpu_count() + 1, 2)  # 最多 2 個 worker
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# 超時設定 - 針對冷啟動優化
timeout = 60  # 增加到 60 秒，給冷啟動更多時間
keepalive = 2
graceful_timeout = 30

# 日誌設定
accesslog = "-"  # 輸出到 stdout
errorlog = "-"   # 輸出到 stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 進程設定
preload_app = True  # 預載入應用程式，減少記憶體使用
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# 安全設定
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# SSL 設定（如果需要）
# keyfile = None
# certfile = None

# 啟動優化
max_worker_memory = 200  # 限制 worker 記憶體使用（MB）

def when_ready(server):
    """伺服器準備就緒時的回調"""
    server.log.info(f"🚀 Gunicorn 伺服器已準備就緒，監聽端口: {port}")
    server.log.info(f"🔧 Workers: {workers}, 連接數: {worker_connections}")

def worker_int(worker):
    """Worker 被中斷時的回調"""
    worker.log.info(f"⚠️ Worker {worker.pid} 收到中斷信號")

def pre_fork(server, worker):
    """Fork worker 前的回調"""
    server.log.info(f"🔄 Worker {worker.pid} 即將啟動")

def post_fork(server, worker):
    """Fork worker 後的回調"""
    server.log.info(f"✅ Worker {worker.pid} 已啟動")

def worker_abort(worker):
    """Worker 異常終止時的回調"""
    worker.log.error(f"❌ Worker {worker.pid} 異常終止") 