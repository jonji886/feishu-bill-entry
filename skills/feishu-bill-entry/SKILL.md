---
name: feishu-bill-entry
description: "飞书账单自然语言录入：将用户的中文记账语句解析为结构化账单并写入飞书多维表格明细表。用户说出如“今天中饭消费 30 元”“昨晚打车 45”“退了外卖 25”时使用。"
metadata:
  short-description: Natural-language bill entry for Feishu Base
---

# 飞书账单自然语言录入

> **前置条件：** 先完成 `lark-cli` 登录授权，并确认目标 Base / table 可访问。

## 目标

把一句自然语言账单输入，转成一条可写入飞书多维表格 `明细表` 的记录。

只处理 `明细表`，不涉及月度统计表。

## 工作方式

1. 先做规则抽取，尽量不用大模型推理。
2. 再按本地分类映射表把口语词映射到已有 `类型` 枚举。
3. 如果类型无法唯一命中，先追问用户，不要猜。
4. 如果信息足够明确，再写入 `明细表`。

## 解析规则

- `日期`：默认今天；支持昨天、前天、明确日期。
- `月份`：由 `日期` 自动换算成 `1月` 到 `12月`。
- `收支类型`：只允许 `支出` / `收入`。
- `支付平台`：只用现有选项 `支付宝` / `微信` / `信用卡`；没提到就留空。
- `流水说明`：保留短摘要，不要长篇解释。
- `订单号`：用户明确给出才写。
- `退款`：按负支出处理，不改成收入。

## `类型` 严格约束

- 只能写入已有枚举。
- 不允许新增分类。
- 不允许把口语词原样写进 `类型`。
- 不允许写“近似但不存在”的分类。
- 多候选时必须追问。

完整映射见 [`references/type-map.md`](references/type-map.md)。

## 写入前检查

写入前必须确认：

- 金额已抽取为数值
- 日期已标准化
- `类型` 能唯一映射到现有枚举
- `收支类型` 合法
- 目标表、字段名和字段类型与真实 Base 一致

写入 Base 时优先使用 `lark-cli base +record-upsert`。

## 省 token 策略

- 高频输入走确定性规则
- 映射表放在本地 reference，不重复塞进上下文
- 输出尽量只给结构化草稿或追问
- 只有歧义时才调用模型兜底

## 追问策略

以下情况必须追问：

- 金额缺失或歧义
- 日期不明确
- `类型` 无法唯一映射
- 用户说“改一下”“补一笔”，但没有明确目标记录

追问要短，一次只问最必要的问题。

## 推荐写入字段

优先写入：

- `日期`
- `月份`
- `款项`
- `收支类型`
- `类型`
- `流水说明`

`支付平台` 和 `订单号` 只有在明确时写入。

## 脚本入口

本 skill 提供两个脚本：

1. `scripts/parse_bill.py`
2. `scripts/write_bill.py`

典型用法：

```bash
# 解析一句自然语言
python3 skills/feishu-bill-entry/scripts/parse_bill.py --text "今天中饭消费 30 元"

# 解析后直接写入飞书 Base
export FEISHU_BASE_TOKEN="<your_base_token>"
export FEISHU_TABLE_ID="<your_detail_table_id>"
export FEISHU_TABLE_NAME="明细表"

python3 skills/feishu-bill-entry/scripts/parse_bill.py --text "今天中饭消费 30 元" \
  | python3 skills/feishu-bill-entry/scripts/write_bill.py \
      --base-token "$FEISHU_BASE_TOKEN" \
      --table-id "$FEISHU_TABLE_ID" \
      --expected-table-name "$FEISHU_TABLE_NAME"
```

说明：

- `write_bill.py` 仅接受 `parse_bill.py` 的 JSON 输出作为 stdin。
- 只有 `action=create_record` 才会执行写入。
- `action=ask_user` 或 `action=reject` 时不会写入，并原样返回。
