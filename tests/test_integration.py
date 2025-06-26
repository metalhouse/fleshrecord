import unittest
import sys
import os
from unittest.mock import patch, Mock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.request_models import DifyWebhookRequest, BudgetQueryParams
from utils.response_builder import APIResponseBuilder
from utils.metrics import SimpleMetrics, track_performance
import json
from pydantic import ValidationError


class TestIntegration(unittest.TestCase):
    """集成测试类"""
    
    def setUp(self):
        """测试前的设置"""
        self.metrics = SimpleMetrics()
    
    def test_dify_webhook_request_validation(self):
        """测试DifyWebhookRequest数据验证"""
        # 有效的请求数据
        valid_data = {
            'api_endpoint': '/budgets',
            'http_method': 'GET',
            'query_parameters': {'budget_id': '123'}
        }
        
        # 应该成功创建
        request = DifyWebhookRequest(**valid_data)
        self.assertEqual(request.api_endpoint, '/budgets')
        self.assertEqual(request.http_method, 'GET')
        self.assertEqual(request.query_parameters['budget_id'], '123')
    
    def test_budget_query_params_validation(self):
        """测试BudgetQueryParams验证"""
        # 有效的查询参数
        valid_params = {
            'budget_id': '123',
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        }
        
        # 应该成功创建
        params = BudgetQueryParams(**valid_params)
        self.assertEqual(params.budget_id, '123')
        self.assertEqual(str(params.start_date), '2024-01-01')
        self.assertEqual(str(params.end_date), '2024-12-31')
    
    def test_budget_query_params_invalid_date(self):
        """测试无效日期格式"""
        invalid_params = {
            'start_date': '2024-13-45',  # 无效日期
        }
        
        # 应该抛出验证错误
        with self.assertRaises(ValidationError):
            BudgetQueryParams(**invalid_params)
    
    def test_api_response_builder_success(self):
        """测试成功响应构建"""
        data = {'id': '123', 'name': 'Test'}
        response = APIResponseBuilder.success_response(data, "操作成功")
        
        self.assertTrue(response['success'])
        self.assertEqual(response['data'], data)
        self.assertEqual(response['message'], "操作成功")
    
    def test_api_response_builder_error(self):
        """测试错误响应构建"""
        response = APIResponseBuilder.error_response("发生错误", code=400)
        
        self.assertFalse(response['success'])
        self.assertEqual(response['error'], "发生错误")
        self.assertEqual(response['status_code'], 400)
    
    def test_simple_metrics(self):
        """测试简单指标收集"""
        # 测试计数器
        self.metrics.increment_counter('test_counter')
        self.metrics.increment_counter('test_counter')
        stats = self.metrics.get_stats()
        self.assertEqual(stats['counters']['test_counter'], 2)
        
        # 测试计时
        import time
        start = time.time()
        time.sleep(0.01)  # 睡眠10毫秒
        self.metrics.record_timing('test_timing', time.time() - start)
        
        stats = self.metrics.get_stats()
        self.assertIn('test_timing', stats['timings'])
        self.assertGreater(stats['timings']['test_timing'][-1], 0)
    
    @patch('time.time')
    def test_track_performance_decorator(self, mock_time):
        """测试性能跟踪装饰器"""
        # 模拟时间
        mock_time.side_effect = [1000, 1001]  # 开始时间1000，结束时间1001
        
        @track_performance(self.metrics)
        def test_function():
            return "test_result"
        
        result = test_function()
        
        # 验证结果
        self.assertEqual(result, "test_result")
        stats = self.metrics.get_stats()
        self.assertIn('test_function', stats['timings'])
    
    def test_dify_webhook_request_with_invalid_data(self):
        """测试DifyWebhookRequest无效数据验证"""
        # 无效的HTTP方法
        invalid_data = {
            'api_endpoint': '/budgets',
            'http_method': 'INVALID_METHOD',  # 无效的HTTP方法
            'query_parameters': {}
        }
        
        with self.assertRaises(ValidationError):
            DifyWebhookRequest(**invalid_data)
    
    def test_complete_workflow_simulation(self):
        """测试完整工作流程模拟"""
        # 1. 验证输入数据
        input_data = {
            'api_endpoint': '/budgets',
            'http_method': 'GET',
            'query_parameters': {
                'budget_id': '123',
                'start_date': '2024-01-01'
            }
        }
        
        # 创建请求对象
        webhook_request = DifyWebhookRequest(**input_data)
        self.assertIsNotNone(webhook_request)
        
        # 2. 提取查询参数并验证
        budget_params = BudgetQueryParams(**webhook_request.query_parameters)
        self.assertEqual(budget_params.budget_id, '123')
        
        # 3. 模拟服务响应
        mock_service_response = {
            'success': True,
            'data': [{'id': '123', 'name': 'Test Budget'}]
        }
        
        # 4. 构建最终响应
        final_response = APIResponseBuilder.success_response(
            mock_service_response['data'], 
            "查询成功"
        )
        
        # 验证最终响应
        self.assertTrue(final_response['success'])
        self.assertEqual(len(final_response['data']), 1)
        self.assertEqual(final_response['message'], "查询成功")


if __name__ == '__main__':
    unittest.main()