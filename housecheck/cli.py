"""Command line.

  housecheck doctor                          test every Zetaris and Nightshift step (run first)
  housecheck usl run "PC1, PC2, PC3"         build the Zetaris USL, run DQ, write docs/usl/RESULTS.md
  housecheck status
  housecheck compare "GU2 7XH, GU1 1AA" --priorities "I walk home late"
  housecheck record "GU2 7XH" [--direct]     save a replayable sample
  housecheck serve                           web page on http://localhost:8000
"""

from __future__ import annotations

import argparse
import re
import sys

import httpx

from . import config as C
from . import sources as S
from .agents.researcher import ZetarisPort, research
from .llm import Nightshift
from .trace import Trace
from .world_model import WorldModel
from .zetaris import Zetaris


def split_postcodes(text: str) -> list[str]:
    parts = [p for p in re.split(r",|;|\bvs\b|\n", text, flags=re.I) if p.strip()]
    return [S.normalise_postcode(p) for p in parts]


def cmd_status(_: argparse.Namespace) -> int:
    s = C.load()
    z_state, z_detail = Zetaris(s).status()
    l_state, models, l_detail = Nightshift(s).status()
    samples = sorted(p.stem for p in s.samples_dir.glob("*.json")) if s.samples_dir.exists() else []
    print(f"Zetaris    {z_state:12} {s.zetaris_url}  {z_detail}")
    print(f"Nightshift {l_state:12} {s.llm_url}  {', '.join(models[:5]) or l_detail}")
    print(f"Data mode  {s.data_mode}")
    print(f"Samples    {', '.join(samples) or 'none recorded yet'}")
    return 0 if z_state == "online" and l_state == "online" else 1


def cmd_doctor(a: argparse.Namespace) -> int:
    """Step-by-step check of every sponsor integration. Run this first on a new machine."""
    s = C.load()
    z, llm = Zetaris(s), Nightshift(s)
    ok = True

    def step(name: str, fn) -> object:
        nonlocal ok
        try:
            out = fn()
            print(f"  PASS  {name}" + (f"  -> {out}" if out not in (None, "") else ""))
            return out
        except Exception as e:  # noqa: BLE001 - report every failure plainly
            ok = False
            print(f"  FAIL  {name}\n        {str(e)[:400]}")
            return None

    pc = S.normalise_postcode(a.postcode)
    key = S.table_key(pc)
    print(f"Zetaris  ({s.zetaris_url}, database {s.zetaris_db})")
    step("API key set", lambda: "yes" if s.zetaris_key else (_ for _ in ()).throw(RuntimeError("set ZETARIS_API_KEY in .env")))
    step("SELECT 1", lambda: z.sql("SELECT 1 AS one").rows)
    step("create Lightning database", lambda: z.ddl(f'CREATE LIGHTNING DATABASE {s.zetaris_db} DESCRIBE BY "HouseCheck live public data"'))
    q = S.postcode_query(key, pc)
    step(f"register REST table {q.table} (postcodes.io)", lambda: z.ddl(S.rest_table(s.zetaris_db, q.table, q.endpoint, q.headers)))
    rows = step(f"query {q.table}", lambda: z.sql(q.select(f"{s.zetaris_db.lower()}.{q.table}")).dicts())
    if rows:
        lat, lng = float(rows[0]["lat"]), float(rows[0]["lng"])
        for q2 in S.area_queries(key, lat, lng) + [S.freshness_query()]:
            step(f"register {q2.table} ({q2.source})", lambda q2=q2: z.ddl(S.rest_table(s.zetaris_db, q2.table, q2.endpoint, q2.headers)))
            step(f"query {q2.table}", lambda q2=q2: f"{len(z.sql(q2.select(f'{s.zetaris_db.lower()}.{q2.table}')).rows)} rows")

    print(f"\nNightshift  ({s.llm_url}, model {s.llm_model})")
    step("runtime token found", lambda: "yes" if s.llm_token else (_ for _ in ()).throw(RuntimeError("set METERLESS_RUNTIME_TOKEN or start Nightshift on this machine")))
    step("GET /models", lambda: (lambda st: st[1][:5] if st[0] == "online" else (_ for _ in ()).throw(RuntimeError(f"{st[0]}: {st[2]}")))(llm.status()))
    step("one chat completion", lambda: (lambda r: f"{r.model}: {r.content[:60]!r}")(llm.chat([{"role": "user", "content": "Reply with the single word: ready"}])))
    print("\nAll good." if ok else "\nFix the first FAIL above, then run doctor again.")
    return 0 if ok else 1


