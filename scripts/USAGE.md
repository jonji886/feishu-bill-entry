# feishu-bill-entry scripts usage

## 0. required params

Set your own Base info first:

```bash
export FEISHU_BASE_TOKEN="<your_base_token>"
export FEISHU_TABLE_ID="<your_detail_table_id>"
export FEISHU_TABLE_NAME="明细表"
```

## 1. parse only

```bash
python3 scripts/parse_bill.py --text "今天中饭消费 30 元"
```

## 2. parse + dry-run write

```bash
python3 scripts/parse_bill.py --text "今天中饭消费 30 元" \
  | python3 scripts/write_bill.py \
      --base-token "$FEISHU_BASE_TOKEN" \
      --table-id "$FEISHU_TABLE_ID" \
      --expected-table-name "$FEISHU_TABLE_NAME" \
      --dry-run
```

## 3. parse + real write

```bash
python3 scripts/parse_bill.py --text "今天中饭消费 30 元" \
  | python3 scripts/write_bill.py \
      --base-token "$FEISHU_BASE_TOKEN" \
      --table-id "$FEISHU_TABLE_ID" \
      --expected-table-name "$FEISHU_TABLE_NAME"
```

## Notes

- `write_bill.py` only writes when parser output has `action=create_record`.
- If parser returns `ask_user` or `reject`, write script will return that JSON and skip writing.
- Category must map to existing enum options. No new category will be created.
