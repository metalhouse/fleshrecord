# API Token 安全认证指南

本指南介绍了如何使用新的API Token认证机制来保护交易API端点。

## 概述

为了提高系统安全性，`/add_transaction` API端点现在需要双重验证：
1. **用户身份验证**: `X-User-ID` header
2. **API Token验证**: `Authorization: Bearer <token>` header

## 安全特性

- ✅ **强随机Token**: 使用加密安全的随机数生成器创建64字符的十六进制token
- ✅ **用户隔离**: 每个用户拥有独立的API token
- ✅ **时序攻击防护**: 使用安全的字符串比较函数
- ✅ **灵活管理**: 支持生成、撤销和验证token
- ✅ **详细日志**: 记录所有认证尝试

## Token管理

### 为用户生成token

```bash
python manage_tokens.py generate <user_id>
```

示例：
```bash
python manage_tokens.py generate metalhouse
```

### 强制重新生成token

```bash
python manage_tokens.py generate <user_id> --force
```

### 撤销用户token

```bash
python manage_tokens.py revoke <user_id>
```

### 列出所有用户token状态

```bash
python manage_tokens.py list
```

### 验证token

```bash
python manage_tokens.py validate <user_id> <token>
```

## API使用方法

### 新的请求格式

现在调用 `/add_transaction` API需要包含以下headers：

```bash
curl -X POST http://192.168.1.90:9012/add_transaction \
  -H 'X-User-ID: metalhouse' \
  -H 'Authorization: Bearer 44b9da2e7db4dd60dbe6ffe556acca7721c5b392d85e67e1bd90436b1c01fd3f' \
  -H 'Content-Type: application/json' \
  -d '{
    "amount": 25.50,
    "description": "午餐费用",
    "date": "2025-09-08",
    "source_account": "现金账户",
    "destination_account": "餐饮",
    "category": "餐饮"
  }'
```

### JavaScript/Fetch示例

```javascript
const response = await fetch('http://192.168.1.90:9012/add_transaction', {
  method: 'POST',
  headers: {
    'X-User-ID': 'metalhouse',
    'Authorization': 'Bearer 44b9da2e7db4dd60dbe6ffe556acca7721c5b392d85e67e1bd90436b1c01fd3f',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    amount: 25.50,
    description: '午餐费用',
    date: '2025-09-08',
    source_account: '现金账户',
    destination_account: '餐饮',
    category: '餐饮'
  })
});

const result = await response.json();
console.log(result);
```

### Python requests示例

```python
import requests

url = 'http://192.168.1.90:9012/add_transaction'
headers = {
    'X-User-ID': 'metalhouse',
    'Authorization': 'Bearer 44b9da2e7db4dd60dbe6ffe556acca7721c5b392d85e67e1bd90436b1c01fd3f',
    'Content-Type': 'application/json'
}
data = {
    'amount': 25.50,
    'description': '午餐费用',
    'date': '2025-09-08',
    'source_account': '现金账户',
    'destination_account': '餐饮',
    'category': '餐饮'
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
```

## 错误处理

### 可能的错误响应

1. **缺少用户ID (401)**
```json
{
  "status": "error",
  "message": "X-User-ID header is required",
  "code": 401
}
```

2. **缺少Authorization header (401)**
```json
{
  "status": "error",
  "message": "Authorization header is required",
  "code": 401
}
```

3. **无效的Authorization header格式 (401)**
```json
{
  "status": "error",
  "message": "Invalid Authorization header format. Expected: Bearer <token>",
  "code": 401
}
```

4. **无效的API token (403)**
```json
{
  "status": "error",
  "message": "Invalid API token",
  "code": 403
}
```

5. **用户配置不存在 (404)**
```json
{
  "status": "error",
  "message": "User configuration not found",
  "code": 404
}
```

## 配置文件结构

用户配置文件 (`data/users/<user_id>.json`) 现在包含 `api_token` 字段：

```json
{
  "firefly_access_token": "eyJ0eXAiOiJKV1QiLCJ...",
  "webhook_url": "https://...",
  "webhook_secret": "...",
  "webhook_secret_update": "...",
  "api_token": "44b9da2e7db4dd60dbe6ffe556acca7721c5b392d85e67e1bd90436b1c01fd3f",
  "firefly_api_url": "http://192.168.1.195:9941/api/v1",
  "notification_enabled": true,
  "language": "zh",
  "dify_config": { ... },
  "report_config": { ... }
}
```

## 安全建议

1. **Token保密**: 将API token视为密码，不要在日志、代码库或不安全的地方存储
2. **定期轮换**: 定期重新生成API token以提高安全性
3. **权限最小化**: 每个用户只能使用自己的token
4. **监控日志**: 定期检查认证日志，发现异常访问
5. **HTTPS传输**: 在生产环境中始终使用HTTPS传输token

## 迁移指南

### 现有API调用更新

如果你之前使用的是：
```bash
curl -X POST http://192.168.1.90:9012/add_transaction?Authorization=Bearer <some-token> \
  -H 'X-User-ID: metalhouse' \
  -H 'Content-Type: application/json' \
  -d '{ ... }'
```

现在需要改为：
```bash
curl -X POST http://192.168.1.90:9012/add_transaction \
  -H 'X-User-ID: metalhouse' \
  -H 'Authorization: Bearer <user-specific-api-token>' \
  -H 'Content-Type: application/json' \
  -d '{ ... }'
```

### 步骤

1. 为每个用户生成API token
2. 更新客户端代码以使用新的token
3. 测试API调用
4. 监控认证日志

## 常见问题

### Q: 忘记了API token怎么办？
A: 使用 `python manage_tokens.py list` 查看token前缀，或重新生成token。

### Q: 如何批量为所有用户生成token？
A: 可以编写脚本调用管理工具：
```bash
for user in $(python manage_tokens.py list | tail -n +3 | awk '{print $1}'); do
  python manage_tokens.py generate "$user" --force
done
```

### Q: Token会过期吗？
A: 当前版本的token不会自动过期，但建议定期手动轮换。

### Q: 可以使用同一个token给多个用户吗？
A: 不可以，每个用户必须使用自己专属的token。

## 技术实现

- Token生成：使用 `secrets.token_hex(32)` 生成64字符的安全随机token
- Token验证：使用 `secrets.compare_digest()` 进行安全的字符串比较
- 存储格式：明文存储在用户配置文件中（建议后续版本考虑加密存储）
