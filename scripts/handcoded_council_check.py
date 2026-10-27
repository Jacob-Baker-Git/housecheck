"""Hand-coded version of ONE USL query, for the Zetaris reflection (criterion 2a bonus).

Does what `05_usl_queries.sql` query 3 ("do the sources agree on the council?")
plus the `dq_food_rating_known` rule do on the USL, but by calling the three
APIs directly and joining in Python. Run it next to the USL query and compare:

    python scripts/handcoded_council_check.py "GU2 7XH, GU1 ..., GU2 ..."

It prints the same table and the time taken, so the two can be compared fairly.
"""

from __future__ import annotations

import sys
import time
from collections import Counter

import httpx

UA = {"user-agent": "HouseCheck handcoded comparison", "accept": "application/json"}
KNOWN_RATINGS = {"0", "1", "2", "3", "4", "5", "Exempt", "AwaitingInspection", "AwaitingPublication", "Pass", "Improvement Required", "Pass and Eat Safe"}


def main(raw: str) -> None:
    started = time.time()
    http = httpx.Client(timeout=30, headers=UA)
    rows, invalid = [], 0
    for pc in [p.strip().upper() for p in raw.split(",") if p.strip()]:
        # 1. postcodes.io: coordinates and council (hand-written URL, hand-parsed JSON)
        r = http.get(f"https://api.postcodes.io/postcodes/{pc.replace(' ', '')}")
        r.raise_for_status()
        res = r.json()["result"]
        lat, lng, council = res["latitude"], res["longitude"], res["admin_district"]
        # 2. FSA: food places nearby (needs its own header, own pagination limits, own JSON shape)
        f = http.get(
            "https://api.ratings.food.gov.uk/Establishments",
            params={"latitude": lat, "longitude": lng, "maxDistanceLimit": 0.5, "sortOptionKey": "distance", "pageSize": 250},
            headers={"x-api-version": "2"},
        )
        f.raise_for_status()
        places = f.json().get("establishments", [])
        # 3. the "join" and the "data quality rule", by hand
        invalid += sum(1 for e in places if str(e.get("RatingValue")) not in KNOWN_RATINGS)
        for fsa_council, n in Counter(e.get("LocalAuthorityName") for e in places).most_common():
            status = "agree" if (fsa_council or "").lower() == council.lower() else "CONFLICT"
            rows.append((pc, council, fsa_council, n, status))
    ms = int((time.time() - started) * 1000)

    print(f"{'postcode':9} {'council_postcodes_io':22} {'council_fsa':22} {'n':>4}  status")
    for pc, a, b, n, s in rows:
        print(f"{pc:9} {a[:22]:22} {str(b)[:22]:22} {n:>4}  {s}")
    print(f"\nrating values failing the 'known rating' rule: {invalid}")
    print(f"hand-coded run: {ms} ms")
    print("Not included, and each would be more code: caching, retries, schema/types, a place others can query it with SQL, "
          "re-running the rule on new data, police.uk (a third API shape), and keeping this in sync with the agent's own code.")


if __name__ == "__main__":
    main(" ".join(sys.argv[1:]) or "GU2 7XH")
