# FleshRecord 项目

## 项目概述

FleshRecord 是一个基于 Python 的多用户财务自动化服务，集成 Firefly III 财务管理系统与 Dify 智能助手，支持定时自动生成和推送日报、周报、月报、年报至企业微信。项目具备灵活的多用户配置、任务调度防重复、Webhook 安全认证、日志与异常告警等特性，适合个人和团队高效管理财务数据与预算。

## 主要功能

- 🔗 与Firefly III API集成，获取预算和交易信息
- 🤖 集成 Dify 智能助手，自动生成结构化财务报告
- ⏰ 支持定时自动生成日报、周报、月报、年报（多用户多配置）
- 📨 报告自动推送至企业微信（Webhook），格式简洁美观
- 🛡️ 多用户独立配置，支持灵活定制 API Key、推送时间等
- 🕹️ 任务调度防重复，避免多线程/多进程重复推送
- 🔐 Webhook签名验证和安全认证
- 📊 提供RESTful API接口查询财务数据
- 📈 速率限制和性能监控
- 🔄 自动重试机制和错误处理
- 📋 日志记录与异常告警，便于问题追踪与调试


## 使用前提

- 需本地或私有云已部署 Firefly III 财务管理系统，并已获取 API Token。
- 需拥有 Dify 平台账号，并已创建好相关工作流（Workflow），获取 API Key 及 Workflow ID。
- Firefly III 与 Dify 服务需可被本服务访问（建议同局域网或已开放端口）。
- 企业微信需已配置好 Webhook 机器人用于接收推送。

## 项目结构

```
## 项目结构

```
conf/             # 配置文件
  ├── config.py   # 应用配置管理
  └── enhanced_config.py # 增强配置
config/           # 环境配置
  ├── __init__.py
  └── env_config.py # 环境变量配置
models/           # 数据模型
  └── request_models.py # Pydantic请求模型
services/         # 业务逻辑
  └── firefly_service.py # Firefly III API服务
utils/            # 工具函数
  ├── response_builder.py # API响应构建器
  ├── retry_decorator.py  # 重试装饰器
  └── sensitive_data_filter.py # 敏感数据过滤
version.py        # 项目版本信息
tests/            # 测试代码
  ├── __init__.py
  ├── test_firefly_service.py
  └── test_integration.py
app.py            # Flask应用入口
.env.example      # 环境变量示例
```

## 版本管理

项目使用语义化版本号管理，版本信息存储在`version.py`文件中。

### 查看当前版本
```python
# 在Python代码中引用
from version import __version__
print(f"当前版本: {__version__}")
```

### 版本更新流程
1. 修改`version.py`文件中的`__version__`变量
2. 更新版本历史记录
3. 提交更改到Git仓库：
```bash
git add version.py
# 添加版本更新说明
git commit -m "Bump version to x.y.z"
git push origin main
```

### 版本历史
- **0.2.0** - 新功能和改进
- **0.1.0** - 初始版本，包含基本模型和核心功能
```

## 安装步骤

### 1. 克隆项目
```bash
git clone [项目地址]
cd fleshrecord
```

### 2. 创建Python虚拟环境
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 环境配置
请参考 [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) 进行详细的环境变量配置。

**快速配置：**
```bash
# 复制环境变量模板
copy .env.example .env  # Windows
cp .env.example .env    # Linux/macOS

# 编辑 .env 文件，填入实际的配置值
```

## 使用方法

### 1. 启动服务
```bash
python app.py
```

### 2. API端点
服务默认运行在 `http://localhost:9012`，主要端点包括：

- `GET /budgets` - 获取所有预算信息
- `GET /budgets?budget_id=<id>` - 获取指定预算限制
- `POST /add_transaction` - 添加交易记录
- `POST /webhook` - 处理Firefly III webhook
- `POST /dify-webhook` - 处理Dify智能助手webhook

### 3. 健康检查
```bash
curl http://localhost:9012/budgets
```

## 技术栈

- **Python 3.10+** - 编程语言
- **Flask 2.3.3** - Web框架
- **Pydantic 2.5.0** - 数据验证
- **Flask-Limiter** - API速率限制
- **requests** - HTTP客户端
- **python-dotenv** - 环境变量管理
- **pytest** - 测试框架

完整依赖列表请参考 `requirements.txt`。

## 集成说明

### Firefly III集成
- 需要配置Firefly III个人访问令牌
- 支持获取预算和交易数据
- 自动重试机制确保请求可靠性

### Dify智能助手集成
- 支持处理自然语言财务查询
- 提供预算和交易信息的智能响应
- Webhook签名验证确保请求安全

### Dify Webhook 交易多条件过滤与统计（2025-07-15 更新）

- 支持通过 Dify Webhook 进行多条件（如分类、标签等）交易查询过滤。
- 仅支持 POST + JSON body 传参，所有查询参数需放在 `query_parameters` 字段内。
- `tags` 支持字符串、列表、None 等多种格式，系统会自动转为字符串列表后进行精确比对。
- 多条件过滤采用“与”关系，只有同时满足所有条件的交易才会被保留。
- summary 统计数量与实际过滤结果严格一致，日志与 API 返回完全同步。
- 修复了 tags 过滤无效、summary 数量不符等问题。
- 过滤和统计逻辑已通过日志与 Postman 验证。

**用法示例：**

```json
POST /dify_webhook
Headers: { "X-User-ID": "your_user_id" }
Body:
{
  "query_parameters": {
    "category": "餐饮",
    "tags": ["外卖", "工作餐"]
  }
}
```
- `category`、`tags` 可单独或组合使用，均为“与”关系。
- `tags` 可为字符串（单标签）、数组（多标签）、或 None。
- 返回结果中的 `summary` 字段数量与实际 data 数组长度一致。

**注意事项：**
- 仅支持 POST + JSON body 方式，URL query 参数不生效。
- 过滤条件不满足时返回空数组，summary 为 0。
- 详见 `handlers/dify_handler.py` 和 `services/firefly_service.py` 实现。

## 测试

```bash
# 运行所有测试
python run_tests.py

# 使用pytest运行
pytest tests/ -v

# 运行测试覆盖率
pytest --cov=. tests/
```

## 安全说明

⚠️ **重要提醒：**
- 所有敏感信息通过环境变量配置
- 启用了Webhook签名验证
- 实施了API速率限制
- 请定期更换访问令牌和密钥

## 故障排除

常见问题及解决方案请参考 [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md#故障排除)。