# 2. Reflection on the USL

> Numbers are from the live run on 27 Oct 2026 ([`RESULTS.md`](RESULTS.md)): 3 postcodes, 1,703 street crimes and 750 food places through the USL. Lines still marked ⟨fill⟩ are Jacob's own estimates or the hand-coded timing.

## 2a. How the USL saved time compared with hand-coding

**What the USL path costs to add a source:** one `CREATE LIGHTNING REST TABLE`, one SchemaStore view that flattens it, one `CREATE TABLE` in the `COMPILE USL` DDL, and one `ACTIVATE`. Everything after that is SQL: joins, rules and the agent's queries.

**What the hand-coded path costs:** a separate HTTP client per API (each with its own headers, parameters and JSON shape), hand-written parsing, hand-written joins, and a hand-written data-quality check that only runs when that script runs.

**Bonus comparison.** `scripts/handcoded_council_check.py` re-implements one USL query (does postcodes.io agree with the FSA on the council?) plus one DQ rule, by calling the APIs directly:

| | USL (`05_usl_queries.sql` query 3 + `dq_food_rating_known`) | Hand-coded |
|---|---|---|
| Code | 1 SQL query (9 lines) + 1 rule (1 line) | ~60 lines of Python, 2 of the 3 sources |
| Covers police.uk too | Yes, same model | No: would be a third client and shape |
| Others can query it | Yes, SQL on `lightning.metastore.housecheck.student_area` | No |
| DQ rule reusable | Registered once, `RUN DQ` any time, `SHOW DQ ALL INVALID` lists rows | Re-written per script |
| Same answer? | Yes: all three councils agree | Yes: all three councils agree, 0 rating values fail the rule |
| Time for 3 postcodes | 2,148 ms (one SQL query over 750 food places) | 547 ms |

**The hand-coded script is about 4× faster for this one question,** because it goes straight to two APIs with no SQL engine in between. We're not claiming the USL is faster to *run*. What it saves is *build and change* time: the 547 ms script answers exactly one question for two of the three sources, and every new question, source or rule means more Python. On the USL, the same model answered four different questions, and five DQ rules over 2,456 rows (3 areas, 1,703 crimes, 750 food places), with no new code.

**What the live run produced** (all from SQL on `lightning.metastore.housecheck.student_area`):

| | GU2 7XH (Guildford) | SO14 5FN (Southampton) | BL4 0LL (Bolton) |
|---|---|---|---|
| Street crimes, Aug 2026, ~1 mile | 554 | 1,149 | no data from police.uk |
| Food places rated 4–5 | 91.9% | 84.5% | 69.1% |
| Food places rated 0–2 (of nearest 250) | 4 | 12 | 28 |

DQ rules ran over every row: `dq_crime_month_format` 1,703/1,703 valid; `dq_food_rating_known` and `dq_food_rating_dated` 750/750 valid; primary and foreign keys all valid. `RUN DQ` took 4–11 s per table.

**Where the time actually went.** The whole USL went from first run to a clean 66/66 in about 15 minutes on the morning of 27 Oct (06:50 to 07:04), across three runs. Each fix was one change to a source definition, not to the agents: leaving out a source with no data (Bolton crime), and re-pointing the FSA source to sort by distance. Once the views existed, each question in `02_explore.sql` and `05_usl_queries.sql` was a single SQL statement. Hand-coding the same three sources and the cross-source check would, in my estimate, have taken ⟨fill: your estimate, e.g. "an afternoon"⟩, and the agent would have had to own that code.

**The USL caught a bug in our own data.** On the first full run, query 2 ("food hygiene per postcode") returned exactly 250 food places for every postcode, all 250 rated 4 or 5. Seeing three different towns side by side in one table made it obvious that was wrong: the FSA caps a search at 250 results and, unless you pass `sortOptionKey=distance`, doesn't return the nearest ones. The council check (query 3) agreed: it listed New Forest for central Southampton and Wigan for Farnworth, both too far away for a 0.5-mile search. We fixed the source definition, re-registered it, re-activated `food_establishment`, and the USL tables and DQ rules picked it up without touching the agent code. In a hand-coded pipeline that check would have been a one-off script nobody re-ran.

**Honest cost.** Because each postcode has different coordinates, each one needs its own REST tables, and the views have to be re-created when a postcode is added (see 2c). For an app taking any postcode, the agent's live path still registers tables per request.

## 2b. Would the USL help in my work?

I'm a second-year Computer Science student heading into a placement year, so "my work" is projects and, from next summer, a placement.

