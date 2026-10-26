import argparse

from app.agent.loop import run


def ask(question: str) -> None:
    result = run(question)
    print(result["answer"])
    print(
        f"(steps={result['steps']} cost={result['cost']:.4f} "
        f"trace={result['trace_id']})"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--question", help="单次提问，非交互模式")
    args = parser.parse_args()

    if args.question:
        ask(args.question)
        return

    print("输入问题，回车发送；q 退出。")
    while True:
        try:
            question = input("> ").strip()
        except EOFError:  # 非 TTY 环境下没有输入时直接退出
            break
        if question in {"q", "quit", "exit"}:
            break
        if not question:
            continue
        ask(question)


if __name__ == "__main__":
    main()
