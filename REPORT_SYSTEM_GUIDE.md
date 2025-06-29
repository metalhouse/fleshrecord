# 定期财务报告系统使用指南

## 概述

定期财务报告系统是 FleshRecord 的一个重要功能，它可以:
- 定期调用 Dify 工作流 API 生成财务报告
- 支持日报、周报、月报、年报四种类型
- 通过企业微信 webhook 推送报告
- 为每个用户独立配置 API Key 和报告计划

## 快速开始

### 1. 环境配置

首先在 `.env` 文件中配置 Dify API 地址:

```bash
# Dify API 配置
DIFY_API_URL=https://api.dify.ai/v1
```

### 2. 用户配置

使用配置脚本快速设置:

```bash
python setup_dify.py
```

或者手动编辑用户配置文件 `data/users/{user_id}.json`:

```json
{
    "user_id": "your_user_id",
    "dify_config": {
        "enabled": true,
        "api_key": "your_dify_api_key",
        "workflow_id": "your_workflow_id"
    },
    "report_config": {
        "daily_enabled": true,
        "daily_time": "09:00",
        "daily_prompt": "请生成今日财务报告，分析支出和收入情况",
        
        "weekly_enabled": true,
        "weekly_day": 1,
        "weekly_time": "09:00",
        "weekly_prompt": "请生成本周财务报告，分析支出趋势和预算执行情况",
        
        "monthly_enabled": true,
        "monthly_day": 1,
        "monthly_time": "09:00",
        "monthly_prompt": "请生成本月财务报告，分析月度预算执行和支出分类",
        
        "yearly_enabled": true,
        "yearly_month": 1,
        "yearly_day": 1,
        "yearly_time": "09:00",
        "yearly_prompt": "请生成年度财务报告，总结全年财务状况和支出分析"
    }
}
```

### 3. 启动应用

```bash
python app.py
```

应用启动后，调度服务会自动开始工作，按配置的时间发送报告。

## 配置选项详解

### Dify 配置 (`dify_config`)

- `enabled`: 是否启用 Dify 功能
- `api_key`: Dify API 密钥（每个用户独立配置）
- `workflow_id`: Dify 工作流 ID

### 报告配置 (`report_config`)

#### 日报配置
- `daily_enabled`: 是否启用日报
- `daily_time`: 发送时间（HH:MM 格式）
- `daily_prompt`: 日报生成提示词

#### 周报配置
- `weekly_enabled`: 是否启用周报
- `weekly_day`: 发送日期（1-7，1=周一）
- `weekly_time`: 发送时间
- `weekly_prompt`: 周报生成提示词

#### 月报配置
- `monthly_enabled`: 是否启用月报
- `monthly_day`: 发送日期（1-31）
- `monthly_time`: 发送时间
- `monthly_prompt`: 月报生成提示词

#### 年报配置
- `yearly_enabled`: 是否启用年报
- `yearly_month`: 发送月份（1-12）
- `yearly_day`: 发送日期（1-31）
- `yearly_time`: 发送时间
- `yearly_prompt`: 年报生成提示词

## 系统架构

### 核心组件

1. **ReportService** (`services/report_service.py`)
   - 负责生成各类型报告
   - 从 Firefly 获取交易数据
   - 调用 Dify API 生成报告

2. **SchedulerService** (`services/scheduler_service.py`)
   - 管理定时任务
   - 检查用户配置
   - 执行报告生成和发送

3. **DifyService** (`services/dify_service.py`)
   - 处理与 Dify API 的交互
   - 格式化财务数据
   - 生成报告内容

4. **NotificationHandler** (`handlers/notification_handler.py`)
   - 发送企业微信通知
   - 处理 webhook 消息

### 工作流程

1. **调度检查**: 每分钟检查是否有需要执行的报告任务
2. **数据获取**: 从 Firefly III 获取相关时间范围的财务数据
3. **报告生成**: 调用 Dify API 生成格式化报告
4. **消息发送**: 通过企业微信 webhook 发送报告
5. **日志记录**: 记录执行状态和错误信息

## 测试和验证

运行测试脚本验证系统功能:

```bash
python test_report_system.py
```

测试包括:
- 用户配置验证
- Dify 服务连接测试
- 报告服务功能测试
- 调度服务测试
- 通知功能测试

## 配置管理工具

使用 `utils/config_manager.py` 进行配置管理:

```bash
python utils/config_manager.py list_users
python utils/config_manager.py config_dify <user_id>
python utils/config_manager.py config_reports <user_id>
python utils/config_manager.py show_config <user_id>
```

## 故障排除

### 常见问题

1. **Dify API 连接失败**
   - 检查 `.env` 中的 `DIFY_API_URL` 配置
   - 验证用户的 `api_key` 和 `workflow_id`
   - 检查网络连接

2. **报告未按时发送**
   - 确认报告配置已启用 (`*_enabled: true`)
   - 检查时间格式是否正确
   - 查看应用日志获取错误信息

3. **企业微信通知失败**
   - 验证 `webhook_url` 配置
   - 检查企业微信机器人设置
   - 确认网络连接正常

### 日志查看

应用日志保存在 `logs/` 目录下，包含详细的执行信息和错误记录。

## 安全注意事项

1. **API 密钥保护**
   - 不要在代码中硬编码 API 密钥
   - 使用环境变量或配置文件存储敏感信息
   - 定期轮换 API 密钥

2. **访问控制**
   - 限制配置文件的访问权限
   - 使用 HTTPS 进行 API 通信
   - 验证 webhook 请求来源

3. **数据隐私**
   - 不在日志中记录敏感财务数据
   - 使用加密存储重要配置信息
   - 遵循数据保护法规

## 扩展和定制

### 添加新的报告类型

1. 在 `ReportService` 中添加新的生成方法
2. 在 `SchedulerService` 中添加检查逻辑
3. 更新用户配置模型
4. 更新配置脚本和文档

### 自定义报告内容

通过修改 `*_prompt` 配置，可以自定义报告的内容和格式:
- 添加特定的分析维度
- 调整报告的详细程度
- 包含特定的财务指标

### 集成其他服务

系统设计支持扩展，可以:
- 集成其他 AI 服务替代 Dify
- 添加更多通知渠道（邮件、短信等）
- 集成更多财务数据源

---

有问题或需要帮助，请查看项目文档或提交 Issue。