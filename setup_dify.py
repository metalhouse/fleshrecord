#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置 Dify 配置的简单脚本
"""

import json
import os
from pathlib import Path

def setup_dify_config():
    """
    设置 Dify 配置
    """
    print("=== Dify 定期报告系统配置 ===")
    
    # 获取用户ID
    user_id = input("请输入用户ID (默认: metalhouse): ").strip() or "metalhouse"
    
    # 配置文件路径
    config_path = Path(f"data/users/{user_id}.json")
    
    # 读取现有配置
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        print(f"错误: 用户配置文件 {config_path} 不存在")
        return
    
    # Dify 配置
    print("\n--- Dify API 配置 ---")
    api_key = input("请输入 Dify API Key (留空跳过): ").strip()
    workflow_id = input("请输入 Dify 工作流ID (留空跳过): ").strip()
    
    if api_key or workflow_id:
        if 'dify_config' not in config:
            config['dify_config'] = {}
        
        if api_key:
            config['dify_config']['api_key'] = api_key
            config['dify_config']['enabled'] = True
        if workflow_id:
            config['dify_config']['workflow_id'] = workflow_id
    
    # 报告配置
    print("\n--- 报告配置 ---")
    
    # 日报
    daily_enabled = input("启用日报? (y/N): ").strip().lower() == 'y'
    if daily_enabled:
        daily_time = input("日报发送时间 (HH:MM, 默认 09:00): ").strip() or "09:00"
        daily_prompt = input("日报提示词 (留空使用默认): ").strip() or "请生成今日财务报告，分析支出和收入情况"
        
        config['report_config']['daily_enabled'] = True
        config['report_config']['daily_time'] = daily_time
        config['report_config']['daily_prompt'] = daily_prompt
    
    # 周报
    weekly_enabled = input("启用周报? (y/N): ").strip().lower() == 'y'
    if weekly_enabled:
        weekly_day = int(input("周报发送日期 (1-7, 1=周一, 默认 1): ").strip() or "1")
        weekly_time = input("周报发送时间 (HH:MM, 默认 09:00): ").strip() or "09:00"
        weekly_prompt = input("周报提示词 (留空使用默认): ").strip() or "请生成本周财务报告，分析支出趋势和预算执行情况"
        
        config['report_config']['weekly_enabled'] = True
        config['report_config']['weekly_day'] = weekly_day
        config['report_config']['weekly_time'] = weekly_time
        config['report_config']['weekly_prompt'] = weekly_prompt
    
    # 月报
    monthly_enabled = input("启用月报? (y/N): ").strip().lower() == 'y'
    if monthly_enabled:
        monthly_day = int(input("月报发送日期 (1-31, 默认 1): ").strip() or "1")
        monthly_time = input("月报发送时间 (HH:MM, 默认 09:00): ").strip() or "09:00"
        monthly_prompt = input("月报提示词 (留空使用默认): ").strip() or "请生成本月财务报告，分析月度预算执行和支出分类"
        
        config['report_config']['monthly_enabled'] = True
        config['report_config']['monthly_day'] = monthly_day
        config['report_config']['monthly_time'] = monthly_time
        config['report_config']['monthly_prompt'] = monthly_prompt
    
    # 年报
    yearly_enabled = input("启用年报? (y/N): ").strip().lower() == 'y'
    if yearly_enabled:
        yearly_month = int(input("年报发送月份 (1-12, 默认 1): ").strip() or "1")
        yearly_day = int(input("年报发送日期 (1-31, 默认 1): ").strip() or "1")
        yearly_time = input("年报发送时间 (HH:MM, 默认 09:00): ").strip() or "09:00"
        yearly_prompt = input("年报提示词 (留空使用默认): ").strip() or "请生成年度财务报告，总结全年财务状况和支出分析"
        
        config['report_config']['yearly_enabled'] = True
        config['report_config']['yearly_month'] = yearly_month
        config['report_config']['yearly_day'] = yearly_day
        config['report_config']['yearly_time'] = yearly_time
        config['report_config']['yearly_prompt'] = yearly_prompt
    
    # 保存配置
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    
    print(f"\n配置已保存到: {config_path}")
    print("\n=== 配置完成 ===")
    
    # 显示配置摘要
    print("\n--- 配置摘要 ---")
    if config.get('dify_config', {}).get('enabled'):
        print(f"✓ Dify API: 已配置")
    else:
        print("✗ Dify API: 未配置")
    
    report_config = config.get('report_config', {})
    enabled_reports = []
    if report_config.get('daily_enabled'):
        enabled_reports.append(f"日报({report_config.get('daily_time')})")
    if report_config.get('weekly_enabled'):
        enabled_reports.append(f"周报(周{report_config.get('weekly_day')} {report_config.get('weekly_time')})")
    if report_config.get('monthly_enabled'):
        enabled_reports.append(f"月报({report_config.get('monthly_day')}日 {report_config.get('monthly_time')})")
    if report_config.get('yearly_enabled'):
        enabled_reports.append(f"年报({report_config.get('yearly_month')}/{report_config.get('yearly_day')} {report_config.get('yearly_time')})")
    
    if enabled_reports:
        print(f"✓ 启用报告: {', '.join(enabled_reports)}")
    else:
        print("✗ 报告: 未启用任何定期报告")

if __name__ == '__main__':
    setup_dify_config()