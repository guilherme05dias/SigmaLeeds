from datetime import datetime

import pytest

from database.services.send_window import (
    is_within_window,
    normalize_send_window_config,
    seconds_until_window_opens,
)


def test_send_window_weekday_inside():
    window = {"enabled": True, "start": "08:00", "end": "18:00", "days": [0, 1, 2, 3, 4]}
    assert is_within_window(datetime(2026, 5, 11, 10, 0), window) is True


def test_send_window_after_hours_next_day():
    window = {"enabled": True, "start": "08:00", "end": "18:00", "days": [0, 1, 2, 3, 4]}
    now = datetime(2026, 5, 11, 19, 0)
    assert is_within_window(now, window) is False
    assert seconds_until_window_opens(now, window) == 13 * 60 * 60


def test_send_window_weekend_next_monday():
    window = {"enabled": True, "start": "08:00", "end": "18:00", "days": [0, 1, 2, 3, 4]}
    now = datetime(2026, 5, 16, 12, 0)
    assert is_within_window(now, window) is False
    assert seconds_until_window_opens(now, window) == 44 * 60 * 60


def test_send_window_disabled_is_always_inside():
    window = {"enabled": False, "start": "08:00", "end": "18:00", "days": []}
    assert is_within_window(datetime(2026, 5, 17, 2, 0), window) is True
    assert seconds_until_window_opens(datetime(2026, 5, 17, 2, 0), window) == 0


def test_send_window_overnight_uses_start_day():
    window = {"enabled": True, "start": "22:00", "end": "06:00", "days": [0]}
    assert is_within_window(datetime(2026, 5, 11, 23, 0), window) is True
    assert is_within_window(datetime(2026, 5, 12, 5, 0), window) is True
    assert is_within_window(datetime(2026, 5, 12, 7, 0), window) is False


def test_send_window_rejects_invalid_payload():
    with pytest.raises(ValueError):
        normalize_send_window_config({"enabled": True, "start": "25:00", "end": "18:00", "days": [1]})
    with pytest.raises(ValueError):
        normalize_send_window_config({"enabled": True, "start": "08:00", "end": "18:00", "days": [7]})
    with pytest.raises(ValueError):
        normalize_send_window_config({"enabled": True, "start": "08:00", "end": "08:00", "days": [1]})
