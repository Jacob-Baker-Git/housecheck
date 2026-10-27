"""Meterless World Model engine, implemented in Python for HouseCheck.

Follows the Meterless World Model specification
(github.com/Meterless/Meterless/tree/main/engines/world-model):

* stable hash IDs: `ent_<sha256(type:normalized_name)[:16]>`, so every agent
  and every run agree on identity without coordination;
* idempotent ingest: an observation's ID is a hash of its content, so
  re-ingesting the same data changes nothing;
* provenance on every observation: which source, which path (Zetaris or a
  recorded sample), the exact SQL, when it was fetched;
* derived, rebuildable views: `current_facts` (what is true now, per source)
  and `conflicts` (attributes where sources disagree).

The World Model is the one shared record that the Researcher writes and the
Critic and Reporter read, so they can never work from different numbers.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


# ---------------------------------------------------------------- stable IDs (spec section 3)

def normalize_name(s: str) -> str:
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s).strip()


def stable_entity_id(name: str, type_: str) -> str:
    h = hashlib.sha256(f"{type_}:{normalize_name(name)}".encode("utf-8")).hexdigest()[:16]
    return f"ent_{h}"


def _hash(*parts: Any) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- canonical records

@dataclass
class Observation:
    """One fact about one entity from one source. The unit of ingest."""

    entity_type: str
    entity_name: str
    attribute: str
    value: Any
    source: str  # e.g. "police.uk", "postcodes.io", "FSA food hygiene"
    via: str  # "zetaris" | "sample" | "derived"
    sql: str = ""
    fetched_at: float = field(default_factory=time.time)
    note: str = ""

    @property
    def entity_id(self) -> str:
        return stable_entity_id(self.entity_name, self.entity_type)

    @property
    def id(self) -> str:
        # Content hash: same entity + attribute + value + source + query = same observation.
        # The query is part of identity so provenance always points at the SQL that produced the value.
        return "obs_" + _hash(self.entity_id, self.attribute, self.value, self.source, self.sql)


@dataclass
class Edge:
    from_name: str
    from_type: str
    type: str
    to_name: str
    to_type: str
    source: str

    @property
    def id(self) -> str:
        return "edge_" + _hash(stable_entity_id(self.from_name, self.from_type), self.type, stable_entity_id(self.to_name, self.to_type))


SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
  id TEXT PRIMARY KEY, type TEXT NOT NULL, name TEXT NOT NULL,
  mention_count INTEGER NOT NULL DEFAULT 0, first_seen_at REAL, last_seen_at REAL,
  state TEXT NOT NULL DEFAULT 'emerging'
);
CREATE TABLE IF NOT EXISTS observations (
  id TEXT PRIMARY KEY, entity_id TEXT NOT NULL REFERENCES entities(id),
  attribute TEXT NOT NULL, value_json TEXT NOT NULL,
  source TEXT NOT NULL, via TEXT NOT NULL, sql TEXT, fetched_at REAL NOT NULL, note TEXT
);
CREATE INDEX IF NOT EXISTS obs_entity_attr ON observations(entity_id, attribute);
CREATE TABLE IF NOT EXISTS edges (
  id TEXT PRIMARY KEY, from_id TEXT NOT NULL, type TEXT NOT NULL, to_id TEXT NOT NULL, source TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS run_observations (
  run_id TEXT NOT NULL, observation_id TEXT NOT NULL, PRIMARY KEY (run_id, observation_id)
);
"""


