"""Researcher: fetches every fact through Zetaris and writes it into the World Model.

No model call here on purpose: numbers come from SQL, not from an LLM.
"""

from __future__ import annotations

import time
from typing import Any, Protocol

from .. import sources as S
from ..trace import Trace
from ..world_model import Edge, Observation, WorldModel
from ..zetaris import Zetaris, ZetarisError


class Port(Protocol):
    via: str

    def rows(self, q: S.Query) -> tuple[list[dict[str, Any]], str]: ...


class ZetarisPort:
    """Registers each REST table (idempotent) and runs the SELECT through Zetaris."""

    via = "zetaris"
    origin = "Zetaris (live)"

    def __init__(self, z: Zetaris, trace: Trace):
        self.z, self.trace = z, trace
        self.db = z.s.zetaris_db
        self._db_ready = False
        self.recorded: dict[str, dict[str, Any]] = {}

    def _ensure_db(self) -> None:
        if not self._db_ready:
            state = self.z.ddl(f'CREATE LIGHTNING DATABASE {self.db} DESCRIBE BY "HouseCheck live public data from postcodes.io, police.uk and the FSA"')
            self.trace.log("researcher", "zetaris_database", database=self.db, result=state)
            self._db_ready = True

    def rows(self, q: S.Query) -> tuple[list[dict[str, Any]], str]:
        self._ensure_db()
        state = self.z.ddl(S.rest_table(self.db, q.table, q.endpoint, q.headers))
        sql = q.select(f"{self.db.lower()}.{q.table}")
        result = self.z.sql(sql)
        rows = result.dicts()
        self.trace.log("researcher", "zetaris_query", query=q.name, table=q.table, registration=state, rows=len(rows), ms=result.ms, sql=sql)
        self.recorded[q.name] = {"sql": sql, "endpoint": q.endpoint, "rows": rows}
        return rows, sql


class SamplePort:
    """Replays rows previously recorded from Zetaris (or a direct fetch), clearly labelled as such."""

    via = "sample"

    def __init__(self, sample: dict[str, Any], trace: Trace):
        self.sample, self.trace = sample, trace
        self.origin = f"replayed sample (recorded via {sample.get('recorded_via', 'unknown')}, {sample.get('recorded_at', '?')})"

    def rows(self, q: S.Query) -> tuple[list[dict[str, Any]], str]:
        rec = self.sample["queries"].get(q.name)
        if rec is None:
            raise S.SourceError(f"sample for {self.sample.get('postcode')} has no {q.name} rows")
        self.trace.log("researcher", "sample_query", query=q.name, rows=len(rec["rows"]), recorded_via=self.sample.get("recorded_via"))
        return rec["rows"], rec.get("sql", "")


