from __future__ import annotations

import time
from dataclasses import dataclass

from openai import OpenAI

from .config import Settings, load_settings


@dataclass
class LLMResult:
    message: object
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    cost: float


_client: OpenAI | None = None


def _get_client(settings: Settings) -> OpenAI:
    global _client
    if _client is None:
        if not settings.api_key:
            raise RuntimeError("缺少 LLM_API_KEY，请复制 .env.example 为 .env 并填入密钥")
        _client = OpenAI(base_url=settings.base_url, api_key=settings.api_key)
    return _client


def chat(
    messages: list[dict],
    tools: list[dict] | None = None,
    response_format: dict | None = None,
) -> LLMResult:
    """一次模型调用，统一返回 message、token、延迟与成本。"""
    settings = load_settings()
    kwargs = {
        "model": settings.model,
        "messages": messages,
        "temperature": 0,
        "timeout": settings.timeout_s,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    if response_format:
        kwargs["response_format"] = response_format

    started = time.perf_counter()
    resp = _get_client(settings).chat.completions.create(**kwargs)
    latency_ms = int((time.perf_counter() - started) * 1000)

    usage = resp.usage
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    cost = (
        prompt_tokens / 1_000_000 * settings.price_input_per_m
        + completion_tokens / 1_000_000 * settings.price_output_per_m
    )
    return LLMResult(
        message=resp.choices[0].message,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        cost=cost,
    )
