from typing import Dict, Any, Optional, Tuple, Union
from flask import request, jsonify, current_app as app
from pydantic import ValidationError
import json
from datetime import datetime
from typing import Union, Dict, Any, Tuple

from utils.response_builder import APIResponseBuilder
from utils.metrics import track_performance
from services.firefly_service import FireflyService
from models.request_models import DifyWebhookRequest, BudgetQueryParams, TransactionQueryParams


class DifyHandler:
    """处理Dify智能助手Webhook请求的专用处理器"""
    
    def __init__(self, firefly_service: FireflyService, budget_handler: Any):
        self.firefly_service = firefly_service
        self.budget_handler = budget_handler
    
    @track_performance('dify_webhook')
    def handle_dify_webhook(self) -> Tuple[Union[str, Dict[str, Any]], int]:
        """处理Dify Webhook请求
        
        Returns:
            Tuple[Union[str, Dict[str, Any]], int]: 响应内容和状态码
        """
        try:
            # 验证请求格式
            if not request.is_json:
                app.logger.warning("Dify webhook请求不是JSON格式")
                return "Request must be JSON", 400
            
            # 验证请求数据
            webhook_data = self._validate_request_data()
            if isinstance(webhook_data, tuple):
                return webhook_data  # 返回错误响应
            
            # 记录请求信息
            app.logger.info(
                f"Dify webhook请求: endpoint={webhook_data.api_endpoint}, "
                f"query_parameters={webhook_data.query_parameters}"
            )
            
            # 路由到相应的处理方法
            return self._route_request(webhook_data)
            
        except Exception as e:
            app.logger.error(f"处理Dify webhook请求时发生错误: {e}", exc_info=True)
            return "Internal Server Error", 500
    
    def _validate_request_data(self) -> Union[DifyWebhookRequest, Tuple[str, int]]:
        """验证请求数据
        
        Returns:
            Union[DifyWebhookRequest, Tuple[str, int]]: 验证成功返回数据对象，失败返回错误响应
        """
        try:
            data = request.get_json()
            webhook_data = DifyWebhookRequest(**data)
            return webhook_data
        except ValidationError as e:
            app.logger.warning(f"Dify webhook数据验证失败: {e}")
            error_details = self._format_validation_errors(e.errors())
            return f"请求数据验证失败: {error_details}", 400
        except Exception as e:
            app.logger.error(f"解析请求数据失败: {e}")
            return "Invalid request data", 400
    
    def _format_validation_errors(self, errors: list) -> str:
        """格式化验证错误信息
        
        Args:
            errors: Pydantic验证错误列表
            
        Returns:
            str: 格式化的错误信息
        """
        error_messages = []
        for error in errors[:3]:  # 只显示前3个错误
            field = '.'.join(str(loc) for loc in error['loc'])
            message = error['msg']
            error_messages.append(f"{field}: {message}")
        
        if len(errors) > 3:
            error_messages.append("...以及其他错误")
        
        return "; ".join(error_messages)
    
    def _route_request(self, webhook_data: DifyWebhookRequest) -> Tuple[Union[str, Dict[str, Any]], int]:
        """根据API端点路由请求
        
        Args:
            webhook_data: 验证后的Webhook数据
            
        Returns:
            Tuple[Union[str, Dict[str, Any]], int]: 响应内容和状态码
        """
        endpoint = webhook_data.api_endpoint.lower()
        
        if endpoint == '/transactions':
            return self._handle_transactions_request(webhook_data.query_parameters)
        elif endpoint == '/budgets':
            return self._handle_budgets_request(webhook_data.query_parameters)
        else:
            app.logger.warning(f"不支持的API端点: {webhook_data.api_endpoint}")
            return f"不支持的API端点: {webhook_data.api_endpoint}", 400
    
    def _handle_transactions_request(self, query: str) -> Tuple[Union[str, Dict[str, Any]], int]:
        """处理交易查询请求
        
        Args:
            query: 查询参数字符串
            
        Returns:
            Tuple[Union[str, Dict[str, Any]], int]: 响应内容和状态码
        """
        try:
            # 解析查询参数
            query_params = self._parse_query_string(query)
            
            # 默认排除转账交易，除非明确指定包含
            if 'type' not in query_params:
                # 只包含支出和收入交易，排除转账
                query_params['type'] = 'withdrawal,deposit'
                app.logger.info("自动添加type参数排除转账交易: withdrawal,deposit")
            
            # 调用Firefly服务获取交易数据
            transactions_result = self.firefly_service.get_transactions(query_params)
            if transactions_result and transactions_result.get('success'):
                filtered_data = transactions_result.get('data', [])
                app.logger.info(f"成功获取 {len(filtered_data)} 条交易记录")
                formatted_result = self._format_transactions_response(filtered_data)
                return formatted_result, 200
            else:
                app.logger.info("未找到匹配的交易记录")
                return "未找到匹配的交易记录", 404
        except Exception as e:
            app.logger.error(f"查询交易记录失败: {e}", exc_info=True)
            return "查询交易记录失败", 500
    
    def _handle_budgets_request(self, query: str) -> Tuple[Union[str, Dict[str, Any]], int]:
        """处理预算查询请求
        
        Args:
            query: 查询参数字符串
            
        Returns:
            Tuple[Union[str, Dict[str, Any]], int]: 响应内容和状态码
        """
        try:
            # 解析查询参数
            query_dict = self._parse_query_string(query)
            
            # 获取预算信息
            if 'budget_id' in query_dict:
                # 获取特定预算
                return self._get_specific_budget_for_dify(query_dict)
            else:
                # 获取所有预算
                budgets = self.budget_handler.get_firefly_budgets()
                formatted_result = self._format_budgets_response(budgets)
                app.logger.info(f"成功获取 {len(budgets)} 个预算")
                return formatted_result, 200
                
        except Exception as e:
            app.logger.error(f"查询预算信息失败: {e}", exc_info=True)
            return "查询预算信息失败", 500
    
    def _get_specific_budget_for_dify(self, query_dict: Dict[str, str]) -> Tuple[Union[str, Dict[str, Any]], int]:
        """为Dify获取特定预算信息"""
        try:
            budget_params = BudgetQueryParams(
                budget_id=query_dict.get('budget_id'),
                start_date=query_dict.get('start_date'),
                end_date=query_dict.get('end_date')
            )
        except ValidationError as e:
            return f"预算查询参数无效: {e.errors()}", 400
        
        query_params = {
            'start': budget_params.start_date,
            'end': budget_params.end_date
        }
        
        result = self.firefly_service.get_budget_limits(
            budget_params.budget_id, query_params
        )
        
        if result:
            formatted_result = self._format_budget_limits_response(result)
            return formatted_result, 200
        else:
            return "未找到指定的预算限制", 404
    
    def _parse_query_string(self, query: Union[str, dict]) -> dict:
        """解析查询字符串或字典
        
        Args:
            query: 查询字符串或字典
            
        Returns:
            dict: 解析后的参数字典
            
        Note:
            支持的交易查询参数包括：
            - type: 交易类型，可选值: withdrawal, deposit, transfer 或它们的组合(逗号分隔)
            - start: 开始日期 (YYYY-MM-DD)
            - end: 结束日期 (YYYY-MM-DD)
            - category: 分类名称
            - tags: 标签(逗号分隔)
            - 其他Firefly III API支持的参数
        """
        if isinstance(query, dict):
            return query
            
        params = {}
        try:
            # 尝试解析为JSON
            if query.strip().startswith('{'):
                params = json.loads(query)
            else:
                # 解析为URL查询参数格式
                for param in query.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        params[key.strip()] = value.strip()
        except (json.JSONDecodeError, ValueError) as e:
            app.logger.warning(f"解析查询参数失败: {e}，原始查询: {query}")
        
        return params
    
    def _format_transactions_response(self, transactions: Union[list, dict]) -> dict:
        """
        Format transactions response to a simplified structure.
        """
        formatted_transactions = []
        # 只处理过滤后的 data
        data_items = transactions if isinstance(transactions, list) else []
        for item in data_items:
            if isinstance(item, dict) and 'attributes' in item:
                for tx in item['attributes'].get('transactions', []):
                    formatted_transactions.append({
                        'amount': float(tx.get('amount', 0)),
                        'date': tx.get('date', ''),
                        'description': tx.get('description', '')
                    })
        return {
            'data': {
                'summary': f"共找到 {len(data_items)} 条交易记录",  # summary与实际过滤后主交易数量一致
                'transactions': formatted_transactions
            },
            'message': "交易记录查询成功",
            'status': "success",
            'timestamp': datetime.now().isoformat()
        }
    
    def _format_budgets_response(self, budgets: list) -> Dict[str, Any]:
        """格式化预算响应数据
        
        Args:
            budgets: 预算数据列表
            
        Returns:
            Dict[str, Any]: 格式化的响应数据
        """
        return {
            "status": "success",
            "message": f"成功获取 {len(budgets)} 个预算",
            "data": budgets
        }
    
    def _format_budget_limits_response(self, limits: Any) -> Dict[str, Any]:
        """格式化预算限制响应数据
        
        Args:
            limits: 预算限制数据
            
        Returns:
            Dict[str, Any]: 格式化的响应数据
        """
        return {
            "status": "success",
            "message": "成功获取预算限制",
            "data": limits
        }