from flask import Flask, request,abort, jsonify,current_app
import subprocess
import json
import logging
import threading
import copy
import hmac
import hashlib
import time
import datetime
import requests
import os
from flask import Flask, request, jsonify
from pydantic import ValidationError

# 导入新的服务层和工具类
from services.firefly_service import FireflyService
from models.request_models import DifyWebhookRequest, BudgetQueryParams
from utils.response_builder import APIResponseBuilder
from utils.metrics import metrics, track_performance

app = Flask(__name__)
# 从配置文件中加载配置
basedir = os.path.abspath(os.path.dirname(__file__))
app.config.from_pyfile(os.path.join(basedir, 'conf/config.py'))

# 设置日志配置
LOG_FILE = app.config.get('LOG_FILE')
LOG_LEVEL = app.config.get('LOG_LEVEL', logging.INFO)
LOG_FORMAT = app.config.get('LOG_FORMAT', '%(asctime)s [%(levelname)s] %(message)s')

# 确保日志目录存在
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# 配置日志处理器
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()  # 同时输出到控制台
    ]
)

# 设置Flask应用的日志级别
app.logger.setLevel(LOG_LEVEL)


# 从配置获取webhook密钥（需要在config.py中添加）
WEBHOOK_SECRET = app.config.get('WEBHOOK_SECRET')
if not WEBHOOK_SECRET:
    raise ValueError("WEBHOOK_SECRET未在配置文件中设置")
WEBHOOK_SECRET_UPDATE = app.config.get('WEBHOOK_SECRET_UPDATE')
url = app.config.get('WEBHOOK_URL')
headers = {"Content-Type": "application/json"}
FIREFLY_ACCESS_TOKEN = app.config.get('FIREFLY_ACCESS_TOKEN')
FIREFLY_API_URL = app.config.get('FIREFLY_API_URL')

firefly_headers = {
    'Authorization': f'Bearer {FIREFLY_ACCESS_TOKEN}',
    'Content-Type': 'application/json'
}

# 初始化FireflyService实例
firefly_service = FireflyService(FIREFLY_API_URL, FIREFLY_ACCESS_TOKEN, app.logger)

def verify_signature(payload, signature_header):
    if not signature_header:
        app.logger.error("缺少Signature请求头")
        return False
    
    # 解析签名组件
    signature_parts = dict(part.split('=') for part in signature_header.split(','))
    if 'v1' not in signature_parts or 't' not in signature_parts:
        app.logger.error("签名格式不正确，缺少必要组件")
        return False
    
    received_signature = signature_parts['v1']
    timestamp = signature_parts['t']
    
    # 将时间戳与请求体组合后计算签名
    signed_payload = f'{timestamp}.'.encode('utf-8') + payload
    computed_signature = hmac.new(
        key=WEBHOOK_SECRET.encode('utf-8'),
        msg=signed_payload,
        digestmod=hashlib.sha3_256  # 修正为SHA-3 256位
    ).hexdigest()
    computed_signature_update = hmac.new(
        key=WEBHOOK_SECRET_UPDATE.encode('utf-8'),
        msg=signed_payload,
        digestmod=hashlib.sha3_256  # 修正为SHA-3 256位
    ).hexdigest()
    if hmac.compare_digest(computed_signature, received_signature) or hmac.compare_digest(computed_signature_update, received_signature):
        return 1
    else:
        return 0



