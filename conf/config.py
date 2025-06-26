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
except (ImportError, ValueError) as e:
    print(f"警告: 无法导入环境配置模块 ({e})，使用默认配置")
    env_config = None

class Config:
    """Flask应用配置类 - 基于环境变量"""
    
    def __init__(self):
        if env_config is None:
            print("警告: 环境配置未加载，请检查 .env 文件和环境变量设置")
    
    # Flask基础配置
    @property
    def DEBUG(self):
        return env_config.debug if env_config else True
    
    @property
    def SECRET_KEY(self):
        return env_config.secret_key if env_config else 'default-secret-key-change-me'
    
    # Firefly III API配置
    @property
    def FIREFLY_API_URL(self):
        return env_config.firefly_api_url if env_config else "http://localhost/api/v1"
    
    @property
    def FIREFLY_ACCESS_TOKEN(self):
        return env_config.firefly_access_token if env_config else ""
    
    # Webhook配置
    @property
    def WEBHOOK_SECRET(self):
        return env_config.webhook_secret if env_config else ""
    
    @property
    def WEBHOOK_SECRET_UPDATE(self):
        return env_config.webhook_secret_update if env_config else ""
    
    @property
    def WEBHOOK_URL(self):
        return env_config.webhook_url if env_config else ""
    
    # 速率限制配置
    @property
    def RATELIMIT_STORAGE_URI(self):
        return env_config.rate_limit_storage_uri if env_config else "memory://"
    
    @property
    def RATELIMIT_DEFAULT(self):
        return env_config.rate_limit_default if env_config else "100 per hour"
        
    @property
    def RATE_LIMIT_WEBHOOK(self):
        return env_config.rate_limit_webhook if env_config else "20 per minute"
    
    # 日志配置
    @property
    def LOG_LEVEL(self):
        return env_config.log_level if env_config else "INFO"
    
    @property
    def LOG_FILE(self):
        return env_config.log_file if env_config else "log/file.log"
    
    # 服务器配置
    @property
    def HOST(self):
        return env_config.host if env_config else "0.0.0.0"
    
    @property
    def PORT(self):
        return env_config.port if env_config else 9012

# 创建配置实例
config = Config()

