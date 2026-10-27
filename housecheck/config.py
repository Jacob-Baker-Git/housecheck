"""Settings, read once from the environment (and .env if present)."""

from __future__ import annotations

import glob
import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv is optional at runtime
    pass

ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _token_from_disk() -> str:
    """Nightshift writes its runtime token to <stateDir>/proxy-token.

    Checked on Windows directly, and from inside WSL via /mnt/c/Users/*.
    """
    candidates = [_env("METERLESS_TOKEN_FILE")]
    if os.environ.get("LOCALAPPDATA"):
        candidates.append(os.path.join(os.environ["LOCALAPPDATA"], "ai.meterless.runtime", "proxy-token"))
    candidates += glob.glob("/mnt/c/Users/*/AppData/Local/ai.meterless.runtime/proxy-token")
    candidates.append(os.path.expanduser("~/.local/share/ai.meterless.runtime/proxy-token"))
    for path in candidates:
        if path and os.path.isfile(path):
            try:
                return Path(path).read_text(encoding="utf-8").strip()
            except OSError:
                continue
    return ""


@dataclass(frozen=True)
class Settings:
    zetaris_url: str
    zetaris_key: str
    zetaris_org: str
    zetaris_db: str
    zetaris_timeout_s: float
    llm_url: str
    llm_token: str
    llm_model: str
    llm_timeout_s: float
    data_mode: str
    samples_dir: Path
    runs_dir: Path
    world_db: Path


def load() -> Settings:
    return Settings(
        zetaris_url=_env("ZETARIS_REST_URL", "http://localhost:8888/api/v1.0").rstrip("/"),
        zetaris_key=_env("ZETARIS_API_KEY"),
        zetaris_org=_env("ZETARIS_ORG_ID", "1"),
        zetaris_db=_env("ZETARIS_DB", "HOUSECHECK_LIVE"),
        zetaris_timeout_s=float(_env("ZETARIS_TIMEOUT_S", "180")),
        llm_url=_env("METERLESS_BASE_URL", "http://127.0.0.1:8088/v1").rstrip("/"),
        llm_token=_env("METERLESS_RUNTIME_TOKEN") or _token_from_disk(),
        llm_model=_env("METERLESS_MODEL", "meterless/auto"),
        llm_timeout_s=float(_env("METERLESS_TIMEOUT_S", "300")),
        data_mode=_env("HOUSECHECK_DATA_MODE", "auto").lower(),
        samples_dir=Path(_env("HOUSECHECK_SAMPLES_DIR", str(ROOT / "data" / "samples"))),
        runs_dir=Path(_env("HOUSECHECK_RUNS_DIR", str(ROOT / "runs"))),
        world_db=Path(_env("HOUSECHECK_WORLD_DB", str(ROOT / ".worldmodel" / "world.sqlite"))),
    )
