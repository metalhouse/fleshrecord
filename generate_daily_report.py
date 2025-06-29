#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成每日财务报告脚本
调用Dify工作流生成报告并发送到微信
"""

import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from handlers.notification_handler import NotificationHandler
from services.dify_service import DifyService
from utils.config_manager import ConfigManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def generate_and_send_daily_report(user_id: str = "metalhouse"):
    """生成并发送每日财务报告
    
    Args:
        user_id: 用户ID，默认为metalhouse
    
    Returns:
        bool: 是否成功生成并发送报告
    """
    try:
        logger.info("=== 开始生成每日财务报告 ===")
        
        # 1. 加载用户配置
        config_manager = ConfigManager()
        user_config = config_manager.config_manager.get_user_config(user_id)
        
        if not user_config:
            logger.error(f"无法加载用户配置: {user_id}")
            return False
        
        logger.info(f"用户配置加载成功: {user_config.user_id}")
        
        # 2. 初始化Dify服务
        dify_service = DifyService(user_config.dify_config.api_key)
        logger.info("Dify服务初始化成功")
        
        # 3. 调用Dify工作流生成报告
        logger.info("开始调用Dify工作流生成消费日报...")
        
        # 直接使用run_workflow方法，输入"消费日报"
        # 从用户配置中获取workflow_id
        workflow_id = user_config.dify_config.workflow_id
        response = dify_service.run_workflow(workflow_id, {
            "query": "消费日报"
        })
        
        if not response or 'data' not in response:
            logger.error("Dify工作流调用失败或返回数据无效")
            return False
        
        # 4. 提取报告内容
        logger.info(f"Dify响应数据: {response}")
        report_content = response.get('message', '')
        if not report_content:
            logger.error(f"Dify返回的报告内容为空，完整响应: {response.get('data', {})}")
            return False
        
        logger.info(f"Dify返回消息长度: {len(report_content)} 字符")
        logger.info(f"Dify返回消息预览: {report_content[:200]}...")
        
        # 4. 通过NotificationHandler发送到微信
        logger.info("开始发送微信通知...")
        notification_handler = NotificationHandler(user_config)
        
        # 构造报告消息
        report_message = f"📊 消费日报\n\n{report_content}"
        
        # 发送微信通知
        send_result = notification_handler.send_webhook_message(report_message)
        
        if send_result:
            logger.info("✅ 消费日报生成并发送成功!")
            return True
        else:
            logger.error("❌ 消费日报发送失败")
            return False
            
    except Exception as e:
        logger.error(f"生成报告过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='生成每日财务报告')
    parser.add_argument('--user', '-u', default='metalhouse', help='用户ID (默认: metalhouse)')
    
    args = parser.parse_args()
    
    success = generate_and_send_daily_report(args.user)
    
    if success:
        logger.info("🎉 每日财务报告生成完成!")
    else:
        logger.error("💥 每日财务报告生成失败!")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()