"""Reporter: Nemotron writes the comparison, citing World Model fact IDs for every claim.

The table of numbers is built deterministically from the World Model; the
model only writes the plain-English claims around it, and the Critic checks
each one. If Nightshift is unavailable, a template reporter writes plain
claims from the same facts so a demo never dies (and the report says so).
"""

from __future__ import annotations

import json
from typing import Any

from ..llm import LLMError, Nightshift
from ..trace import Trace
from ..world_model import WorldModel
from .critic import Flag
from .planner import Plan

REPORT_ATTRS = [
    "local_authority", "ward", "police_force", "crime_month", "crime_total_1mile", "crime_burglary",
    "crime_violent", "crime_antisocial", "crime_bicycle_theft", "crime_by_category",
    "food_places_half_mile", "food_rated_count", "food_pct_rated_4_or_5", "food_rated_0_to_2", "food_avg_rating",
]


def fact_sheet(postcodes: list[str], world: WorldModel) -> dict[str, list[dict[str, Any]]]:
    sheet = {}
    for pc in postcodes:
        facts = world.current_facts(pc)
        sheet[pc] = [
            {"id": f["id"], "attribute": a, "value": f["value"], "source": f["source"], **({"note": f["note"]} if f["note"] else {})}
            for a in REPORT_ATTRS for f in facts.get(a, [])
        ]
    return sheet


def _validate(v: Any) -> dict[str, Any]:
    if not isinstance(v.get("addresses"), list):
        raise ValueError("'addresses' must be a list")
    for b in v["addresses"]:
        if "postcode" not in b or not isinstance(b.get("claims"), list):
            raise ValueError("each address needs 'postcode' and a 'claims' list")
        for c in b["claims"]:
            if not isinstance(c.get("facts"), list) or not c.get("text"):
                raise ValueError("each claim needs 'text' and a 'facts' list of fact ids")
    v.setdefault("comparison", [])
    v.setdefault("headline", "")
    return v


SYSTEM = (
    "You write a short, plain-English comparison of UK rental addresses for a university student.\n"
    "Rules:\n"
    "- Use ONLY the facts given. Every claim must list the ids of the facts it relies on in 'facts'.\n"
    "- Every number you write must appear in a cited fact. Do not compute new numbers (no differences, ratios or percentages that are not given).\n"
    "- If you mention a month, cite the crime_month fact.\n"
    "- Respect each fact's note. In particular food_places_half_mile is the nearest places capped at 250: say 'the nearest 250 food places', never '250 food places within half a mile'.\n"
    "- Respect the reviewer flags: mention a conflict or weak evidence rather than hiding it, and never call an area 'safe' or 'dangerous'; compare.\n"
    "- 2-4 claims per address, 1-3 comparison claims. Short sentences.\n"
    "Reply with only JSON: {\"headline\": \"one sentence\", \"addresses\": [{\"postcode\": \"...\", \"claims\": [{\"text\": \"...\", \"facts\": [\"obs_...\"]}]}], "
    "\"comparison\": [{\"text\": \"...\", \"facts\": [\"obs_...\"]}]}"
)


def draft(postcodes: list[str], plan: Plan, flags: list[Flag], world: WorldModel, llm: Nightshift, trace: Trace,
          feedback: list[dict[str, Any]] | None = None, previous: dict[str, Any] | None = None, use_llm: bool = True) -> tuple[dict[str, Any], str]:
    sheet = fact_sheet(postcodes, world)
    if use_llm:
        user = {
            "student_priorities": plan.focus,
            "weights": plan.weights,
            "highlight_crimes": plan.highlight_crimes,
            "facts": sheet,
            "reviewer_flags": [{"postcode": f.postcode, "kind": f.kind, "message": f.message} for f in flags],
        }
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps(user, default=str)}]
        if feedback and previous:
            messages += [
                {"role": "assistant", "content": json.dumps(previous)},
                {"role": "user", "content": "The reviewer rejected these claims:\n" + "\n".join(f"- \"{r['text']}\": {r['reason']}" for r in feedback)
                 + "\nRewrite the whole JSON. Fix or drop each rejected claim; keep the accepted ones."},
            ]
        try:
            v, model = llm.chat_json(trace, "reporter", "revise" if feedback else "draft", messages, _validate)
            return v, f"Nemotron via Nightshift ({model})"
        except LLMError as e:
            trace.log("reporter", "llm_unavailable", status="warn", error=str(e)[:200])
    return template_draft(postcodes, sheet, plan), "template (Nightshift unavailable)"


def template_draft(postcodes: list[str], sheet: dict[str, list[dict[str, Any]]], plan: Plan) -> dict[str, Any]:
    def f(pc: str, attr: str) -> dict[str, Any] | None:
        return next((x for x in sheet[pc] if x["attribute"] == attr), None)

    out: dict[str, Any] = {"headline": "", "addresses": [], "comparison": []}
    for pc in postcodes:
        claims = []
        total, month = f(pc, "crime_total_1mile"), f(pc, "crime_month")
        if total and total["value"] is not None and month:
            claims.append({"text": f"police.uk recorded {total['value']} street crimes within about 1 mile in {month['value']}.", "facts": [total["id"], month["id"]]})
        for attr, label in (("crime_burglary", "burglaries"), ("crime_violent", "violent crimes")):
            x = f(pc, attr)
            if x is not None and plan.weights.get("safety", 0) >= 2:
                claims.append({"text": f"That includes {x['value']} {label}.", "facts": [x["id"]]})
        pct, rated = f(pc, "food_pct_rated_4_or_5"), f(pc, "food_rated_count")
        if pct and rated and plan.weights.get("food", 0) > 0:
            claims.append({"text": f"{pct['value']}% of {rated['value']} rated food places within 0.5 miles score 4 or 5 for hygiene.", "facts": [pct["id"], rated["id"]]})
        out["addresses"].append({"postcode": pc, "claims": claims})
    totals = [(pc, f(pc, "crime_total_1mile")) for pc in postcodes]
    totals = [(pc, t) for pc, t in totals if t and t["value"] is not None]
    if len(totals) >= 2:
        lo = min(totals, key=lambda t: t[1]["value"])
        hi = max(totals, key=lambda t: t[1]["value"])
        if lo[0] != hi[0]:
            out["comparison"].append({"text": f"{lo[0]} had the fewest recorded crimes nearby ({lo[1]['value']}) and {hi[0]} the most ({hi[1]['value']}).", "facts": [lo[1]["id"], hi[1]["id"]]})
    out["headline"] = "Comparison written from a template because Nightshift was unavailable."
    return out
