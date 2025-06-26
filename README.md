# FleshRecord 项目

## 项目概述

FleshRecord 是一个基于Python的后端服务项目，主要用于处理数据记录和API服务。项目使用了FastAPI框架和Pydantic数据验证。

## 主要功能

- 提供RESTful API接口
- 数据验证和格式化
- 日志记录和监控
- 服务重试机制

## 项目结构

```
conf/        # 配置文件
models/      # 数据模型
services/    # 业务逻辑
utils/       # 工具函数
tests/       # 测试代码
```

## 安装步骤

1. 克隆项目仓库
2. 创建虚拟环境: `python -m venv venv`
3. 激活虚拟环境: `venv\Scripts\activate` (Windows)
4. 安装依赖: `pip install -r requirements.txt`

## 使用方法

1. 启动服务: `python app.py`
2. 访问API文档: `http://localhost:8000/docs`

## 依赖

- Python 3.10+
- FastAPI
- Pydantic
- 其他依赖请参考requirements.txt

## 测试

运行测试: `python run_tests.py`