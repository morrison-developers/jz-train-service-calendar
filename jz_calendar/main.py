from __future__ import annotations

import argparse
import logging
import sys

from jz_calendar.calendar_client import GoogleCalendarClient
from jz_calendar.classifier import classify
from jz_calendar.config import Settings
from jz_calendar.events import build_events
from jz_calendar.logging_config import configure_logging
from jz_calendar.mta_client import FeedError, MTAClient
from jz_calendar.parser import parse_feed
from jz_calendar.sync import synchronize


def run(settings: Settings) -> int:
    configure_logging(settings.log_level)
    log = logging.getLogger(__name__)
    try:
        payload = MTAClient().fetch()
        parsed = parse_feed(payload)
        if not parsed or not any(alert.periods for alert in parsed):
            raise FeedError("No parseable active periods; refusing destructive sync")
        desired = []
        for alert in parsed:
            result = classify(alert, settings.target_routes, settings.include_realtime)
            if result.included:
                desired.extend(build_events(alert, result))
        client = GoogleCalendarClient(settings.calendar_id, settings.service_account_json)
        outcome = synchronize(client, desired, dry_run=settings.dry_run)
        log.info(
            "sync_complete",
            extra={
                "event": "sync_complete",
                "creates": outcome.creates,
                "updates": outcome.updates,
                "deletes": outcome.deletes,
                "unchanged": outcome.unchanged,
                "dry_run": settings.dry_run,
            },
        )
        return 0
    except FeedError:
        log.exception("feed_error_sync_aborted")
        return 2
    except Exception:
        log.exception("sync_failed")
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="do not modify Google Calendar")
    args = parser.parse_args()
    try:
        settings = Settings.from_env()
        if args.dry_run:
            settings = Settings(
                settings.calendar_id,
                settings.service_account_json,
                settings.target_routes,
                settings.include_realtime,
                True,
                settings.log_level,
            )
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    raise SystemExit(run(settings))


if __name__ == "__main__":
    main()
