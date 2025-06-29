#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动带有定时任务的FleshRecord应用
"""

import logging
import signal
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app import app, scheduler_service
from conf.config import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    """
    处理停止信号
    """
    logger.info("收到停止信号，正在关闭服务...")
    scheduler_service.stop()
    logger.info("定时任务服务已停止")
    sys.exit(0)

def main():
    """
    启动应用和定时任务服务
    """
    try:
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("🚀 启动FleshRecord应用...")
        logger.info(f"📍 服务地址: http://{config.HOST}:{config.PORT}")
        logger.info("⏰ 定时报告服务已启用")
        logger.info("📱 每日财务报告将在设定时间自动发送")
        logger.info("")
        logger.info("💡 提示:")
        logger.info("- 使用 Ctrl+C 停止服务")
        logger.info("- 查看定时任务状态: python setup_daily_report.py status <用户ID>")
        logger.info("- 修改报告时间: python setup_daily_report.py <用户ID> <新时间>")
        logger.info("="*60)
        
        # 启动定时任务调度器
        scheduler_service.start()
        logger.info("✅ 定时报告服务已启动")
        
        # 启动Flask应用
        app.run(
            host=config.HOST,
            port=config.PORT,
            debug=config.DEBUG
        )
        
    except KeyboardInterrupt:
        logger.info("\n用户中断，正在停止应用...")
        scheduler_service.stop()
        logger.info("应用已停止")
    except Exception as e:
        logger.error(f"启动应用时出错: {e}")
        scheduler_service.stop()
        sys.exit(1)

if __name__ == '__main__':
    main()