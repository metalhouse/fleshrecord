from typing import Dict, Any, List, Optional
from flask import request, jsonify, current_app as app
import datetime
import requests
from typing import Dict, Any
from pydantic import ValidationError

from utils.response_builder import APIResponseBuilder
from utils.metrics import track_performance
from services.firefly_service import FireflyService
from models.request_models import BudgetQueryParams


class BudgetHandler:
    """处理预算相关请求的专用处理器"""
    
    def __init__(self, config, firefly_service: FireflyService, user_config: Dict[str, Any]):
        self.config = config
        self.firefly_service = firefly_service
        self.user_config = user_config
        self.firefly_headers = self._build_firefly_headers()
    
    def _build_firefly_headers(self) -> Dict[str, str]:
        """构建Firefly API请求头"""
        access_token = self.user_config.get('firefly_access_token')
        if not access_token:
            raise ValueError("firefly_access_token未在用户配置文件中设置")
        
        # 确保access_token不包含重复的'Bearer'前缀
        clean_token = str(access_token).replace('Bearer ', '').strip()
        return {
            'Authorization': f'Bearer {clean_token}',
            'Content-Type': 'application/json'
        }
    
    @track_performance('budgets_endpoint')
    def get_budgets_endpoint(self) -> tuple:
        """获取预算信息的API端点处理器
        
        Returns:
            tuple: (response_data, status_code)
        """
        try:
            # 验证查询参数
            try:
                query_params = BudgetQueryParams(
                    start_date=request.args.get('start_date'),
                    end_date=request.args.get('end_date'),
                    budget_id=request.args.get('budget_id')
                )
            except ValidationError as e:
                app.logger.warning(f"参数验证失败: {e}")
                return jsonify(APIResponseBuilder.error_response(
                    f"参数验证失败: {e.errors()}", 400
                )), 400
            
            # 如果指定了budget_id，获取特定预算限制
            if query_params.budget_id:
                return self._get_specific_budget(query_params)
            else:
                # 获取所有预算信息
                return self._get_all_budgets()
        
        except Exception as e:
            app.logger.error(f"获取预算信息时发生错误: {e}", exc_info=True)
            return jsonify(APIResponseBuilder.error_response(
                "获取预算信息失败", 500
            )), 500
    
    def _get_specific_budget(self, query_params: BudgetQueryParams) -> tuple:
        """获取特定预算的限制信息"""
        query_dict = {
            'start': query_params.start_date,
            'end': query_params.end_date
        }
        
        result = self.firefly_service.get_budget_limits(
            query_params.budget_id, query_dict
        )
        
        if result:
            app.logger.info(f"成功获取预算限制: budget_id={query_params.budget_id}")
            return jsonify(APIResponseBuilder.success_response(
                "成功获取预算限制", result
            )), 200
        else:
            app.logger.warning(f"未找到预算限制: budget_id={query_params.budget_id}")
            return jsonify(APIResponseBuilder.error_response(
                "未找到指定的预算限制", 404
            )), 404
    
    def _get_all_budgets(self) -> tuple:
        """获取所有预算信息"""
        budgets = self.get_firefly_budgets()
        app.logger.info(f"成功获取 {len(budgets)} 个预算")
        return jsonify(APIResponseBuilder.success_response(
            "成功获取预算信息", budgets
        )), 200
    
    def get_firefly_budgets(self) -> List[Dict[str, Any]]:
        """获取Firefly-III的预算信息
        
        Returns:
            List[Dict[str, Any]]: 预算信息列表
        """
        today = datetime.datetime.today()
        start_date, end_date = self._get_current_month_range(today)
        
        # 获取所有预算
        budgets_url = f'{self.firefly_service.api_url}/budgets'
        response = requests.get(budgets_url, headers=self.firefly_headers)
        response.raise_for_status()
        budgets = response.json()['data']
        
        result = []
        for budget in budgets:
            budget_info = self._process_single_budget(
                budget, start_date, end_date, today
            )
            result.append(budget_info)
        
        return result
    
    def _get_current_month_range(self, today: datetime.datetime) -> tuple:
        """获取当前月份的日期范围
        
        Args:
            today: 当前日期
            
        Returns:
            tuple: (start_date, end_date) 字符串格式
        """
        start_date = today.replace(day=1).strftime('%Y-%m-%d')
        end_of_month = (
            today.replace(day=28) + datetime.timedelta(days=4)
        ).replace(day=1) - datetime.timedelta(days=1)
        end_date = end_of_month.strftime('%Y-%m-%d')
        
        return start_date, end_date
    
    def _process_single_budget(self, budget: Dict[str, Any], 
                              start_date: str, end_date: str, 
                              today: datetime.datetime) -> Dict[str, Any]:
        """处理单个预算信息
        
        Args:
            budget: 预算数据
            start_date: 开始日期
            end_date: 结束日期
            today: 当前日期
            
        Returns:
            Dict[str, Any]: 处理后的预算信息
        """
        budget_id = budget['id']
        name = budget['attributes']['name']
        
        # 获取该预算的全部限额（limits）
        limits_url = (
            f'{self.firefly_service.api_url}/budgets/{budget_id}/limits'
            f'?start_date={start_date}&end_date={end_date}'
        )
        
        try:
            limits_response = requests.get(limits_url, headers=self.firefly_headers)
            limits_response.raise_for_status()
            limits_data = limits_response.json()['data']
            
            total_budget, total_spent = self._calculate_budget_totals(
                limits_data, today
            )
            
        except requests.RequestException as e:
            app.logger.error(f"获取预算限制失败 (budget_id: {budget_id}): {e}")
            total_budget, total_spent = 0.0, 0.0
        
        remaining = max(0.0, total_budget - total_spent)
        
        return {
            'name': name,
            'total_budget': round(total_budget, 2),
            'total_spent': round(total_spent, 2),
            'remaining': round(remaining, 2)
        }
    
    def _calculate_budget_totals(self, limits_data: List[Dict[str, Any]], 
                                today: datetime.datetime) -> tuple:
        """计算预算总额和支出总额
        
        Args:
            limits_data: 预算限制数据
            today: 当前日期
            
        Returns:
            tuple: (total_budget, total_spent)
        """
        total_budget = 0.0
        total_spent = 0.0
        today_str = today.strftime('%Y-%m-%d')
        
        for limit in limits_data:
            limit_attr = limit['attributes']
            limit_start = limit_attr['start']
            limit_amount = limit_attr.get('amount', '0')
            limit_spent = limit_attr.get('spent', '0')
            
            # 仅统计本月且开始时间不超过今天的周期
            if limit_start <= today_str:
                total_budget += float(limit_amount) if limit_amount else 0.0
                # spent是负数，取正值
                total_spent += abs(float(limit_spent)) if limit_spent else 0.0
        
        return total_budget, total_spent
    
    def build_budget_message(self, budgets: List[Dict[str, Any]]) -> str:
        """构建预算信息消息
        
        Args:
            budgets: 预算信息列表
            
        Returns:
            str: 格式化的预算消息
        """
        if not budgets:
            return "\n当前没有预算信息。"
        
        message = "\n交易处理完成，当前预算情况:"
        for budget in budgets:
            app.logger.info(budget)
            message += (
                f"\n当月预算: {budget['total_budget']}，"
                f"支出：{budget['total_spent']}，"
                f"剩余： {budget['remaining']} 元"
            )
        
        return message