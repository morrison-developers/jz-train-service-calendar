from __future__ import annotations

import pytest

from jz_calendar.config import Settings


def test_keyless_google_configuration(monkeypatch):
    monkeypatch.setenv("GOOGLE_CALENDAR_ID", "calendar@example.com")
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
    settings = Settings.from_env()
    assert settings.calendar_id == "calendar@example.com"
    assert settings.service_account_json == ""


def test_calendar_id_is_still_required(monkeypatch):
    monkeypatch.delenv("GOOGLE_CALENDAR_ID", raising=False)
    with pytest.raises(ValueError, match="GOOGLE_CALENDAR_ID"):
        Settings.from_env()
