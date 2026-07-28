from __future__ import annotations

import pytest

from jz_calendar.mta_client import FeedError, MTAClient


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"header": {"incrementality": "FULL_DATASET"}, "entity": []},
        {
            "header": {"incrementality": "FULL_DATASET"},
            "entity": [{"alert": {}}],
        },
        {"header": {"incrementality": "DIFFERENTIAL"}, "entity": [{"alert": {}}]},
        "not-an-object",
    ],
)
def test_empty_or_malformed_response_rejected(payload):
    with pytest.raises(FeedError):
        MTAClient.validate(payload)
