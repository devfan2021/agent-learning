from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., Any]

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


_TOOLS: dict[str, ToolSpec] = {}


def tool(name: str, description: str, parameters: dict):
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        _TOOLS[name] = ToolSpec(name, description, parameters, fn)
        return fn

    return decorator


def schemas() -> list[dict]:
    return [spec.schema() for spec in _TOOLS.values()]


def execute(name: str, arguments: dict) -> dict:
    """统一返回 {ok, data|error}，让模型能读懂失败原因。"""
    spec = _TOOLS.get(name)
    if spec is None:
        return {"ok": False, "error": f"未知工具: {name}"}
    if not isinstance(arguments, dict):
        return {"ok": False, "error": "工具参数必须是 JSON 对象"}
    try:
        return {"ok": True, "data": spec.handler(**arguments)}
    except TypeError as exc:
        return {"ok": False, "error": f"参数错误: {exc}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
