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
app = Flask(__name__)

# 设置日志级别
logging.basicConfig(level=logging.DEBUG)

# 从配置文件中加载配置
basedir = os.path.abspath(os.path.dirname(__file__))
app.config.from_pyfile(os.path.join(basedir, 'conf/config.py'))


# 从配置获取webhook密钥（需要在config.py中添加）
WEBHOOK_SECRET = app.config.get('WEBHOOK_SECRET')
if not WEBHOOK_SECRET:
    raise ValueError("WEBHOOK_SECRET未在配置文件中设置")
WEBHOOK_SECRET_UPDATE = app.config.get('WEBHOOK_SECRET_UPDATE')
url = app.config.get('WEBHOOK_URL')
headers = {"Content-Type": "application/json"}
FIREFLY_ACCESS_TOKEN = app.config.get('FIREFLY_ACCESS_TOKEN')
FIREFLY_API_URL = app.config.get('FIREFLY_API_URL')

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
    headers = {
        'Authorization': f'Bearer {FIREFLY_ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }

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
def get_budgets():
    try:
        budgets = get_firefly_budgets()
        if not budgets:
            return jsonify({'error': '获取预算失败'}), 500
        return jsonify(budgets)
    except Exception as e:
        app.logger.error(f'Budget endpoint error: {str(e)}')
        return jsonify({'error': '服务器内部错误'}), 500

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    try:
        # 获取原始请求数据并记录日志
        raw_data = request.get_data().decode('utf-8')
        app.logger.info(f"Received raw transaction data: {raw_data}")
        
        # 手动解析JSON并捕获解析错误
        data = json.loads(raw_data)
    except json.JSONDecodeError as e:
        app.logger.error(f"JSON解析失败: {str(e)}, 原始数据: {raw_data}")
        return jsonify({
            "status": "error", 
            "detail": f"无效的JSON格式: {str(e)}",
            "raw_data": raw_data  # 仅用于调试，生产环境应移除
        }), 400
    except Exception as e:
        app.logger.error(f"请求处理失败: {str(e)}")
        return jsonify({"status": "error", "detail": str(e)}), 400

    headers = {
        'Authorization': f'Bearer {FIREFLY_ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(
            f"{FIREFLY_API_URL}/transactions",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        return jsonify({"status": "success", "response": response.json()})
    except Exception as e:
        app.logger.error(f"添加交易失败: {e}")
        return jsonify({"status": "error", "detail": str(e)}), 500


if __name__ == '__main__':
    app.run(
        host='0.0.0.0', 
        port=9012,
    )
