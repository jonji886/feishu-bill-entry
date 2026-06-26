---
name: feishu-bill-entry
version: 1.0.0
description: "飞书账单自然语言录入：将用户的中文记账语句解析为结构化账单并写入飞书多维表格明细表。用户说出如“今天中饭消费 30 元”“昨晚打车 45”“退了外卖 25”时使用。"
metadata:
  short-description: Natural-language bill entry for Feishu Base
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli feishu-bill-entry --help"
---

# 飞书账单自然语言录入（精简执行版）

> 本文件面向 Agent 执行，保留最小必需规则以减少 token 消耗。  
> 详细说明、流程图、FAQ、自测样例见 `README.md`。

## 目标

将中文自然语言账单转换为结构化记录并写入飞书多维表格 `明细表`。

## 必要前置

- `lark-cli` 已登录并具备 Base 读写权限。
- 已提供 `base_token` 与 `table_id`。
- 目标表包含字段：`日期` `月份` `支付平台` `类型` `收支类型` `订单号` `流水说明` `款项`。

## 强约束（必须遵守）

1. 只写入 `明细表`，不处理月度统计表。
2. `类型` 只能使用已有枚举，不得新增或猜测。
3. 类型存在多候选或缺失时，必须返回 `ask_user`，不可写入。
4. 仅当 `action=create_record` 时才允许调用写入脚本。
5. `退款` 按负支出处理（`收支类型=支出`，`款项` 为负数）。
6. `流水说明` 应保留“描述文本”，去掉金额片段。

## 输入输出契约

`parse_bill.py` 输出 JSON：

- `action=create_record`：可写入
- `action=ask_user`：仅追问，不写入
- `action=reject`：拒绝处理

记录字段：

- `date` `month` `payment_platform` `category`
- `income_type` `order_no` `note` `amount`

## 决策规则（简版）

- 金额缺失或多个金额：`ask_user`
- 类型缺失/歧义：`ask_user`
- 日期默认今天，支持昨天/前天
- 支付平台仅识别：`支付宝` `微信` `信用卡`
- 收入分类来自 `references/type-map.json` 的 `income_categories`

## 本地映射源

- 类型映射与收入分类：`references/type-map.json`
- 更新分类词优先改该文件，避免改解析逻辑

## 执行命令

```bash
# 仅解析
python3 scripts/parse_bill.py --text "中饭 30元"

# 解析 + dry-run 写入
python3 scripts/parse_bill.py --text "中饭 30元" \
  | python3 scripts/write_bill.py \
      --base-token "<your_base_token>" \
      --table-id "<your_table_id>" \
      --expected-table-name "明细表" \
      --dry-run
```

## Token 优化原则

- 规则优先，模型兜底
- 输出最小化：只给结构化结果或单条追问
- 避免在执行阶段重复加载长文档说明