def cmd_compare(a: argparse.Namespace) -> int:
    from .pipeline import run

    pcs = split_postcodes(" ".join(a.postcodes))
    r = run(pcs, a.priorities or "", mode=a.mode, use_llm=not a.no_llm)
    print(r["report_md"])
    print(f"\n(trace: runs/{r['run_id']}/trace.jsonl)", file=sys.stderr)
    return 0


def cmd_record(a: argparse.Namespace) -> int:
    s = C.load()
    for pc in split_postcodes(" ".join(a.postcodes)):
        key = S.table_key(pc)
        if a.direct:
            http = httpx.Client(timeout=30)
            q = S.postcode_query(key, pc)
            first = S.direct_rows(q, http)
            results = {"postcode": {"sql": "", "endpoint": q.endpoint, "rows": first}}
            for q in S.area_queries(key, float(first[0]["lat"]), float(first[0]["lng"])) + [S.freshness_query()]:
                results[q.name] = {"sql": "", "endpoint": q.endpoint, "rows": S.direct_rows(q, http)}
            path = S.save_sample(s.samples_dir, key, pc, results, "direct")
        else:
            trace = Trace(s.runs_dir)
            port = ZetarisPort(Zetaris(s), trace)
            research(pc, port, WorldModel(), trace, trace.run_id)
            path = S.save_sample(s.samples_dir, key, pc, port.recorded, "zetaris")
        print(f"{pc}: saved {path}")
    return 0


def cmd_usl(a: argparse.Namespace) -> int:
    """Build and showcase the Zetaris Unified Semantic Layer for a set of postcodes."""
    import os

    from . import usl

    s = C.load()
    raw = " ".join(a.postcodes) or os.environ.get("USL_POSTCODES", "")
    if not raw.strip():
        print('Give 3 or more postcodes, e.g. housecheck usl run "GU2 7XH, GU1 ..., GU2 ..." (or set USL_POSTCODES in .env)')
        return 2
    pcs = split_postcodes(raw)
    out_dir = C.ROOT / "sql"
    if a.action == "sql":
        for p in usl.write_sql(out_dir, s.zetaris_db, pcs, {}):
            print(f"wrote {p}")
        print("(01_onboard.sql has stage-1 tables only; stage-2 tables need coordinates, which `usl run` gets from Zetaris.)")
        return 0
    phases = a.phases.split(",") if a.phases else ["onboard", "explore", "views", "usl", "query"]
    print(f"Zetaris USL `{usl.MODEL}` for {', '.join(pcs)}  (phases: {', '.join(phases)})")
    results = usl.run(Zetaris(s), pcs, phases)
    coords = {}
    for r in results:
        if r.title.startswith("coordinates for ") and r.rows:
            coords[r.title.removeprefix("coordinates for ")] = (float(r.rows[0]["lat"]), float(r.rows[0]["lng"]))
    usl.write_sql(out_dir, s.zetaris_db, pcs, coords)
    path = usl.write_results(C.ROOT / "docs" / "usl" / "RESULTS.md", pcs, results)
    failed = [r for r in results if r.status == "FAILED"]
    print(f"\nEvidence: {path}\nSQL files: {out_dir}\n{len(results) - len(failed)} ok, {len(failed)} failed")
    return 1 if failed else 0


def cmd_serve(a: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run("housecheck.server:app", host=a.host, port=a.port)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="housecheck")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    d = sub.add_parser("doctor", help="test Zetaris and Nightshift step by step")
    d.add_argument("--postcode", default="GU2 7XH")
    d.set_defaults(fn=cmd_doctor)
    c = sub.add_parser("compare")
    c.add_argument("postcodes", nargs="+", help='e.g. "GU2 7XH, GU1 1AA"')
    c.add_argument("--priorities", "-p", default="")
    c.add_argument("--mode", choices=["live", "auto", "sample"])
    c.add_argument("--no-llm", action="store_true", help="skip Nightshift (template planner/reporter)")
    c.set_defaults(fn=cmd_compare)
    r = sub.add_parser("record")
    r.add_argument("postcodes", nargs="+")
    r.add_argument("--direct", action="store_true", help="fetch the APIs directly instead of through Zetaris")
    r.set_defaults(fn=cmd_record)
    u = sub.add_parser("usl", help="build the Zetaris Unified Semantic Layer and record evidence")
    u.add_argument("action", choices=["run", "sql"])
    u.add_argument("postcodes", nargs="*")
    u.add_argument("--phases", help="comma list of onboard,explore,views,usl,query (default all)")
    u.set_defaults(fn=cmd_usl)
    sv = sub.add_parser("serve")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8000)
    sv.set_defaults(fn=cmd_serve)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
