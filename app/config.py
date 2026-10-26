import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    model: str
    max_steps: int
    timeout_s: float
    price_input_per_m: float
    price_output_per_m: float
    trace_dir: str
    database_url: str


def load_settings() -> Settings:
    """每次读取环境变量，便于改 .env 后无需改代码。"""
    return Settings(
        base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1"),
        api_key=os.getenv("LLM_API_KEY", ""),
        model=os.getenv("LLM_MODEL", "deepseek-chat"),
        max_steps=int(os.getenv("AGENT_MAX_STEPS", "6")),
        timeout_s=float(os.getenv("AGENT_TIMEOUT_S", "60")),
        price_input_per_m=float(os.getenv("PRICE_INPUT_PER_M", "0.5")),
        price_output_per_m=float(os.getenv("PRICE_OUTPUT_PER_M", "2.0")),
        trace_dir=os.getenv("TRACE_DIR", "traces"),
        database_url=os.getenv(
            "DATABASE_URL", "postgresql://agent:agent@localhost:5432/agent"
        ),
    )
