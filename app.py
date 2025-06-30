import hashlib
import hmac
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Tuple, Union

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from conf.config import config
from services.firefly_service import FireflyService
from handlers.budget_handler import BudgetHandler
from handlers.notification_handler import NotificationHandler
from handlers.webhook_handler import WebhookHandler
from handlers.transaction_handler import TransactionHandler
from handlers.dify_handler import DifyHandler
from services.scheduler_service import scheduler_service
from utils.retry_decorator import track_performance
from utils.response_builder import APIResponseBuilder

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

# 强制全局DEBUG，确保所有debug日志输出
logging.getLogger().setLevel(logging.DEBUG)

# 添加Werkzeug日志过滤器以屏蔽敏感参数
from werkzeug._internal import _log
import re
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode

class SensitiveDataLogFilter(logging.Filter):
    """过滤日志中的敏感数据"""
    SENSITIVE_PARAMS = {'authorization', 'token', 'secret', 'key', 'password', 'access_token', 'api_key', 'firefly_access_token'}
    HEADER_PATTERN = re.compile(r'(Authorization: Bearer) [^\r\n]+', re.IGNORECASE)
    # JWT Token 正则表达式（匹配eyJ开头的token）
    JWT_TOKEN_PATTERN = re.compile(r'eyJ[A-Za-z0-9_.-]{20,}', re.IGNORECASE)
    # 补充正则表达式用于捕获URL参数和表单数据中的敏感信息
    PARAM_REGEX = re.compile(r'((?:["\']?%s["\']?\s*[:=]\s*)|(?:%s\s*=)|(?:/\s*%s\s*/))([^&"\'\'\s]+)' % ('|'.join(SENSITIVE_PARAMS), '|'.join(SENSITIVE_PARAMS), '|'.join(SENSITIVE_PARAMS)), re.IGNORECASE)

    def _filter_query_params(self, url):
        """使用URL解析过滤敏感查询参数，支持完整URL和路径+查询字符串格式"""
        # 处理仅包含路径和查询参数的情况
        if not urlparse(url).scheme:
            # 添加虚拟域名以便正确解析
            url = f"http://dummy.com{url}"
            parsed = urlparse(url)
            is_path_only = True
        else:
            parsed = urlparse(url)
            is_path_only = False

        if not parsed.query:
            return parsed.path if is_path_only else url

        # 解析查询参数
        query_params = parse_qs(parsed.query)
        # 过滤敏感参数（不区分大小写）
        for key in list(query_params.keys()):
            if key.lower() in self.SENSITIVE_PARAMS:
                query_params[key] = '[FILTERED]'
        # 重建查询字符串
        filtered_query = urlencode(query_params, doseq=True)
        # 重建URL
        filtered_url = urlunparse(parsed._replace(query=filtered_query))

        # 如果是路径+查询字符串格式，返回过滤后的路径部分
        return urlparse(filtered_url).path + ('?' + filtered_query if filtered_query else '') if is_path_only else filtered_url

    def filter(self, record):
        # 处理Werkzeug访问日志中的URL参数
        if record.name == 'werkzeug' and record.args:
            # 查找包含请求行的参数（通常是第三个参数，格式如"GET /path?params HTTP/1.1"）
            for i, arg in enumerate(record.args):
                # 处理可能被引号包裹的请求行（如"GET /path HTTP/1.1"）
                # 先移除ANSI颜色码
                clean_arg = re.sub(r'\x1b\[[0-9;]*m', '', str(arg))
                stripped_arg = clean_arg.strip('"\'')
                if isinstance(arg, str) and ' ' in stripped_arg and stripped_arg.split()[0] in ['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS']:
                    request_line = stripped_arg  # 使用去掉引号的版本进行解析
                    parts = request_line.split()
                    if len(parts) >= 2:
                        method, path, *protocol = parts
                        filtered_path = self._filter_query_params(path)
                        new_request_line = f"{method} {filtered_path} {' '.join(protocol)}"
                        # 过滤JWT tokens (eyJ开头的长token)
                        new_request_line = self.JWT_TOKEN_PATTERN.sub('[JWT_TOKEN_FILTERED]', new_request_line)
                        # 应用正则表达式过滤剩余的敏感参数
                        new_request_line = self.PARAM_REGEX.sub(r'\1[FILTERED]', new_request_line)
                        # 保持原有的ANSI颜色码和引号格式
                        if '\x1b[31m\x1b[1m' in str(arg):  # 红色粗体
                            new_request_line = f'\x1b[31m\x1b[1m{new_request_line}\x1b[0m'
                        elif arg.startswith('"') and arg.endswith('"'):
                            new_request_line = f'"{new_request_line}"'
                        elif arg.startswith("'") and arg.endswith("'"):
                            new_request_line = f"'{new_request_line}'"
                        # 更新参数元组
                        record.args = record.args[:i] + (new_request_line,) + record.args[i+1:]
                    break
        
        # 处理常规日志消息
        if hasattr(record, 'message'):
            # 过滤URL中的敏感参数
            record.message = self._filter_query_params(record.message)
            # 过滤请求头中的敏感信息
            record.message = self.HEADER_PATTERN.sub(r'\1 [FILTERED]', record.message)
            # 过滤JWT tokens (eyJ开头的长token)
            record.message = self.JWT_TOKEN_PATTERN.sub('[JWT_TOKEN_FILTERED]', record.message)
            # 使用正则表达式补充过滤其他形式的敏感参数
            record.message = self.PARAM_REGEX.sub(r'\1[FILTERED]', record.message)
            record.args = ()
        return True

