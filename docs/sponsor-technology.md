# How HouseCheck uses the sponsor technology

## Zetaris: the data layer

HouseCheck never calls a public API itself during a run. For each postcode the Researcher:

1. creates (once) the Lightning database `HOUSECHECK_LIVE`;
2. registers `pc_<postcode>` as a Lightning REST table over postcodes.io and selects coordinates, council, ward and LSOA from it;
3. uses **the coordinates Zetaris returned** to register three more REST tables: `hood_<postcode>` (police.uk neighbourhood), `crime_<postcode>` (police.uk street crime) and `food_<postcode>` (FSA ratings within 0.5 miles, with the `x-api-version: 2` header);
4. aggregates in Zetaris SQL rather than in Python:
   - crime: `SELECT category, month, COUNT(*) AS n FROM … GROUP BY category, month`
   - food: `SELECT e.RatingValue, e.LocalAuthorityName, COUNT(*) FROM … LATERAL VIEW explode(establishments) AS e GROUP BY …`

The exact SQL is stored with every fact in the World Model and printed under **Sources** in each report, so a judge can re-run any number in the Zetaris SQL editor.

Each live run also saves Zetaris's answers to `data/samples/`, so the same comparison can be replayed offline; the report labels replayed data.

## Meterless Nightshift with NVIDIA Nemotron: the reasoning

`housecheck/llm.py` follows the Meterless Runtime provider contract: OpenAI-compatible `/v1/chat/completions`, bearer runtime token (read from Nightshift's `proxy-token` file if not set), `meterless-app: housecheck`, `meterless-scope: user`, a raised first-token limit for Nemotron's reasoning, and `GET /v1/models` as the health check.

Two agents use it:
- **Planner**: student's free-text priorities → validated weights and crime categories to highlight.
- **Reporter**: writes the comparison as JSON claims that must cite World Model fact IDs; revises once if the Critic rejects claims.

Numbers never come from the model. The Critic rejects any sentence containing a number that isn't in the facts it cites, including arithmetic the model did itself.

## Meterless World Model engine: one shared truth

`housecheck/world_model.py` implements the Meterless World Model specification in Python:

| Spec | HouseCheck |
|---|---|
| Stable hash IDs (§3) | `ent_` + first 16 hex of sha256(`type:normalized_name`), NFKD/casing/whitespace normalised |
| Idempotent ingest (§5) | observation ID = hash of entity, attribute, value, source; re-ingesting is a no-op (tested) |
| Provenance | source, path (`zetaris`/`sample`), exact SQL, fetch time on every observation |
| Entities and edges | address → ward, council, police force |
| Aggregates rebuilt (§5 step 9) | `mention_count`, `state` updated for touched entities |
| Derived views (§8–9) | `current_facts` (latest per attribute and source) and `conflicts` (sources disagree) |

The council comes from two sources (postcodes.io, and the authority that inspects most nearby food places). When they differ, the World Model's `conflicts` view surfaces it and the Critic tells the student the food data may describe the neighbouring area.

## Zetaris USL

See [`usl/USE_CASE.md`](usl/USE_CASE.md), [`usl/REFLECTION.md`](usl/REFLECTION.md) and the evidence in [`usl/RESULTS.md`](usl/RESULTS.md).
