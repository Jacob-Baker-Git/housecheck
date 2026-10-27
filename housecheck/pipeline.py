"""One HouseCheck run: Planner -> Researcher -> Critic (evidence) -> Reporter <-> Critic (claims) -> report."""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from typing import Any

from . import config as C
from .agents import critic, planner, reporter, researcher
from .llm import Nightshift
from .sources import SourceError, normalise_postcode
from .trace import Trace
from .world_model import WorldModel
from .zetaris import Zetaris, ZetarisError

MAX_REVISIONS = 1


def score(postcodes: list[str], world: WorldModel, weights: dict[str, int]) -> list[dict[str, Any]]:
    """Deterministic fit-for-priorities score (0-100). Relative to the addresses compared, not absolute."""
    def val(pc: str, attr: str) -> float | None:
        fs = world.current_facts(pc).get(attr) or []
        v = fs[0]["value"] if fs else None
        return float(v) if isinstance(v, (int, float)) else None

    metrics = {"safety": ("crime_total_1mile", False), "food": ("food_pct_rated_4_or_5", True)}
    parts: dict[str, dict[str, float]] = {pc: {} for pc in postcodes}
    for factor, (attr, higher_better) in metrics.items():
        vals = {pc: val(pc, attr) for pc in postcodes}
        present = [v for v in vals.values() if v is not None]
        if not present:
            continue
        lo, hi = min(present), max(present)
        for pc, v in vals.items():
            if v is None:
                continue
            norm = 1.0 if hi == lo else (v - lo) / (hi - lo)
            parts[pc][factor] = norm if higher_better else 1 - norm
    total_w = sum(weights.get(f, 0) for f in metrics) or 1
    out = []
    for pc in postcodes:
        s = sum(weights.get(f, 0) * parts[pc].get(f, 0.5) for f in metrics) / total_w
        out.append({"postcode": pc, "score": round(100 * s), "parts": {k: round(100 * v) for k, v in parts[pc].items()}})
    return sorted(out, key=lambda r: -r["score"])


def run(addresses: list[str], priorities: str = "", mode: str | None = None, settings: C.Settings | None = None,
        world: WorldModel | None = None, use_llm: bool = True) -> dict[str, Any]:
    s = settings or C.load()
    mode = (mode or s.data_mode).lower()
    trace = Trace(s.runs_dir)
    world = world or WorldModel(s.world_db)
    z, llm = Zetaris(s), Nightshift(s)
    started = time.time()

    postcodes = []
    for a in addresses:
        pc = normalise_postcode(a)
        if pc not in postcodes:
            postcodes.append(pc)
    if not 2 <= len(postcodes) <= 4:
        raise SourceError("compare between 2 and 4 different postcodes")
    trace.log("pipeline", "start", postcodes=postcodes, priorities=priorities, mode=mode)

    # 1. Planner
    p = planner.plan(priorities, postcodes, llm, trace, use_llm=use_llm)

    # 2. Researcher (through Zetaris) -> World Model
    data_paths = {}
    for pc in postcodes:
        port = researcher.make_port(pc, mode, z, s.samples_dir, trace)
        researcher.research(pc, port, world, trace, trace.run_id)
        data_paths[pc] = port.origin
        if isinstance(port, researcher.ZetarisPort):
            # Keep what Zetaris answered, so the same run can be replayed offline later.
            from .sources import save_sample, table_key
            save_sample(s.samples_dir, table_key(pc), pc, port.recorded, "zetaris")

    # 3. Critic: evidence review
    flags = critic.review_evidence(postcodes, world, trace)

    # 4. Reporter <-> Critic
    draft, written_by = reporter.draft(postcodes, p, flags, world, llm, trace, use_llm=use_llm)
    accepted, rejected = critic.review_claims(draft, postcodes, world, trace)
    revisions = 0
    while rejected and revisions < MAX_REVISIONS and written_by.startswith("Nemotron"):
        revisions += 1
        draft2, written_by = reporter.draft(postcodes, p, flags, world, llm, trace, feedback=rejected, previous=draft, use_llm=use_llm)
        accepted2, rejected2 = critic.review_claims(draft2, postcodes, world, trace)
        draft, accepted, rejected = draft2, accepted2, rejected2

    ranking = score(postcodes, world, p.weights)
    result = {
        "run_id": trace.run_id,
        "postcodes": postcodes,
        "priorities": priorities,
        "plan": asdict(p),
        "data_paths": data_paths,
        "headline": draft.get("headline", ""),
        "facts": reporter.fact_sheet(postcodes, world),
        "flags": [asdict(f) for f in flags],
        "claims": accepted,
        "removed_claims": rejected,
        "ranking": ranking,
        "written_by": written_by,
        "revisions": revisions,
        "seconds": round(time.time() - started, 1),
    }
    result["report_md"] = render_markdown(result, world)
    result["trace"] = [{k: v for k, v in e.items() if k in ("agent", "action", "status", "query", "rows", "ms", "model", "postcode", "accepted")} for e in trace.events]
    trace.save("result.json", json.dumps({k: v for k, v in result.items() if k != "report_md"}, indent=1, default=str))
    trace.save("report.md", result["report_md"])
    trace.log("pipeline", "done", seconds=result["seconds"], claims=len(accepted), removed=len(rejected), revisions=revisions)
    return result