**Where it would help.** In my Custom PC Builder project, the component catalogue (678 components) comes from several retailers' data, each with its own names and formats. I wrote validation scripts and tests to keep it consistent. A USL would have given one model (`component`, `retailer_price`, `compatibility`), declared keys, and DQ rules that run on demand instead of only in CI. In banking or payments placements (I've done work experience at Lloyds and Global Payments), the same pattern applies to systems that each name the same customer or merchant differently.

**Where it wouldn't.** For a single source with a stable schema, or a mobile app that has to work offline (my IronPulse Android app deliberately has no network permission), a semantic layer adds a server I don't need.

**Bonus: forecast.** For the PC Builder catalogue: onboarding a new retailer feed is currently ⟨fill: e.g. ~3 hours⟩ (parser, mapping, tests); on a USL I'd expect ⟨fill: ~1 hour⟩ (REST table, view, activate), mostly because the joins and DQ rules already exist. Over ⟨fill⟩ feeds that is ⟨fill⟩ hours saved.

## 2c. How to make the USL stronger: a PM requirement

### Requirement: parameterised REST sources

**Problem.** Public APIs are usually *queried by parameter* (a postcode, a coordinate, a date), not downloaded whole. Today a Lightning REST table has a fixed endpoint, so HouseCheck needs one table per postcode (`crime_gu27xh`, `crime_gu11aa`, …), the SchemaStore views are `UNION ALL`s that must be rebuilt for every new postcode, and the USL has to be re-activated. That breaks the promise of "one governed model" for exactly the sources agents use most.

**User story.** *As a data engineer, I register `police.uk street crime` once, with `lat` and `lng` as parameters, and any USL table or query that joins it supplies the parameters from another table. As an agent, I query the USL for a postcode nobody has asked about before and Zetaris fetches it.*

**Acceptance criteria.**
1. `CREATE LIGHTNING REST TABLE … PARAMETERS (name type, …)` with `{name}` placeholders in the endpoint, headers and body.
2. Parameters bound by `WHERE` equality or by a `LATERAL` join from another table.
3. Per-parameter-set caching with a TTL, so repeated questions don't hit the API.
4. USL tables can be activated over a parameterised source; DQ rules run over whatever has been fetched.
5. Rate-limit settings per source (police.uk and FSA both throttle).
6. A declared schema for a REST table (`COLUMNS (id BIGINT, category STRING, …)`), so an empty response still has columns. We hit this live: police.uk returned no street crime for BL4 0LL (Bolton), the table had no inferred columns, the `UNION ALL` view failed, and every USL table built on it failed with it. HouseCheck now probes each source first and leaves empty ones out, but the platform should handle "no rows" as a normal answer.

**Why it matters for Zetaris.** Agents ask new questions constantly. Without parameters, every new postcode, company or date is a DDL change. With them, the USL describes the *shape* of the world once and fetches facts on demand, which is what an agent data layer needs.

**Bonus: mock of the feature and the resulting USL.**

```sql
-- One source, not one per postcode
CREATE LIGHTNING REST TABLE postcode_lookup FROM HOUSECHECK_LIVE
  PARAMETERS (pc STRING)
  REQUEST(endpoint "https://api.postcodes.io/postcodes/{pc}", method "get", response_type "json") CACHE TTL 30 DAYS;

CREATE LIGHTNING REST TABLE street_crime_at FROM HOUSECHECK_LIVE
  PARAMETERS (lat DOUBLE, lng DOUBLE)
  REQUEST(endpoint "https://data.police.uk/api/crimes-street/all-crime?lat={lat}&lng={lng}", method "get", response_type "json")
  CACHE TTL 1 DAY RATE LIMIT 15 PER SECOND;

-- The USL activates over the parameterised sources once
ACTIVATE USL TABLE lightning.metastore.housecheck.student_area.street_crime AS
SELECT concat(CAST(c.id AS STRING), '-', a.postcode) AS crime_key, a.postcode, c.category AS crime_category,
       c.month AS crime_month, c.location.street.name AS street_name, c.outcome_status.category AS outcome
FROM lightning.metastore.housecheck.student_area.area a,
     LATERAL street_crime_at(a.lat, a.lng) c;

-- A brand-new postcode is now just a query, no DDL
SELECT crime_category, COUNT(*) FROM lightning.metastore.housecheck.student_area.street_crime
WHERE postcode = 'GU2 7XH' GROUP BY crime_category;
```

Today's equivalent in this repo is `housecheck/usl.py`, which generates one REST table and one `UNION ALL` branch per postcode: about 30 lines of generated SQL per postcode that the feature above would remove.