@app.route('/webhook', methods=['POST'])
def webhook():
    # 获取签名头
    signature = request.headers.get('Signature')
    # 添加请求头日志
    app.logger.info(f"Request headers: {dict(request.headers)}")

    # 使用原始请求体进行验证
    if not verify_signature(request.data, signature):
        app.logger.warning("Webhook签名验证失败")
        abort(403)
        
    try:
        data = request.json
        app.logger.info(f"Received raw data: {json.dumps(data, ensure_ascii=False)}")
        
        trigger = data.get('trigger', '')
        content = data.get('content', {})
        transactions = content.get('transactions', [])

        if not transactions:
            app.logger.warning("No transactions found in payload.")
            return "No transactions found", 400

        transaction = transactions[0]
        description = transaction.get('description', '无描述')
        amount = transaction.get('amount', '0')
        category_name = transaction.get('category_name', '无分类')
        budget_name = transaction.get('budget_name', '无预算')

        if trigger == "UPDATE_TRANSACTION":
            message = f"您更新了一笔交易：{description}, 费用：{amount}，分类：{category_name}，预算：{budget_name}。"
        elif trigger == "STORE_TRANSACTION":
            message = f"您新增了一笔交易：{description}, 费用：{amount}，分类：{category_name}，预算：{budget_name}。"
      
        # 获取并记录预算信息
        budgets = get_firefly_budgets()
        message += f"\n交易处理完成，当前预算情况:"
        for budget in budgets:
            app.logger.info(budget)
            message += f"\n当月预算: {budget['total_budget']}，支出：{budget['total_spent']}，剩余： {budget['remaining']} 元"     
        
        app.logger.info(f"构造消息内容: {message}")

        json_data = {
            "msgtype": "text",
            "text": {"content": message}
        }
        call_curl(url, json_data, headers)   
        return "Webhook processed", 200

    except Exception as e:
        app.logger.error(f"Error processing webhook: {e}", exc_info=True)
        return "Internal Server Error", 500

def call_curl(url, data, headers):
    try:
        # 使用 requests 库发送 POST 请求
        import requests
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()  # 抛出异常如果请求不成功
        app.logger.info(f"Webhook response: {response.text}")
    except Exception as e:
        app.logger.error(f"Error calling webhook: {e}")


