# FleshRecord 项目

## 项目概述

FleshRecord 是一个基于Python的后端服务项目，主要用于与Firefly III财务管理系统集成，处理财务数据记录和预算信息。项目使用Flask框架、Pydantic数据验证和多种安全机制。

## 主要功能

- 🔗 与Firefly III API集成，获取预算和交易信息
- 📡 处理Dify智能助手的Webhook请求
- 🔐 Webhook签名验证和安全认证
- 📊 提供RESTful API接口查询财务数据
- 📈 速率限制和性能监控
- 🔄 自动重试机制和错误处理
- 📝 完整的日志记录系统

## 项目结构

```
conf/             # 配置文件
  ├── config.py   # 应用配置管理
config/           # 环境配置
  └── env_config.py # 环境变量配置
models/           # 数据模型
  └── request_models.py # Pydantic请求模型
services/         # 业务逻辑
  └── firefly_service.py # Firefly III API服务
utils/            # 工具函数
  ├── response_builder.py # API响应构建器
  ├── retry_decorator.py  # 重试装饰器
  └── metrics.py         # 性能指标收集
tests/            # 测试代码
app.py            # Flask应用入口
.env.example      # 环境变量示例
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