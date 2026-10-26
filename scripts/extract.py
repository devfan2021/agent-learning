"""D2：把自然语言抽成结构化查询参数。

练习点（按顺序做）：
1. 改 SYSTEM_PROMPT，把 intent 的边界写清楚，看 exact_match 怎么变。
2. 改 validate()，补上你自己的校验规则（订单号格式、intent 枚举）。
3. 给 CASES 加你真实业务里的说法，尤其是模糊表达。

运行：
    python -m scripts.extract
    python -m scripts.extract --limit 5 --verbose
"""

from __future__ import annotations

import argparse
import json
import statistics

from app.llm import chat

INTENTS = {"order_status", "shipping", "amount", "refund", "unknown"}

SYSTEM_PROMPT = """你是查询参数抽取器。把用户的话转成一个 JSON 对象，不要输出任何解释。

字段：
- order_id：订单号，统一大写；用户没给就填 null。格式为 A 加 4 位数字。
- intent：只能是 order_status / shipping / amount / refund / unknown 之一。
  order_status 问订单状态、是否支付、是否发货；
  shipping 问物流、到货时间、运单号；
  amount 问金额、价格；
  refund 问退款；
  其余情况为 unknown。

只输出 JSON，例如：{"order_id": "A1001", "intent": "shipping"}
"""

# (用户输入, 期望结果)
CASES: list[tuple[str, dict]] = [
    ("帮我查一下订单 A1001 的状态", {"order_id": "A1001", "intent": "order_status"}),
    ("A1001 到哪了", {"order_id": "A1001", "intent": "shipping"}),
    ("订单 a1001 的物流信息", {"order_id": "A1001", "intent": "shipping"}),
    ("查下 A1002 多少钱", {"order_id": "A1002", "intent": "amount"}),
    ("A1002 还没付款吗", {"order_id": "A1002", "intent": "order_status"}),
    ("我的订单 A1001 什么时候能到", {"order_id": "A1001", "intent": "shipping"}),
    ("订单号 A1001，帮我看看发货没", {"order_id": "A1001", "intent": "order_status"}),
    ("A9999 这个订单存在吗", {"order_id": "A9999", "intent": "order_status"}),
    ("帮我查订单", {"order_id": None, "intent": "unknown"}),
    ("订单 A1002 申请退款", {"order_id": "A1002", "intent": "refund"}),
    ("退款进度查一下，订单 A1001", {"order_id": "A1001", "intent": "refund"}),
    ("我想买点东西", {"order_id": None, "intent": "unknown"}),
    ("A1001 的运单号是多少", {"order_id": "A1001", "intent": "shipping"}),
    ("帮我看看 A1002 支付了没有", {"order_id": "A1002", "intent": "order_status"}),
    ("订单 A1001 金额", {"order_id": "A1001", "intent": "amount"}),
    ("查 A1002 的订单详情", {"order_id": "A1002", "intent": "order_status"}),
    ("你好", {"order_id": None, "intent": "unknown"}),
    ("订单A1001到哪了？", {"order_id": "A1001", "intent": "shipping"}),
    ("A1002 订单金额是多少", {"order_id": "A1002", "intent": "amount"}),
    ("帮我查下订单 a9999", {"order_id": "A9999", "intent": "order_status"}),
]


def parse_json(text: str) -> dict:
    """容忍模型偶尔加上的 ``` 围栏。"""
    text = (text or "").strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def validate(data: dict) -> list[str]:
    """TODO(D2)：在这里写你的校验规则，返回错误列表；空列表表示合法。

    建议至少覆盖：
    - order_id 为 null 或匹配 ^A\\d{4}$
    - intent 必须在 INTENTS 内
    - 不允许出现额外字段
    """
    return []


def normalize(data: dict) -> dict:
    order_id = data.get("order_id")
    order_id = order_id.strip().upper() if isinstance(order_id, str) else None
    intent = data.get("intent")
    return {
        "order_id": order_id or None,
        "intent": intent if intent in INTENTS else "unknown",
    }


def extract(text: str) -> tuple[dict, float, int]:
    """返回 (抽取结果, 成本, 尝试次数)。JSON 不合法时重试一次。"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]
    cost = 0.0

    for attempt in range(2):
        result = chat(messages, response_format={"type": "json_object"})
        cost += result.cost
        content = result.message.content or ""
        try:
            return parse_json(content), cost, attempt + 1
        except json.JSONDecodeError:
            if attempt == 0:
                messages.append({"role": "assistant", "content": content})
                messages.append(
                    {"role": "user", "content": "上次输出不是合法 JSON，只输出 JSON 对象。"}
                )

    raise ValueError("两次都没有返回合法 JSON")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--min", type=float, default=0.9, help="低于该通过率则非零退出")
    args = parser.parse_args()

    cases = CASES[: args.limit] if args.limit else CASES
    passed = 0
    retries = 0
    costs: list[float] = []

    for text, expected in cases:
        try:
            data, cost, attempts = extract(text)
            costs.append(cost)
            retries += attempts > 1
            got = normalize(data)
            errors = validate(data)
            ok = not errors and got == expected
        except Exception as exc:  # 单条失败不影响整轮
            got, ok, errors = {}, False, [str(exc)]

        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  {text}")
        if args.verbose or not ok:
            print(f"      got      {json.dumps(got, ensure_ascii=False)}")
            if not ok:
                print(f"      expected {json.dumps(expected, ensure_ascii=False)}")
                if errors:
                    print(f"      errors   {errors}")

    total = len(cases)
    rate = passed / total if total else 0.0
    print("-" * 56)
    print(f"exact_match {rate:.0%}  ({passed}/{total})")
    print(f"retries     {retries}")
    print(f"avg_cost    {statistics.fmean(costs):.5f}" if costs else "avg_cost    0")

    raise SystemExit(0 if rate >= args.min else 1)


if __name__ == "__main__":
    main()
