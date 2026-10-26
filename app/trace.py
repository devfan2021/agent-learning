from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Trace:
    """一次运行的全链路事件，按行落 JSONL，便于回放单次失败。"""

    name: str
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: float = field(default_factory=time.perf_counter)
    events: list[dict] = field(default_factory=list)

    def add(self, event_type: str, **fields) -> None:
        self.events.append(
            {
                "trace_id": self.trace_id,
                "run": self.name,
                "event": event_type,
                "elapsed_ms": int((time.perf_counter() - self.started_at) * 1000),
                "at": datetime.now().isoformat(timespec="seconds"),
                **fields,
            }
        )

    def save(self, out_dir: str) -> str:
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"{datetime.now():%Y-%m-%d}.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            for event in self.events:
                f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        return path
