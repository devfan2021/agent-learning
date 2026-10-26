# AI Agent 学习项目 — 会话接力手册

> 这份文档记录了第 1 周（D1–D7）已经做完的事、学到的关键点、以及下一步要做什么。
> 当你切换到 TraeCode 桌面版的本地/云端模式时，**新会话的第一句话请 AI 读这个文件**：
> "请先读 SESSION-SUMMARY.md，然后接着做 D2。"

---

## 项目是什么

一个让后端工程师用 28 天从 0 学懂 AI Agent 的脚手架。核心代码量约 800 行，不依赖 LangChain / AutoGen 等重框架，所有关键路径自己写一遍。

- 计划：`PLAN.md`
- 快速开始：`README.md`
- 目录结构：

```
agent-learning/
├── app/
│   ├── agent/loop.py        # 核心：手写 Agent Loop
│   ├── llm.py               # LLM 封装（DeepSeek）
│   ├── tools/registry.py    # 工具注册与 execute
│   ├── tools/mock_tools.py  # 两个 mock 工具（get_order / get_shipping）
│   ├── trace.py             # trace_id + JSONL 事件记录
│   ├── config.py            # 配置加载
│   └── main.py              # FastAPI 入口
├── scripts/
│   ├── chat.py              # 命令行跑完整 Agent Loop
│   ├── extract.py           # D2 结构化输出练习
│   └── show_trace.py        # 查看 trace
├── evals/
│   ├── run.py               # 评测脚手架
│   └── dataset.jsonl        # 数据集（空，后面自己补）
├── docs/                    # 本目录
└── traces/                  # 运行日志（.gitignore 已排除）
```

## 已完成

| 天 | 任务 | 产出 |
|---|---|---|
| D1 | 环境 + 第一次调用 | 跑通 `python -m scripts.chat -q "A1001 到哪了"`；trace.jsonl 里能看到 `llm → tool → llm → final` 四事件 |
| D1.5 | Agent Loop 深度解读 | 逐行解释 loop.py（见 `docs/loop-deep-dive.md`）；画出流程图 |
| - | uv 迁移 | 从 `requirements.txt + pip` 改成 `uv` 管理；更新 Makefile / Dockerfile / README；删掉 requirements.txt |

## 进行中（当前卡点）

### D2 — 结构化输出

`scripts/extract.py` 的状态：
- SYSTEM_PROMPT 已写好 intent 边界
- `parse_json` 已实现（容忍 ```json 围栏）
- `normalize` 已实现（小写转大写、非枚举 intent 归 unknown）
- **`validate()` 还是空的** ← 今天要写
- **基线跑过了**（exact_match 数字用户本地有）
- CASES 共 20 条（已覆盖正常/边界/闲聊）

### D2 要做的三件事

1. **实现 validate()**，至少四条规则：
   - 整体是 dict，不是 list / str / null
   - 只有 `order_id` / `intent` 两个字段，多一个就报错
   - `order_id` 为 null 或匹配 `^A\d{4}$`
   - `intent` 必须在 `INTENTS = {order_status, shipping, amount, refund, unknown}` 里
2. **先跑基线再改 prompt**：`uv run python -m scripts.extract --verbose`，把 exact_match / retries / avg_cost 记下来
3. **补到 100 条用例**，分三组：正常 / 边界 / 对抗

### D2 的验收

```bash
uv run python -m scripts.extract --min 0.95   # 通过率 ≥95%
```

并且 validate 能拦住非法输出 — 即使模型返回 `{"order_id": 123, "intent": "shipping"}`（order_id 是数字）也要报错，不能靠 normalize 悄悄兜住。

## 还没开始

| 天 | 内容 |
|---|---|
| D3 | function calling 协议细节 + 接两个 mock 工具（loop.py 已经写完了，这部分其实提前做了） |
| D4 | 手写 Agent Loop 复盘（看 `docs/loop-deep-dive.md`） |
| D5 | 上下文工程：两版 prompt 对比 |
| D6 | 评测脚手架 `evals/run.py` |
| D7 | 项目 1 收尾 |
| D8–D28 | RAG → 编排 → 安全 → 上线（见 PLAN.md） |

## 关键知识点（对话中重点讲过的）

1. **Agent 没有内部状态，记忆全在 messages 列表里**。每次调 LLM 都把完整历史重发一遍。
2. **trace_id 生成**：`Trace` dataclass 初始化时 `uuid.uuid4().hex[:12]`，一次 run 一个；step 是循环变量，第几次 LLM 请求就等于几。见 `docs/trace-and-step.md`。
3. **tool_calls 协议**：模型返回 `tool_calls` 时要先 append 一条 assistant 消息（带全部 tool_calls），再逐个 append tool 消息（每个必须带 `tool_call_id`，和对应 call 匹配）。漏一个下一轮 API 报错。
4. **相对导入 `from ..config import ...`**：loop.py 是 `app.agent.loop`，两个点跳到父包 `app`。直接跑 `python app/agent/loop.py` 会报 ImportError，必须用 `python -m scripts.chat`。
5. **`from __future__ import annotations`**：让类型注解延迟求值，主要是避免旧版本不支持 `list[dict]`；在这个项目里更像保险而非必需。
6. **`uv run`** 每次会校验 `.venv` 和 `uv.lock` 一致，不一致自动同步；不是单纯启动器。IDE 里把解释器指向 `.venv/bin/python` 就不必走 uv。
7. **"没有 eval 的项目不算完成"**：eval 是唯一能量化效果的东西。不跑 eval 就改 prompt / 改模型，永远在凭感觉调。
8. **项目学习代码的正确姿势**：先预测，再跑，猜错的地方才是细节值得挖的地方。

## 本地 ↔ 云端切换指南（TraeCode 官方方式）

文章标题：《Hands-Off! 本地云端自由切，项目推进不断档》

步骤：
1. 把项目 push 到 GitHub（唯一入口，Trae 云端环境只接受从 GitHub 拉）
2. TraeCode 桌面版打开这个仓库
3. 左下角头像 → 设置 → 云端运行环境 → 创建（选 Python 3.11 + uv + 填 LLM_API_KEY）
4. 对话输入框左下角点运行环境切换：**本地 / 云端 / 工作树**

适合放云端的场景：eval 批量跑、长任务（RAG 入库）、换设备继续。

## 给下一位 AI 的接力棒

切换会话时，直接把下面这段贴给新会话的 AI：

> "请先读 SESSION-SUMMARY.md。当前进度：D1 已完成，Agent Loop 已经跑通并详细解读过（见 docs/loop-deep-dive.md），uv 迁移完成。正在做 D2 结构化输出，validate() 还是空的，normalize 和 parse_json 已实现，CASES 20 条。下一步：实现 validate() 的四条规则，跑基线记数字，补到 100 条用例。跑完基线把 FAIL 列表贴我。"
