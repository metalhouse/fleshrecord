#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置每日财务报告定时任务
"""

import logging
import sys
from pathlib import Path
from models.user_config import UserConfig, ReportConfig, user_config_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def setup_daily_report_schedule(user_id: str, daily_time: str = "23:00"):
    """
    为指定用户设置每日财务报告定时任务
    
    Args:
        user_id: 用户ID
        daily_time: 每日报告时间，格式：HH:MM，默认23:00（晚上11点）
    """
    try:
        logger.info(f"开始为用户 {user_id} 设置每日财务报告...")
        
        # 1. 获取用户配置
        user_config = user_config_manager.get_user_config(user_id)
        if not user_config:
            logger.error(f"找不到用户 {user_id} 的配置文件")
            return False
        
        # 2. 验证用户配置是否完整
        if not user_config.dify_config or not user_config.dify_config.enabled:
            logger.error(f"用户 {user_id} 的Dify配置未启用")
            return False
            
        if not user_config.webhook_url:
            logger.error(f"用户 {user_id} 缺少微信webhook配置")
            return False
        
        # 3. 创建或更新报告配置
        if not user_config.report_config:
            user_config.report_config = ReportConfig()
            logger.info("创建新的报告配置")
        
        # 设置日报配置
        user_config.report_config.daily_enabled = True
        user_config.report_config.daily_time = daily_time
        user_config.report_config.daily_prompt = "请生成今日财务日报，包括支出收入情况和预算执行情况"
        
        # 可以选择性关闭其他报告（用户可以后续修改）
        logger.info(f"设置每日报告时间为: {daily_time}")
        
        # 4. 保存配置
        success = user_config_manager.save_user_config(user_config)
        if success:
            logger.info(f"✅ 成功为用户 {user_id} 设置每日财务报告定时任务")
            logger.info(f"📅 每天 {daily_time} 将自动生成并发送财务日报到微信")
            return True
        else:
            logger.error(f"保存用户配置失败")
            return False
            
    except Exception as e:
        logger.error(f"设置定时任务时出错: {e}")
        return False

def show_schedule_status(user_id: str):
    """
    显示用户的定时报告设置状态
    """
    try:
        user_config = user_config_manager.get_user_config(user_id)
        if not user_config:
            print(f"❌ 找不到用户 {user_id} 的配置")
            return
        
        print(f"\n📊 用户 {user_id} 的定时报告配置:")
        print("="*50)
        
        if not user_config.report_config:
            print("❌ 未配置任何定时报告")
            return
            
        rc = user_config.report_config
        
        # 日报状态
        status = "✅ 已启用" if rc.daily_enabled else "❌ 未启用"
        print(f"📅 每日报告: {status}")
        if rc.daily_enabled:
            print(f"   ⏰ 发送时间: 每天 {rc.daily_time}")
        
        # 周报状态
        status = "✅ 已启用" if rc.weekly_enabled else "❌ 未启用"
        print(f"📈 每周报告: {status}")
        if rc.weekly_enabled:
            weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            day_name = weekdays[rc.weekly_day - 1]
            print(f"   ⏰ 发送时间: 每{day_name} {rc.weekly_time}")
        
        # 月报状态
        status = "✅ 已启用" if rc.monthly_enabled else "❌ 未启用"
        print(f"📋 每月报告: {status}")
        if rc.monthly_enabled:
            print(f"   ⏰ 发送时间: 每月{rc.monthly_day}号 {rc.monthly_time}")
        
        # 年报状态
        status = "✅ 已启用" if rc.yearly_enabled else "❌ 未启用"
        print(f"📊 每年报告: {status}")
        if rc.yearly_enabled:
            print(f"   ⏰ 发送时间: 每年{rc.yearly_month}月{rc.yearly_day}号 {rc.yearly_time}")
            
        print("="*50)
        
    except Exception as e:
        logger.error(f"查看配置状态时出错: {e}")

def main():
    """
    主函数
    """
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python setup_daily_report.py <用户ID> [时间]")
        print("  python setup_daily_report.py status <用户ID>")
        print("")
        print("示例:")
        print("  python setup_daily_report.py metalhouse 23:00")
        print("  python setup_daily_report.py status metalhouse")
        return
    
    command = sys.argv[1]
    
    if command == "status":
        if len(sys.argv) < 3:
            print("请指定用户ID")
            return
        user_id = sys.argv[2]
        show_schedule_status(user_id)
    else:
        user_id = command
        daily_time = sys.argv[2] if len(sys.argv) > 2 else "23:00"
        
        # 验证时间格式
        try:
            hour, minute = map(int, daily_time.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except (ValueError, IndexError):
            print(f"❌ 时间格式错误: {daily_time}")
            print("请使用HH:MM格式，例如: 23:00")
            return
        
        success = setup_daily_report_schedule(user_id, daily_time)
        if success:
            print(f"\n🎉 设置成功! 每天晚上 {daily_time} 将自动发送财务日报")
            print("\n💡 提示:")
            print("1. 确保Flask应用正在运行以执行定时任务")
            print("2. 可以运行 'python app.py' 启动应用和定时服务")
            print(f"3. 查看状态: python setup_daily_report.py status {user_id}")
        else:
            print("❌ 设置失败，请检查日志了解详情")

if __name__ == "__main__":
    main()