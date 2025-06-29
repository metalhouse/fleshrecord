import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Callable
from models.user_config import UserConfig, user_config_manager
from services.report_service import ReportService
from handlers.notification_handler import NotificationHandler
from services.firefly_service import FireflyService
import os

logger = logging.getLogger(__name__)


class SchedulerService:
    """定时任务调度服务"""
    
    def __init__(self):
        self.running = False
        self.scheduler_thread = None
        self.tasks = []
        self.last_check_time = {}
        
        # 获取环境变量
        self.dify_api_url = os.getenv('DIFY_API_URL', 'https://api.dify.ai/v1')
        self.firefly_api_url = os.getenv('FIREFLY_API_URL', 'http://localhost:8080/api/v1')
    
    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已经在运行中")
            return
            
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("定时任务调度器已启动")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        logger.info("定时任务调度器已停止")
    
    def _run_scheduler(self):
        """调度器主循环"""
        while self.running:
            try:
                self._check_and_execute_reports()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"调度器运行出错: {e}")
                time.sleep(60)
    
    def _check_and_execute_reports(self):
        """检查并执行报告任务"""
        current_time = datetime.now()
        users = user_config_manager.list_users()
        
        for user_id, config_path in users.items():
            try:
                user_config = user_config_manager.get_user_config(user_id)
                if not user_config or not user_config.dify_config or not user_config.dify_config.enabled:
                    continue
                    
                if not user_config.report_config:
                    continue
                
                # 检查各种报告类型
                self._check_daily_report(user_config, current_time)
                self._check_weekly_report(user_config, current_time)
                self._check_monthly_report(user_config, current_time)
                self._check_yearly_report(user_config, current_time)
                
            except Exception as e:
                logger.error(f"处理用户 {user_id} 的报告任务时出错: {e}")
    
    def _check_daily_report(self, user_config: UserConfig, current_time: datetime):
        """检查日报"""
        if not user_config.report_config.daily_enabled:
            return
            
        task_key = f"{user_config.user_id}_daily"
        target_time = self._parse_time(user_config.report_config.daily_time)
        
        if self._should_execute_task(task_key, current_time, target_time, 'daily'):
            self._execute_report_task(user_config, 'daily')
    
    def _check_weekly_report(self, user_config: UserConfig, current_time: datetime):
        """检查周报"""
        if not user_config.report_config.weekly_enabled:
            return
            
        task_key = f"{user_config.user_id}_weekly"
        target_time = self._parse_time(user_config.report_config.weekly_time)
        target_weekday = user_config.report_config.weekly_day - 1  # 转换为 Python 的 weekday (0=周一)
        
        if (current_time.weekday() == target_weekday and 
            self._should_execute_task(task_key, current_time, target_time, 'weekly')):
            self._execute_report_task(user_config, 'weekly')
    
    def _check_monthly_report(self, user_config: UserConfig, current_time: datetime):
        """检查月报"""
        if not user_config.report_config.monthly_enabled:
            return
            
        task_key = f"{user_config.user_id}_monthly"
        target_time = self._parse_time(user_config.report_config.monthly_time)
        target_day = user_config.report_config.monthly_day
        
        if (current_time.day == target_day and 
            self._should_execute_task(task_key, current_time, target_time, 'monthly')):
            self._execute_report_task(user_config, 'monthly')
    
    def _check_yearly_report(self, user_config: UserConfig, current_time: datetime):
        """检查年报"""
        if not user_config.report_config.yearly_enabled:
            return
            
        task_key = f"{user_config.user_id}_yearly"
        target_time = self._parse_time(user_config.report_config.yearly_time)
        target_month = user_config.report_config.yearly_month
        target_day = user_config.report_config.yearly_day
        
        if (current_time.month == target_month and current_time.day == target_day and 
            self._should_execute_task(task_key, current_time, target_time, 'yearly')):
            self._execute_report_task(user_config, 'yearly')
    
    def _parse_time(self, time_str: str) -> tuple:
        """解析时间字符串 HH:MM"""
        try:
            hour, minute = map(int, time_str.split(':'))
            return (hour, minute)
        except:
            logger.error(f"无法解析时间格式: {time_str}")
            return (9, 0)  # 默认 09:00
    
    def _should_execute_task(self, task_key: str, current_time: datetime, target_time: tuple, report_type: str) -> bool:
        """判断是否应该执行任务"""
        target_hour, target_minute = target_time
        
        # 检查当前时间是否匹配目标时间 (允许1分钟误差)
        time_matches = (
            current_time.hour == target_hour and 
            abs(current_time.minute - target_minute) <= 1
        )
        
        if not time_matches:
            return False
        
        # 检查是否已经执行过
        last_execution = self.last_check_time.get(task_key)
        if last_execution:
            if report_type == 'daily':
                # 日报：同一天不重复执行
                if last_execution.date() == current_time.date():
                    return False
            elif report_type == 'weekly':
                # 周报：同一周不重复执行
                if self._same_week(last_execution, current_time):
                    return False
            elif report_type == 'monthly':
                # 月报：同一月不重复执行
                if (last_execution.year == current_time.year and 
                    last_execution.month == current_time.month):
                    return False
            elif report_type == 'yearly':
                # 年报：同一年不重复执行
                if last_execution.year == current_time.year:
                    return False
        
        return True
    
    def _same_week(self, date1: datetime, date2: datetime) -> bool:
        """判断两个日期是否在同一周"""
        # 获取周一的日期
        monday1 = date1 - timedelta(days=date1.weekday())
        monday2 = date2 - timedelta(days=date2.weekday())
        return monday1.date() == monday2.date()
    
    def _execute_report_task(self, user_config: UserConfig, report_type: str):
        """执行报告任务"""
        try:
            # 创建服务实例
            firefly_service = FireflyService(
                api_url=user_config.firefly_api_url or self.firefly_api_url,
                access_token=user_config.firefly_access_token
            )
            
            report_service = ReportService(
                dify_api_url=self.dify_api_url,
                firefly_service=firefly_service
            )
            
            notification_handler = NotificationHandler(user_config)
            
            # 生成报告
            report_content = None
            if report_type == 'daily':
                report_content = report_service.generate_daily_report(user_config)
            elif report_type == 'weekly':
                report_content = report_service.generate_weekly_report(user_config)
            elif report_type == 'monthly':
                report_content = report_service.generate_monthly_report(user_config)
            elif report_type == 'yearly':
                report_content = report_service.generate_yearly_report(user_config)
            
            # 发送报告
            if report_content:
                report_title = {
                    'daily': '📊 财务日报',
                    'weekly': '📈 财务周报', 
                    'monthly': '📋 财务月报',
                    'yearly': '📊 财务年报'
                }.get(report_type, f'{report_type.title()} 报告')
                
                message = f"{report_title}\n\n{report_content}"
                
                success = notification_handler.send_webhook_message(message)
                if success:
                    logger.info(f"成功发送 {report_type} 报告给用户 {user_config.user_id}")
                    # 记录执行时间
                    task_key = f"{user_config.user_id}_{report_type}"
                    self.last_check_time[task_key] = datetime.now()
                else:
                    logger.error(f"发送 {report_type} 报告失败，用户: {user_config.user_id}")
            else:
                logger.warning(f"生成 {report_type} 报告失败，用户: {user_config.user_id}")
                
        except Exception as e:
            logger.error(f"执行 {report_type} 报告任务时出错，用户: {user_config.user_id}, 错误: {e}")


# 全局调度器实例
scheduler_service = SchedulerService()