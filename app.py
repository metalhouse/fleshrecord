import hashlib
import hmac
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Tuple, Union

from flask import Flask, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from conf.config import config
from services.firefly_service import FireflyService
from handlers.budget_handler import BudgetHandler
from handlers.notification_handler import NotificationHandler
from handlers.webhook_handler import WebhookHandler
from handlers.transaction_handler import TransactionHandler
from handlers.dify_handler import DifyHandler
from utils.retry_decorator import track_performance

from version import __version__
app = Flask(__name__)
# 从配置文件中加载配置
basedir = os.path.abspath(os.path.dirname(__file__))
# 修改配置加载方式
app.config.from_object('conf.config.Config')  # 使用Flask的标准配置加载方式
app.config.from_pyfile(os.path.join(basedir, 'conf/config.py'))  # 修正配置文件路径

# 设置日志配置
LOG_FILE: str = config.LOG_FILE or 'log/file.log'  # 确保有默认值
LOG_LEVEL: int = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
LOG_FORMAT: str = '%(asctime)s [%(levelname)s] %(message)s'

# 确保日志目录存在
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# 配置日志处理器
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding='utf-8')
    ]
)

# 设置Flask应用的日志级别
app.logger.setLevel(LOG_LEVEL)
    app.logger.info(f"Starting Flask application v{__version__}")


# 获取必需的配置项并进行验证
url = app.config.get('WEBHOOK_URL')
headers = {"Content-Type": "application/json"}
FIREFLY_ACCESS_TOKEN: str = app.config.get('FIREFLY_ACCESS_TOKEN')
FIREFLY_API_URL: str = app.config.get('FIREFLY_API_URL')

# 确保access_token不包含重复的'Bearer'前缀
if FIREFLY_ACCESS_TOKEN:
    clean_token = str(FIREFLY_ACCESS_TOKEN).replace('Bearer ', '').strip()
    firefly_headers = {
        'Authorization': f'Bearer {clean_token}',
        'Content-Type': 'application/json'
    }
else:
    app.logger.error("环境变量 FIREFLY_ACCESS_TOKEN 未设置")
    raise ValueError("FIREFLY_ACCESS_TOKEN未在配置文件中设置")

# 配置速率限制
limiter: Limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[config.RATELIMIT_DEFAULT],
    storage_uri=config.RATELIMIT_STORAGE_URI,
    strategy='fixed-window',
    headers_enabled=True
)

# 初始化服务层
firefly_service: FireflyService = FireflyService(config.FIREFLY_API_URL, config.FIREFLY_ACCESS_TOKEN, app.logger)

# 初始化处理器
budget_handler: BudgetHandler = BudgetHandler(firefly_service, config)
notification_handler: NotificationHandler = NotificationHandler(config)
webhook_handler: WebhookHandler = WebhookHandler(firefly_service, config)
transaction_handler: TransactionHandler = TransactionHandler(firefly_service)
dify_handler: DifyHandler = DifyHandler(firefly_service, budget_handler)

def verify_signature(payload: bytes, signature_header: str) -> bool:
    """
    验证webhook签名
    
    Args:
        payload: 请求载荷
        signature_header: 签名头
        
    Returns:
        bool: 签名验证结果
    """
    if not signature_header:
        app.logger.error("缺少Signature请求头")
        return False
    
    # 解析签名组件
    signature_parts = dict(part.split('=') for part in signature_header.split(','))
    if 'v1' not in signature_parts or 't' not in signature_parts:
        app.logger.error("签名格式不正确，缺少必要组件")
        return False
    
    received_signature = signature_parts['v1']
    timestamp = signature_parts['t']
    
    # 将时间戳与请求体组合后计算签名
    signed_payload = f'{timestamp}.'.encode('utf-8') + payload
    computed_signature = hmac.new(
        key=config.WEBHOOK_SECRET.encode('utf-8'),
        msg=signed_payload,
        digestmod=hashlib.sha3_256  # 修正为SHA-3 256位
    ).hexdigest()
    computed_signature_update = hmac.new(
        key=config.WEBHOOK_SECRET_UPDATE.encode('utf-8'),
        msg=signed_payload,
        digestmod=hashlib.sha3_256  # 修正为SHA-3 256位
    ).hexdigest()
    if hmac.compare_digest(computed_signature, received_signature) or hmac.compare_digest(computed_signature_update, received_signature):
        return True
    else:
        return False



@app.route('/webhook', methods=['POST'])
@limiter.limit(config.RATE_LIMIT_WEBHOOK)
@track_performance('webhook')
def webhook() -> Tuple[Union[str, Dict[str, Any]], int]:
    """处理webhook请求
    
    Returns:
        Tuple[Union[str, Dict[str, Any]], int]: (响应内容, 状态码)
    """
    return webhook_handler.handle_webhook_request()

# Note: call_curl and get_firefly_budgets functions have been moved to their respective handler classes

@app.route('/budgets', methods=['GET'])
@track_performance('budgets')
def get_budgets() -> Tuple[Dict[str, Any], int]:
    """
    获取预算信息API endpoint
    
    Returns:
        Tuple[Dict[str, Any], int]: (响应内容, 状态码)
    """
    return budget_handler.get_budgets_endpoint()

@app.route('/add_transaction', methods=['POST'])
@track_performance('add_transaction')
def add_transaction() -> Tuple[Dict[str, Any], int]:
    """
    添加交易API endpoint
    
    Returns:
        Tuple[Dict[str, Any], int]: (响应内容, 状态码)
    """
    return transaction_handler.add_transaction_endpoint()

@app.route("/dify_webhook", methods=["POST"])
@track_performance("dify_webhook")
def dify_webhook() -> Tuple[Dict[str, Any], int]:
    """
    处理来自Dify智能助手的webhook请求
    
    Returns:
        Tuple[Dict[str, Any], int]: (响应内容, 状态码)
    """
    return dify_handler.handle_dify_webhook()

if __name__ == '__main__':
    app.run(
        host=config.HOST, 
        port=config.PORT,
        debug=config.DEBUG
    )
