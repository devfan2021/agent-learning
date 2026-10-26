# Agent Learning Skeleton

后端工程师 4 周 AI Agent 实操骨架。配套逐日计划见 [PLAN.md](./PLAN.md)。

不是框架演示，而是一条可运行的最小主线：

```
模型调用 → 手写 Agent Loop → 工具注册 → 链路 Trace → 评测集
```

第 2 周起在这个骨架上加 RAG，第 3 周起加状态机与权限，第 4 周起加灰度与成本控制。

## 快速开始

项目用 [uv](https://docs.astral.sh/uv/) 管理 Python 版本与依赖，需要 3.11+，无需手动建虚拟环境。

```bash
cd agent-learning
cp .env.example .env          # 填入 LLM_API_KEY
uv sync                       # 按 uv.lock 建 .venv 并装依赖

uv run python -m scripts.chat        # 命令行对话，验证模型连通
uv run python -m evals.run           # 跑评测集，输出通过率 / P95 / 成本
make serve                           # FastAPI: POST /agent/run
```

`uv run` 会自动检查环境是否与 `uv.lock` 一致，不需要 `source .venv/bin/activate`。
IDE 的解释器请指向 `.venv/bin/python`（Windows 为 `.venv\Scripts\python.exe`）。

数据库（第 2 周用到）：

```bash
docker compose up -d db       # pgvector + 初始化 schema
```

## 目录

```
app/
  config.py          环境变量与单价配置
  llm.py             模型调用封装，返回 token / 延迟 / 成本
  trace.py           每次运行的完整事件链，落 JSONL
  agent/loop.py      手写 Agent Loop（最大步数、超时、错误回传）
  tools/
    registry.py      工具注册与执行，统一错误结构
    mock_tools.py    两个 mock 工具，离线可跑
  main.py            FastAPI 入口
evals/
  run.py             评测 runner
  dataset.jsonl      黄金用例（示例 5 条，补到 20 条）
db/
  schema.sql         documents / chunks / traces / eval_runs
scripts/chat.py      命令行对话
```

## 三个里程碑

| 阶段 | 项目 | 验收指标 |
|---|---|---|
| 第 1 周 | 工具助手（只读查询） | 20 条用例通过率 ≥80%，P95 <5s，单次成本 <¥0.05 |
| 第 2 周 | RAG 文档问答 | recall@5 ≥0.8，引用准确率 ≥90%，拒答正确率 ≥80% |
| 第 3–4 周 | 排查 / 分派 Agent | 完成率 ≥70%，人工接管率 <30%，零越权写操作 |

## 三条纪律

1. 一周最多引入一个新依赖。
2. 没有 eval 的项目不算完成，改 prompt 必须跑回归。
3. 每天写 10 分钟失败日志：检索错、工具错，还是模型没遵循指令。
