from __future__ import annotations

import json
import time

from ..config import load_settings
from ..llm import chat
from ..tools import execute, schemas
from ..trace import Trace

SYSTEM_PROMPT = """你是一个后端业务助手。

工作规则：
1. 需要订单、物流等外部数据时必须调用工具，禁止编造。
2. 参数不明确时先向用户确认，不要猜测。
3. 工具返回错误时先阅读错误信息，最多重试一次；仍失败就如实说明。
4. 最终回答不超过 3 句话，并说明依据来自哪个工具。
"""


def run(question: str) -> dict:
    """最小 Agent Loop：调模型 -> 执行工具 -> 结果回传 -> 直到给出答案。"""
    settings = load_settings()
    trace = Trace(name="agent.run")
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    total_cost = 0.0
    deadline = time.monotonic() + settings.timeout_s
    steps = 0

    for steps in range(1, settings.max_steps + 1):
        if time.monotonic() > deadline:
            break

        result = chat(messages, tools=schemas())
        total_cost += result.cost
        trace.add(
            "llm",
            step=steps,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            latency_ms=result.latency_ms,
            cost=round(result.cost, 6),
        )

        message = result.message
        if not message.tool_calls:
            answer = message.content or ""
            trace.add("final", step=steps, answer=answer)
            trace.save(settings.trace_dir)
            return {
                "answer": answer,
                "steps": steps,
                "cost": round(total_cost, 6),
                "trace_id": trace.trace_id,
            }

        messages.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [call.model_dump() for call in message.tool_calls],
            }
        )

        for call in message.tool_calls:
            arguments: dict = {}
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                output = {"ok": False, "error": "工具参数不是合法 JSON"}
            else:
                output = execute(call.function.name, arguments)

            trace.add(
                "tool",
                step=steps,
                name=call.function.name,
                arguments=arguments,
                result=output,
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(output, ensure_ascii=False),
                }
            )

    answer = f"未能在 {settings.max_steps} 步内完成，请缩小问题范围或补充信息。"
    trace.add("abort", step=steps, reason="max_steps_or_timeout")
    trace.save(settings.trace_dir)
    return {
        "answer": answer,
        "steps": steps,
        "cost": round(total_cost, 6),
        "trace_id": trace.trace_id,
    }