# 添加预算获取函数
def get_firefly_budgets():
    headers = firefly_headers
    today = datetime.datetime.today()
    start_date = today.replace(day=1).strftime('%Y-%m-%d')
    end_of_month = (today.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
    end_date = end_of_month.strftime('%Y-%m-%d')

    budgets_url = f'{FIREFLY_API_URL}/budgets'
    response = requests.get(budgets_url, headers=headers)
    response.raise_for_status()
    budgets = response.json()['data']

    result = []

    for budget in budgets:
        budget_id = budget['id']
        name = budget['attributes']['name']

        # 获取该预算的全部限额（limits）
        limits_url = f'{FIREFLY_API_URL}/budgets/{budget_id}/limits?start_date={start_date}&end_date={end_date}'
        limits_response = requests.get(limits_url, headers=headers)
        limits_response.raise_for_status()
        limits_data = limits_response.json()['data']

        total_budget = 0.0
        total_spent = 0.0

        for limit in limits_data:
            limit_attr = limit['attributes']
            limit_start = limit_attr['start']
            limit_amount = limit_attr.get('amount', '0')
            limit_spent = limit_attr.get('spent', '0')

            # 仅统计本月且开始时间不超过今天的周期
            if limit_start <= today.strftime('%Y-%m-%d'):
                total_budget += float(limit_amount) if limit_amount else 0.0
                total_spent += abs(float(limit_spent)) if limit_spent else 0.0  # spent是负数，取正

        remaining = total_budget - total_spent
        if remaining < 0:
            remaining = 0.0

        result.append({
            'name': name,
            'total_budget': round(total_budget, 2),
            'total_spent': round(total_spent, 2),
            'remaining': round(remaining, 2)
        })

    return result

# 添加预算查询路由
@app.route('/budgets', methods=['GET'])
@track_performance('budgets_endpoint')
def get_budgets():
    """获取预算信息的API端点 - 使用新的服务层架构"""
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
        
        # 如果指定了budget_id，使用新的服务层获取特定预算限制
        if query_params.budget_id:
            query_dict = {
                'start': query_params.start_date,
                'end': query_params.end_date
            }
            result = firefly_service.get_budget_limits(
                query_params.budget_id, 
                query_dict
            )
            
            # 构建响应格式
            budget_info = {
                'budget_id': query_params.budget_id,
                'total_limit': result['total_limit'],
                'current_limit_amount': result['current_limit'],
                'date_range': {
                    'start': query_params.start_date,
                    'end': query_params.end_date
                }
            }
            
            metrics.increment('budgets_specific_success')
            return jsonify(APIResponseBuilder.success_response(
                budget_info, 
                "成功获取预算限制信息"
            ))
        
        # 否则使用原有逻辑获取所有预算
        budgets = get_firefly_budgets()
        if not budgets:
            metrics.increment('budgets_all_empty')
            return jsonify(APIResponseBuilder.error_response(
                '未找到预算数据', 404
            )), 404
        
        metrics.increment('budgets_all_success')
        return jsonify(APIResponseBuilder.success_response(
            budgets,
            "成功获取所有预算信息"
        ))
        
    except Exception as e:
        app.logger.error(f'Budget endpoint error: {str(e)}', exc_info=True)
        metrics.increment('budgets_error')
        return jsonify(APIResponseBuilder.error_response(
            '服务器内部错误', 500
        )), 500

@app.route('/add_transaction', methods=['POST'])
@track_performance('add_transaction_endpoint')
def add_transaction():
    """添加交易的API端点 - 使用新的服务层架构"""
    try:
        # 获取并验证请求数据
        try:
            raw_data = request.get_data().decode('utf-8')
            app.logger.info(f"Received transaction request, data length: {len(raw_data)}")
            
            # 解析JSON数据
            data = json.loads(raw_data)
            
            # 基本数据验证
            if not isinstance(data, dict):
                raise ValueError("请求数据必须是JSON对象")
                
        except json.JSONDecodeError as e:
            app.logger.error(f"JSON解析失败: {str(e)}")
            metrics.increment('add_transaction_json_error')
            return jsonify(APIResponseBuilder.error_response(
                f"无效的JSON格式: {str(e)}", 400
            )), 400
        except Exception as e:
            app.logger.error(f"请求数据处理失败: {str(e)}")
            metrics.increment('add_transaction_request_error')
            return jsonify(APIResponseBuilder.error_response(
                f"请求处理失败: {str(e)}", 400
            )), 400

        # 使用服务层添加交易
        try:
            result = firefly_service.add_transaction(data)
            
            if result.get('success'):
                metrics.increment('add_transaction_success')
                return jsonify(APIResponseBuilder.success_response(
                    result.get('data'), 
                    "交易添加成功"
                ))
            else:
                metrics.increment('add_transaction_service_error')
                return jsonify(APIResponseBuilder.error_response(
                    result.get('error', '添加交易失败'), 
                    result.get('status_code', 500)
                )), result.get('status_code', 500)
                
        except Exception as e:
            app.logger.error(f"服务层处理失败: {str(e)}", exc_info=True)
            metrics.increment('add_transaction_service_exception')
            return jsonify(APIResponseBuilder.error_response(
                '交易处理服务异常', 500
            )), 500
            
    except Exception as e:
        app.logger.error(f"添加交易端点异常: {str(e)}", exc_info=True)
        metrics.increment('add_transaction_endpoint_error')
        return jsonify(APIResponseBuilder.error_response(
            '服务器内部错误', 500
        )), 500

@app.route("/dify_webhook", methods=["POST"])
@track_performance('dify_webhook_endpoint')
def dify_webhook():
    """Dify智能助手的Webhook端点 - 使用新的服务层架构"""
    try:
        # 请求数据验证
        try:
            raw_payload = request.get_json(force=True)
            if not raw_payload:
                raise ValueError("请求体不能为空")
            
            # 使用Pydantic验证请求数据
            webhook_request = DifyWebhookRequest(**raw_payload)
            app.logger.info(f"[Dify] 验证通过的请求: {webhook_request.api_endpoint}")
            
        except ValidationError as e:
            app.logger.error(f"[Dify] 请求验证失败: {e}")
            metrics.increment('dify_webhook_validation_error')
            return jsonify(APIResponseBuilder.error_response(
                f"请求格式错误: {str(e)}", 400
            )), 400
        except Exception as e:
            app.logger.error(f"[Dify] 请求解析失败: {str(e)}")
            metrics.increment('dify_webhook_parse_error')
            return jsonify(APIResponseBuilder.error_response(
                f"请求解析失败: {str(e)}", 400
            )), 400

        # 根据API端点路由到对应的服务方法
        try:
            if webhook_request.api_endpoint == "/transactions":
                # 查询交易记录
                query_params = webhook_request.query_parameters or {}
                result = firefly_service.get_transactions(query_params)
                
                if result.get('success'):
                    # 格式化交易数据
                    transactions_data = result.get('data', [])
                    total_records = result.get('total_records', len(transactions_data))
                    filtered_count = result.get('filtered_count', len(transactions_data))
                    formatted_result = {
                        "summary": f"共找到 {filtered_count} 条交易记录",
                        "transactions": [
                            {
                                "description": t["attributes"]["transactions"][0].get("description", "未提供描述"),
                                "amount": float(t["attributes"]["transactions"][0].get("amount", "0")),
                                "date": t["attributes"]["transactions"][0].get("date", "未提供日期")
                            } for t in transactions_data
                        ]
                    }
                    metrics.increment('dify_webhook_transactions_success')
                    return jsonify(APIResponseBuilder.success_response(
                        formatted_result, "交易记录查询成功"
                    ))
                else:
                    metrics.increment('dify_webhook_transactions_error')
                    return jsonify(APIResponseBuilder.error_response(
                        result.get('error', '交易记录查询失败'), 
                        result.get('status_code', 500)
                    )), result.get('status_code', 500)
                    
            elif webhook_request.api_endpoint == "/budgets":
                # 查询预算信息 - 使用现有的预算查询逻辑
                query_params = BudgetQueryParams(
                    start=webhook_request.query_parameters.get('start') if webhook_request.query_parameters else None,
                    end=webhook_request.query_parameters.get('end') if webhook_request.query_parameters else None
                )
                
                # 使用现有的get_firefly_budgets函数（保持兼容性）
                budget_result = get_firefly_budgets()
                
                if isinstance(budget_result, tuple):
                    # 错误响应
                    error_data, status_code = budget_result
                    metrics.increment('dify_webhook_budgets_error')
                    return jsonify(APIResponseBuilder.error_response(
                        error_data.get('detail', '预算查询失败'), status_code
                    )), status_code
                else:
                    # 成功响应，格式化为Dify格式
                    budget_data = budget_result  # get_firefly_budgets直接返回列表
                    formatted_result = {
                        "summary": f"共找到 {len(budget_data)} 个预算项目",
                        "budgets": budget_data
                    }
                    metrics.increment('dify_webhook_budgets_success')
                    return jsonify(APIResponseBuilder.success_response(
                        formatted_result, "预算信息查询成功"
                    ))
            else:
                # 不支持的API端点
                metrics.increment('dify_webhook_unsupported_endpoint')
                return jsonify(APIResponseBuilder.error_response(
                    f"不支持的API端点: {webhook_request.api_endpoint}", 400
                )), 400
                
        except Exception as e:
            app.logger.error(f"[Dify] 服务处理失败: {str(e)}", exc_info=True)
            metrics.increment('dify_webhook_service_error')
            return jsonify(APIResponseBuilder.error_response(
                '服务处理异常', 500
            )), 500
            
    except Exception as e:
        app.logger.error(f"[Dify] Webhook处理异常: {str(e)}", exc_info=True)
        metrics.increment('dify_webhook_endpoint_error')
        return jsonify(APIResponseBuilder.error_response(
            '服务器内部错误', 500
        )), 500

if __name__ == '__main__':
    app.run(
        host='0.0.0.0', 
        port=9012,
    )