class WorldModel:
    def __init__(self, path: Path | str = ":memory:"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    # ------------------------------------------------------------ ingest (spec section 5, per-observation path)

    def ingest(self, observations: Iterable[Observation], edges: Iterable[Edge] = (), run_id: str = "") -> dict[str, int]:
        """extract -> normalize -> resolve -> validate -> append -> project. Safe to re-run."""
        report = {"observations_new": 0, "observations_seen": 0, "entities": 0, "edges": 0}
        now = time.time()
        with self.db:
            touched: set[str] = set()
            for ob in observations:
                self._validate(ob)
                eid = ob.entity_id
                self._upsert_entity(eid, ob.entity_type, ob.entity_name, now)
                touched.add(eid)
                cur = self.db.execute(
                    "INSERT OR IGNORE INTO observations (id, entity_id, attribute, value_json, source, via, sql, fetched_at, note) VALUES (?,?,?,?,?,?,?,?,?)",
                    (ob.id, eid, ob.attribute, json.dumps(ob.value, sort_keys=True, default=str), ob.source, ob.via, ob.sql, ob.fetched_at, ob.note),
                )
                report["observations_new" if cur.rowcount else "observations_seen"] += 1
                if run_id:
                    self.db.execute("INSERT OR IGNORE INTO run_observations VALUES (?,?)", (run_id, ob.id))
            for e in edges:
                fid, tid = stable_entity_id(e.from_name, e.from_type), stable_entity_id(e.to_name, e.to_type)
                self._upsert_entity(fid, e.from_type, e.from_name, now)
                self._upsert_entity(tid, e.to_type, e.to_name, now)
                touched.update({fid, tid})
                cur = self.db.execute("INSERT OR IGNORE INTO edges VALUES (?,?,?,?,?)", (e.id, fid, e.type, tid, e.source))
                report["edges"] += cur.rowcount
            # rebuild aggregates for touched entities (spec step 9)
            for eid in touched:
                n = self.db.execute("SELECT COUNT(*) FROM observations WHERE entity_id=?", (eid,)).fetchone()[0]
                self.db.execute(
                    "UPDATE entities SET mention_count=?, state=CASE WHEN ?>0 THEN 'active' ELSE state END WHERE id=?",
                    (n, n, eid),
                )
            report["entities"] = len(touched)
        return report

    @staticmethod
    def _validate(ob: Observation) -> None:
        if not ob.entity_name or not ob.attribute:
            raise ValueError(f"observation missing entity or attribute: {ob}")
        if ob.via not in {"zetaris", "sample", "derived"}:
            raise ValueError(f"unknown provenance path {ob.via!r}")
        if ob.via == "zetaris" and not ob.sql:
            raise ValueError(f"Zetaris observation {ob.attribute} has no SQL provenance")

    def _upsert_entity(self, eid: str, type_: str, name: str, now: float) -> None:
        self.db.execute(
            "INSERT INTO entities (id, type, name, first_seen_at, last_seen_at) VALUES (?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET last_seen_at=excluded.last_seen_at",
            (eid, type_, name, now, now),
        )

    # ------------------------------------------------------------ read surface (spec section 9)

    def current_facts(self, entity_name: str, entity_type: str = "address") -> dict[str, list[dict[str, Any]]]:
        """Latest value per (attribute, source): what each source says is true now."""
        eid = stable_entity_id(entity_name, entity_type)
        rows = self.db.execute(
            "SELECT o.* FROM observations o JOIN ("
            "  SELECT attribute, source, MAX(fetched_at) AS t FROM observations WHERE entity_id=? GROUP BY attribute, source"
            ") latest ON o.attribute=latest.attribute AND o.source=latest.source AND o.fetched_at=latest.t "
            "WHERE o.entity_id=? ORDER BY o.attribute, o.source",
            (eid, eid),
        ).fetchall()
        out: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            out.setdefault(r["attribute"], []).append(_row(r))
        return out

    def fact(self, observation_id: str) -> dict[str, Any] | None:
        r = self.db.execute(
            "SELECT o.*, e.name AS entity_name FROM observations o JOIN entities e ON e.id=o.entity_id WHERE o.id=?", (observation_id,)
        ).fetchone()
        return _row(r) | {"entity_name": r["entity_name"]} if r else None

    def conflicts(self, entity_name: str, entity_type: str = "address") -> list[dict[str, Any]]:
        """Attributes where two sources currently disagree (compared after normalisation)."""
        out = []
        for attribute, facts in self.current_facts(entity_name, entity_type).items():
            values = {normalize_name(str(f["value"])) for f in facts}
            if len(facts) > 1 and len(values) > 1:
                out.append({"attribute": attribute, "facts": facts})
        return out

    def neighbours(self, entity_name: str, entity_type: str = "address") -> list[dict[str, str]]:
        eid = stable_entity_id(entity_name, entity_type)
        rows = self.db.execute(
            "SELECT ed.type, e.type AS to_type, e.name AS to_name, ed.source FROM edges ed JOIN entities e ON e.id=ed.to_id WHERE ed.from_id=?",
            (eid,),
        ).fetchall()
        return [dict(r) for r in rows]

    def snapshot(self) -> dict[str, Any]:
        """Whole-world dump, used by the idempotency check."""
        return {
            t: [dict(r) for r in self.db.execute(f"SELECT * FROM {t} ORDER BY id").fetchall()]
            for t in ("observations", "edges")
        } | {"entities": [dict(r) for r in self.db.execute("SELECT id, type, name, mention_count, state FROM entities ORDER BY id")]}


def _row(r: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": r["id"],
        "attribute": r["attribute"],
        "value": json.loads(r["value_json"]),
        "source": r["source"],
        "via": r["via"],
        "sql": r["sql"],
        "fetched_at": r["fetched_at"],
        "note": r["note"],
    }
