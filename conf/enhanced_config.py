# conf/enhanced_config.py
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class APIConfig:
    """API相关配置"""
    timeout: int = 10
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_per_minute: int = 60

@dataclass
class CacheConfig:
    """缓存配置"""
    enabled: bool = True
    ttl_seconds: int = 300  # 5分钟
    max_size: int = 1000

@dataclass
class AppConfig:
    """应用配置"""
    firefly_api_url: str
    firefly_access_token: str
    webhook_secret: str
    api: APIConfig = APIConfig()
    cache: CacheConfig = CacheConfig()
    
    @classmethod
    def from_env(cls):
        return cls(
            firefly_api_url=os.getenv('FIREFLY_API_URL'),
            firefly_access_token=os.getenv('FIREFLY_ACCESS_TOKEN'),
            webhook_secret=os.getenv('WEBHOOK_SECRET')
        )