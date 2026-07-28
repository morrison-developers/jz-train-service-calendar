from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any, Protocol

import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build

from jz_calendar.models import DesiredEvent

MANAGED_BY = "jz-service-calendar"
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarClient(Protocol):
    def managed_events(self, time_min: str) -> Iterator[dict[str, Any]]: ...
    def create(self, event: DesiredEvent) -> dict[str, Any]: ...
    def update(self, google_event_id: str, event: DesiredEvent) -> dict[str, Any]: ...
    def delete(self, google_event_id: str) -> None: ...


def event_body(event: DesiredEvent) -> dict[str, Any]:
    updated = event.updated_at.isoformat() if event.updated_at else ""
    return {
        "summary": event.title,
        "description": event.description,
        "start": {"dateTime": event.start.isoformat(), "timeZone": "America/New_York"},
        "end": {"dateTime": event.end.isoformat(), "timeZone": "America/New_York"},
        "transparency": "transparent",
        "extendedProperties": {
            "private": {
                "managedBy": MANAGED_BY,
                "eventKey": event.key,
                "mtaAlertId": event.alert_id,
                "mtaUpdatedAt": updated,
                "category": event.category.value,
            }
        },
        "source": {"title": "MTA Service Alerts", "url": "https://www.mta.info/alerts"},
    }


class GoogleCalendarClient:
    def __init__(self, calendar_id: str, service_account_json: str = "") -> None:
        if service_account_json:
            try:
                info = json.loads(service_account_json)
            except json.JSONDecodeError as exc:
                raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON") from exc
            credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        else:
            credentials, _ = google.auth.default(scopes=SCOPES)
        self.service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
        self.calendar_id = calendar_id

    def create_owned_public_calendar(self, summary: str, description: str) -> str:
        calendar = (
            self.service.calendars()
            .insert(
                body={
                    "summary": summary,
                    "description": description,
                    "timeZone": "America/New_York",
                }
            )
            .execute()
        )
        calendar_id = calendar["id"]
        self.service.acl().insert(
            calendarId=calendar_id,
            body={"scope": {"type": "default"}, "role": "reader"},
        ).execute()
        return str(calendar_id)

    def managed_events(self, time_min: str) -> Iterator[dict[str, Any]]:
        page_token: str | None = None
        while True:
            response = (
                self.service.events()
                .list(
                    calendarId=self.calendar_id,
                    privateExtendedProperty=f"managedBy={MANAGED_BY}",
                    timeMin=time_min,
                    singleEvents=True,
                    showDeleted=False,
                    maxResults=2500,
                    pageToken=page_token,
                )
                .execute()
            )
            yield from response.get("items", [])
            page_token = response.get("nextPageToken")
            if not page_token:
                return

    def create(self, event: DesiredEvent) -> dict[str, Any]:
        return (
            self.service.events()
            .insert(calendarId=self.calendar_id, body=event_body(event))
            .execute()
        )

    def update(self, google_event_id: str, event: DesiredEvent) -> dict[str, Any]:
        return (
            self.service.events()
            .update(
                calendarId=self.calendar_id,
                eventId=google_event_id,
                body=event_body(event),
            )
            .execute()
        )

    def delete(self, google_event_id: str) -> None:
        self.service.events().delete(calendarId=self.calendar_id, eventId=google_event_id).execute()
