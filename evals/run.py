from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from app.agent.loop import run

DATASET = Path(__file__).with_name("dataset.jsonl")


def load_cases(path: Path) -> list[dict]:
    cases = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def percentile(values: list[int], p: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(p / 100 * (len(ordered) - 1))))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser(description="跑黄金用例，输出通过率 / P95 / 平均成本")
    parser.add_argument("--file", type=Path, default=DATASET)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--min-pass", type=float, default=0.8)
    args = parser.parse_args()

    cases = load_cases(args.file)
    if args.limit:
        cases = cases[: args.limit]

    passed = 0
    latencies: list[int] = []
    costs: list[float] = []
    failures: list[tuple[dict, dict, list[str], str | None]] = []

    for case in cases:
        started = time.perf_counter()
        error = None
        try:
            result = run(case["input"])
        except Exception as exc:  # 单条失败不影响整轮评测
            result = {"answer": "", "steps": 0, "cost": 0.0}
            error = str(exc)
        latency_ms = int((time.perf_counter() - started) * 1000)

        missing = [s for s in case.get("expect_contains", []) if s not in result["answer"]]
        ok = error is None and not missing
        passed += ok
        latencies.append(latency_ms)
        costs.append(result.get("cost", 0.0))

        print(
            f"{'PASS' if ok else 'FAIL'}  {case['id']:<16} "
            f"{latency_ms:>6}ms  steps={result.get('steps')}"
        )
        if not ok:
            failures.append((case, result, missing, error))

    total = len(cases)
    pass_rate = passed / total if total else 0.0

    print("-" * 56)
    print(f"pass_rate   {pass_rate:.0%}  ({passed}/{total})")
    print(f"p95_latency {percentile(latencies, 95)}ms")
    print(f"avg_cost    {statistics.fmean(costs):.4f}" if costs else "avg_cost    0")

    for case, result, missing, error in failures:
        print("-" * 56)
        print(f"FAIL {case['id']}")
        if error:
            print(f"  error:   {error}")
        if missing:
            print(f"  missing: {missing}")
        print(f"  answer:  {result.get('answer', '')}")

    raise SystemExit(0 if pass_rate >= args.min_pass else 1)


if __name__ == "__main__":
    main()
