from datetime import datetime, timedelta, timezone

from core.models import Position
from core.position_filter import FilterStatus, PositionFilter
from core.tracking_status import describe_tracking, format_age

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def pos(x, y, z=0.0, seconds=0.0):
    return Position(x, y, z, T0 + timedelta(seconds=seconds))


def test_first_reading_is_accepted():
    assert PositionFilter().check(pos(1000, 2000)).accepted


def test_exact_duplicate_is_ignored():
    f = PositionFilter()
    assert f.check(pos(1000, 2000, seconds=0)).accepted
    assert f.check(pos(1000, 2000, seconds=5)).status is FilterStatus.DUPLICATE


def test_normal_movement_is_accepted():
    f = PositionFilter()
    f.check(pos(0, 0, seconds=0))
    assert f.check(pos(5_000, 3_000, seconds=10)).accepted


def test_single_bad_copy_does_not_teleport_the_pin():
    f = PositionFilter()
    f.check(pos(0, 0, seconds=0))
    result = f.check(pos(400_000, -300_000, seconds=3))
    assert result.status is FilterStatus.REJECTED
    assert f.last_accepted.x == 0
    # Next sane reading near the original place is still accepted.
    assert f.check(pos(800, 600, seconds=6)).accepted


def test_confirmed_jump_is_accepted_as_a_real_teleport():
    f = PositionFilter()
    f.check(pos(0, 0, seconds=0))
    assert f.check(pos(400_000, 0, seconds=3)).status is FilterStatus.REJECTED
    assert f.check(pos(400_500, 200, seconds=8)).accepted  # respawn confirmed


def test_two_unrelated_bad_reads_are_both_rejected():
    f = PositionFilter()
    f.check(pos(0, 0, seconds=0))
    assert not f.check(pos(400_000, 0, seconds=3)).accepted
    assert not f.check(pos(-400_000, 100_000, seconds=6)).accepted


def test_long_gap_allows_long_travel():
    f = PositionFilter()
    f.check(pos(0, 0, seconds=0))
    assert f.check(pos(300_000, 0, seconds=600)).accepted


def test_outside_map_bounds_is_rejected():
    f = PositionFilter(bounds=(-1000, 1000, -1000, 1000), bounds_margin=100)
    assert f.check(pos(500, 500)).accepted
    assert f.check(pos(5000, 0, seconds=1)).status is FilterStatus.REJECTED


def test_reset_clears_history():
    f = PositionFilter()
    f.check(pos(0, 0))
    f.reset()
    assert f.check(pos(900_000, 0, seconds=1)).accepted


def test_tracking_status_states():
    assert describe_tracking(None, None).state == "waiting"
    now = T0 + timedelta(seconds=10)
    active = describe_tracking(T0, "clipboard", now)
    assert active.state == "active" and "Clipboard" in active.text
    stale = describe_tracking(T0, "ocr", T0 + timedelta(seconds=120))
    assert stale.state == "stale" and "OCR" in stale.text


def test_format_age():
    assert format_age(5) == "5s ago"
    assert format_age(125) == "2m 05s ago"
    assert format_age(3700) == "1h 01m ago"
