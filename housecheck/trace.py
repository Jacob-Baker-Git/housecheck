"""Per-run trace: every agent step is written to runs/<run_id>/trace.jsonl.

The trace is the evidence for judges that the agents actually ran, and what
each one decided.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any


class Trace:
    def __init__(self, runs_dir: Path, run_id: str | None = None):
        self.run_id = run_id or time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        self.dir = runs_dir / self.run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "trace.jsonl"
        self.events: list[dict[str, Any]] = []

    def log(self, agent: str, action: str, status: str = "ok", **details: Any) -> dict[str, Any]:
        event = {"ts": round(time.time(), 3), "agent": agent, "action": action, "status": status, **details}
        self.events.append(event)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")
        return event

    def save(self, name: str, content: str) -> Path:
        path = self.dir / name
        path.write_text(content, encoding="utf-8")
        return path
