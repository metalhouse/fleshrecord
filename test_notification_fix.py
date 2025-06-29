#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的通知功能
"""

import os
import sys
import json
import logging
from flask import Flask

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from handlers.notification_handler import NotificationHandler
from models.user_config import UserConfig
from handlers.transaction_handler import TransactionHandler
from services.firefly_service import FireflyService

def test_notification_integration():
    """测试通知集成功能"""
    print("开始测试通知集成功能...")
    
    try:
        # 读取用户配置
        with open('data/users/metalhouse.json', 'r', encoding='utf-8') as f:
            user_data = json.load(f)
        
        # 添加缺失的user_id字段
        user_data['user_id'] = 'metalhouse'
        
        # 创建用户配置对象
        user_config = UserConfig(**user_data)
        print(f"用户配置加载成功: webhook_url = {user_config.webhook_url}")
        
        # 测试NotificationHandler
        notification_handler = NotificationHandler(user_config)
        print("NotificationHandler 创建成功")
        
        # 测试发送简单消息
        test_message = "测试消息：通知功能修复验证"
        result = notification_handler.send_webhook_message(test_message)
        print(f"简单消息发送结果: {result}")
        
        # 测试发送交易通知
        transaction_info = {
            'trigger': 'Manual',
            'description': '测试交易',
            'amount': 100.0,
            'category': '测试分类',
            'budget': '测试预算'
        }
        
        result2 = notification_handler.send_transaction_notification(transaction_info)
        print(f"交易通知发送结果: {result2}")
        
        print("\n测试完成！")
        return result and result2
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_notification_integration()
    if success:
        print("✅ 通知功能测试通过")
    else:
        print("❌ 通知功能测试失败")
    
    sys.exit(0 if success else 1)