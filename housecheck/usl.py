"""Zetaris Unified Semantic Layer (USL) for HouseCheck: model `student_area`.

Steps (each one is a SQL file under sql/, generated for a set of postcodes):

  01_onboard.sql   Lightning database + one REST table per source per postcode
  02_explore.sql   exploratory queries, 2-3 per source, on the raw REST tables
  03_views.sql     SchemaStore container `housecheck` + one flattened view per source
  04_usl.sql       COMPILE USL student_area (the DDL), descriptions, ACTIVATE, REGISTER DQ, RUN DQ
  05_usl_queries.sql  queries against the activated USL, including the cross-source council check

`housecheck usl sql` writes the files; `housecheck usl run` executes them in order
through the Zetaris REST API and writes the evidence to docs/usl/RESULTS.md.
Statements are separated by `-- @@stmt`, one statement per call, as Zetaris requires.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from . import sources as S
from .zetaris import Zetaris, ZetarisError

SEP = "\n-- @@stmt\n"
NS = "lightning.metastore.housecheck"
MODEL = "student_area"
USL = f"{NS}.{MODEL}"
CONTAINER = "housecheck"

# ---------------------------------------------------------------- the USL DDL (criterion 1c)

USL_DDL = """CREATE TABLE area (postcode varchar(8) NOT NULL PRIMARY KEY, lat decimal(9,6), lng decimal(9,6), local_authority varchar(80), ward varchar(120), lsoa varchar(80), region varchar(80));
CREATE TABLE police_area (postcode varchar(8) NOT NULL PRIMARY KEY, police_force varchar(60), neighbourhood varchar(60));
CREATE TABLE street_crime (crime_key varchar(40) NOT NULL PRIMARY KEY, postcode varchar(8) FOREIGN KEY REFERENCES area(postcode), crime_category varchar(60), crime_month varchar(7), street_name varchar(200), outcome varchar(120));
CREATE TABLE food_establishment (food_key varchar(40) NOT NULL PRIMARY KEY, postcode varchar(8) FOREIGN KEY REFERENCES area(postcode), fhrsid varchar(20), business_name varchar(200), business_type varchar(80), rating_value varchar(40), rating_date date, local_authority varchar(80))"""

DESCRIPTIONS = {
    "": "Student rental areas: where a postcode is, who polices it, recorded street crime nearby and the hygiene of food businesses nearby. Built from postcodes.io, police.uk and the FSA.",
    "area": "One row per postcode a student is considering, from postcodes.io: coordinates, council, ward and LSOA.",
    "police_area": "The police force and neighbourhood team covering the postcode, from police.uk.",
    "street_crime": "One recorded street-level crime within about a mile of the postcode in the latest month, from police.uk. Locations are snapped to anonymous points.",
    "food_establishment": "One of the nearest food businesses (up to 250, within 0.5 miles) to the postcode, with its FSA hygiene rating and the council that inspects it.",
}

DQ_RULES = [
    ("dq_area_in_great_britain", "area", "lat BETWEEN 49.8 AND 60.9 AND lng BETWEEN -8.7 AND 1.8"),
    ("dq_crime_month_format", "street_crime", "crime_month IS NOT NULL AND length(crime_month) = 7"),
    ("dq_food_rating_known", "food_establishment",
     "rating_value IN ('0','1','2','3','4','5','Exempt','AwaitingInspection','AwaitingPublication','Pass','Improvement Required','Pass and Eat Safe')"),
    ("dq_food_rating_dated", "food_establishment", "rating_value NOT IN ('0','1','2','3','4','5') OR rating_date IS NOT NULL"),
    # The FSA uses 1901-01-01 as a placeholder date; the rating scheme only started in 2010.
    ("dq_food_rating_date_real", "food_establishment", "rating_date IS NULL OR rating_date >= DATE '2010-01-01'"),
]


@dataclass
class Area:
    postcode: str
    key: str


def areas(postcodes: list[str]) -> list[Area]:
    out = []
    for p in postcodes:
        pc = S.normalise_postcode(p)
        out.append(Area(pc, S.table_key(pc)))
    return out


def raw(db: str, table: str) -> str:
    return f"{db.lower()}.{table}"


# ---------------------------------------------------------------- 01 onboard

def onboard(db: str, area_list: list[Area], coords: dict[str, tuple[float, float]]) -> list[str]:
    """REST tables. Stage-2 tables need coordinates, which come from querying stage 1 (see run())."""
    out = [f'CREATE LIGHTNING DATABASE {db} DESCRIBE BY "HouseCheck live public data from postcodes.io, police.uk and the FSA"']
    fq = S.freshness_query()
    out.append(S.rest_table(db, fq.table, fq.endpoint, fq.headers))
    for a in area_list:
        q = S.postcode_query(a.key, a.postcode)
        out.append(S.rest_table(db, q.table, q.endpoint, q.headers))
        if a.postcode in coords:
            for q2 in S.area_queries(a.key, *coords[a.postcode]):
                out.append(S.rest_table(db, q2.table, q2.endpoint, q2.headers))
    return out


# ---------------------------------------------------------------- 02 explore (criterion 1b: 2-3 queries per source)

def explore(db: str, area_list: list[Area]) -> list[tuple[str, str]]:
    a = area_list[0]
    pc, hood, crime, food = (raw(db, f"{p}_{a.key}") for p in ("pc", "hood", "crime", "fsa"))
    return [
        ("postcodes.io: where is it and who runs it?", f"SELECT result.postcode, result.admin_district, result.admin_ward, result.lsoa FROM {pc}"),
        ("postcodes.io: which other geographies does it sit in?", f"SELECT result.region, result.parliamentary_constituency, result.codes.admin_district AS council_code FROM {pc}"),
        ("police.uk: which force and neighbourhood team?", f"SELECT force, neighbourhood FROM {hood}"),
        ("police.uk: crimes by category, latest month", f"SELECT category, month, COUNT(*) AS n FROM {crime} GROUP BY category, month ORDER BY n DESC"),
        ("police.uk: what happened to them? (outcomes)", f"SELECT outcome_status.category AS outcome, COUNT(*) AS n FROM {crime} GROUP BY outcome_status.category ORDER BY n DESC"),
        ("police.uk: busiest streets", f"SELECT location.street.name AS street, COUNT(*) AS n FROM {crime} GROUP BY location.street.name ORDER BY n DESC LIMIT 10"),
        ("FSA: hygiene rating distribution", f"SELECT e.RatingValue AS rating, COUNT(*) AS n FROM {food} LATERAL VIEW explode(establishments) AS e GROUP BY e.RatingValue ORDER BY rating"),
        ("FSA: what kinds of food business?", f"SELECT e.BusinessType AS business_type, COUNT(*) AS n FROM {food} LATERAL VIEW explode(establishments) AS e GROUP BY e.BusinessType ORDER BY n DESC"),
        ("FSA: which councils inspect them, and how recently?", f"SELECT e.LocalAuthorityName AS council, COUNT(*) AS n, MIN(e.RatingDate) AS oldest, MAX(e.RatingDate) AS newest FROM {food} LATERAL VIEW explode(establishments) AS e GROUP BY e.LocalAuthorityName"),
    ]


# ---------------------------------------------------------------- 03 views (SchemaStore)

def views(db: str, area_list: list[Area], has_data: dict[str, set[str]] | None = None) -> list[str]:
    """`has_data[source]` = postcode keys whose raw table returned rows. An empty REST table has no
    inferred columns, so it can't be in a UNION (police.uk has no data for some forces)."""
    def union(parts: list[str]) -> str:
        return " UNION ALL ".join(parts)

    def keep(source: str) -> list[Area]:
        if has_data is None:
            return area_list
        return [a for a in area_list if a.key in has_data.get(source, set())]

    area_v = union([
        f"SELECT '{a.postcode}' AS postcode, CAST(result.latitude AS DOUBLE) AS lat, CAST(result.longitude AS DOUBLE) AS lng, "
        f"result.admin_district AS local_authority, result.admin_ward AS ward, result.lsoa AS lsoa, result.region AS region FROM {raw(db, 'pc_' + a.key)}"
        for a in area_list
    ])
    police_v = union([f"SELECT '{a.postcode}' AS postcode, force AS police_force, neighbourhood FROM {raw(db, 'hood_' + a.key)}" for a in keep("hood")])
    crime_v = union([
        f"SELECT concat(CAST(id AS STRING), '-{a.key}') AS crime_key, '{a.postcode}' AS postcode, category AS crime_category, month AS crime_month, "
        f"location.street.name AS street_name, outcome_status.category AS outcome FROM {raw(db, 'crime_' + a.key)}"
        for a in keep("crime")
    ])
    food_v = union([
        f"SELECT concat(CAST(e.FHRSID AS STRING), '-{a.key}') AS food_key, '{a.postcode}' AS postcode, CAST(e.FHRSID AS STRING) AS fhrsid, "
        f"e.BusinessName AS business_name, e.BusinessType AS business_type, CAST(e.RatingValue AS STRING) AS rating_value, "
        f"substr(CAST(e.RatingDate AS STRING), 1, 10) AS rating_date, e.LocalAuthorityName AS local_authority "
        f"FROM {raw(db, 'fsa_' + a.key)} LATERAL VIEW explode(establishments) AS e"
        for a in keep("fsa")
    ])
    out = [f"CREATE SCHEMASTORE CONTAINER {CONTAINER}", f"CREATE SCHEMASTORE VIEW area_v WITH CONTAINER {CONTAINER} AS {area_v}"]
    for name, body in (("police_area_v", police_v), ("street_crime_v", crime_v), ("fsa_establishment_v", food_v)):
        if body:
            out.append(f"CREATE SCHEMASTORE VIEW {name} WITH CONTAINER {CONTAINER} AS {body}")
    return out


