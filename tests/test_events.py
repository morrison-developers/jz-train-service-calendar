from __future__ import annotations

from datetime import UTC, datetime

from jz_calendar.classifier import classify
from jz_calendar.events import build_events
from jz_calendar.parser import parse_feed


def test_dst_boundary_uses_new_york_offsets(make_entity, feed):
    # 2026-03-08 crosses the spring-forward boundary in New York.
    entity = make_entity(
        periods=[
            {
                "start": int(datetime(2026, 3, 8, 6, 30, tzinfo=UTC).timestamp()),
                "end": int(datetime(2026, 3, 8, 7, 30, tzinfo=UTC).timestamp()),
            }
        ]
    )
    alert = parse_feed(feed(entity))[0]
    events = build_events(
        alert,
        classify(alert, frozenset({"J", "Z"})),
        now=datetime(2026, 3, 1, tzinfo=UTC),
    )
    assert events[0].start.utcoffset().total_seconds() == -5 * 3600
    assert events[0].end.utcoffset().total_seconds() == -4 * 3600


def test_multiple_periods_create_unique_deterministic_keys(make_entity, feed):
    entity = make_entity(
        periods=[
            {"start": 1_800_000_000, "end": 1_800_003_600},
            {"start": 1_800_086_400, "end": 1_800_090_000},
        ]
    )
    alert = parse_feed(feed(entity))[0]
    classification = classify(alert, frozenset({"J", "Z"}))
    first = build_events(alert, classification, now=datetime(2020, 1, 1, tzinfo=UTC))
    second = build_events(alert, classification, now=datetime(2020, 1, 1, tzinfo=UTC))
    assert len(first) == 2
    assert first[0].key != first[1].key
    assert [event.key for event in first] == [event.key for event in second]


def test_title_keeps_meaningful_mid_sentence_route_reference(make_entity, feed):
    entity = make_entity(
        alert_type="Planned - Reroute",
        header="[M] runs via the [J] to Broad St",
        informed=[{"route_id": "J"}, {"route_id": "M"}],
    )
    alert = parse_feed(feed(entity))[0]
    events = build_events(
        alert,
        classify(alert, frozenset({"J", "Z"})),
        now=datetime(2020, 1, 1, tzinfo=UTC),
    )
    assert events[0].title == "[J] [M] runs via the [J] to Broad St"