# 获取Werkzeug的日志记录器并添加过滤器
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addFilter(SensitiveDataLogFilter())

# 获取requests库的日志记录器并添加过滤器
requests_logger = logging.getLogger('requests')
requests_logger.addFilter(SensitiveDataLogFilter())

# 应用过滤器到根日志记录器以覆盖所有日志
root_logger = logging.getLogger()
root_logger.addFilter(SensitiveDataLogFilter())

# 过滤Flask自身的日志
app.logger.addFilter(SensitiveDataLogFilter())

# 设置Flask应用的日志级别
app.logger.setLevel(LOG_LEVEL)
app.logger.info(f"Starting Flask application v{__version__}")


# 获取必需的全局配置项并进行验证
FIREFLY_API_URL: str = app.config.get('FIREFLY_API_URL')
if not FIREFLY_API_URL:
    app.logger.error("环境变量 FIREFLY_API_URL 未设置")
    raise ValueError("FIREFLY_API_URL未在配置文件中设置")

# 配置速率限制
limiter: Limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[config.RATELIMIT_DEFAULT],
    storage_uri=config.RATELIMIT_STORAGE_URI,
    strategy='fixed-window',
    headers_enabled=True
)

# 导入用户配置管理器
from models.user_config import user_config_manager

# 初始化全局服务（基础配置）
_base_firefly_service: FireflyService = FireflyService(config.FIREFLY_API_URL, '', app.logger)

# 创建全局处理器（不含用户特定配置）
# Note: 全局budget_handler和dify_handler已移除，现在每个请求都会创建用户特定的handler

# 用户特定服务创建函数
def get_user_services(user_id: str):
    """获取用户特定的服务实例"""
    user_config = user_config_manager.get_user_config(user_id)
    if not user_config:
        return None, None, None

    # 创建用户特定的Firefly服务
    firefly_service = FireflyService(
        api_url=user_config.firefly_api_url or config.FIREFLY_API_URL,
        access_token=user_config.firefly_access_token,
        logger=app.logger
    )

    # 创建用户特定的处理器
    notification_handler = NotificationHandler(user_config)
    webhook_handler = WebhookHandler(firefly_service, user_config)
    transaction_handler = TransactionHandler(firefly_service, notification_handler)

    return firefly_service, notification_handler, webhook_handler, transaction_handler

