import pytest

from housecheck.agents.critic import check_claim
from housecheck.llm import extract_json, strip_reasoning
from housecheck.sources import SourceError, normalise_postcode, table_key
from housecheck.world_model import Observation, WorldModel
from housecheck.zetaris import normalise


@pytest.fixture
def world():
    w = WorldModel()
    w.ingest([
        Observation("address", "TE1 1AA", "crime_total_1mile", 45, "police.uk", "zetaris", "s", 1.0),
        Observation("address", "TE1 1AA", "food_pct_rated_4_or_5", 92.7, "FSA food hygiene", "zetaris", "s", 1.0),
        Observation("address", "TE2 2BB", "crime_total_1mile", 81, "police.uk", "zetaris", "s", 1.0),
    ])
    return w


def ids(w, pc, attr):
    return [f["id"] for f in w.current_facts(pc)[attr]]


def test_supported_claim_passes(world):
    c = {"text": "45 street crimes were recorded within about 1 mile.", "facts": ids(world, "TE1 1AA", "crime_total_1mile")}
    assert check_claim(c, "TE1 1AA", world, {1.0}).ok


def test_rounded_percentage_passes(world):
    c = {"text": "About 93% of food places score 4 or 5.", "facts": ids(world, "TE1 1AA", "food_pct_rated_4_or_5")}
    assert check_claim(c, "TE1 1AA", world, set()).ok


def test_invented_number_is_rejected(world):
    c = {"text": "60 street crimes were recorded.", "facts": ids(world, "TE1 1AA", "crime_total_1mile")}
    v = check_claim(c, "TE1 1AA", world, set())
    assert not v.ok and "60" in v.reason


def test_computed_difference_is_rejected(world):
    # 81 - 45 = 36 is not in any cited fact: the Reporter must not do arithmetic.
    c = {"text": "TE2 2BB had 36 more crimes.", "facts": ids(world, "TE1 1AA", "crime_total_1mile") + ids(world, "TE2 2BB", "crime_total_1mile")}
    assert not check_claim(c, None, world, {1.0, 2.0}).ok


def test_fact_about_other_address_is_rejected(world):
    c = {"text": "81 crimes.", "facts": ids(world, "TE2 2BB", "crime_total_1mile")}
    assert not check_claim(c, "TE1 1AA", world, set()).ok


def test_uncited_and_unknown_facts_are_rejected(world):
    assert not check_claim({"text": "Lovely area.", "facts": []}, "TE1 1AA", world, set()).ok
    assert not check_claim({"text": "Lovely area.", "facts": ["obs_nope"]}, "TE1 1AA", world, set()).ok


def test_postcodes():
    assert normalise_postcode("gu27xh") == "GU2 7XH"
    assert table_key(" GU2 7XH ") == "gu27xh"
    with pytest.raises(SourceError):
        normalise_postcode("not a postcode")


def test_json_extraction_and_reasoning_strip():
    assert extract_json('Sure!\n```json\n{"a": 1}\n```') == {"a": 1}
    assert strip_reasoning("<think>hmm</think>\n{\"a\":1}") == '{"a":1}'
    assert strip_reasoning("thinking without open tag</think>answer") == "answer"


def test_zetaris_reply_shapes():
    assert normalise({"headers": ["a", "b"], "data": [[1, 2]]}) == (["a", "b"], [[1, 2]])
    assert normalise({"data": [{"a": 1, "b": 2}]}) == (["a", "b"], [[1, 2]])
    assert normalise({"columns": [{"name": "a"}], "data": [[1]]}) == (["a"], [[1]])
