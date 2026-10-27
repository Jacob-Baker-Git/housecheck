from dataclasses import replace
from pathlib import Path

import pytest

from housecheck import config as C

FIXTURES = Path(__file__).parent / "fixtures" / "samples"


@pytest.fixture
def settings(tmp_path):
    return replace(
        C.load(),
        samples_dir=FIXTURES,
        runs_dir=tmp_path / "runs",
        world_db=tmp_path / "world.sqlite",
        data_mode="sample",
        zetaris_key="",
        llm_token="",
    )