@app.route('/webhook', methods=['POST'])
@limiter.limit(config.RATE_LIMIT_WEBHOOK)
@track_performance('webhook')
def webhook() -> Tuple[Union[str, Dict[str, Any]], int]:
    """处理webhook请求，支持FireflyIII（Signature签名验证）和第三方服务（X-User-ID）
    
    Returns:
        Tuple[Union[str, Dict[str, Any]], int]: (响应内容, 状态码)
    """
    # 检查是否为FireflyIII webhook请求（通过Signature头判断）
    signature_header = request.headers.get('Signature')
    if signature_header:
        # 这是一个带有签名的请求，很可能是FireflyIII webhook
        # 需要找到匹配的用户配置来验证签名
        user_id = None
        
        # 遍历所有用户配置，找到能够验证此签名的用户
        for user_file in os.listdir('data/users'):
            if user_file.endswith('.json'):
                try:
                    potential_user_id = user_file[:-5]  # 移除 .json 后缀
                    _, _, webhook_handler, _ = get_user_services(potential_user_id)
                    
                    if webhook_handler:
                        # 尝试验证签名
                        raw_payload = request.get_data()
                        if webhook_handler.verify_signature(raw_payload, signature_header):
                            user_id = potential_user_id
                            break
                except Exception as e:
                    app.logger.error(f"尝试验证用户 {user_file} 的签名时失败: {e}")
                    continue
        
        if not user_id:
            app.logger.warning("无法验证Webhook签名")
            return jsonify(APIResponseBuilder.error_response("Invalid signature", 403)), 403
        
        # 获取已验证的用户服务
        _, _, webhook_handler, _ = get_user_services(user_id)
        
        # 处理FireflyIII webhook请求（已经验证过签名）
        return webhook_handler.process_webhook_event(skip_signature=True)
    
    # 非签名验证请求，使用X-User-ID验证
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        app.logger.warning("缺少X-User-ID请求头")
        return jsonify(APIResponseBuilder.error_response("X-User-ID header is required", 400)), 400
    
    # 获取用户特定服务
    _, _, webhook_handler, _ = get_user_services(user_id)
    if not webhook_handler:
        app.logger.error(f"用户配置不存在或无效: {user_id}")
        return jsonify(APIResponseBuilder.error_response("User configuration not found", 404)), 404
    
    return webhook_handler.handle_webhook_request()

@app.route('/firefly-webhook', methods=['POST'])
@limiter.limit(config.RATE_LIMIT_WEBHOOK)
@track_performance('firefly_webhook')
def firefly_webhook() -> Tuple[Union[str, Dict[str, Any]], int]:
    """处理FireFly III的webhook请求（通过Authorization Bearer token验证）
    
    Returns:
        Tuple[Union[str, Dict[str, Any]], int]: (响应内容, 状态码)
    """
    # 从Authorization请求头获取token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        app.logger.warning("缺少Authorization Bearer token")
        return jsonify(APIResponseBuilder.error_response("Authorization Bearer token is required", 401)), 401
    
    token = auth_header[7:]  # 移除 'Bearer ' 前缀
    
    # 根据token查找对应的用户
    user_id = None
    for user_file in os.listdir('data/users'):
        if user_file.endswith('.json'):
            try:
                with open(f'data/users/{user_file}', 'r', encoding='utf-8') as f:
                    user_data = json.load(f)
                    if user_data.get('firefly_access_token') == token:
                        user_id = user_file[:-5]  # 移除 .json 后缀
                        break
            except Exception as e:
                app.logger.error(f"读取用户配置文件 {user_file} 失败: {e}")
                continue
    
    if not user_id:
        app.logger.warning("无效的FireFly access token")
        return jsonify(APIResponseBuilder.error_response("Invalid token", 403)), 403
    
    # 获取用户特定服务
    _, _, webhook_handler, _ = get_user_services(user_id)
    if not webhook_handler:
        app.logger.error(f"用户配置不存在或无效: {user_id}")
        return jsonify(APIResponseBuilder.error_response("User configuration not found", 404)), 404
    
    # 调用webhook处理器，但跳过签名验证（FireFly III有自己的验证）
    return webhook_handler.handle_firefly_webhook_request()

