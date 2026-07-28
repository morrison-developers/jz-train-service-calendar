from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def make_entity():
    def factory(
        *,
        alert_id: str = "lmm:planned_work:100",
        alert_type: str = "Planned - Part Suspended",
        header: str = "No [J] trains between Crescent St and Broad St",
        description: str = "Use alternate service.",
        informed: list[dict[str, str]] | None = None,
        periods: list[dict[str, int]] | None = None,
        updated: int = 1_700_000_000,
    ) -> dict[str, Any]:
        return {
            "id": alert_id,
            "alert": {
                "active_period": periods or [{"start": 1_800_000_000, "end": 1_800_003_600}],
                "informed_entity": informed or [{"route_id": "J"}],
                "header_text": {"translation": [{"language": "en", "text": header}]},
                "description_text": {"translation": [{"language": "en", "text": description}]},
                "transit_realtime.mercury_alert": {
                    "alert_type": alert_type,
                    "updated_at": updated,
                },
            },
        }

    return factory


@pytest.fixture
def feed():
    def factory(*entities: dict[str, Any]) -> dict[str, Any]:
        return {
            "header": {
                "gtfs_realtime_version": "2.0",
                "incrementality": "FULL_DATASET",
                "timestamp": 1_700_000_000,
            },
            "entity": list(entities),
        }

    return factory
