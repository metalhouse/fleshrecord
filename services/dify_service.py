#!/usr/bin/env python3
"""
Dify API 服务
用于与 Dify 工作流 API 进行交互
"""

import logging
import requests
from typing import Dict, Any, Optional
from conf.config import config

logger = logging.getLogger(__name__)


class DifyService:
    """Dify API 服务类"""
    
    def __init__(self, api_key: str):
        """
        初始化 Dify 服务
        
        Args:
            api_key: Dify API Key
        """
        self.api_key = api_key
        self.api_url = config.DIFY_API_URL
        self.timeout = 60  # 增加超时时间以适应工作流处理时间
        
        # 设置请求头
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json; charset=utf-8',
            'User-Agent': 'FleshRecord/1.0'
        }
    
    def run_workflow(self, workflow_id: str, inputs: Dict[str, Any], user: str = "fleshrecord-system") -> Dict[str, Any]:
        """
        执行 Dify 对话型应用
        
        Args:
            workflow_id: 应用ID（对话型应用）
            inputs: 应用输入参数
            user: 用户标识
        
        Returns:
            Dict[str, Any]: Dify 的响应
        """
        try:
            # 构造查询内容
            query = inputs.get('query', '') or inputs.get('report_data', '') or str(inputs)
            
            # 构造请求数据（对话型应用格式）
            request_data = {
                'inputs': inputs,
                'query': query,
                'response_mode': 'blocking',
                'user': user,
                'conversation_id': '',  # 空字符串表示新对话
                'auto_generate_name': False
            }
            
            # 发送请求到对话API
            response = requests.post(
                f"{self.api_url}/chat-messages",
                json=request_data,
                headers=self.headers,
                timeout=self.timeout
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 设置响应编码为UTF-8
            response.encoding = 'utf-8'
            
            # 解析响应
            response_data = response.json()
            
            logger.info(f"Dify 工作流执行成功，工作流ID: {workflow_id}")
            logger.debug(f"Dify API 响应: {response_data}")
            
            # 从对话型应用响应中提取消息
            message = ''
            workflow_run_id = ''
            try:
                # 对话型应用的响应格式
                message = response_data.get('answer', '')
                workflow_run_id = response_data.get('message_id', '') or response_data.get('id', '')
                
                # 如果没有answer字段，尝试其他可能的字段
                if not message:
                    message = response_data.get('message', '') or response_data.get('content', '') or response_data.get('text', '')
                    
            except Exception as extract_error:
                logger.warning(f"提取消息内容时出错: {extract_error}")
                message = '无法提取响应内容'
            
            return {
                'success': True,
                'data': response_data,
                'message': message,
                'workflow_run_id': workflow_run_id
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Dify API 请求失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '调用 Dify API 时发生网络错误'
            }
        
        except Exception as e:
            logger.error(f"Dify 服务处理失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '处理 Dify 响应时发生错误'
            }
    
    def generate_financial_report(self, workflow_id: str, report_type: str, transaction_data: Dict[str, Any], 
                                report_query: str) -> Dict[str, Any]:
        """
        生成财务报告
        
        Args:
            workflow_id: Dify工作流ID
            report_type: 报告类型 (daily/weekly/monthly/yearly)
            transaction_data: 交易数据
            report_query: 报告查询语句
        
        Returns:
            Dict[str, Any]: 生成的报告
        """
        try:
            # 如果不需要交易数据，直接只发prompt
            if transaction_data is None:
                inputs = {
                    'report_type': report_type,
                    'report_query': report_query,
                    'transaction_data': '',
                    'query': report_query
                }
            else:
                transaction_summary = self._format_transaction_data(transaction_data)
                inputs = {
                    'report_type': report_type,
                    'report_query': report_query,
                    'transaction_data': transaction_summary,
                    'query': f"""{report_query}

交易数据:
{transaction_summary}

请根据以上数据生成 {report_type} 报告。"""
                }
            # 调用工作流API
            result = self.run_workflow(workflow_id, inputs)
            if result['success']:
                logger.info(f"成功生成 {report_type} 报告")
            else:
                logger.error(f"生成 {report_type} 报告失败: {result.get('error')}")
            return result
        except Exception as e:
            logger.error(f"生成财务报告时出错: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'生成 {report_type} 报告时发生错误'
            }
    
    def _format_transaction_data(self, transaction_data: Dict[str, Any]) -> str:
        """
        格式化交易数据为文本
        
        Args:
            transaction_data: 交易数据
        
        Returns:
            str: 格式化后的交易数据文本
        """
        try:
            lines = []
            
            # 统计信息
            if 'summary' in transaction_data:
                summary = transaction_data['summary']
                lines.append("=== 统计摘要 ===")
                lines.append(f"交易总数: {summary.get('total_transactions', 0)}")
                lines.append(f"总收入: {summary.get('total_income', 0)}")
                lines.append(f"总支出: {summary.get('total_expense', 0)}")
                lines.append(f"净额: {summary.get('net_amount', 0)}")
                lines.append("")
            
            # 分类统计
            if 'categories' in transaction_data:
                lines.append("=== 分类统计 ===")
                for category, amount in transaction_data['categories'].items():
                    lines.append(f"{category}: {amount}")
                lines.append("")
            
            # 预算统计
            if 'budgets' in transaction_data:
                lines.append("=== 预算统计 ===")
                for budget, data in transaction_data['budgets'].items():
                    lines.append(f"{budget}: 已用 {data.get('spent', 0)} / 限额 {data.get('limit', 0)}")
                lines.append("")
            
            # 详细交易（限制数量）
            if 'transactions' in transaction_data:
                lines.append("=== 交易明细 (最近10条) ===")
                transactions = transaction_data['transactions'][:10]
                for tx in transactions:
                    amount = tx.get('amount', 0)
                    description = tx.get('description', '无描述')
                    category = tx.get('category', '未分类')
                    date = tx.get('date', '无日期')
                    lines.append(f"{date}: {description} - {amount} ({category})")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"格式化交易数据失败: {e}")
            return f"交易数据格式化失败: {str(e)}"
    
    def test_connection(self, workflow_id: str) -> Dict[str, Any]:
        """
        测试与 Dify API 的连接
        
        Args:
            workflow_id: 用于测试的工作流ID
        
        Returns:
            Dict[str, Any]: 测试结果
        """
        test_inputs = {
            'query': 'Hello, this is a connection test.',
            'report_type': 'test',
            'transaction_data': '测试连接',
            'report_query': '这是一个连接测试'
        }
        return self.run_workflow(workflow_id, test_inputs)