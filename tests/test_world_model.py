import pytest

from housecheck.world_model import Edge, Observation, WorldModel, normalize_name, stable_entity_id


def test_stable_ids_ignore_case_whitespace_and_accents():
    assert normalize_name("  Café   Road ") == "cafe road"
    assert stable_entity_id("GU2 7XH", "address") == stable_entity_id("gu2  7xh", "address")
    assert stable_entity_id("GU2 7XH", "address") != stable_entity_id("GU2 7XH", "ward")
    assert stable_entity_id("x", "address").startswith("ent_")


def _obs():
    return [
        Observation("address", "GU2 7XH", "crime_total_1mile", 120, "police.uk", "zetaris", "SELECT 1", 1.0),
        Observation("address", "GU2 7XH", "local_authority", "Guildford", "postcodes.io", "zetaris", "SELECT 2", 1.0),
    ]


def test_ingest_is_idempotent():
    w = WorldModel()
    edges = [Edge("GU2 7XH", "address", "in_local_authority", "Guildford", "local_authority", "postcodes.io")]
    first = w.ingest(_obs(), edges)
    snap = w.snapshot()
    second = w.ingest(_obs(), edges)
    assert first["observations_new"] == 2
    assert second["observations_new"] == 0 and second["observations_seen"] == 2
    assert w.snapshot() == snap


def test_conflict_when_sources_disagree():
    w = WorldModel()
    w.ingest(_obs() + [Observation("address", "GU2 7XH", "local_authority", "Waverley", "FSA food hygiene", "zetaris", "SELECT 3", 2.0)])
    conflicts = w.conflicts("GU2 7XH")
    assert [c["attribute"] for c in conflicts] == ["local_authority"]
    assert {f["source"] for f in conflicts[0]["facts"]} == {"postcodes.io", "FSA food hygiene"}


def test_no_conflict_when_sources_agree_after_normalising():
    w = WorldModel()
    w.ingest(_obs() + [Observation("address", "GU2 7XH", "local_authority", "guildford ", "FSA food hygiene", "zetaris", "SELECT 3", 2.0)])
    assert w.conflicts("GU2 7XH") == []


def test_latest_value_per_source_wins():
    w = WorldModel()
    w.ingest([Observation("address", "A1 1AA", "crime_total_1mile", 10, "police.uk", "zetaris", "s", 1.0)])
    w.ingest([Observation("address", "A1 1AA", "crime_total_1mile", 12, "police.uk", "zetaris", "s", 2.0)])
    assert w.current_facts("A1 1AA")["crime_total_1mile"][0]["value"] == 12


def test_zetaris_observation_needs_sql():
    with pytest.raises(ValueError):
        WorldModel().ingest([Observation("address", "A1 1AA", "x", 1, "police.uk", "zetaris", "")])
