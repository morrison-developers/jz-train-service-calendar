from unittest.mock import MagicMock

from jz_calendar.calendar_client import GoogleCalendarClient


def test_create_owned_public_calendar() -> None:
    service = MagicMock()
    service.calendars.return_value.insert.return_value.execute.return_value = {
        "id": "service-account-calendar-id"
    }
    client = GoogleCalendarClient.__new__(GoogleCalendarClient)
    client.service = service
    client.calendar_id = ""

    calendar_id = client.create_owned_public_calendar("J/Z Planned Work", "Description")

    assert calendar_id == "service-account-calendar-id"
    service.calendars.return_value.insert.assert_called_once_with(
        body={
            "summary": "J/Z Planned Work",
            "description": "Description",
            "timeZone": "America/New_York",
        }
    )
    service.acl.return_value.insert.assert_called_once_with(
        calendarId="service-account-calendar-id",
        body={"scope": {"type": "default"}, "role": "reader"},
    )
