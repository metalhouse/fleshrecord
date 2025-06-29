#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试webhook发送功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.user_config import UserConfigManager
from handlers.notification_handler import NotificationHandler
from flask import Flask

# 创建Flask应用用于日志
app = Flask(__name__)
app.config['TESTING'] = True

def test_webhook_send():
    """测试webhook发送"""
    with app.app_context():
        # 获取用户配置
        config_manager = UserConfigManager("data/users")
        user_config = config_manager.get_user_config("metalhouse")
        
        if not user_config:
            print("未找到metalhouse用户配置")
            return False
            
        print(f"找到用户配置，webhook_url: {user_config.webhook_url}")
        
        # 创建notification handler
        notification_handler = NotificationHandler(user_config)
        
        # 测试发送消息
        test_message = "测试webhook消息发送功能"
        result = notification_handler.send_webhook_message(test_message)
        
        if result:
            print("Webhook消息发送成功")
        else:
            print("Webhook消息发送失败")
            
        return result

if __name__ == "__main__":
    success = test_webhook_send()
    sys.exit(0 if success else 1)