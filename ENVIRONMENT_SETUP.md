# 环境变量配置指南

为了增强系统安全性，所有敏感信息现在都通过环境变量进行配置。请按照以下步骤进行设置：

## 1. 安装依赖

首先需要安装 `python-dotenv` 包来支持 `.env` 文件：

```bash
pip install python-dotenv
```

## 2. 创建环境变量文件

### 方法一：使用 .env 文件（推荐用于开发）

1. 复制 `.env.example` 文件为 `.env`：
   ```bash
   copy .env.example .env  # Windows
   # 或
   cp .env.example .env    # Linux/macOS
   ```

2. 编辑 `.env` 文件，填入实际的配置值：
   ```env
   # Firefly III API 配置
   FIREFLY_API_URL=https://your-firefly-instance.com/api/v1
   FIREFLY_ACCESS_TOKEN=eyJ0eXAiOiJKV1Q...
   
   # Webhook 配置
   WEBHOOK_SECRET=your_actual_webhook_secret
   WEBHOOK_SECRET_UPDATE=your_actual_update_secret
   WEBHOOK_URL=https://your-webhook-url.com
   
   # 其他配置...
   ```

### 方法二：设置系统环境变量（推荐用于生产）

#### Windows:
```cmd
setx FIREFLY_ACCESS_TOKEN "your_token_here"
setx WEBHOOK_SECRET "your_secret_here"
setx WEBHOOK_SECRET_UPDATE "your_update_secret_here"
```

#### Linux/macOS:
```bash
export FIREFLY_ACCESS_TOKEN="your_token_here"
export WEBHOOK_SECRET="your_secret_here"
export WEBHOOK_SECRET_UPDATE="your_update_secret_here"

# 添加到 ~/.bashrc 或 ~/.zshrc 以持久保存
echo 'export FIREFLY_ACCESS_TOKEN="your_token_here"' >> ~/.bashrc
```

## 3. 必需的环境变量

以下环境变量是必须设置的，缺少任何一个都会导致应用启动失败：

- `FIREFLY_ACCESS_TOKEN` - Firefly III 的个人访问令牌
- `WEBHOOK_SECRET` - Webhook 验证密钥

## 4. 可选的环境变量

这些变量有默认值，可以根据需要进行自定义：

- `FIREFLY_API_URL` - Firefly III API 地址（默认：http://localhost/api/v1）
- `WEBHOOK_SECRET_UPDATE` - 更新操作的Webhook密钥
- `WEBHOOK_URL` - Webhook 通知地址
- `DEBUG` - 调试模式（默认：false）
- `HOST` - 服务器监听地址（默认：0.0.0.0）
- `PORT` - 服务器端口（默认：9012）
- 更多配置请参考 `.env.example` 文件

## 5. 安全注意事项

### ⚠️ 重要安全提醒

1. **永远不要将 `.env` 文件提交到版本控制系统**
   - 已将 `.env` 添加到 `.gitignore`
   - 只提交 `.env.example` 作为模板

2. **定期更换敏感信息**
   - 定期更换 API 令牌和 Webhook 密钥
   - 使用强密码生成器创建密钥

3. **生产环境推荐使用系统环境变量**
   - 避免在文件系统中存储敏感信息
   - 使用容器编排工具的密钥管理功能

## 6. 验证配置

运行以下命令检查配置是否正确：

```bash
python -c "from config.env_config import env_config; print('配置加载成功:', env_config.get_config_dict())"
```

如果配置正确，你将看到配置信息（敏感信息会被隐藏）。

## 7. 故障排除

### 常见错误及解决方法

1. **"缺少必需的环境变量"** 错误
   - 检查必需的环境变量是否已设置
   - 确认变量名拼写正确
   - 确认值不为空

2. **"无法导入环境配置模块"** 警告
   - 检查是否安装了 `python-dotenv`
   - 检查 `.env` 文件是否存在且格式正确

3. **应用无法连接到 Firefly III**
   - 检查 `FIREFLY_API_URL` 是否正确
   - 验证网络连接
   - 确认 `FIREFLY_ACCESS_TOKEN` 有效

## 8. 迁移说明

如果你是从旧版本升级，原来硬编码的配置已被移除。请：

1. 从 `conf/config.py.bak`（如果存在）中找到之前的配置值
2. 将这些值设置为对应的环境变量
3. 删除备份文件以避免混淆

---

如有任何问题，请查看日志文件或联系系统管理员。