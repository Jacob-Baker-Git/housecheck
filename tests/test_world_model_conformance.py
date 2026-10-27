"""Meterless World Model conformance suite, ported to Python.

Each test mirrors one check in the official runner
(github.com/Meterless/Meterless/blob/main/engines/world-model/conformance/runner.ts),
with the same id and description. The official runner loads a TypeScript module,
so it can't run HouseCheck's Python engine directly; this port runs the same
assertions against it. The reference implementation itself passes the official
runner 8/8 (checked when these vectors were generated).

`test_ids_match_reference_vectors` compares HouseCheck's IDs with IDs produced by
the reference implementation's own `entityIdFromName` / `normalizeName` / `decide`
(tests/fixtures/meterless_reference_vectors.json), so the two agree byte for byte.
"""

import json
from pathlib import Path

import pytest

from housecheck.world_model import (
    Edge, Observation, ProvenanceError, WorldModel, decide, entity_id_from_name, normalize_name,
)

VECTORS = json.loads((Path(__file__).parent / "fixtures" / "meterless_reference_vectors.json").read_text(encoding="utf-8"))

# The two observations the official runner ingests ("Fed holds rates", "Powell signals patience"),
# expressed as HouseCheck observations: same entity, two facts, one source.
def observations(title_suffix: str = ""):
    return [
        Observation("person", "Jerome Powell", "headline:a1", "Fed holds rates" + title_suffix, "rss", "derived", fetched_at=1.0),
        Observation("person", "Jerome Powell", "headline:a2", "Powell signals patience", "rss", "derived", fetched_at=2.0),
    ]


def test_ids_match_reference_vectors():
    for v in VECTORS["ids"]:
        assert normalize_name(v["name"]) == v["normalized"], v["name"]
        assert entity_id_from_name(v["type"], v["name"]) == v["id"], v["name"]
    for v in VECTORS["decide"]:
        assert decide(v["s"]) == v["d"], v["s"]


def test_sid_001_diacritics_and_nbsp_normalize_identically():
    """stable ids: diacritics and NBSP normalize identically (NFKD + strip marks)"""
    assert normalize_name("José  García") == normalize_name("Jose Garcia")
    assert entity_id_from_name("person", "José García") == entity_id_from_name("person", "jose garcia")


def test_sid_002_distinct_names_stay_distinct():
    """stable ids: distinct names stay distinct (no over-normalization)"""
    assert entity_id_from_name("org", "Acme Corp") != entity_id_from_name("org", "Acme Corporation")
    assert entity_id_from_name("person", "x") != entity_id_from_name("org", "x")


def test_band_001_merge_bands_at_the_boundaries():
    """merge bands at the boundaries: 0.85 auto, 0.84 review, 0.82 review, 0.81 new"""
    assert decide(0.85) == "auto-merge"
    assert decide(0.84) == "review"
    assert decide(0.82) == "review"
    assert decide(0.81) == "new"


def test_prov_001_writes_without_provenance_are_rejected():
    """writes without provenance are rejected"""
    w = WorldModel()
    with pytest.raises(ProvenanceError):
        w.ingest([Observation("person", "No Provenance", "x", 1, source="", via="derived")])
    with pytest.raises(ProvenanceError):
        w.ingest([Observation("address", "A1 1AA", "crime_total_1mile", 5, "police.uk", "zetaris", sql="")])
    with pytest.raises(ProvenanceError):
        w.relate(Edge("A1 1AA", "address", "in_ward", "W", "ward", source=""))
    assert w.snapshot()["observations"] == [] and w.audit() == []


def test_idem_001_same_batch_twice_produces_an_empty_diff():
    """ingest idempotency: same batch twice produces an empty diff"""
    w = WorldModel()
    w.ingest(observations())
    shape1 = w.state_shape_canonical()
    second = w.ingest(observations())
    assert second["changed"] is False
    assert w.state_shape_canonical() == shape1


def test_idem_002_a_mutated_batch_changes_the_shape():
    """the idempotency check can fail: a mutated batch changes the shape"""
    w = WorldModel()
    w.ingest(observations())
    shape1 = w.state_shape_canonical()
    run = w.ingest(observations(" (edited)"))
    assert run["changed"] is True
    assert w.state_shape_canonical() != shape1


def test_bitemp_001_superseding_edge_closes_the_old_one():
    """bitemporal edges: a superseding edge closes the old one; point-in-time queries respect validity"""
    w = WorldModel()
    w.relate(Edge("p1", "player", "plays-for", "a", "team", "manual", valid_from="2087-01-01T00:00:00.000Z"))
    w.relate(Edge("p1", "player", "plays-for", "b", "team", "manual", valid_from="2088-03-01T00:00:00.000Z"))
    now = w.neighbors_of("p1", "player", via="plays-for")
    assert [n["to_name"] for n in now] == ["b"]
    then = w.neighbors_of("p1", "player", via="plays-for", at="2087-06-01T00:00:00.000Z")
    assert [n["to_name"] for n in then] == ["a"]


def test_audit_001_every_mutation_writes_an_audit_entry_in_order():
    """every mutation writes an audit entry in order"""
    w = WorldModel()
    w.ingest([Observation("x", "Audit One", "a", 1, "manual", "derived", fetched_at=1.0)])
    w.ingest([Observation("x", "Audit Two", "a", 1, "manual", "derived", fetched_at=2.0)])
    audit = w.audit()
    assert len(audit) >= 2
    assert all(audit[i]["seq"] > audit[i - 1]["seq"] for i in range(1, len(audit)))
