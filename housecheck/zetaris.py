"""Zetaris client: runs one Lightning SQL statement at a time over the platform's REST API.

Zetaris is HouseCheck's data layer. Every public API HouseCheck reads
(postcodes.io, police.uk, FSA food hygiene) is registered in Zetaris as a
Lightning REST table and queried with SQL; the SQL behind every fact is kept
as provenance in the World Model.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from .config import Settings


class ZetarisError(RuntimeError):
    pass


@dataclass
class Rows:
    columns: list[str]
    rows: list[list[Any]]
    sql: str
    ms: int

    def dicts(self) -> list[dict[str, Any]]:
        return [dict(zip(self.columns, r)) for r in self.rows]


ALREADY_EXISTS = ("already exist", "already registered", "duplicate")


class Zetaris:
    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.s = settings
        self.http = client or httpx.Client(timeout=settings.zetaris_timeout_s)

    @property
    def configured(self) -> bool:
        return bool(self.s.zetaris_key)

    def sql(self, statement: str, limit: int = 5000) -> Rows:
        """Run one statement.

        Retries: once on a timeout/5xx (Spark under Zetaris can stall on a busy laptop), and up to
        three times with a growing wait when a public API behind a REST table rate-limits (HTTP 429;
        police.uk allows roughly 15 requests a second and Zetaris re-fetches on every query).
        """
        waits = [5, 10, 20]
        for attempt in range(len(waits) + 1):
            try:
                return self._once(statement, limit)
            except ZetarisError as e:
                msg = str(e)
                if "429" in msg and attempt < len(waits):
                    time.sleep(waits[attempt])
                    continue
                if attempt == 0 and ("timeout" in msg.lower() or "HTTP 5" in msg):
                    time.sleep(2)
                    continue
                raise
        raise ZetarisError("unreachable")

    def ddl(self, statement: str) -> str:
        """Run a DDL statement; 'already exists' counts as done. Returns 'created' or 'exists'."""
        try:
            self.sql(statement, limit=1)
            return "created"
        except ZetarisError as e:
            if any(k in str(e).lower() for k in ALREADY_EXISTS):
                return "exists"
            raise

    def status(self) -> tuple[str, str]:
        if not self.configured:
            return "unconfigured", "ZETARIS_API_KEY is not set"
        try:
            r = self.sql("SELECT 1 AS one", limit=1)
            ok = r.rows and str(r.rows[0][0]) == "1"
            return ("online", "") if ok else ("offline", "unexpected reply to SELECT 1")
        except ZetarisError as e:
            msg = str(e)
            return ("unauthorized" if "HTTP 401" in msg or "HTTP 403" in msg else "offline"), msg[:200]

    def _once(self, statement: str, limit: int) -> Rows:
        if not self.configured:
            raise ZetarisError("ZETARIS_API_KEY is not set (create one in the Zetaris web UI)")
        started = time.time()
        try:
            res = self.http.post(
                f"{self.s.zetaris_url}/sql-editor/sqls/run",
                headers={
                    "Authorization": f"Bearer {self.s.zetaris_key}",
                    "X-Org-ID": self.s.zetaris_org,
                    "X-Request-ID": str(uuid.uuid4()),
                    "Content-Type": "application/json",
                },
                json={"queryId": str(uuid.uuid4()), "sql": statement, "source": "SqlEditor", "limit": limit},
            )
        except httpx.TimeoutException as e:
            raise ZetarisError(f"Zetaris timeout: {e}") from e
        except httpx.HTTPError as e:
            raise ZetarisError(f"Zetaris unreachable: {e}") from e
        if res.status_code >= 400:
            raise ZetarisError(f"Zetaris HTTP {res.status_code}: {res.text[:300]}")
        try:
            body = res.json()
        except ValueError as e:
            raise ZetarisError(f"Zetaris returned non-JSON: {res.text[:200]}") from e
        columns, rows = normalise(body)
        return Rows(columns, rows, statement, int((time.time() - started) * 1000))


def normalise(body: dict[str, Any]) -> tuple[list[str], list[list[Any]]]:
    """The REST reply carries rows under `data`; column names come back in a few shapes."""
    if isinstance(body, dict) and body.get("error"):
        raise ZetarisError(f"Zetaris error: {str(body.get('error'))[:300]}")
    data = body.get("data") or []
    meta = next((body[k] for k in ("headers", "columns", "columnNames", "schema", "metadata") if k in body), None)
    columns: list[str] = []
    if isinstance(meta, list):
        columns = [c if isinstance(c, str) else str(c.get("name") or c.get("columnName") or "") for c in meta]
    if data and isinstance(data[0], dict):
        columns = columns or list(data[0].keys())
        return columns, [[r.get(c) for c in columns] for r in data]
    return columns, [list(r) for r in data]