PROBES = {
    "hood": ("police.uk neighbourhood", "SELECT force FROM {t} LIMIT 1"),
    "crime": ("police.uk street crime", "SELECT id FROM {t} LIMIT 1"),
    "fsa": ("FSA food hygiene", "SELECT size(establishments) AS n FROM {t}"),
}


# ---------------------------------------------------------------- 04 USL: compile, describe, activate, DQ

def usl() -> list[str]:
    out = [
        "CREATE NAMESPACE IF NOT EXISTS lightning.metastore",
        f"CREATE NAMESPACE IF NOT EXISTS {NS}",
        f"COMPILE USL IF NOT EXISTS {MODEL} DEPLOY NAMESPACE {NS} DDL\n{USL_DDL}",
    ]
    for table, desc in DESCRIPTIONS.items():
        target = USL if not table else f"{USL}.{table}"
        out.append(f"UPDATE USL {target} SET {'TABLE ' if table else ''}DESCRIPTION '{desc}'")
    out += [
        f"ACTIVATE USL TABLE {USL}.area AS SELECT COALESCE(postcode, '') AS postcode, CAST(lat AS DECIMAL(9,6)) AS lat, CAST(lng AS DECIMAL(9,6)) AS lng, local_authority, ward, lsoa, region FROM {CONTAINER}.area_v",
        f"ACTIVATE USL TABLE {USL}.police_area AS SELECT COALESCE(postcode, '') AS postcode, police_force, neighbourhood FROM {CONTAINER}.police_area_v",
        f"ACTIVATE USL TABLE {USL}.street_crime AS SELECT COALESCE(crime_key, '') AS crime_key, postcode, crime_category, crime_month, street_name, outcome FROM {CONTAINER}.street_crime_v",
        f"ACTIVATE USL TABLE {USL}.food_establishment AS SELECT COALESCE(food_key, '') AS food_key, postcode, fhrsid, business_name, business_type, rating_value, CAST(rating_date AS DATE) AS rating_date, local_authority FROM {CONTAINER}.fsa_establishment_v",
    ]
    out += [f"REGISTER DQ {name} TABLE {USL}.{table} AS {expr}" for name, table, expr in DQ_RULES]
    out += [f"RUN DQ TABLE {USL}.{t}" for t in dict.fromkeys(t for _, t, _ in DQ_RULES)]
    out += [f"SHOW DQ ALL INVALID TABLE {USL}.{t}" for t in dict.fromkeys(t for _, t, _ in DQ_RULES)]
    return out


