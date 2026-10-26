"""按 trace_id 打印一次运行的完整事件链。

用法：
    python -m scripts.show_trace              # 最近一次运行
    python -m scripts.show_trace 627dc818c440 # 指定 trace_id
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

TRACE_DIR = Path(__file__).resolve().parents[1] / "traces"


def load(paths: list[Path]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for path in paths:
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    row = json.loads(line)
                    groups[row["trace_id"]].append(row)
    return groups


def show(rows: list[dict]) -> None:
    print(f"trace {rows[0]['trace_id']}  ({len(rows)} events, {rows[-1]['elapsed_ms']}ms)")

    for e in rows:
        step = e.get("step", "-")
        if e["event"] == "llm":
            detail = (
                f"{e.get('latency_ms')}ms  "
                f"tokens {e.get('prompt_tokens')}+{e.get('completion_tokens')}  "
                f"cost {e.get('cost')}"
            )
        elif e["event"] == "tool":
            result = e.get("result") or {}
            detail = f"{e.get('name')} {json.dumps(e.get('arguments'), ensure_ascii=False)}"
            detail += " -> ok" if result.get("ok") else f" -> error: {result.get('error')}"
        elif e["event"] == "final":
            detail = e.get("answer", "")
        else:
            detail = e.get("reason", "")

        print(f"  step {step}  {e['event']:<5}  {detail}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace_id", nargs="?", help="不填则看最近一次")
    parser.add_argument("--file", type=Path)
    args = parser.parse_args()

    paths = [args.file] if args.file else sorted(TRACE_DIR.glob("*.jsonl"))
    groups = load(paths)

    if not groups:
        print("没有 trace 文件，先跑一次 scripts.chat")
        return

    if args.trace_id:
        if args.trace_id not in groups:
            print(f"找不到 trace_id: {args.trace_id}")
            raise SystemExit(1)
        show(groups[args.trace_id])
    else:
        show(list(groups.values())[-1])


if __name__ == "__main__":
    main()