def research(postcode: str, port: Port, world: WorldModel, trace: Trace, run_id: str) -> dict[str, Any]:
    """Fetch, derive and ingest everything for one postcode. Returns a short summary for the trace."""
    pc = S.normalise_postcode(postcode)
    key = S.table_key(pc)
    obs: list[Observation] = []
    edges: list[Edge] = []
    now = time.time()

    def add(attr: str, value: Any, source: str, sql: str, note: str = "") -> None:
        obs.append(Observation("address", pc, attr, value, source, port.via, sql, now, note))

    def rows_or_empty(q: S.Query) -> tuple[list[dict[str, Any]], str]:
        """A REST table with no rows has no columns in Zetaris, so its SELECT fails. That's missing data, not a crash."""
        try:
            return port.rows(q)
        except (ZetarisError, S.SourceError) as e:
            trace.log("researcher", "source_empty", status="warn", query=q.name, postcode=pc, error=str(e)[:200])
            return [], q.select(f"{getattr(port, 'db', '').lower()}.{q.table}") if hasattr(port, "db") else ""

    # Stage 1: postcode -> coordinates and area
    rows, sql = port.rows(S.postcode_query(key, pc))
    if not rows:
        raise S.SourceError(f"postcodes.io has no record for {pc}")
    p = rows[0]
    lat, lng = float(p["lat"]), float(p["lng"])
    add("coordinates", [round(lat, 5), round(lng, 5)], S.SRC_POSTCODES, sql)
    add("local_authority", p["admin_district"], S.SRC_POSTCODES, sql)
    add("ward", p["ward"], S.SRC_POSTCODES, sql)
    add("lsoa", p["lsoa"], S.SRC_POSTCODES, sql)
    edges += [
        Edge(pc, "address", "in_ward", p["ward"], "ward", S.SRC_POSTCODES),
        Edge(pc, "address", "in_local_authority", p["admin_district"], "local_authority", S.SRC_POSTCODES),
    ]

    # Stage 2: coordinates (from Zetaris) -> police and food tables
    q_hood, q_crime, q_food = S.area_queries(key, lat, lng)

    rows, sql = rows_or_empty(q_hood)
    if rows:
        add("police_force", rows[0].get("force"), S.SRC_POLICE, sql)
        add("police_neighbourhood", rows[0].get("neighbourhood"), S.SRC_POLICE, sql)
        edges.append(Edge(pc, "address", "policed_by", str(rows[0].get("force")), "police_force", S.SRC_POLICE))

    rows, sql = rows_or_empty(q_crime)
    if rows:
        month = max(str(r["month"]) for r in rows)
        latest = [r for r in rows if str(r["month"]) == month]
        by_cat = {str(r["category"]): int(r["n"]) for r in latest}
        total = sum(by_cat.values())
        add("crime_month", month, S.SRC_POLICE, sql)
        add("crime_total_1mile", total, S.SRC_POLICE, sql, "street-level crimes within about 1 mile, one month")
        add("crime_by_category", dict(sorted(by_cat.items(), key=lambda kv: -kv[1])), S.SRC_POLICE, sql)
        for cat, attr in (("burglary", "crime_burglary"), ("anti-social-behaviour", "crime_antisocial"), ("violent-crime", "crime_violent"), ("bicycle-theft", "crime_bicycle_theft")):
            add(attr, by_cat.get(cat, 0), S.SRC_POLICE, sql)
    else:
        add("crime_total_1mile", None, S.SRC_POLICE, sql or "no rows", "police.uk returned no crimes for this point")

    rows, sql = rows_or_empty(S.freshness_query())
    if rows and rows[0].get("date"):
        add("police_data_latest", str(rows[0]["date"])[:7], S.SRC_POLICE, sql)

    rows, sql = rows_or_empty(q_food)
    total_food = sum(int(r["n"]) for r in rows)
    numeric = [(int(r["rating"]), int(r["n"])) for r in rows if str(r["rating"]).isdigit()]
    rated = sum(n for _, n in numeric)
    add("food_places_half_mile", total_food, S.SRC_FSA, sql, f"the nearest food places, capped at {S.FOOD_PAGE_SIZE} by the FSA; not necessarily every place within 0.5 miles")
    add("food_rated_count", rated, S.SRC_FSA, sql)
    if rated:
        good = sum(n for r, n in numeric if r >= 4)
        low = sum(n for r, n in numeric if r <= 2)
        add("food_pct_rated_4_or_5", round(100 * good / rated, 1), S.SRC_FSA, sql)
        add("food_rated_0_to_2", low, S.SRC_FSA, sql)
        add("food_avg_rating", round(sum(r * n for r, n in numeric) / rated, 2), S.SRC_FSA, sql)
    if rows:
        by_auth: dict[str, int] = {}
        for r in rows:
            by_auth[str(r["authority"])] = by_auth.get(str(r["authority"]), 0) + int(r["n"])
        dominant = max(by_auth.items(), key=lambda kv: kv[1])[0]
        # Same attribute as postcodes.io, different source: the World Model flags it if they disagree.
        add("local_authority", dominant, S.SRC_FSA, sql, "council that inspects most food places within 0.5 miles")

    report = world.ingest(obs, edges, run_id=run_id)
    trace.log("researcher", "world_model_ingest", postcode=pc, via=port.via, **report)
    return {"postcode": pc, "observations": len(obs), **report}


def make_port(postcode: str, mode: str, z: Zetaris, samples_dir, trace: Trace) -> Port:
    """live: Zetaris only. sample: recorded rows only. auto: Zetaris if reachable, else recorded rows."""
    key = S.table_key(postcode)
    if mode == "sample":
        return SamplePort(S.load_sample(samples_dir, key), trace)
    if mode == "live":
        return ZetarisPort(z, trace)
    state, detail = z.status()
    if state == "online":
        return ZetarisPort(z, trace)
    trace.log("researcher", "fallback_to_sample", status="warn", zetaris=state, detail=detail)
    return SamplePort(S.load_sample(samples_dir, key), trace)


__all__ = ["research", "make_port", "ZetarisPort", "SamplePort", "ZetarisError"]