# ---------------------------------------------------------------- 05 queries on the active USL (criterion 1c)

def usl_queries() -> list[tuple[str, str]]:
    t = lambda name: f"{USL}.{name}"  # noqa: E731
    return [
        ("USL: crime profile per postcode, with council and force (3 tables joined)",
         f"SELECT a.postcode, a.local_authority, p.police_force, c.crime_month, COUNT(*) AS crimes, "
         f"SUM(CASE WHEN c.crime_category = 'burglary' THEN 1 ELSE 0 END) AS burglary, "
         f"SUM(CASE WHEN c.crime_category = 'violent-crime' THEN 1 ELSE 0 END) AS violent, "
         f"SUM(CASE WHEN c.crime_category = 'anti-social-behaviour' THEN 1 ELSE 0 END) AS antisocial "
         f"FROM {t('area')} a JOIN {t('police_area')} p ON p.postcode = a.postcode JOIN {t('street_crime')} c ON c.postcode = a.postcode "
         f"GROUP BY a.postcode, a.local_authority, p.police_force, c.crime_month ORDER BY crimes"),
        ("USL: food hygiene per postcode",
         f"SELECT a.postcode, COUNT(*) AS food_places, SUM(CASE WHEN f.rating_value IN ('4','5') THEN 1 ELSE 0 END) AS rated_4_or_5, "
         f"SUM(CASE WHEN f.rating_value IN ('0','1','2') THEN 1 ELSE 0 END) AS rated_0_to_2, "
         f"ROUND(100.0 * SUM(CASE WHEN f.rating_value IN ('4','5') THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN f.rating_value IN ('0','1','2','3','4','5') THEN 1 ELSE 0 END), 0), 1) AS pct_4_or_5 "
         f"FROM {t('area')} a LEFT JOIN {t('food_establishment')} f ON f.postcode = a.postcode GROUP BY a.postcode ORDER BY pct_4_or_5 DESC"),
        ("USL: do the sources agree on the council? (postcodes.io vs FSA inspector)",
         f"SELECT a.postcode, a.local_authority AS council_postcodes_io, f.local_authority AS council_fsa, COUNT(*) AS food_places, "
         f"CASE WHEN lower(a.local_authority) = lower(f.local_authority) THEN 'agree' ELSE 'CONFLICT' END AS status "
         f"FROM {t('area')} a JOIN {t('food_establishment')} f ON f.postcode = a.postcode "
         f"GROUP BY a.postcode, a.local_authority, f.local_authority ORDER BY a.postcode, food_places DESC"),
        ("USL: streets with the most recorded crime near each postcode",
         f"SELECT c.postcode, c.street_name, COUNT(*) AS crimes FROM {t('street_crime')} c GROUP BY c.postcode, c.street_name ORDER BY crimes DESC LIMIT 15"),
    ]


