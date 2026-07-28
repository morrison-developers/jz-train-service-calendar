from __future__ import annotations

import logging
import os
import sys

from jz_calendar.calendar_client import GoogleCalendarClient
from jz_calendar.logging_config import configure_logging


def main() -> None:
    configure_logging(os.getenv("LOG_LEVEL", "INFO"))
    log = logging.getLogger(__name__)
    try:
        client = GoogleCalendarClient(
            calendar_id="",
            service_account_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", ""),
        )
        calendar_id = client.create_owned_public_calendar(
            summary="J/Z Train Planned Work",
            description=(
                "Upcoming planned NYC Subway J and Z service changes, sourced from official "
                "MTA service alerts. Information may change."
            ),
        )
    except Exception:
        log.exception("calendar_bootstrap_failed")
        raise SystemExit(1) from None
    print(f"GOOGLE_CALENDAR_ID={calendar_id}")
    log.info("calendar_bootstrap_complete", extra={"event": "calendar_bootstrap_complete"})
    raise SystemExit(0)


if __name__ == "__main__":
    sys.exit(main())
