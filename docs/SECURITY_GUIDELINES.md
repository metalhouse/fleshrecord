# 敏感信息处理安全指南

## 概述

本项目严格遵循敏感信息保护原则，确保用户的财务数据和隐私信息得到妥善保护。

## 敏感信息分类

### 1. 金融敏感信息
- 交易金额 (amount, foreign_amount)
- 账户余额 (balance)
- 工资信息 (salary)
- 银行账户信息 (bank_account)
- 信用卡信息 (credit_card)

### 2. 认证敏感信息
- 密码 (password)
- 访问令牌 (token)
- API密钥 (key, api_key)
- 会话信息 (session, cookie)
- 授权信息 (authorization)

## 安全处理机制

### 1. 日志过滤

项目使用 `SensitiveDataFilter` 类来统一处理敏感信息过滤：

```python
from utils.sensitive_data_filter import SensitiveDataFilter

# 过滤字典数据
safe_data = SensitiveDataFilter.filter_dict(original_data)

# 过滤消息文本
safe_message = SensitiveDataFilter.filter_message(message)

# 过滤HTTP头
safe_headers = SensitiveDataFilter.filter_headers(headers)
```

### 2. 日志记录规范

- **生产环境**: 所有包含用户数据的日志必须经过敏感信息过滤
- **开发环境**: 建议使用过滤器，避免敏感数据泄露到开发日志中
- **测试环境**: 使用模拟数据，避免真实用户数据

### 3. 消息通知

```python
# 正确方式：构建安全的通知消息
safe_message = self.build_safe_notification_message(transaction_info)
app.logger.info(f"处理成功: {safe_message}")

# 错误方式：直接记录包含敏感信息的消息
message = self.build_notification_message(transaction_info)  # 包含金额
app.logger.info(f"处理成功: {message}")  # 敏感信息泄露
```

## 开发规范

### 1. 新功能开发

- 在记录任何用户数据前，必须评估是否包含敏感信息
- 使用 `SensitiveDataFilter` 进行数据过滤
- 在代码审查中检查敏感信息处理是否正确

### 2. 日志审查

定期审查应用程序日志，确保：
- 没有明文记录金融金额
- 没有记录认证令牌或密码
- 所有敏感字段都被正确标记为 `[FILTERED]`

### 3. 错误处理

```python
try:
    # 业务逻辑
    process_transaction(data)
except Exception as e:
    # 错误日志中避免包含敏感数据
    safe_data = SensitiveDataFilter.filter_dict(data)
    app.logger.error(f"处理失败: {e}, 数据: {safe_data}")
```

## 配置管理

### 1. 敏感字段配置

在 `SensitiveDataFilter` 类中维护敏感字段列表：

```python
SENSITIVE_FIELDS = {
    'amount', 'foreign_amount', 'salary', 'balance', 
    'password', 'token', 'key', 'secret'
}
```

### 2. 过滤规则扩展

根据业务需求，可以扩展敏感信息过滤规则：

```python
# 添加新的敏感字段
SENSITIVE_FIELDS.add('new_sensitive_field')

# 添加新的过滤模式
SENSITIVE_PATTERNS = [
    r'\b\d{4}-\d{4}-\d{4}-\d{4}\b',  # 信用卡号
    r'\b\d{3}-\d{2}-\d{4}\b'        # 社会保障号
]
```

## 监控和审计

### 1. 日志监控

- 使用日志监控工具检测可能的敏感信息泄露
- 设置关键词警报（如明文金额、未过滤的认证信息）

### 2. 代码审计

- 定期进行代码安全审计
- 使用静态分析工具检测潜在的敏感信息泄露
- 在CI/CD中集成安全检查

### 3. 合规性检查

- 确保符合GDPR、PCI DSS等相关法规要求
- 定期更新安全策略和处理流程

## 应急响应

### 1. 敏感信息泄露处理

如发现敏感信息泄露：

1. 立即停止有问题的服务
2. 评估泄露范围和影响
3. 清理相关日志文件
4. 修复安全漏洞
5. 通知相关方并记录事件

### 2. 预防措施

- 定期轮换API密钥和访问令牌
- 实施最小权限原则
- 加强开发团队安全意识培训

## 工具和资源

### 1. 相关文件

- `utils/sensitive_data_filter.py`: 敏感数据过滤器
- `handlers/webhook_handler.py`: Webhook处理器（包含安全实践示例）

### 2. 检查工具

```bash
# 检查日志中是否包含敏感信息模式
grep -r "费用：[0-9]" logs/
grep -r "amount.*[0-9]" logs/

# 检查代码中潜在的敏感信息泄露
grep -r "logger.*amount" src/
```

---

*本指南将随着项目发展和安全要求变化持续更新。*