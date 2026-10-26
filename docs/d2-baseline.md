# D2 结构化输出 — 当前状态与下一步

## 脚本位置

`scripts/extract.py`

## 现状

| 组件 | 状态 | 备注 |
|---|---|---|
| SYSTEM_PROMPT | ✅ 已写 | intent 边界已定义：order_status / shipping / amount / refund / unknown |
| parse_json | ✅ 已写 | 容忍模型偶尔加的 ```json 围栏 |
| extract() | ✅ 已写 | response_format 强制 JSON；两次失败重试 |
| normalize() | ✅ 已写 | 小写 order_id 转大写；非枚举 intent 归 unknown |
| **validate()** | ❌ **空壳** | **这是今天最核心的事** |
| CASES | 20 条 | 覆盖正常/边界/闲聊；需补到 100 条 |

## 必须写的 4 条 validate 规则

顺序是 **先校验再归一化**：normalize 不该帮非法输出悄悄兜住。

```python
def validate(data: dict) -> list[str]:
    errors = []

    # 1. 必须是 dict
    if not isinstance(data, dict):
        return ["输出不是 JSON 对象"]

    # 2. 只有两个字段
    allowed = {"order_id", "intent"}
    extra = set(data) - allowed
    if extra:
        errors.append(f"多余字段: {extra}")

    # 3. order_id: null 或匹配 ^A\d{4}$
    oid = data.get("order_id")
    if oid is not None:
        if not isinstance(oid, str) or not re.match(r"^[Aa]\d{4}$", oid):
            errors.append(f"order_id 格式不合法: {oid}")

    # 4. intent 必须在枚举里
    intent = data.get("intent")
    if intent not in INTENTS:
        errors.append(f"intent 不在枚举: {intent}")

    return errors
```

注意 validate **不做 normalize 的事**（比如小写转大写），也不修复错误，只报。

## 跑基线的标准命令

```bash
uv run python -m scripts.extract --verbose
```

记四个数：

```
exact_match  通过率（normalize 后和 expected 完全相等）
retries      JSON 不合法重试了几次
avg_cost     单条平均成本
FAIL 列表    每条的 got / expected / errors
```

## 三条预测草稿（跑基线前先写）

在纸上写，跑完对比，猜错的地方最有价值。

| 输入 | 我猜的 got | 猜的原因 |
|---|---|---|
| A9999 这个订单存在吗 | order_status | "存在吗"虽像闲聊，但核心意图仍在订单 |
| 查 A1002 的订单详情 | order_status | "详情"语义太宽，但 prompt 里没说它归 unknown |
| 退款进度查一下，订单 A1001 | refund | 主语是"进度"，但语义锚点在"退款" |

## 常见坑

1. **validate 放 normalize 之后**：normalize 把非法值修成合法，validate 永远过。顺序必须是 validate → normalize。
2. **模型返回 `{"order_id": 123, "intent": "shipping"}`**：order_id 是数字不是字符串，validate 第 3 条能拦住。靠 normalize 去修会默默丢失错误信息。
3. **prompt 和 CASES 的预期不一致**：prompt 说"详情"归 status，但 CASES 里写了 order_status，这就成了 prompt 和 CASES 对不上。先改 prompt 让它自洽，再改 CASES。

## 验收标准（PLAN.md 定义）

```bash
uv run python -m scripts.extract --min 0.95   # 通过率 ≥ 95%
```
