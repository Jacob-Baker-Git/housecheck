"""The public data HouseCheck uses, registered in Zetaris as Lightning REST tables.

Per postcode, four REST tables are registered at run time in the HouseCheck
Lightning database and then queried with SQL:

  pc_<key>     postcodes.io          -> coordinates, local authority, ward, LSOA
  hood_<key>   police.uk neighbourhood -> police force and neighbourhood
  crime_<key>  police.uk street crime  -> crimes within 1 mile, latest month (aggregated in SQL)
  fsa_<key>    FSA food hygiene        -> the nearest food businesses (up to 250) within 0.5 miles, sorted by distance

plus one shared table, `crime_updated` (police.uk data freshness).

The second stage depends on the first: the coordinates that Zetaris returns
from postcodes.io are what the police and FSA tables are registered with.

Rows from every query are saved to data/samples/<key>.json, in the same shape
Zetaris returns, so `sample` mode replays exactly what Zetaris answered.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

UA = "HouseCheck/0.1 (Open Agent Hackathon 2026)"
POSTCODE_RE = re.compile(r"^([A-Z]{1,2}[0-9][A-Z0-9]?)\s*([0-9][A-Z]{2})$")

SRC_POSTCODES = "postcodes.io"
SRC_POLICE = "police.uk"
SRC_FSA = "FSA food hygiene"

FOOD_RADIUS_MILES = 0.5
# The FSA returns at most this many per page. Without sortOptionKey=distance it does NOT return the nearest ones.
FOOD_PAGE_SIZE = 250


class SourceError(RuntimeError):
    pass


def normalise_postcode(raw: str) -> str:
    m = POSTCODE_RE.match(raw.strip().upper().replace("  ", " "))
    if not m:
        raise SourceError(f"{raw!r} is not a valid UK postcode")
    return f"{m.group(1)} {m.group(2)}"


def table_key(postcode: str) -> str:
    return normalise_postcode(postcode).replace(" ", "").lower()


def rest_table(db: str, table: str, endpoint: str, headers: dict[str, str] | None = None) -> str:
    h = ", ".join(f'{k} "{v}"' for k, v in ({"user-agent": UA, "accept": "application/json"} | (headers or {})).items())
    return (
        f'CREATE LIGHTNING REST TABLE {table} FROM {db} REQUEST(endpoint "{endpoint}", method "get", '
        f'response_type "json", http_encoding "URLENCODED") HEADER ({h}) BODY ()'
    )


# ---------------------------------------------------------------- query plans

@dataclass
class Query:
    name: str  # key in the sample file
    source: str
    table: str
    endpoint: str
    select: Callable[[str], str]  # fully-qualified table -> SQL
    headers: dict[str, str] | None = None


def postcode_query(key: str, postcode: str) -> Query:
    return Query(
        "postcode", SRC_POSTCODES, f"pc_{key}",
        f"https://api.postcodes.io/postcodes/{postcode.replace(' ', '')}",
        lambda t: (
            "SELECT result.postcode AS postcode, result.latitude AS lat, result.longitude AS lng, "
            "result.admin_district AS admin_district, result.admin_ward AS ward, result.lsoa AS lsoa "
            f"FROM {t}"
        ),
    )


def area_queries(key: str, lat: float, lng: float) -> list[Query]:
    return [
        Query(
            "neighbourhood", SRC_POLICE, f"hood_{key}",
            f"https://data.police.uk/api/locate-neighbourhood?q={lat:.6f},{lng:.6f}",
            lambda t: f"SELECT force, neighbourhood FROM {t}",
        ),
        Query(
            "crime", SRC_POLICE, f"crime_{key}",
            f"https://data.police.uk/api/crimes-street/all-crime?lat={lat:.6f}&lng={lng:.6f}",
            lambda t: f"SELECT category, month, COUNT(*) AS n FROM {t} GROUP BY category, month ORDER BY n DESC",
        ),
        Query(
            "food", SRC_FSA, f"fsa_{key}",
            f"https://api.ratings.food.gov.uk/Establishments?latitude={lat:.6f}&longitude={lng:.6f}"
            f"&maxDistanceLimit={FOOD_RADIUS_MILES}&sortOptionKey=distance&pageSize={FOOD_PAGE_SIZE}",
            lambda t: (
                "SELECT e.RatingValue AS rating, e.LocalAuthorityName AS authority, COUNT(*) AS n "
                f"FROM {t} LATERAL VIEW explode(establishments) AS e GROUP BY e.RatingValue, e.LocalAuthorityName"
            ),
            headers={"x-api-version": "2"},
        ),
    ]


def freshness_query() -> Query:
    return Query(
        "crime_updated", SRC_POLICE, "crime_updated",
        "https://data.police.uk/api/crime-last-updated",
        lambda t: f"SELECT date FROM {t}",
    )


# ---------------------------------------------------------------- samples (recorded Zetaris answers)

def sample_path(samples_dir: Path, key: str) -> Path:
    return samples_dir / f"{key}.json"


def load_sample(samples_dir: Path, key: str) -> dict[str, Any]:
    path = sample_path(samples_dir, key)
    if not path.exists():
        available = sorted(p.stem for p in samples_dir.glob("*.json")) if samples_dir.exists() else []
        raise SourceError(f"no recorded sample for {key} (have: {', '.join(available) or 'none'})")
    return json.loads(path.read_text(encoding="utf-8"))


def save_sample(samples_dir: Path, key: str, postcode: str, results: dict[str, dict[str, Any]], via: str) -> Path:
    samples_dir.mkdir(parents=True, exist_ok=True)
    path = sample_path(samples_dir, key)
    payload = {"postcode": postcode, "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "recorded_via": via, "queries": results}
    path.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    return path


# ---------------------------------------------------------------- direct fetch (only for recording samples without Zetaris)

def direct_rows(q: Query, http) -> list[dict[str, Any]]:
    """Fetch the endpoint directly and reshape it to the rows the Zetaris SQL would return.

    Used by scripts/record_samples.py --direct when Zetaris is unavailable. Rows
    recorded this way are labelled `recorded_via: direct` and never `zetaris`.
    """
    res = http.get(q.endpoint, headers={"user-agent": UA, "accept": "application/json", **(q.headers or {})})
    res.raise_for_status()
    body = res.json()
    if q.name == "postcode":
        r = body["result"]
        return [{"postcode": r["postcode"], "lat": r["latitude"], "lng": r["longitude"], "admin_district": r["admin_district"], "ward": r["admin_ward"], "lsoa": r["lsoa"]}]
    if q.name == "neighbourhood":
        return [{"force": body.get("force"), "neighbourhood": body.get("neighbourhood")}]
    if q.name == "crime_updated":
        return [{"date": body.get("date")}]
    if q.name == "crime":
        counts: dict[tuple[str, str], int] = {}
        for c in body:
            k = (c["category"], c["month"])
            counts[k] = counts.get(k, 0) + 1
        return [{"category": c, "month": m, "n": n} for (c, m), n in sorted(counts.items(), key=lambda kv: -kv[1])]
    if q.name == "food":
        counts2: dict[tuple[str, str], int] = {}
        for e in body.get("establishments", []):
            k = (str(e.get("RatingValue")), e.get("LocalAuthorityName") or "")
            counts2[k] = counts2.get(k, 0) + 1
        return [{"rating": r, "authority": a, "n": n} for (r, a), n in counts2.items()]
    raise SourceError(f"unknown query {q.name}")