# ---------------------------------------------------------------- write files / run

def write_sql(out_dir: Path, db: str, postcodes: list[str], coords: dict[str, tuple[float, float]]) -> list[Path]:
    a = areas(postcodes)
    out_dir.mkdir(parents=True, exist_ok=True)
    header = f"-- HouseCheck USL, generated {time.strftime('%Y-%m-%d %H:%M')} for {', '.join(x.postcode for x in a)}\n-- One statement per Zetaris call; statements separated by '-- @@stmt'.\n\n"
    files = {
        "01_onboard.sql": onboard(db, a, coords),
        "02_explore.sql": [f"-- {title}\n{sql}" for title, sql in explore(db, a)],
        "03_views.sql": views(db, a),
        "04_usl.sql": usl(),
        "05_usl_queries.sql": [f"-- {title}\n{sql}" for title, sql in usl_queries()],
    }
    paths = []
    for name, stmts in files.items():
        p = out_dir / name
        p.write_text(header + SEP.join(stmts) + "\n", encoding="utf-8")
        paths.append(p)
    return paths


@dataclass
class StepResult:
    phase: str
    title: str
    sql: str
    status: str
    ms: int
    rows: list[dict]
    detail: str = ""


def run(z: Zetaris, postcodes: list[str], phases: list[str], log=print) -> list[StepResult]:
    db = z.s.zetaris_db
    a = areas(postcodes)
    results: list[StepResult] = []

    def do(phase: str, title: str, sql: str, ddl: bool = False) -> StepResult:
        started = time.time()
        try:
            if ddl:
                state = z.ddl(sql)
                r = StepResult(phase, title, sql, state, int((time.time() - started) * 1000), [])
            else:
                res = z.sql(sql, limit=200)
                r = StepResult(phase, title, sql, "ok", res.ms, res.dicts())
        except ZetarisError as e:
            r = StepResult(phase, title, sql, "FAILED", int((time.time() - started) * 1000), [], str(e)[:500])
        results.append(r)
        log(f"  {r.status:8} {phase:8} {title[:90]}" + (f"  ({len(r.rows)} rows)" if r.rows else "") + (f"\n           {r.detail}" if r.detail else ""))
        return r

    if "onboard" in phases:
        for stmt in onboard(db, a, {}):
            do("onboard", stmt.split(" REQUEST")[0][:90], stmt, ddl=True)
        coords = {}
        for x in a:
            q = S.postcode_query(x.key, x.postcode)
            r = do("onboard", f"coordinates for {x.postcode}", q.select(raw(db, q.table)))
            if r.rows:
                coords[x.postcode] = (float(r.rows[0]["lat"]), float(r.rows[0]["lng"]))
        for x in a:
            if x.postcode in coords:
                for q2 in S.area_queries(x.key, *coords[x.postcode]):
                    do("onboard", f"register {q2.table} ({q2.source})", S.rest_table(db, q2.table, q2.endpoint, q2.headers), ddl=True)
    if "explore" in phases:
        for title, sql in explore(db, a):
            do("explore", title, sql)
    if "views" in phases:
        # Probe every raw table: a source with no rows for a postcode is a data-quality finding, not a crash.
        has_data: dict[str, set[str]] = {k: set() for k in PROBES}
        for x in a:
            for src, (label, probe) in PROBES.items():
                r = do("probe", f"{label} has data for {x.postcode}?", probe.format(t=raw(db, f"{src}_{x.key}")))
                n = r.rows[0].get("n") if r.rows and "n" in r.rows[0] else len(r.rows)
                if r.status == "ok" and n and int(n) > 0:
                    has_data[src].add(x.key)
                else:
                    r.status, r.detail = "NO DATA", f"{label} returned nothing for {x.postcode}; left out of the view"
                    log(f"           -> left out of the {src} view (no rows)")
        for stmt in views(db, a, has_data):
            do("views", stmt.split(" AS ")[0][:90], stmt, ddl=True)
    if "usl" in phases:
        for stmt in usl():
            is_query = stmt.startswith(("RUN DQ", "SHOW DQ"))
            do("usl", stmt.split("\n")[0][:90], stmt, ddl=not is_query)
    if "query" in phases:
        for title, sql in usl_queries():
            do("query", title, sql)
    return results


def write_results(path: Path, postcodes: list[str], results: list[StepResult]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# Zetaris USL run: {', '.join(postcodes)}", "", f"Run at {time.strftime('%Y-%m-%d %H:%M')} against the local Zetaris platform.", "",
             "| Phase | Step | Status | ms | Rows |", "|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r.phase} | {r.title.replace('|', '/')[:100]} | {r.status} | {r.ms} | {len(r.rows)} |")
    lines.append("")
    for r in results:
        if r.rows or r.detail:
            lines += [f"## {r.phase}: {r.title}", "", "```sql", r.sql, "```", ""]
            if r.detail:
                lines += [f"**{r.status}:** {r.detail}", ""]
            if r.rows:
                cols = list(r.rows[0].keys())
                lines += ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
                for row in r.rows[:25]:
                    lines.append("| " + " | ".join(json.dumps(row.get(c), default=str).strip('"')[:60] for c in cols) + " |")
                if len(r.rows) > 25:
                    lines.append(f"\n_{len(r.rows) - 25} more rows not shown._")
                lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
