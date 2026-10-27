import json
from dataclasses import replace

import httpx

from housecheck import usl
from housecheck.zetaris import Zetaris

PCS = ["TE1 1AA", "TE2 2BB", "TE3 3CC"]


def test_sql_files_cover_every_criterion(tmp_path):
    paths = usl.write_sql(tmp_path, "HOUSECHECK_LIVE", PCS, {"TE1 1AA": (51.2, -0.5)})
    text = {p.name: p.read_text() for p in paths}
    assert text["04_usl.sql"].count("CREATE TABLE") == 4  # the USL DDL
    assert "COMPILE USL IF NOT EXISTS student_area DEPLOY" in text["04_usl.sql"]
    assert text["04_usl.sql"].count("REGISTER DQ") == 5 and "RUN DQ TABLE" in text["04_usl.sql"]
    assert text["02_explore.sql"].count("@@stmt") >= 8  # 3 sources x 2-3 queries
    assert text["05_usl_queries.sql"].count("lightning.metastore.housecheck.student_area") >= 4
    assert "crime_te11aa" in text["01_onboard.sql"] and "crime_te22bb" not in text["01_onboard.sql"]  # stage 2 needs coordinates
    assert text["03_views.sql"].count("UNION ALL") >= 3 * (len(PCS) - 1)
    # Column names Zetaris's USL compiler is known to reject
    assert " text " not in usl.USL_DDL


def test_run_executes_every_phase_against_fake_zetaris(settings):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        sql = json.loads(request.content)["sql"]
        seen.append(sql)
        if "result.latitude AS lat" in sql:
            return httpx.Response(200, json={"data": [{"postcode": "X", "lat": 51.2, "lng": -0.5, "admin_district": "D", "ward": "W", "lsoa": "L"}]})
        if sql.startswith("CREATE SCHEMASTORE CONTAINER"):
            return httpx.Response(400, json={"error": "container housecheck already exists"})
        return httpx.Response(200, json={"headers": ["n"], "data": [[1]]})

    z = Zetaris(replace(settings, zetaris_key="k"), client=httpx.Client(transport=httpx.MockTransport(handler)))
    results = usl.run(z, PCS, ["onboard", "explore", "views", "usl", "query"], log=lambda *_: None)
    assert not [r for r in results if r.status == "FAILED"]
    assert any(r.status == "exists" for r in results)
    assert sum(1 for s in seen if s.startswith("CREATE LIGHTNING REST TABLE crime_te")) == len(PCS)
    assert any(s.startswith("COMPILE USL") for s in seen) and any(s.startswith("RUN DQ") for s in seen)
    out = usl.write_results(settings.runs_dir / "RESULTS.md", PCS, results)
    assert "| query |" in out.read_text()
