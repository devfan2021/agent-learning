# trace_id 和 step 字段的生成

> 为什么同一次 run 有 4 行相同的 trace_id，为什么 step 在同一次 tool_calls 里不变？

## trace_id

生成点：`app/trace.py`

```python
@dataclass
class Trace:
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    ...
```

- `default_factory` 意思是：**每创建一个 Trace 实例调一次**
- 所以它**一次 run 生成一次**，不是每个事件生成一次
- `uuid4().hex` 是 32 位十六进制，截前 12 位（48 bit），本地调试够用
- 如果要汇总多个服务的 trace，换成完整 uuid 避免碰撞

在 loop.py 里：

```python
trace = Trace(name="agent.run")   # 这行生成 trace_id
# ... 下面所有 trace.add(...) 都复用同一个 trace_id
trace.add("llm",    step=steps, ...)
trace.add("tool",   step=steps, ...)
trace.add("final",  step=steps, ...)
```

## step

不是 trace 内部维护的计数器，而是 loop.run 的**循环变量通过参数传进去**：

```python
for steps in range(1, settings.max_steps + 1):   # L34
    # step = 第几次 LLM 请求

    trace.add("llm", step=steps, ...)            # 每次 LLM 调用记一次 step

    for call in message.tool_calls:
        trace.add("tool", step=steps, ...)       # 同一次调用的多个工具共享 step
```

| 场景 | step 变化 |
|---|---|
| 第一次 LLM 调用 | step = 1 |
| 该调用返回 2 个 tool_calls | 两条 tool 记录 step 都是 1 |
| 第二次 LLM 调用 | step = 2 |
| final 回答 | step = 2 |

## 分工

```
trace_id     标识"哪一次运行"   → 分组
step         标识"第几轮"       → 组内排序
elapsed_ms   标识"轮内先后"     → 同一 step 下精确排序
```

要找某一次 run，用 trace_id 分组后按 step + elapsed_ms 排序。

## 真实 trace 示例

来自 traces/2026-10-22.jsonl，trace_id = `627dc818c440`：

```
step=1  llm      → 调第 1 次模型
step=1  tool     → 执行 get_shipping
step=2  llm      → 调第 2 次模型（带着工具结果）
step=2  final    → 最终答案
```

可以看到 prompt_tokens 从 465 涨到 569 — 因为第二轮把第一轮的 assistant 和 tool 消息又发了一遍。
