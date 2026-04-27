from __future__ import annotations

import os

import pytest

from vnthuquan import VnThuQuanClient


pytestmark = pytest.mark.skipif(
    os.environ.get("VNTHUQUAN_LIVE_TESTS") != "1",
    reason="set VNTHUQUAN_LIVE_TESTS=1 to run live Vietnam Thu Quan smoke tests",
)


def test_live_default_mirror_responds() -> None:
    client = VnThuQuanClient(timeout=15, retries=1)

    status = client.live_check()

    assert status.ok, status.to_dict()


def test_live_search_returns_results() -> None:
    client = VnThuQuanClient(timeout=15, retries=1)

    results = client.search("Kim Dung", field="author", limit=3)

    assert results
    assert all(result.url for result in results)
