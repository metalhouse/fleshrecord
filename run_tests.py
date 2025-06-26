#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试运行脚本
用于验证新的服务层架构是否正常工作
"""

import sys
import os
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('test_run.log', encoding='utf-8')
        ]
    )

def test_imports():
    """测试所有模块导入"""
    logger = logging.getLogger(__name__)
    logger.info("开始测试模块导入...")
    
    try:
        # 测试服务层导入
        from services.firefly_service import FireflyService
        logger.info("✓ FireflyService 导入成功")
        
        # 测试模型导入
        from models.request_models import DifyWebhookRequest, BudgetQueryParams
        logger.info("✓ 请求模型导入成功")
        
        # 测试工具类导入
        from utils.response_builder import APIResponseBuilder
        from utils.retry_decorator import retry_on_failure
        from utils.metrics import SimpleMetrics, track_performance
        logger.info("✓ 工具类导入成功")
        
        return True
        
    except ImportError as e:
        logger.error(f"✗ 模块导入失败: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ 未知错误: {e}")
        return False

def test_service_initialization():
    """测试服务初始化"""
    logger = logging.getLogger(__name__)
    logger.info("开始测试服务初始化...")
    
    try:
        from services.firefly_service import FireflyService
        
        # 模拟配置
        api_url = "https://test.example.com/api/v1"
        access_token = "test_token"
        mock_logger = logging.getLogger('test')
        
        # 初始化服务
        service = FireflyService(api_url, access_token, mock_logger)
        
        if service.api_url == api_url and service.access_token == access_token:
            logger.info("✓ FireflyService 初始化成功")
            return True
        else:
            logger.error("✗ FireflyService 初始化参数不正确")
            return False
            
    except Exception as e:
        logger.error(f"✗ 服务初始化失败: {e}")
        return False

def test_data_validation():
    """测试数据验证"""
    logger = logging.getLogger(__name__)
    logger.info("开始测试数据验证...")
    
    try:
        from models.request_models import DifyWebhookRequest, BudgetQueryParams
        from pydantic import ValidationError
        
        # 测试有效的WebhookRequest
        valid_webhook_data = {
            'api_endpoint': '/budgets',
            'http_method': 'GET',
            'query_parameters': {'budget_id': '123'}
        }
        
        webhook_request = DifyWebhookRequest(**valid_webhook_data)
        logger.info("✓ DifyWebhookRequest 验证成功")
        
        # 测试有效的BudgetQueryParams
        valid_budget_params = {
            'budget_id': '123',
            'start_date': '2024-01-01'
        }
        
        budget_params = BudgetQueryParams(**valid_budget_params)
        logger.info("✓ BudgetQueryParams 验证成功")
        
        # 测试无效数据
        try:
            invalid_webhook_data = {
                'api_endpoint': '/budgets',
                'http_method': 'INVALID_METHOD'  # 无效的HTTP方法
            }
            DifyWebhookRequest(**invalid_webhook_data)
            logger.error("✗ 应该抛出验证错误但没有")
            return False
        except ValidationError:
            logger.info("✓ 无效数据验证正确")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 数据验证测试失败: {e}")
        return False

def test_response_builder():
    """测试响应构建器"""
    logger = logging.getLogger(__name__)
    logger.info("开始测试响应构建器...")
    
    try:
        from utils.response_builder import APIResponseBuilder
        
        # 测试成功响应
        success_response = APIResponseBuilder.success_response(
            {'test': 'data'}, 
            "测试成功"
        )
        
        if (success_response['success'] and 
            success_response['data']['test'] == 'data' and
            success_response['message'] == "测试成功"):
            logger.info("✓ 成功响应构建正确")
        else:
            logger.error("✗ 成功响应构建失败")
            return False
        
        # 测试错误响应
        error_response = APIResponseBuilder.error_response("测试错误", 400)
        
        if (not error_response['success'] and
            error_response['error'] == "测试错误" and
            error_response['status_code'] == 400):
            logger.info("✓ 错误响应构建正确")
        else:
            logger.error("✗ 错误响应构建失败")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 响应构建器测试失败: {e}")
        return False

def test_metrics():
    """测试指标收集"""
    logger = logging.getLogger(__name__)
    logger.info("开始测试指标收集...")
    
    try:
        from utils.metrics import SimpleMetrics, track_performance
        import time
        
        # 初始化指标
        metrics = SimpleMetrics()
        
        # 测试计数器
        metrics.increment_counter('test_counter')
        metrics.increment_counter('test_counter')
        
        stats = metrics.get_stats()
        if stats['counters']['test_counter'] == 2:
            logger.info("✓ 计数器功能正常")
        else:
            logger.error("✗ 计数器功能异常")
            return False
        
        # 测试performance decorator
        @track_performance(metrics)
        def test_function():
            time.sleep(0.001)  # 睡眠1毫秒
            return "test"
        
        result = test_function()
        if result == "test":
            logger.info("✓ 性能跟踪装饰器正常")
        else:
            logger.error("✗ 性能跟踪装饰器异常")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 指标收集测试失败: {e}")
        return False

def main():
    """主函数"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info(f"开始测试新的服务层架构 - {datetime.now()}")
    logger.info("=" * 60)
    
    tests = [
        ("模块导入", test_imports),
        ("服务初始化", test_service_initialization),
        ("数据验证", test_data_validation),
        ("响应构建器", test_response_builder),
        ("指标收集", test_metrics)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
                logger.info(f"✓ {test_name} 测试通过")
            else:
                logger.error(f"✗ {test_name} 测试失败")
        except Exception as e:
            logger.error(f"✗ {test_name} 测试异常: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        logger.info("🎉 所有测试通过！新的服务层架构集成成功！")
        return 0
    else:
        logger.error(f"❌ 有 {total - passed} 个测试失败")
        return 1

if __name__ == '__main__':
    sys.exit(main())