# ---------------------------------------------------------------- report

ROWS = [
    ("Council (postcodes.io)", "local_authority", "postcodes.io"),
    ("Police force", "police_force", None),
    ("Crime month", "crime_month", None),
    ("Street crimes, ~1 mile", "crime_total_1mile", None),
    ("  burglary", "crime_burglary", None),
    ("  violent crime", "crime_violent", None),
    ("  anti-social behaviour", "crime_antisocial", None),
    ("  bicycle theft", "crime_bicycle_theft", None),
    ("Food places (nearest, max 250)", "food_places_half_mile", None),
    ("  rated 4-5 (%)", "food_pct_rated_4_or_5", None),
    ("  rated 0-2", "food_rated_0_to_2", None),
]


def render_markdown(r: dict[str, Any], world: WorldModel) -> str:
    pcs = r["postcodes"]
    sources: dict[str, int] = {}
    lines = [f"# HouseCheck: {' vs '.join(pcs)}", ""]
    if r["priorities"]:
        lines += [f"**What matters to you:** {r['priorities']}", ""]
    if r["headline"]:
        lines += [f"> {r['headline']}", ""]

    lines += ["## At a glance", "", "| | " + " | ".join(pcs) + " |", "|---|" + "---|" * len(pcs)]
    for label, attr, only_source in ROWS:
        cells = []
        for pc in pcs:
            fs = [f for f in world.current_facts(pc).get(attr, []) if not only_source or f["source"] == only_source]
            cells.append(str(fs[0]["value"]) if fs and fs[0]["value"] is not None else "–")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines.append("")

    lines += ["## Fit for your priorities", ""]
    w = r["plan"]["weights"]
    lines.append(f"Weights: safety {w.get('safety', 0)}, food hygiene {w.get('food', 0)} (set by {r['plan']['planned_by']}). "
                 "Scores are relative to these addresses only.")
    lines.append("")
    for i, x in enumerate(r["ranking"], 1):
        lines.append(f"{i}. **{x['postcode']}**: {x['score']}/100")
    lines.append("")

    def cite(ids: list[str]) -> str:
        marks = []
        for fid in ids:
            f = world.fact(fid)
            if not f:
                continue
            key = f"{f['source']}|{f['sql']}"
            if key not in sources:
                sources[key] = len(sources) + 1
            marks.append(sources[key])
        return "".join(f"[{m}]" for m in sorted(set(marks)))

    lines += ["## What the agents found", ""]
    for pc in pcs:
        cs = [c for c in r["claims"] if c.get("postcode") == pc]
        if cs:
            lines.append(f"**{pc}**")
            lines += [f"- {c['text']} {cite(c['facts'])}" for c in cs]
            lines.append("")
    comp = [c for c in r["claims"] if c.get("postcode") is None]
    if comp:
        lines.append("**Side by side**")
        lines += [f"- {c['text']} {cite(c['facts'])}" for c in comp]
        lines.append("")

    flags = [f for f in r["flags"]]
    if flags:
        lines += ["## Checked by the Critic", ""]
        for f in flags:
            lines.append(f"- **{f['postcode']}** ({f['kind']}): {f['message']}")
        lines.append("")
    if r["removed_claims"]:
        lines += ["## Removed because the evidence didn't support them", ""]
        lines += [f"- ~~{c['text']}~~ ({c['reason']})" for c in r["removed_claims"]]
        lines.append("")

    lines += ["## Sources", ""]
    for key, n in sorted(sources.items(), key=lambda kv: kv[1]):
        src, sql = key.split("|", 1)
        lines.append(f"{n}. {src}" + (f": `{sql}`" if sql else ""))
    paths = "; ".join(f"{pc}: {v}" for pc, v in r["data_paths"].items())
    lines += ["", f"_Data path: {paths}. Written by {r['written_by']}; {r['revisions']} revision(s) after review. Run {r['run_id']} in {r['seconds']}s._", ""]
    return "\n".join(lines)
