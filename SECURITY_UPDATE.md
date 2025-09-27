# 🔒 API安全认证更新说明

## 重要变更

为了提高系统安全性，以下API端点现在需要**双重认证**：

### 🔐 需要Token验证的API端点

1. `POST /add_transaction` - 添加交易
2. `GET /budgets` - 查询预算信息  
3. `POST /dify_webhook` - Dify智能助手webhook
4. `POST /webhook` - 第三方服务webhook（非签名验证部分）

### 📋 认证要求

1. **用户身份**: `X-User-ID` header
2. **API Token**: `Authorization: Bearer <token>` header

## 快速开始

### 1. 为用户生成API Token

```bash
# 为单个用户生成token
python manage_tokens.py generate <user_id>

# 为所有用户批量生成token
python batch_token_manager.py batch-generate
```

### 2. 更新API调用

**之前的调用方式**（不安全）：
```bash
# 添加交易
curl -X POST http://192.168.1.90:9012/add_transaction?Authorization=Bearer <some-token> \
  -H 'X-User-ID: metalhouse'

# 查询预算
curl -X GET http://192.168.1.90:9012/budgets \
  -H 'X-User-ID: metalhouse'
```

**现在的调用方式**（安全）：
```bash
# 添加交易
curl -X POST http://192.168.1.90:9012/add_transaction \
  -H 'X-User-ID: metalhouse' \
  -H 'Authorization: Bearer 44b9da2e7db4dd60dbe6ffe556acca7721c5b392d85e67e1bd90436b1c01fd3f' \
  -H 'Content-Type: application/json' \
  -d '{
    "amount": 25.50,
    "description": "午餐费用",
    "date": "2025-09-08",
    "source_account": "现金账户",
    "destination_account": "餐饮"
  }'

# 查询预算
curl -X GET http://192.168.1.90:9012/budgets \
  -H 'X-User-ID: metalhouse' \
  -H 'Authorization: Bearer 44b9da2e7db4dd60dbe6ffe556acca7721c5b392d85e67e1bd90436b1c01fd3f'

# Dify webhook
curl -X POST http://192.168.1.90:9012/dify_webhook \
  -H 'X-User-ID: metalhouse' \
  -H 'Authorization: Bearer 44b9da2e7db4dd60dbe6ffe556acca7721c5b392d85e67e1bd90436b1c01fd3f' \
  -H 'Content-Type: application/json' \
  -d '{"query": "本月预算执行情况如何？"}'

# 第三方webhook（非签名验证）
curl -X POST http://192.168.1.90:9012/webhook \
  -H 'X-User-ID: metalhouse' \
  -H 'Authorization: Bearer 44b9da2e7db4dd60dbe6ffe556acca7721c5b392d85e67e1bd90436b1c01fd3f' \
  -H 'Content-Type: application/json' \
  -d '{"trigger": "STORE_TRANSACTION", "content": {...}}'
```

### 3. 验证配置

```bash
# 查看所有用户的token状态
python manage_tokens.py list

# 进行安全审计
python batch_token_manager.py audit
```

## 安全特性

✅ **64位随机Token**: 使用加密安全的随机数生成  
✅ **用户隔离**: 每用户独立token，无法跨用户访问  
✅ **时序攻击防护**: 安全的字符串比较  
✅ **详细日志**: 记录所有认证尝试  
✅ **灵活管理**: 支持生成、撤销、验证token  

## 错误响应

- `401` - 缺少认证信息
- `403` - Token验证失败  
- `404` - 用户配置不存在

## 管理命令

```bash
# Token管理
python manage_tokens.py generate <user_id>     # 生成token
python manage_tokens.py revoke <user_id>       # 撤销token
python manage_tokens.py list                   # 列出状态
python manage_tokens.py validate <user_id> <token>  # 验证token

# 批量管理
python batch_token_manager.py batch-generate   # 批量生成
python batch_token_manager.py audit           # 安全审计
python batch_token_manager.py examples        # 生成使用示例
```

## 配置文件变更

用户配置文件现在包含 `api_token` 字段：

```json
{
  "firefly_access_token": "...",
  "api_token": "44b9da2e7db4dd60dbe6ffe556acca7721c5b392d85e67e1bd90436b1c01fd3f",
  "webhook_url": "...",
  "notification_enabled": true,
  ...
}
```

详细文档请参考: [API_TOKEN_SECURITY_GUIDE.md](API_TOKEN_SECURITY_GUIDE.md)
