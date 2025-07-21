# 交易类型过滤功能说明

## 概述

为了在查询交易时排除转账交易，我们在 `DifyHandler` 中添加了自动过滤功能。

## 功能特性

### 1. 自动排除转账
- **默认行为**: 当查询参数中没有指定 `type` 时，系统会自动添加 `type=withdrawal,deposit` 来排除转账交易
- **包含的交易类型**:
  - `withdrawal`: 支出交易
  - `deposit`: 收入交易
- **排除的交易类型**:
  - `transfer`: 转账交易

### 2. 手动控制交易类型
如果您需要查询特定类型的交易，可以在查询参数中明确指定 `type` 参数：

#### 查询所有类型的交易（包括转账）
```json
{
    "start": "2024-01-01",
    "end": "2024-12-31",
    "type": "withdrawal,deposit,transfer"
}
```

#### 只查询转账交易
```json
{
    "start": "2024-01-01",
    "end": "2024-12-31",
    "type": "transfer"
}
```

#### 只查询支出交易
```json
{
    "start": "2024-01-01",
    "end": "2024-12-31",
    "type": "withdrawal"
}
```

## 使用示例

### Dify Webhook 请求示例

#### 1. 默认查询（自动排除转账）
```json
{
    "api_endpoint": "/transactions",
    "method": "GET",
    "query_parameters": {
        "start": "2024-01-01",
        "end": "2024-12-31",
        "category": "食物"
    }
}
```
实际执行时会自动添加 `type=withdrawal,deposit`

#### 2. 手动指定包含转账
```json
{
    "api_endpoint": "/transactions",
    "method": "GET",
    "query_parameters": {
        "start": "2024-01-01",
        "end": "2024-12-31",
        "type": "withdrawal,deposit,transfer",
        "category": "食物"
    }
}
```

## 支持的查询参数

| 参数名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `type` | string | 交易类型，多个类型用逗号分隔 | `withdrawal,deposit` |
| `start` | string | 开始日期 (YYYY-MM-DD) | `2024-01-01` |
| `end` | string | 结束日期 (YYYY-MM-DD) | `2024-12-31` |
| `category` | string | 分类名称 | `食物` |
| `tags` | string | 标签，多个标签用逗号分隔 | `tag1,tag2` |

## 交易类型说明

根据 Firefly III API 文档，交易类型包括：

1. **withdrawal** (支出)
   - 从资产账户到费用账户的交易
   - 例如：购买食物、支付账单等

2. **deposit** (收入)
   - 从收入账户到资产账户的交易
   - 例如：工资、奖金等

3. **transfer** (转账)
   - 在两个资产账户之间的转账
   - 例如：从储蓄账户转到支票账户

## 日志记录

当系统自动添加 `type` 参数时，会在日志中记录相关信息：
```
自动添加type参数排除转账交易: withdrawal,deposit
```

## 向后兼容性

- 现有的查询不会受到影响
- 如果已经指定了 `type` 参数，系统不会覆盖
- 所有其他查询参数保持不变
