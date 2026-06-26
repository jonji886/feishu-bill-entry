#!/usr/bin/env python3
import argparse
import json
import re
from datetime import datetime, timedelta


TYPE_MAP = {
    "餐食（三餐+盒马山姆都算）": [
        "中饭", "午饭", "午餐", "早饭", "早餐", "晚饭", "晚餐", "夜宵", "外卖", "聚餐", "吃饭",
        "餐厅", "饭店", "便当", "盒饭", "小吃", "烧烤", "火锅", "日料", "快餐", "水果", "零食",
        "奶茶", "咖啡", "饮料", "下午茶", "买菜", "超市", "盒马", "山姆", "烘焙", "面包", "蛋糕",
    ],
    "停车费及其他交通费": [
        "打车", "滴滴", "出租车", "网约车", "快车", "专车", "顺风车", "地铁", "公交", "公交车",
        "停车", "停车费", "加油", "油费", "高速", "高速费", "过路费", "共享单车", "骑行", "哈啰", "摩拜",
    ],
    "车子养护（电费、保养等）": [
        "充电", "充电桩", "保养", "洗车", "车险", "保险", "年检", "修车", "4S", "轮胎", "机油", "违章", "罚款",
    ],
    "水电费": ["电费", "水费", "燃气", "煤气", "天然气", "暖气"],
    "话费": ["话费", "手机费", "充话费", "宽带", "网费", "流量"],
    "物业费": ["物业", "物业费", "物业管理"],
    "房贷": ["房贷", "还贷", "月供", "贷款"],
    "服饰大类": [
        "衣服", "裤子", "鞋", "鞋子", "包", "帽子", "围巾", "T恤", "衬衫", "外套", "羽绒服", "内衣", "袜子",
        "买衣服", "逛街买衣服", "淘宝买衣服",
    ],
    "养狗相关费用": ["狗粮", "狗狗", "狗", "驱虫", "洗澡", "宠物", "猫粮", "猫", "猫砂", "宠物医院", "疫苗"],
    "医药费": ["看病", "买药", "挂号", "医院", "药费", "诊所", "门诊", "体检", "牙科", "中药", "西药", "医保"],
    "旅行费用（含etc）": ["旅行", "旅游", "机票", "酒店", "民宿", "火车票", "高铁", "景区", "门票", "ETC", "跟团", "度假"],
    "兴趣类支出": ["自习室", "游戏", "充值", "氪金", "买书", "文具", "健身", "运动", "球鞋", "球拍", "游泳", "乐器", "摄影", "手办", "模型"],
    "其他家用": ["日用品", "纸巾", "洗衣液", "洗发水", "牙膏", "沐浴露", "家居", "家具", "家电", "厨具", "拖把", "垃圾桶", "收纳"],
    "热植相关": ["植物", "绿植", "花", "花盆", "土", "营养土", "肥料", "多肉", "盆栽", "种子", "浇水"],
    "节日、礼金等": ["红包", "礼金", "份子钱", "送礼", "节日礼物", "生日礼物", "结婚红包", "压岁钱"],
    "小健家招待": ["请客", "招待", "聚会", "请吃饭", "来家吃饭"],
    "公司请客": ["公司请客", "报销", "商务宴请", "招待客户", "团建", "差旅"],
    "工资收入": ["工资", "发工资", "薪资", "薪水", "奖金", "年终奖"],
    "其他收入": ["红包", "退款", "返现", "卖闲置", "闲鱼", "二手", "转账收入", "报销款"],
    "理财收入": ["理财", "基金", "股票", "利息", "分红", "收益", "赎回"],
    "亚琪副业": ["亚琪", "副业", "兼职", "接单"],
}

INCOME_CATEGORIES = {"工资收入", "其他收入", "理财收入", "亚琪副业"}
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
