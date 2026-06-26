#!/usr/bin/env python3
import argparse
import json
import os
import re
from datetime import datetime, timedelta


_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_JSON_PATH = os.path.join(_SCRIPT_DIR, "..", "references", "type-map.json")

with open(_JSON_PATH, "r", encoding="utf-8") as _f:
    _data = json.load(_f)

TYPE_MAP = _data["type_map"]
INCOME_CATEGORIES = set(_data.get("income_categories", []))
PAYMENT_HINTS = {"支付宝": "支付宝", "微信": "微信", "信用卡": "信用卡"}
REFUND_HINTS = ("退款", "退了", "退回", "退我")


def resolve_date(text: str, now: datetime) -> datetime:
    if "前天" in text:
        return now - timedelta(days=2)
    if "昨天" in text or "昨晚" in text:
        return now - timedelta(days=1)
    return now


def extract_amounts(text: str):
    amounts = re.findall(r"(?<!\d)(\d+(?:\.\d+)?)\s*元?", text)
    return [float(x) for x in amounts]


def resolve_category(text: str):
    hits = []
    for category, keywords in TYPE_MAP.items():
        for kw in keywords:
            if kw.lower() in text.lower():
                hits.append(category)
                break
    hits = sorted(set(hits))
    if len(hits) == 1:
        return hits[0], hits
    return None, hits


def resolve_income_type(category: str, text: str):
    if category in INCOME_CATEGORIES:
        return "收入"
    if any(k in text for k in REFUND_HINTS):
        return "支出"
    return "支出"


def resolve_platform(text: str):
    for k, v in PAYMENT_HINTS.items():
        if k in text:
            return v
    return ""


def build_record(text: str, now: datetime):
    amounts = extract_amounts(text)
    if not amounts:
        return {"action": "ask_user", "records": [], "questions": ["这笔多少钱？"], "reason": "missing_amount"}
    if len(amounts) > 1:
        return {
            "action": "ask_user",
            "records": [],
            "questions": [f"我识别到多个金额 {amounts}，本次记哪个？"],
            "reason": "ambiguous_amount",
        }

    category, candidates = resolve_category(text)
    if not category:
        if candidates:
            return {
                "action": "ask_user",
                "records": [],
                "questions": [f"类型有多个候选：{', '.join(candidates)}，请选一个。"],
                "reason": "ambiguous_category",
            }
        return {
            "action": "ask_user",
            "records": [],
            "questions": ["这笔记成什么类型？请使用明细表已有分类。"],
            "reason": "missing_category",
        }

    amount = amounts[0]
    income_type = resolve_income_type(category, text)
    if any(k in text for k in REFUND_HINTS):
        amount = -abs(amount)

    date_dt = resolve_date(text, now)
    date_str = date_dt.strftime("%Y-%m-%d")
    month = f"{date_dt.month}月"
    platform = resolve_platform(text)

    # 从原文中去掉金额部分，保留纯描述作为流水说明
    note = text.strip()
    note = re.sub(r"(?<!\d)(\d+(?:\.\d+)?)\s*元?", "", note).strip()
    note = note[:120] if note else text.strip()[:120]

    return {
        "action": "create_record",
        "records": [
            {
                "date": date_str,
                "month": month,
                "payment_platform": platform,
                "category": category,
                "income_type": income_type,
                "order_no": "",
                "note": note,
                "amount": amount,
            }
        ],
        "questions": [],
        "reason": "",
    }


def main():
    parser = argparse.ArgumentParser(description="Parse Chinese bill text into structured records.")
    parser.add_argument("--text", required=True, help="Natural-language bill text")
    parser.add_argument("--now", default="", help="Optional override for current date, format YYYY-MM-DD")
    args = parser.parse_args()

    if args.now:
        now = datetime.strptime(args.now, "%Y-%m-%d")
    else:
        now = datetime.now()

    result = build_record(args.text, now)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
