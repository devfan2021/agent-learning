from __future__ import annotations

from .registry import tool

# 离线可用的 mock 数据，第 1 周不依赖任何内部系统。
_ORDERS = {
    "A1001": {
        "order_id": "A1001",
        "status": "已发货",
        "amount": 399.0,
        "created_at": "2026-10-01",
    },
    "A1002": {
        "order_id": "A1002",
        "status": "待支付",
        "amount": 129.0,
        "created_at": "2026-10-18",
    },
}

_SHIPPING = {
    "A1001": {
        "carrier": "顺丰",
        "tracking_no": "SF123456789",
        "latest": "运输中，预计 10-23 送达",
    },
}


@tool(
    name="get_order",
    description="按订单号查询订单状态、金额和下单时间。订单号格式为 A 开头加 4 位数字。",
    parameters={
        "type": "object",
        "properties": {
            "order_id": {"type": "string", "description": "订单号，例如 A1001"}
        },
        "required": ["order_id"],
    },
)
def get_order(order_id: str) -> dict:
    order = _ORDERS.get(order_id.strip().upper())
    if not order:
        raise LookupError(f"未找到订单 {order_id}")
    return order


@tool(
    name="get_shipping",
    description="按订单号查询物流承运商、运单号和最新轨迹。仅已发货订单有物流信息。",
    parameters={
        "type": "object",
        "properties": {
            "order_id": {"type": "string", "description": "订单号，例如 A1001"}
        },
        "required": ["order_id"],
    },
)
def get_shipping(order_id: str) -> dict:
    key = order_id.strip().upper()
    info = _SHIPPING.get(key)
    if not info:
        return {"order_id": key, "latest": "暂无物流信息，可能尚未发货"}
    return {"order_id": key, **info}
