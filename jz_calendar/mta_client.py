from __future__ import annotations

import logging
from typing import Any

import httpx

DEFAULT_MTA_URL = (
    "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fsubway-alerts.json"
)


class FeedError(RuntimeError):
    """The MTA feed could not be safely used."""


class MTAClient:
    def __init__(self, url: str = DEFAULT_MTA_URL, timeout_seconds: float = 30) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds
        self.log = logging.getLogger(__name__)

    def fetch(self) -> dict[str, Any]:
        try:
            response = httpx.get(
                self.url,
                timeout=self.timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": "jz-service-calendar/1.0"},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise FeedError(f"Unable to fetch valid MTA JSON: {exc}") from exc
        self.validate(payload)
        self.log.info(
            "mta_feed_fetched",
            extra={"event": "mta_feed_fetched", "entity_count": len(payload["entity"])},
        )
        return payload

    @staticmethod
    def validate(payload: object) -> None:
        if not isinstance(payload, dict):
            raise FeedError("MTA response must be a JSON object")
        header = payload.get("header")
        entities = payload.get("entity")
        if not isinstance(header, dict) or header.get("incrementality") != "FULL_DATASET":
            raise FeedError("MTA response is not a recognized full-dataset feed")
        if not isinstance(entities, list) or not entities:
            raise FeedError("MTA response contains no entities; refusing destructive sync")
        alerts = [
            item["alert"]
            for item in entities
            if isinstance(item, dict) and isinstance(item.get("alert"), dict)
        ]
        if not alerts:
            raise FeedError("MTA response has no valid alert entities")
        if not any(
            isinstance(alert.get("active_period"), list)
            and isinstance(alert.get("informed_entity"), list)
            and isinstance(alert.get("header_text"), dict)
            for alert in alerts
        ):
            raise FeedError("MTA alert schema is not recognized")
