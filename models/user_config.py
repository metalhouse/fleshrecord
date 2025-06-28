# -*- coding: utf-8 -*-
"""
用户配置模型
定义多用户环境下的用户特定配置
"""

import json
import os
from typing import Dict, Optional, Any
from pydantic import BaseModel, field_validator, ValidationError
from pathlib import Path

class UserConfig(BaseModel):
    """用户配置模型"""
    user_id: str
    firefly_access_token: str
    webhook_url: str
    webhook_secret: str
    webhook_secret_update: str
    # 可选的用户特定配置
    firefly_api_url: Optional[str] = None  # 默认为全局配置
    notification_enabled: bool = True
    language: str = "zh"

    @field_validator('firefly_access_token')
    def validate_token(cls, v):
        if not v or not v.strip():
            raise ValueError("访问令牌不能为空")
        # 移除可能的Bearer前缀
        return v.replace('Bearer ', '').strip()


class UserConfigManager:
    """用户配置管理器"""
    def __init__(self, config_dir: str = "data/users"):
        self.config_dir = Path(config_dir)
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def get_user_config(self, user_id: str) -> Optional[UserConfig]:
        """获取指定用户的配置"""
        config_file = self.config_dir / f"{user_id}.json"
        if not config_file.exists():
            return None

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            # 添加user_id到配置数据
            config_data['user_id'] = user_id
            return UserConfig(**config_data)
        except (json.JSONDecodeError, ValidationError, KeyError) as e:
            from flask import current_app as app
            app.logger.error(f"加载用户配置失败 (user_id={user_id}): {str(e)}")
            return None

    def save_user_config(self, config: UserConfig) -> bool:
        """保存用户配置"""
        try:
            config_file = self.config_dir / f"{config.user_id}.json"
            # 转换为字典并排除user_id（文件名已包含）
            config_dict = config.model_dump(exclude={'user_id'})
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            from flask import current_app as app
            app.logger.error(f"保存用户配置失败 (user_id={config.user_id}): {str(e)}")
            return False

    def list_users(self) -> Dict[str, str]:
        """列出所有用户配置"""
        users = {}
        for file in self.config_dir.glob("*.json"):
            user_id = file.stem
            users[user_id] = str(file)
        return users

    def delete_user_config(self, user_id: str) -> bool:
        """删除用户配置"""
        config_file = self.config_dir / f"{user_id}.json"
        if config_file.exists():
            try:
                config_file.unlink()
                return True
            except Exception as e:
                from flask import current_app as app
                app.logger.error(f"删除用户配置失败 (user_id={user_id}): {str(e)}")
        return False


# 创建全局用户配置管理器实例
user_config_manager = UserConfigManager()