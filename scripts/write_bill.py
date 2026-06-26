#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys

REQUIRED_FIELDS = {"日期", "月份", "支付平台", "类型", "收支类型", "订单号", "流水说明", "款项"}


def read_stdin_json():
    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("stdin is empty; expected parse_bill.py JSON output")
    return json.loads(raw)


def build_payload(record: dict):
    return {
        "日期": record["date"],
        "月份": record["month"],
        "支付平台": record["payment_platform"],
        "类型": record["category"],
        "收支类型": record["income_type"],
        "订单号": record["order_no"],
        "流水说明": record["note"],
        "款项": record["amount"],
    }


def run_upsert(base_token: str, table_id: str, payload: dict, dry_run: bool):
    cmd = [
        "lark-cli",
        "base",
        "+record-upsert",
        "--as",
        "user",
        "--base-token",
        base_token,
        "--table-id",
        table_id,
        "--json",
        json.dumps(payload, ensure_ascii=False),
        "--format",
        "json",
    ]
    if dry_run:
        cmd.append("--dry-run")
    return subprocess.run(cmd, capture_output=True, text=True)


def run_cmd(cmd: list[str]):
    return subprocess.run(cmd, capture_output=True, text=True)


def validate_target_table(base_token: str, table_id: str, expected_table_name: str):
    table_cmd = [
        "lark-cli",
        "base",
        "+table-get",
        "--as",
        "user",
        "--base-token",
        base_token,
        "--table-id",
        table_id,
        "--format",
        "json",
    ]
    table_proc = run_cmd(table_cmd)
    if table_proc.returncode != 0:
        return False, f"table_get_failed: {table_proc.stderr.strip()}"
    try:
        table_json = json.loads(table_proc.stdout)
        table_name = table_json["data"]["table"]["name"]
    except Exception:
        return False, "table_get_parse_failed"

    fields_cmd = [
        "lark-cli",
        "base",
        "+field-list",
        "--as",
        "user",
        "--base-token",
        base_token,
        "--table-id",
        table_id,
        "--format",
        "json",
    ]
    fields_proc = run_cmd(fields_cmd)
    if fields_proc.returncode != 0:
        return False, f"field_list_failed: {fields_proc.stderr.strip()}"
    try:
        fields_json = json.loads(fields_proc.stdout)
        field_names = {f["name"] for f in fields_json["data"]["fields"]}
    except Exception:
        return False, "field_list_parse_failed"

    missing = sorted(REQUIRED_FIELDS - field_names)
    if missing:
        return (
            False,
            f"wrong_table_or_schema: table='{table_name}', missing_fields={','.join(missing)}",
        )

    if expected_table_name and table_name != expected_table_name:
        return False, f"unexpected_table_name: '{table_name}' (expected '{expected_table_name}')"
    return True, ""


def main():
    parser = argparse.ArgumentParser(description="Write parsed bill record into Feishu Base.")
    parser.add_argument("--base-token", required=True, help="Feishu Base token")
    parser.add_argument("--table-id", required=True, help="Target table ID")
    parser.add_argument(
        "--expected-table-name",
        default="",
        help="Optional safety check for table name (e.g. 明细表)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Use lark-cli dry-run mode")
    args = parser.parse_args()

    parsed = read_stdin_json()
    action = parsed.get("action", "")
    if action != "create_record":
        print(json.dumps(parsed, ensure_ascii=False))
        return

    records = parsed.get("records", [])
    if not records:
        print(json.dumps({"ok": False, "error": "no records to write"}, ensure_ascii=False))
        sys.exit(1)

    ok_table, reason = validate_target_table(args.base_token, args.table_id, args.expected_table_name)
    if not ok_table:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "target_table_validation_failed",
                    "reason": reason,
                    "hint": "请检查 --base-token / --table-id / --expected-table-name 是否正确",
                },
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    outputs = []
    for record in records:
        payload = build_payload(record)
        proc = run_upsert(args.base_token, args.table_id, payload, args.dry_run)
        outputs.append(
            {
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "payload": payload,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
            }
        )

    all_ok = all(item["ok"] for item in outputs)
    print(json.dumps({"ok": all_ok, "results": outputs}, ensure_ascii=False))
    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
