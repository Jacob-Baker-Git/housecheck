"""Critic: the agent that refuses to let anything unsupported through.

Two passes, both deterministic so they can't be talked round:

1. Evidence review, before any writing: conflicts between sources (from the
   World Model), thin samples, stale police data, replayed sample data.
2. Claim review, after the Reporter drafts: every claim must cite World Model
   facts that exist and belong to the right address, and every number in the
   sentence must match one of those facts. Failures go back to the Reporter
   once; anything still unsupported is removed and listed in the report.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..trace import Trace
from ..world_model import WorldModel

MIN_RATED_FOOD = 5


@dataclass
class Flag:
    postcode: str
    kind: str  # conflict | weak | stale | replayed | missing
    message: str
    facts: list[str] = field(default_factory=list)


def review_evidence(postcodes: list[str], world: WorldModel, trace: Trace) -> list[Flag]:
    flags: list[Flag] = []
    for pc in postcodes:
        facts = world.current_facts(pc)
        for c in world.conflicts(pc):
            vals = "; ".join(f"{f['source']} says {f['value']}" for f in c["facts"])
            flags.append(Flag(pc, "conflict", f"Sources disagree on {c['attribute'].replace('_', ' ')}: {vals}. "
                              "Near a council boundary the food data may describe a neighbouring area.", [f["id"] for f in c["facts"]]))
        rated = _val(facts, "food_rated_count")
        if rated is not None and rated < MIN_RATED_FOOD:
            flags.append(Flag(pc, "weak", f"Only {rated} rated food places within 0.5 miles, too few to compare hygiene fairly.", _ids(facts, "food_rated_count")))
        places = _val(facts, "food_places_half_mile")
        if places is not None and places >= 250:
            flags.append(Flag(pc, "weak", f"The FSA returns at most 250 places per search, so these are the {places} nearest food places, not every one within 0.5 miles.", _ids(facts, "food_places_half_mile")))
        month, latest = _val(facts, "crime_month"), _val(facts, "police_data_latest")
        if month and latest and str(month) < str(latest):
            flags.append(Flag(pc, "stale", f"Crime figures are for {month} but police.uk has data to {latest}.", _ids(facts, "crime_month") + _ids(facts, "police_data_latest")))
        if _val(facts, "crime_total_1mile") is None:
            flags.append(Flag(pc, "missing", "police.uk returned no street-crime data for this location (some police forces don't publish there), so crime can't be compared for it.", _ids(facts, "crime_total_1mile")))
        if any(f["via"] == "sample" for fs in facts.values() for f in fs):
            flags.append(Flag(pc, "replayed", "Data replayed from a recorded run, not fetched live through Zetaris just now.", []))
        # Always true of police.uk: say it once per address so nobody over-reads one month.
        if month:
            flags.append(Flag(pc, "weak", f"Crime is one month ({month}) within about a mile; police.uk snaps locations to nearby points, so treat small differences as noise.", _ids(facts, "crime_total_1mile")))
    trace.log("critic", "evidence_review", flags=[{"postcode": f.postcode, "kind": f.kind} for f in flags])
    return flags


BAND_RE = re.compile(r"\b(?:rated|rating|scor(?:e|es|ed|ing)|of)\s+[0-5]\s*(?:or|to|-|–|and)\s*[0-5]\b", re.I)
NUM_RE = re.compile(r"(?<![\w.])-?\d+(?:[.,]\d+)*(?:\.\d+)?")


def _numbers(text: str) -> list[float]:
    out = []
    for m in NUM_RE.findall(text):
        try:
            out.append(float(m.replace(",", "")))
        except ValueError:
            pass
    return out


def _fact_numbers(value: Any) -> list[float]:
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, str):
        return _numbers(value)
    if isinstance(value, dict):
        return [n for v in value.values() for n in _fact_numbers(v)]
    if isinstance(value, list):
        return [n for v in value for n in _fact_numbers(v)]
    return []


def _matches(n: float, allowed: list[float]) -> bool:
    return any(abs(n - a) < 1e-9 or round(a) == n or round(a, 1) == n or abs(n - a) <= 0.5 for a in allowed)


@dataclass
class ClaimVerdict:
    ok: bool
    reason: str = ""


def check_claim(claim: dict[str, Any], postcode: str | None, world: WorldModel, known_numbers: set[float]) -> ClaimVerdict:
    text, ids = str(claim.get("text", "")).strip(), claim.get("facts") or []
    if not text:
        return ClaimVerdict(False, "empty claim")
    if not ids:
        return ClaimVerdict(False, "cites no facts")
    facts = []
    for fid in ids:
        f = world.fact(str(fid))
        if f is None:
            return ClaimVerdict(False, f"cites {fid}, which is not in the World Model")
        if postcode and f["entity_name"] != postcode:
            return ClaimVerdict(False, f"cites {fid}, a fact about {f['entity_name']}, not {postcode}")
        facts.append(f)
    allowed = [n for f in facts for n in _fact_numbers(f["value"])]
    # Hygiene bands ("score 4 or 5", "rated 0-2") name the scale, they aren't data.
    for n in _numbers(BAND_RE.sub(" ", text)):
        # Postcode digits and years/months inside the text are not claims about the data.
        if n in known_numbers:
            continue
        if not _matches(n, allowed):
            return ClaimVerdict(False, f"the number {n:g} is not in the cited facts")
    return ClaimVerdict(True)


def review_claims(draft: dict[str, Any], postcodes: list[str], world: WorldModel, trace: Trace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Returns (accepted, rejected). Each rejected item carries the reason."""
    known = {1.0, 0.5}  # the fixed search radii ("about 1 mile", "0.5 miles")
    for pc in postcodes:
        known.update(_numbers(pc))
    accepted, rejected = [], []
    for block in draft.get("addresses", []):
        pc = block.get("postcode")
        for claim in block.get("claims", []):
            v = check_claim(claim, pc, world, known)
            (accepted if v.ok else rejected).append({**claim, "postcode": pc, **({} if v.ok else {"reason": v.reason})})
    for claim in draft.get("comparison", []):
        v = check_claim(claim, None, world, known)
        (accepted if v.ok else rejected).append({**claim, "postcode": None, **({} if v.ok else {"reason": v.reason})})
    trace.log("critic", "claim_review", accepted=len(accepted), rejected=[{"text": r["text"][:80], "reason": r["reason"]} for r in rejected])
    return accepted, rejected


def _val(facts: dict[str, list[dict[str, Any]]], attr: str) -> Any:
    fs = facts.get(attr) or []
    return fs[0]["value"] if fs else None


def _ids(facts: dict[str, list[dict[str, Any]]], attr: str) -> list[str]:
    return [f["id"] for f in facts.get(attr) or []]
