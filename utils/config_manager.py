#!/usr/bin/env python3
"""
用户配置管理工具
用于设置 Dify API 配置和报告配置
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

# 添加项目路径到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.user_config import UserConfig, DifyConfig, ReportConfig, user_config_manager


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.config_manager = user_config_manager
    
    def list_users(self):
        """列出所有用户"""
        users = self.config_manager.list_users()
        if not users:
            print("没有找到用户配置文件")
            return
            
        print("\n现有用户:")
        print("-" * 40)
        for user_id, config_path in users.items():
            user_config = self.config_manager.get_user_config(user_id)
            dify_status = "已配置" if (user_config and user_config.dify_config and user_config.dify_config.enabled) else "未配置"
            report_status = "已配置" if (user_config and user_config.report_config) else "未配置"
            print(f"用户ID: {user_id}")
            print(f"  配置文件: {config_path}")
            print(f"  Dify状态: {dify_status}")
            print(f"  报告配置: {report_status}")
            print()
    
    def configure_dify(self, user_id: str, api_key: str, enabled: bool = True):
        """配置 Dify API"""
        user_config = self.config_manager.get_user_config(user_id)
        if not user_config:
            print(f"用户 {user_id} 不存在，请先创建基本配置")
            return False
            
        # 更新 Dify 配置
        user_config.dify_config = DifyConfig(
            api_key=api_key,
            enabled=enabled
        )
        
        # 保存配置
        if self.config_manager.save_user_config(user_config):
            print(f"成功配置用户 {user_id} 的 Dify API")
            return True
        else:
            print(f"保存用户 {user_id} 的 Dify 配置失败")
            return False
    
    def configure_reports(self, user_id: str, **kwargs):
        """配置报告设置"""
        user_config = self.config_manager.get_user_config(user_id)
        if not user_config:
            print(f"用户 {user_id} 不存在，请先创建基本配置")
            return False
            
        # 获取当前报告配置或创建默认配置
        current_report_config = user_config.report_config or ReportConfig()
        
        # 更新配置
        report_dict = current_report_config.model_dump()
        report_dict.update(kwargs)
        
        try:
            user_config.report_config = ReportConfig(**report_dict)
            
            # 保存配置
            if self.config_manager.save_user_config(user_config):
                print(f"成功配置用户 {user_id} 的报告设置")
                return True
            else:
                print(f"保存用户 {user_id} 的报告配置失败")
                return False
        except Exception as e:
            print(f"配置报告设置时出错: {e}")
            return False
    
    def show_user_config(self, user_id: str):
        """显示用户配置"""
        user_config = self.config_manager.get_user_config(user_id)
        if not user_config:
            print(f"用户 {user_id} 不存在")
            return
            
        print(f"\n用户 {user_id} 的配置:")
        print("=" * 50)
        
        # 基本配置
        print("基本配置:")
        print(f"  Firefly API URL: {user_config.firefly_api_url or '使用全局配置'}")
        print(f"  通知启用: {user_config.notification_enabled}")
        print(f"  语言: {user_config.language}")
        print()
        
        # Dify 配置
        if user_config.dify_config:
            print("Dify 配置:")
            print(f"  API Key: {'已设置' if user_config.dify_config.api_key else '未设置'}")
            print(f"  启用状态: {user_config.dify_config.enabled}")
        else:
            print("Dify 配置: 未配置")
        print()
        
        # 报告配置
        if user_config.report_config:
            print("报告配置:")
            rc = user_config.report_config
            print(f"  日报: {'启用' if rc.daily_enabled else '禁用'} (时间: {rc.daily_time})")
            print(f"  周报: {'启用' if rc.weekly_enabled else '禁用'} (周{rc.weekly_day} {rc.weekly_time})")
            print(f"  月报: {'启用' if rc.monthly_enabled else '禁用'} (每月{rc.monthly_day}日 {rc.monthly_time})")
            print(f"  年报: {'启用' if rc.yearly_enabled else '禁用'} ({rc.yearly_month}月{rc.yearly_day}日 {rc.yearly_time})")
        else:
            print("报告配置: 未配置")
    
    def enable_disable_report(self, user_id: str, report_type: str, enabled: bool):
        """启用或禁用特定类型的报告"""
        valid_types = ['daily', 'weekly', 'monthly', 'yearly']
        if report_type not in valid_types:
            print(f"无效的报告类型: {report_type}，支持的类型: {', '.join(valid_types)}")
            return False
            
        field_name = f"{report_type}_enabled"
        return self.configure_reports(user_id, **{field_name: enabled})


def main():
    """命令行工具主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='FleshRecord 配置管理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 列出用户命令
    list_parser = subparsers.add_parser('list', help='列出所有用户')
    
    # 显示用户配置命令
    show_parser = subparsers.add_parser('show', help='显示用户配置')
    show_parser.add_argument('user_id', help='用户ID')
    
    # 配置 Dify 命令
    dify_parser = subparsers.add_parser('dify', help='配置 Dify API')
    dify_parser.add_argument('user_id', help='用户ID')
    dify_parser.add_argument('api_key', help='Dify API Key')
    dify_parser.add_argument('--disable', action='store_true', help='禁用 Dify')
    
    # 报告配置命令
    report_parser = subparsers.add_parser('report', help='配置报告设置')
    report_parser.add_argument('user_id', help='用户ID')
    report_parser.add_argument('--daily-time', help='日报时间 (HH:MM)')
    report_parser.add_argument('--weekly-day', type=int, help='周报星期 (1=周一, 7=周日)')
    report_parser.add_argument('--weekly-time', help='周报时间 (HH:MM)')
    report_parser.add_argument('--monthly-day', type=int, help='月报日期 (1-31)')
    report_parser.add_argument('--monthly-time', help='月报时间 (HH:MM)')
    report_parser.add_argument('--yearly-month', type=int, help='年报月份 (1-12)')
    report_parser.add_argument('--yearly-day', type=int, help='年报日期 (1-31)')
    report_parser.add_argument('--yearly-time', help='年报时间 (HH:MM)')
    
    # 启用/禁用报告类型命令
    enable_parser = subparsers.add_parser('enable', help='启用报告类型')
    enable_parser.add_argument('user_id', help='用户ID')
    enable_parser.add_argument('report_type', choices=['daily', 'weekly', 'monthly', 'yearly'], help='报告类型')
    
    disable_parser = subparsers.add_parser('disable', help='禁用报告类型')
    disable_parser.add_argument('user_id', help='用户ID')
    disable_parser.add_argument('report_type', choices=['daily', 'weekly', 'monthly', 'yearly'], help='报告类型')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    config_manager = ConfigManager()
    
    if args.command == 'list':
        config_manager.list_users()
    
    elif args.command == 'show':
        config_manager.show_user_config(args.user_id)
    
    elif args.command == 'dify':
        enabled = not args.disable
        config_manager.configure_dify(args.user_id, args.api_key, enabled)
    
    elif args.command == 'report':
        kwargs = {}
        if args.daily_time:
            kwargs['daily_time'] = args.daily_time
        if args.weekly_day:
            kwargs['weekly_day'] = args.weekly_day
        if args.weekly_time:
            kwargs['weekly_time'] = args.weekly_time
        if args.monthly_day:
            kwargs['monthly_day'] = args.monthly_day
        if args.monthly_time:
            kwargs['monthly_time'] = args.monthly_time
        if args.yearly_month:
            kwargs['yearly_month'] = args.yearly_month
        if args.yearly_day:
            kwargs['yearly_day'] = args.yearly_day
        if args.yearly_time:
            kwargs['yearly_time'] = args.yearly_time
        
        if kwargs:
            config_manager.configure_reports(args.user_id, **kwargs)
        else:
            print("请提供至少一个报告配置参数")
    
    elif args.command == 'enable':
        config_manager.enable_disable_report(args.user_id, args.report_type, True)
    
    elif args.command == 'disable':
        config_manager.enable_disable_report(args.user_id, args.report_type, False)


if __name__ == '__main__':
    main()