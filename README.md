# feishu-bill-entry

飞书多维表格自然语言记账 — **说一句中文，自动写入飞书账单明细表。**

## 这是什么？

一个命令行工具 + AI Agent skill，把"中饭 30 元""昨晚打车 45"这种日常记账语句，自动解析并写入飞书多维表格（Base）的 `明细表`。信息不全时会先追问，不瞎写。由 `parse_bill.py`（解析）+ `write_bill.py`（写入）两个脚本配合完成。

---

## 前置条件

开始使用前，请确保你已经有：

| 项目 | 说明 |
|------|------|
| Python 3.9+ | 运行脚本 |
| [lark-cli](https://github.com/larksuite/lark-cli) | 飞书命令行工具，已登录并授权 Base 读写权限 |
| 飞书多维表格 | 已创建 `明细表`，包含右侧 8 个字段 → | `日期` · `月份` · `支付平台` · `类型` · `收支类型` · `订单号` · `流水说明` · `款项` |

> 💡 没有 Base？在飞书新建一个多维表格，新建一个「明细表」视图，加上面这些字段即可。

---

## 快速上手（5 分钟）

### 第 1 步：设置环境变量

```bash
export FEISHU_BASE_TOKEN="<你的多维表格 Base Token>"
export FEISHU_TABLE_ID="<你的明细表 Table ID>"
export FEISHU_TABLE_NAME="明细表"
```

> 不知道怎么获取 Token 和 Table ID？请参考 [lark-cli Base 文档](https://github.com/larksuite/lark-cli)。

### 第 2 步：试解析（不下笔）

```bash
python3 scripts/parse_bill.py --text "中饭 30元"
```

你会看到类似这样的输出 —— 说明解析成功：

```json
{"action": "create_record", "records": [{
  "date": "2026-06-26", "month": "6月",
  "payment_platform": "", "category": "餐食（三餐+盒马山姆都算）",
  "income_type": "支出", "order_no": "", "note": "中饭", "amount": 30.0
}], "questions": [], "reason": ""}
```

### 第 3 步：试写入（预览模式）

```bash
python3 scripts/parse_bill.py --text "中饭 30元" \
  | python3 scripts/write_bill.py \
      --base-token "$FEISHU_BASE_TOKEN" \
      --table-id "$FEISHU_TABLE_ID" \
      --expected-table-name "$FEISHU_TABLE_NAME" \
      --dry-run
```

`--dry-run` 表示只校验不写入，安全预览。

### 第 4 步：正式记账

去掉 `--dry-run`，真正写入飞书：

```bash
python3 scripts/parse_bill.py --text "中饭 30元" \
  | python3 scripts/write_bill.py \
      --base-token "$FEISHU_BASE_TOKEN" \
      --table-id "$FEISHU_TABLE_ID" \
      --expected-table-name "$FEISHU_TABLE_NAME"
```

打开飞书多维表格，确认数据已写入 `明细表`。

---

## 使用示例

| 输入 | 类型 | 金额 | 流水说明 | 日期 |
|------|------|------|----------|------|
| `中饭 30元` | 餐食 | 30 | `中饭` | 今天 |
| `昨晚打车 45` | 停车费及其他交通费 | 45 | `打车` | 昨天 |
| `今天地铁往返5元` | 停车费及其他交通费 | 5 | `地铁往返` | 今天 |
| `昨天退了外卖 25` | 餐食 | -25 | `退了外卖` | 昨天 |
| `支付宝交电费 200` | 水电费 | 200 | `交电费` | 今天 |
| `信用卡还房贷 5000` | 房贷 | 5000 | `还房贷` | 今天 |

> - 日期关键词：`今天`（默认）、`昨天`、`前天` → 自动计算
> - 支付平台：`支付宝` `微信` `信用卡` → 自动识别
> - 退款：含"退款/退了"等 → 金额自动为负数

### 信息不全时（系统会先问）

```bash
$ python3 scripts/parse_bill.py --text "打车"
{"action": "ask_user", "questions": ["这笔多少钱？"], "reason": "missing_amount"}
```

```bash
$ python3 scripts/parse_bill.py --text "买了个东西 50"
{"action": "ask_user", "questions": ["这笔记成什么类型？请使用明细表已有分类。"], "reason": "missing_category"}
```

---

## 数据表结构（明细表）

你的飞书多维表格 `明细表` 需要包含以下字段：

| 字段名 | 字段类型 | 示例值 | 说明 |
|--------|----------|--------|------|
| 日期 | 日期 | `2026-06-26` | 消费发生日期，默认今天 |
| 月份 | 单选 | `6月` | 由日期自动换算，用于月度筛选 |
| 支付平台 | 单选 | `支付宝` | 可空，仅识别：支付宝 / 微信 / 信用卡 |
| 类型 | 单选 | `餐食（三餐+盒马山姆都算）` | ⭐ **严格使用已有枚举**，不新增不猜测 |
| 收支类型 | 单选 | `支出` | 仅两个值：`支出` / `收入` |
| 订单号 | 文本 | `202606260001` | 可空，暂未使用 |
| 流水说明 | 文本 | `中饭` | 去掉金额和时间词的纯描述 |
| 款项 | 数字 | `30` / `-25` | 退款按负数处理（如 `-25`） |

### 关于"类型"字段

`类型` 字段的所有可选值及对应关键词，定义在 `references/type-map.json` 中。例如：

```json
{
  "type_map": {
    "餐食（三餐+盒马山姆都算）": ["饭", "餐", "吃", "外卖", "中饭", "早", "晚", "盒马", "山姆", "水果", ...],
    "停车费及其他交通费": ["打车", "地铁", "停车", "公交", "加油", "ETC", ...],
    ...
  }
}
```

> ✏️ 想调整关键词？直接修改 `references/type-map.json` 即可，无需改 Python 代码。

---

## 工作流程

```mermaid
flowchart TD
    A[用户输入: "中饭 30元"] --> B[parse_bill.py 规则解析]
    B --> C{金额、类型<br>都唯一确定?}
    C -->|❌ 缺金额或无匹配| D[返回 ask_user<br>追问具体信息]
    D --> A
    C -->|⚠️ 多个候选| E[返回 ask_user<br>让用户选择]
    E --> A
    C -->|✅ 是| F[构造 create_record]
    F --> G[write_bill.py 校验<br>表名 / 字段 / 枚举]
    G --> H{校验通过?}
    H -->|❌ 否| I[报错并提示修正]
    H -->|✅ 是| J[调用 lark-cli API<br>写入多维表格]
    J --> K[返回写入结果]
```

**核心原则：宁可多问一次，也不写错一笔。**

---

## 什么时候用 / 什么时候不适合

### ✅ 适合

| 场景 | 举例 |
|------|------|
| 日常单笔记账 | `"中饭 30元"` `"昨晚打车 45"` |
| 快速录入飞书多维表 | 说一句话，自动写入 |
| 已有固定分类 | 类型枚举已覆盖你的消费类别 |
| 可接受追问 | 信息不全时愿意回答系统提问 |

### ❌ 暂不适合

| 场景 | 原因 |
|------|------|
| 批量导入历史流水 | 一条条说太慢，建议用 Excel 导入 |
| 截图/拍照识别 | 不支持 OCR，需要文字输入 |
| 自动生成月报/统计图表 | 只负责录入，分析请用 Base 的统计功能 |
| 自动创建新分类 | `类型` 必须使用已有枚举，不会新增 |

---

## 目录结构

```
feishu-bill-entry/
├── README.md                 ← 本文件，新人入门文档
├── SKILL.md                  ← AI Agent 执行文档（精简版）
├── references/
│   └── type-map.json         ← 分类关键词映射表（唯一数据源）
├── scripts/
│   ├── parse_bill.py         ← 自然语言 → 结构化记录
│   ├── write_bill.py         ← 结构化记录 → 飞书 Base
│   └── USAGE.md              ← 脚本参数详解
├── LICENSE
└── .gitignore
```

---

## 许可

[MIT](./LICENSE)
