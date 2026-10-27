"""Planner: turns the student's priorities into weights the rest of the run uses.

Nemotron (via Nightshift) reads free text like "I walk home late, I don't
care about takeaways" and returns validated weights. If Nightshift is down the
run still works from keywords, and the report says so.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..llm import LLMError, Nightshift
from ..trace import Trace

FACTORS = {
    "safety": "street crime overall, burglary, violent crime, anti-social behaviour (police.uk)",
    "food": "hygiene ratings of takeaways, cafes and restaurants nearby (FSA)",
}
DEFAULT_WEIGHTS = {"safety": 2, "food": 1}


@dataclass
class Plan:
    weights: dict[str, int]
    highlight_crimes: list[str] = field(default_factory=list)
    focus: str = ""
    planned_by: str = "rules"


CRIME_CATEGORIES = [
    "anti-social-behaviour", "bicycle-theft", "burglary", "criminal-damage-arson", "drugs", "other-theft",
    "possession-of-weapons", "public-order", "robbery", "shoplifting", "theft-from-the-person",
    "vehicle-crime", "violent-crime", "other-crime",
]


def _validate(v: Any) -> Plan:
    w = v["weights"]
    weights = {k: int(w.get(k, 0)) for k in FACTORS}
    if not all(0 <= x <= 3 for x in weights.values()) or not any(weights.values()):
        raise ValueError("weights must be integers 0-3 and not all zero")
    hl = [c for c in v.get("highlight_crimes", []) if c in CRIME_CATEGORIES][:4]
    return Plan(weights, hl, str(v.get("focus", ""))[:300])


def plan(priorities: str, postcodes: list[str], llm: Nightshift, trace: Trace, use_llm: bool = True) -> Plan:
    if use_llm and priorities.strip():
        messages = [
            {"role": "system", "content": (
                "You plan a comparison of UK rental addresses for a student. Factors available:\n"
                + "\n".join(f"- {k}: {d}" for k, d in FACTORS.items())
                + f"\nCrime categories: {', '.join(CRIME_CATEGORIES)}\n"
                "Reply with only JSON: {\"weights\": {\"safety\": 0-3, \"food\": 0-3}, "
                "\"highlight_crimes\": [up to 4 categories from the list], \"focus\": \"one sentence on what matters to this student\"}"
            )},
            {"role": "user", "content": f"Addresses: {', '.join(postcodes)}\nWhat the student cares about: {priorities}"},
        ]
        try:
            p, model = llm.chat_json(trace, "planner", "plan", messages, _validate)
            p.planned_by = f"Nemotron via Nightshift ({model})"
            trace.log("planner", "plan_ready", weights=p.weights, highlight=p.highlight_crimes, by=p.planned_by)
            return p
        except LLMError as e:
            trace.log("planner", "llm_unavailable", status="warn", error=str(e)[:200])

    p = _rules(priorities)
    trace.log("planner", "plan_ready", weights=p.weights, highlight=p.highlight_crimes, by=p.planned_by)
    return p


def _rules(priorities: str) -> Plan:
    t = priorities.lower()
    weights = dict(DEFAULT_WEIGHTS)
    hl = []
    if any(k in t for k in ("safe", "crime", "night", "late", "walk", "burglar", "bike")):
        weights["safety"] = 3
    if any(k in t for k in ("food", "takeaway", "eat", "restaurant", "cafe")):
        weights["food"] = 2
    if "don't care about food" in t or "dont care about food" in t:
        weights["food"] = 0
    if "bike" in t or "bicycle" in t:
        hl.append("bicycle-theft")
    if "burglar" in t or "break in" in t:
        hl.append("burglary")
    if "night" in t or "late" in t:
        hl += ["violent-crime", "anti-social-behaviour"]
    return Plan(weights, hl[:4], priorities.strip()[:300], "keyword rules (Nightshift unavailable)")
