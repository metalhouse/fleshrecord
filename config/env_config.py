# -*- coding: utf-8 -*-
"""
环境变量配置管理模块
用于安全地加载和验证环境变量
"""

import os
from typing import Optional, List
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

class EnvironmentConfig:
    """
    环境变量配置类
    负责从环境变量中读取和验证配置项
    """
    
    def __init__(self):
        """初始化配置并验证必需的环境变量"""
        self.validate_required_vars()
    
    # Firefly III 配置
    @property
    def firefly_api_url(self) -> str:
        return os.getenv('FIREFLY_API_URL', 'http://localhost/api/v1')
    
    @property
    def firefly_access_token(self) -> str:
        return os.getenv('FIREFLY_ACCESS_TOKEN', '')
    
    # Webhook 配置
    @property
    def webhook_secret(self) -> str:
        return os.getenv('WEBHOOK_SECRET', '')
    
    @property
    def webhook_secret_update(self) -> str:
        return os.getenv('WEBHOOK_SECRET_UPDATE', '')
    
    @property
    def webhook_url(self) -> str:
        return os.getenv('WEBHOOK_URL', '')
    
    # Flask 配置
    @property
    def flask_env(self) -> str:
        return os.getenv('FLASK_ENV', 'production')
    
    @property
    def debug(self) -> bool:
        return os.getenv('DEBUG', 'false').lower() in ('true', '1', 'yes', 'on')
    
    @property
    def secret_key(self) -> str:
        return os.getenv('SECRET_KEY', 'default-secret-key-change-me')
    
    # 速率限制配置
    @property
    def rate_limit_storage_uri(self) -> str:
        return os.getenv('RATE_LIMIT_STORAGE_URI', 'memory://')
    
    @property
    def rate_limit_default(self) -> str:
        return os.getenv('RATE_LIMIT_DEFAULT', '100 per hour')
        
    @property
    def rate_limit_webhook(self) -> str:
        return os.getenv('RATE_LIMIT_WEBHOOK', '20 per minute')
    
    # 日志配置
    @property
    def log_level(self) -> str:
        return os.getenv('LOG_LEVEL', 'INFO')
    
    @property
    def log_file(self) -> str:
        return os.getenv('LOG_FILE', 'log/file.log')
    
    # 服务器配置
    @property
    def host(self) -> str:
        return os.getenv('HOST', '0.0.0.0')
    
    @property
    def port(self) -> int:
        return int(os.getenv('PORT', '9012'))
    
    def get_required_vars(self) -> List[str]:
        """返回必需的环境变量列表"""
        return [
            'FIREFLY_ACCESS_TOKEN',
            'WEBHOOK_SECRET'
        ]
    
    def validate_required_vars(self) -> None:
        """
        验证必需的环境变量是否已设置
        如果缺少必需的变量，抛出 ValueError
        """
        required_vars = self.get_required_vars()
        missing_vars = []
        
        for var in required_vars:
            value = os.getenv(var)
            if not value or value.strip() == '':
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(
                f"缺少必需的环境变量: {', '.join(missing_vars)}\n"
                f"请参考 .env.example 文件进行配置"
            )
    
    def get_config_dict(self) -> dict:
        """返回所有配置的字典形式（隐藏敏感信息）"""
        return {
            'firefly_api_url': self.firefly_api_url,
            'firefly_access_token': '***隐藏***' if self.firefly_access_token else '未设置',
            'webhook_secret': '***隐藏***' if self.webhook_secret else '未设置',
            'webhook_url': self.webhook_url,
            'flask_env': self.flask_env,
            'debug': self.debug,
            'rate_limit_storage_uri': self.rate_limit_storage_uri,
            'rate_limit_default': self.rate_limit_default,
            'log_level': self.log_level,
            'log_file': self.log_file,
            'host': self.host,
            'port': self.port,
        }

# 创建全局配置实例
env_config = EnvironmentConfig()