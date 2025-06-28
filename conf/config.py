# -*- coding: utf-8 -*-
"""
配置文件
包含Flask应用的所有配置参数
现在使用环境变量来管理敏感信息
"""

import os
import sys

# 添加 config 目录到 Python 路径
config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
sys.path.insert(0, config_dir)

try:
    from env_config import env_config
except (ImportError, ValueError):
    env_config = None  # 静默忽略环境配置缺失，使用用户配置优先

class Config:
    """Flask应用配置类 - 基于环境变量"""
    
    # 初始化环境配置
    DEBUG = env_config.debug if env_config else True
    SECRET_KEY = env_config.secret_key if env_config else 'default-secret-key-change-me'
    
    # Firefly III API配置
    FIREFLY_API_URL = env_config.firefly_api_url if env_config else "http://localhost/api/v1"
    FIREFLY_ACCESS_TOKEN = ""  # 由用户配置提供
    
    # Webhook配置
    WEBHOOK_SECRET = ""  # 由用户配置提供
    WEBHOOK_SECRET_UPDATE = env_config.webhook_secret_update if env_config else ""
    WEBHOOK_URL = env_config.webhook_url if env_config else ""
    
    # 速率限制配置
    RATELIMIT_STORAGE_URI = env_config.rate_limit_storage_uri if env_config else "memory://"
    RATELIMIT_DEFAULT = env_config.rate_limit_default if env_config else "100 per hour"
    RATE_LIMIT_WEBHOOK = env_config.rate_limit_webhook if env_config else "20 per minute"
    
    # 日志配置
    LOG_LEVEL = env_config.log_level if env_config else "INFO"
    LOG_FILE = env_config.log_file if env_config else "log/file.log"
    
    # 服务器配置
    HOST = env_config.host if env_config else "0.0.0.0"
    PORT = env_config.port if env_config else 9012

# 创建配置实例
config = Config()

