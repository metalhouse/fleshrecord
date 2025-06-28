# 多用户配置指南

## 概述
本指南介绍如何配置和使用多用户功能，使家庭成员能够独立使用应用而不相互干扰。

## 配置文件结构
用户配置文件存储在 `data/users/` 目录下，每个用户一个JSON文件，文件名为 `<user_id>.json`。

### 配置文件格式
```json
{
    "firefly_access_token": "用户的Firefly访问令牌",
    "webhook_url": "用户的Webhook通知URL",
    "webhook_secret": "Webhook签名密钥",
    "webhook_secret_update": "更新操作的Webhook签名密钥",
    "firefly_api_url": "可选，覆盖全局的Firefly API URL",
    "notification_enabled": true,  // 是否启用通知
    "language": "zh"  // 语言偏好
}
```

## 添加家庭成员
1. 在 `data/users/` 目录下为每个成员创建一个JSON文件
2. 文件名格式: `<成员唯一标识>.json` (例如: `dad.json`, `mom.json`, `son.json`)
3. 复制 `example_user.json` 内容并修改为该成员的实际配置

## API请求要求
所有API请求必须包含 `X-User-ID` 请求头，指定要使用的用户配置：

```http
POST /add_transaction HTTP/1.1
Host: your-server.com
X-User-ID: dad
Content-Type: application/json

{"transaction_data": ...}
```

## 管理用户配置
### 添加新用户
```powershell
# 复制示例配置创建新用户
copy data\users\example_user.json data\users\new_user.json
# 编辑新用户配置
notepad data\users\new_user.json
```

### 删除用户
```powershell
# 删除用户配置文件
remove-item data\users\user_to_delete.json
```

## 故障排除
1. **404 User configuration not found**
   - 确保 `X-User-ID` 请求头正确
   - 确认 `data/users/<user_id>.json` 文件存在

2. **权限错误**
   - 确保应用程序有权读写 `data/users/` 目录

3. **签名验证失败**
   - 检查用户配置中的 `webhook_secret` 是否与发送方匹配

## 示例
### 创建用户配置
为家庭成员"小明"创建配置：
1. 创建文件 `data/users/xiaoming.json`
2. 填入配置：
```json
{
    "firefly_access_token": "xiaoming_firefly_token_123",
    "webhook_url": "https://xiaoming_webhook.example.com",
    "webhook_secret": "xiaoming_webhook_secret",
    "webhook_secret_update": "xiaoming_webhook_update_secret",
    "notification_enabled": true,
    "language": "zh"
}
```

### 使用curl发送请求
```bash
curl -X POST https://your-server.com/add_transaction \
  -H "X-User-ID: xiaoming" \
  -H "Content-Type: application/json" \
  -d '{"description":"超市购物","amount":150.50,"category":"日常开销"}'
```