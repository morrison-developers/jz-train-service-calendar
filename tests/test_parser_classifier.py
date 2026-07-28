from __future__ import annotations

from jz_calendar.classifier import classify
from jz_calendar.models import DisruptionCategory
from jz_calendar.parser import parse_feed

TARGETS = frozenset({"J", "Z"})


def parsed(make_entity, feed, **kwargs):
    return parse_feed(feed(make_entity(**kwargs)))[0]


def test_j_partially_suspended(make_entity, feed):
    result = classify(parsed(make_entity, feed), TARGETS)
    assert result.included
    assert result.category == DisruptionCategory.SUSPENSION
    assert result.affected_routes == {"J"}


def test_z_partially_suspended(make_entity, feed):
    alert = parsed(
        make_entity,
        feed,
        header="No [Z] trains between stations",
        informed=[{"route_id": "Z"}],
    )
    assert classify(alert, TARGETS).affected_routes == {"Z"}


def test_j_rerouted_over_m(make_entity, feed):
    alert = parsed(
        make_entity,
        feed,
        alert_type="Planned - Reroute",
        header="[J] trains run via the [M] between Myrtle Av and Delancey St",
        informed=[{"route_id": "M"}, {"route_id": "J"}],
    )
    result = classify(alert, TARGETS)
    assert result.included
    assert result.category == DisruptionCategory.REROUTE


def test_m_work_at_shared_station_is_excluded(make_entity, feed):
    alert = parsed(
        make_entity,
        feed,
        header="[M] trains skip Myrtle Av",
        alert_type="Planned - Stops Skipped",
        informed=[{"route_id": "M"}, {"stop_id": "M11"}],
    )
    assert not classify(alert, TARGETS).included


def test_shared_station_closure_explicitly_affecting_jz(make_entity, feed):
    alert = parsed(
        make_entity,
        feed,
        header="[J] [M] and [Z] trains bypass Myrtle Av",
        alert_type="Planned - Stops Skipped",
        informed=[{"route_id": "M"}, {"stop_id": "M11"}],
    )
    result = classify(alert, TARGETS)
    assert result.included
    assert result.affected_routes == {"J", "Z"}


def test_j_second_or_later_in_informed_entity(make_entity, feed):
    alert = parsed(
        make_entity,
        feed,
        informed=[{"route_id": "M"}, {"stop_id": "M11"}, {"route_id": "J"}],
    )
    assert "J" in alert.routes
    assert classify(alert, TARGETS).included


def test_multiple_active_periods(make_entity, feed):
    alert = parsed(
        make_entity,
        feed,
        periods=[
            {"start": 1_800_000_000, "end": 1_800_003_600},
            {"start": 1_800_086_400, "end": 1_800_090_000},
        ],
    )
    assert len(alert.periods) == 2


def test_z_skip_stop_suspended_while_j_continues(make_entity, feed):
    alert = parsed(
        make_entity,
        feed,
        alert_type="Special Schedule",
        header="[Z] skip-stop service is suspended; [J] trains continue to run",
        informed=[{"route_id": "Z"}, {"route_id": "J"}],
    )
    result = classify(alert, TARGETS)
    assert result.included
    assert result.category == DisruptionCategory.SKIP_STOP_SUSPENDED


def test_other_train_running_via_j_line(make_entity, feed):
    alert = parsed(
        make_entity,
        feed,
        alert_type="Extra Service",
        header="[M] trains run via the [J] to Broad St",
        informed=[{"route_id": "M"}, {"route_id": "J"}],
    )
    result = classify(alert, TARGETS)
    assert result.included
    assert result.category == DisruptionCategory.REROUTE
