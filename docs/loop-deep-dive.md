# Agent Loop 深度解读

> 基于 app/agent/loop.py 的逐行讲解。读一遍，然后合起来重写一次 loop.py（30 分钟），才算真正学会。

## 一句话版本

**Agent 没有内部状态，它所有的"记忆"就是 `messages: list[dict]`。每一轮 LLM 调用都把完整历史重发一遍。**

## 流程图

```
                    ┌──────────────────────────────────┐
                    │  初始化 messages = [system, user] │
                    │  trace = Trace()                  │
                    └──────────────────────────────────┘
                                     │
                                     ▼
                        ┌──────────────────────────┐
                   ┌──▶│ for step in 1..max_steps │◀──┐
                   │    └──────────────────────────┘   │
                   │             │                      │
                   │             ▼                      │
                   │   ┌──────────────────────┐        │
                   │   │ 超时? break          │        │
                   │   └──────────────────────┘        │
                   │             │                      │
                   │             ▼                      │
                   │   ┌─────────────────────────┐     │
                   │   │ result = chat(messages,  │     │
                   │   │               tools=..) │     │
                   │   └─────────────────────────┘     │
                   │             │                      │
                   │             ▼                      │
                   │   ┌──────────────────────┐        │
                   │   │ trace.add("llm", ...)│        │
                   │   └──────────────────────┘        │
                   │             │                      │
                   │             ▼                      │
                   │   ┌─────────────────────────────┐ │
                   │   │ if not message.tool_calls:  │ │
                   │   │     ↓                       │ │
                   │   │ return 最终答案              │ │
                   │   │     ↑                       │ │
                   │   └─ │ ─────────────────────────┘ │
                   │      │                             │
                   │      │ (非空 → 不走 return)        │
                   │      ▼                             │
                   │   ┌─────────────────────────┐     │
                   │   │ messages.append({        │     │
                   │   │   role: "assistant",     │     │
                   │   │   tool_calls: [...]      │     │
                   │   │ })                       │     │
                   │   └─────────────────────────┘     │
                   │             │                      │
                   │             ▼                      │
                   │   ┌─────────────────────────┐     │
                   │   │ for call in tool_calls:  │     │
                   │   │   arguments = json.loads │     │
                   │   │   output = execute(...)  │     │
                   │   │   trace.add("tool", ...) │     │
                   │   │   messages.append({      │     │
                   │   │     role: "tool",        │     │
                   │   │     tool_call_id: ...    │     │
                   │   │   })                     │     │
                   │   └─────────────────────────┘     │
                   │             │                      │
                   │             └──────────────────────┘
                   │
        max_steps 或超时 ──▶ 兜底返回 abort
```

## messages 在两轮间的演变

**第 1 次调用前：**

```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user",   "content": "A1001 到哪了"},
]
# prompt_tokens 约 465
```

**第 1 次调用后，追加两条消息：**

```python
messages.append({
    "role": "assistant",
    "content": "",                       # 调工具时 content 通常空
    "tool_calls": [{
        "id": "call_abc123",
        "type": "function",
        "function": {"name": "get_shipping", "arguments": "{\"order_id\":\"A1001\"}"}
    }]
})
messages.append({
    "role": "tool",
    "tool_call_id": "call_abc123",       # 必须和上面的 id 一致
    "content": "{\"ok\":true,\"data\":{\"carrier\":\"顺丰\",...}}"
})
```

**第 2 次调用前：**

```python
messages = [system, user, assistant(tool_calls), tool(result)]
# prompt_tokens 涨到约 569，因为上一轮的两条又被发了一遍
```

## 逐段解读

### 初始化（L23–32）

```python
settings = load_settings()
trace = Trace(name="agent.run")
messages: list[dict] = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user",   "content": question},
]
deadline = time.monotonic() + settings.timeout_s
```

- `messages` 是唯一状态载体，后面只增不减
- `deadline` 是墙钟超时，和 max_steps 形成双保险
- `SYSTEM_PROMPT` 写死在文件顶部，是"行为规则"，不是"知识"

### 主循环（L34）

```python
for steps in range(1, settings.max_steps + 1):
```

`step` = 第几次 LLM 请求，从 1 开始。同一个 step 里可以有多个工具调用，它们共享同一个 step 值。

### 调模型（L38）

```python
result = chat(messages, tools=schemas())
```

- `messages` 是完整历史，不是增量
- `tools=schemas()` 每次都传，告诉模型"你有哪些工具、参数长什么样"
- `schemas()` 是不变的，可以提到循环外算一次（现在工具少无所谓）

### 判断：要不要工具（L50）

```python
if not message.tool_calls:
    answer = message.content or ""
    trace.add("final", step=steps, answer=answer)
    trace.save(settings.trace_dir)
    return {...}
```

**空 / None → return**。`not None` 和 `not []` 都是 True，两种情况都算"没要求用工具"，直接返回。命中就退出函数，不走下面的工具执行。

### 追加 assistant 消息（L61）

```python
messages.append({
    "role": "assistant",
    "content": message.content or "",
    "tool_calls": [call.model_dump() for call in message.tool_calls],
})
```

**一条 assistant 消息装全部 tool_calls**。即使模型要求调 3 个工具，也只 append 这一条。`call.model_dump()` 把 Pydantic 对象转成普通 dict，才能存进 JSON。

### 执行工具（L69–91）

```python
for call in message.tool_calls:
    arguments: dict = {}
    try:
        arguments = json.loads(call.function.arguments or "{}")
    except json.JSONDecodeError:
        output = {"ok": False, "error": "工具参数不是合法 JSON"}
    else:
        output = execute(call.function.name, arguments)

    trace.add("tool", step=steps, ...)
    messages.append({
        "role": "tool",
        "tool_call_id": call.id,          # 和 call.id 匹配
        "content": json.dumps(output, ensure_ascii=False),
    })
```

要点：
- `call.function.arguments` 是 **JSON 字符串**，不是 dict，必须 `json.loads`
- 解析失败 **不执行工具**，造一个错误结果回传。目的是让模型能看到错误并纠正，不让整个 run 崩
- `role=tool` 的消息必须带 `tool_call_id`，这是 OpenAI 兼容 API 的硬要求
- 多个工具 → 先 append 一条 assistant，再逐条 append tool，所以 2 个工具会加 3 条消息

### 两个兜底出口

**正常结束**（L54）：`if not tool_calls` 里 return
**兜底结束**（L96）：循环走完（max_steps）或超时 break 后 return

两个出口都会 `trace.save()`，所以失败也有完整记录。

## 对话里讲过的易错点

1. **`from ..config import load_settings`**：相对导入，两个点跳到父包。直接 `python app/agent/loop.py` 会报 ImportError，必须用 `python -m scripts.chat`
2. **tool_call_id 不匹配**：每个 tool 消息的 `tool_call_id` 必须和对应 assistant 消息里的 `call.id` 完全一致，否则下一轮 API 直接报错
3. **messages 只增不减**：所以 token 越跑越多。D5 的上下文工程要解决这个问题
4. **不要混淆 result 和 messages**：`result` 只在当前轮用，不传给下一轮。传给下一轮的是往 messages 里 append 的那两条
5. **`from __future__ import annotations`**：让类型注解延迟求值，避免旧版本不支持 `list[dict]`

## 建议做一遍

合起文件，30 分钟内不看源码重写 loop.py。必须能独立处理三件事：

1. assistant 消息带 tool_calls 时怎么追加
2. tool 消息的 tool_call_id 怎么填
3. 步数和超时双保险

写不出来就翻一眼，再合上重写。这次练习比读十遍代码都有用。
