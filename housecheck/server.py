"""Small web front end: one page, one POST /api/compare."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import config as C
from .cli import split_postcodes
from .llm import Nightshift
from .pipeline import run
from .sources import SourceError
from .zetaris import Zetaris, ZetarisError

app = FastAPI(title="HouseCheck")
STATIC = Path(__file__).parent / "static"


class CompareIn(BaseModel):
    postcodes: str
    priorities: str = ""
    mode: str | None = None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/status")
def status() -> dict:
    s = C.load()
    z, _ = Zetaris(s).status()
    l, models, _ = Nightshift(s).status()
    return {"zetaris": z, "nightshift": l, "models": models[:5], "mode": s.data_mode}


@app.post("/api/compare")
def compare(body: CompareIn) -> dict:
    try:
        r = run(split_postcodes(body.postcodes), body.priorities, mode=body.mode)
    except (SourceError, ZetarisError) as e:
        raise HTTPException(400, str(e)) from e
    return r
