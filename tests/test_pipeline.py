"""End-to-end runs on synthetic fixtures (tests/fixtures/samples), no network."""

import json

import httpx

from housecheck import pipeline
from housecheck.llm import Nightshift
from housecheck.world_model import WorldModel


def test_offline_run_produces_sourced_report(settings):
    r = pipeline.run(["TE1 1AA", "te2 2bb"], "I walk home late", settings=settings, use_llm=False)
    assert r["postcodes"] == ["TE1 1AA", "TE2 2BB"]
    assert r["claims"] and not r["removed_claims"]  # template claims are always supported
    kinds = {(f["postcode"], f["kind"]) for f in r["flags"]}
    assert ("TE2 2BB", "conflict") in kinds  # FSA authority differs from postcodes.io
    assert ("TE2 2BB", "weak") in kinds  # only 3 rated food places
    assert ("TE1 1AA", "replayed") in kinds
    assert r["ranking"][0]["postcode"] == "TE1 1AA"  # fewer crimes, safety weighted 3
    md = r["report_md"]
    assert "## Sources" in md and "police.uk" in md and "## Checked by the Critic" in md
    assert (settings.runs_dir / r["run_id"] / "trace.jsonl").exists()


def test_rerun_is_idempotent_in_world_model(settings):
    w = WorldModel(settings.world_db)
    pipeline.run(["TE1 1AA", "TE2 2BB"], settings=settings, world=w, use_llm=False)
    snap = w.snapshot()
    pipeline.run(["TE1 1AA", "TE2 2BB"], settings=settings, world=w, use_llm=False)
    assert w.snapshot() == snap


def test_critic_sends_bad_claim_back_and_nemotron_fixes_it(settings, monkeypatch):
    """Fake Nightshift: the first draft invents a number, the revision fixes it."""
    from dataclasses import replace

    s = replace(settings, llm_token="test-token")
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        system = body["messages"][0]["content"]
        if "plan a comparison" in system:
            reply = {"weights": {"safety": 3, "food": 1}, "highlight_crimes": ["violent-crime"], "focus": "walks home late"}
        else:
            calls["n"] += 1
            facts = json.loads(body["messages"][1]["content"])["facts"]
            fid = next(f["id"] for f in facts["TE1 1AA"] if f["attribute"] == "crime_total_1mile")
            number = 99 if calls["n"] == 1 else 45
            reply = {"headline": "TE1 1AA looks quieter.", "addresses": [
                {"postcode": "TE1 1AA", "claims": [{"text": f"{number} street crimes within about 1 mile.", "facts": [fid]}]},
                {"postcode": "TE2 2BB", "claims": []}], "comparison": []}
        return httpx.Response(200, json={"model": "nvidia/nemotron-test", "choices": [{"message": {"content": "<think>x</think>" + json.dumps(reply)}}]})

    fake = Nightshift(s, client=httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(pipeline, "Nightshift", lambda _s: fake)
    r = pipeline.run(["TE1 1AA", "TE2 2BB"], "I walk home late", settings=s)
    assert calls["n"] == 2 and r["revisions"] == 1
    assert [c["text"] for c in r["claims"]] == ["45 street crimes within about 1 mile."]
    assert r["plan"]["weights"] == {"safety": 3, "food": 1}
    assert "Nemotron" in r["written_by"]


def test_address_with_no_crime_data_is_flagged_not_fatal(settings):
    r = pipeline.run(["TE1 1AA", "TE3 3CC"], settings=settings, use_llm=False)
    assert ("TE3 3CC", "missing") in {(f["postcode"], f["kind"]) for f in r["flags"]}
    assert not r["removed_claims"]