# Note: call_curl and get_firefly_budgets functions have been moved to their respective handler classes

@app.route('/budgets', methods=['GET'])
@track_performance('budgets')
def get_budgets() -> Tuple[Dict[str, Any], int]:
    """
    获取预算信息API endpoint
    
    Returns:
        Tuple[Dict[str, Any], int]: (响应内容, 状态码)
    """
    # 从请求头获取用户ID
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        app.logger.warning("缺少X-User-ID请求头")
        return jsonify(APIResponseBuilder.error_response("X-User-ID header is required", 400)), 400
    
    # 获取用户配置
    user_config = user_config_manager.get_user_config(user_id)
    if not user_config:
        app.logger.error(f"用户配置不存在或无效: {user_id}")
        return jsonify(APIResponseBuilder.error_response("User configuration not found", 404)), 404
    
    # 创建用户特定的Firefly服务和Budget Handler
    firefly_service = FireflyService(
        api_url=user_config.firefly_api_url or config.FIREFLY_API_URL,
        access_token=user_config.firefly_access_token,
        logger=app.logger
    )
    user_budget_handler = BudgetHandler(config, firefly_service, user_config.model_dump())
    
    return user_budget_handler.get_budgets_endpoint()

@app.route('/add_transaction', methods=['POST'])
@track_performance('add_transaction')
def add_transaction() -> Tuple[Dict[str, Any], int]:
    """
    添加交易API endpoint
    
    Returns:
        Tuple[Dict[str, Any], int]: (响应内容, 状态码)
    """
    # 从请求头获取用户ID
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        app.logger.warning("缺少X-User-ID请求头")
        return jsonify(APIResponseBuilder.error_response("X-User-ID header is required", 400)), 400
    
    # 获取用户特定服务
    _, _, _, transaction_handler = get_user_services(user_id)
    if not transaction_handler:
        app.logger.error(f"用户配置不存在或无效: {user_id}")
        return jsonify(APIResponseBuilder.error_response("User configuration not found", 404)), 404
    
    return transaction_handler.add_transaction_endpoint()

@app.route("/dify_webhook", methods=["POST"])
@limiter.limit(config.RATE_LIMIT_WEBHOOK)
@track_performance("dify_webhook")
def dify_webhook() -> Tuple[Dict[str, Any], int]:
    """
    处理来自Dify智能助手的webhook请求
    
    Returns:
        Tuple[Dict[str, Any], int]: (响应内容, 状态码)
    """
    # 从请求头获取用户ID
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        app.logger.warning("缺少X-User-ID请求头")
        return jsonify(APIResponseBuilder.error_response("X-User-ID header is required", 400)), 400
    
    # 获取用户配置
    user_config = user_config_manager.get_user_config(user_id)
    if not user_config:
        app.logger.error(f"用户配置不存在或无效: {user_id}")
        return jsonify(APIResponseBuilder.error_response("User configuration not found", 404)), 404
    
    # 创建用户特定的Firefly服务和处理器
    firefly_service = FireflyService(
        api_url=user_config.firefly_api_url or config.FIREFLY_API_URL,
        access_token=user_config.firefly_access_token,
        logger=app.logger
    )
    user_budget_handler = BudgetHandler(config, firefly_service, user_config.dict())
    user_dify_handler = DifyHandler(firefly_service, user_budget_handler)
    
    return user_dify_handler.handle_dify_webhook()

if __name__ == '__main__':
    # 只在主进程启动定时任务调度器，避免多进程重复
    if not os.environ.get('WERKZEUG_RUN_MAIN') or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        scheduler_service.start()
        app.logger.info("定时报告服务已启动")
    try:
        app.run(
            host=config.HOST, 
            port=config.PORT,
            debug=config.DEBUG
        )
    except KeyboardInterrupt:
        app.logger.info("正在停止应用...")
        scheduler_service.stop()
        app.logger.info("应用已停止")
