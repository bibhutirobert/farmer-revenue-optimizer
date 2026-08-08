import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils import weather_utils
from utils.weather_utils import (
    clear_cache,
    fetch_forecast,
    heavy_rain_dates,
    total_rainfall,
    weather_tips,
)


@pytest.fixture(autouse=True)
def _clean_cache():
    clear_cache()
    yield
    clear_cache()


class FakeResponse:
    def __init__(self, payload, status_ok=True):
        self._payload = payload
        self._status_ok = status_ok

    def raise_for_status(self):
        if not self._status_ok:
            raise RuntimeError("simulated HTTP error")

    def json(self):
        return self._payload


def _payload(rain, dates=None):
    dates = dates or [f"2026-08-{i + 1:02d}" for i in range(len(rain))]
    return {
        "daily": {
            "time": dates,
            "precipitation_sum": rain,
            "temperature_2m_max": [32.0] * len(rain),
            "temperature_2m_min": [24.0] * len(rain),
        }
    }


def _stub_get(monkeypatch, payload, status_ok=True, calls=None):
    def fake_get(*args, **kwargs):
        if calls is not None:
            calls.append(kwargs.get("params"))
        return FakeResponse(payload, status_ok)

    monkeypatch.setattr(weather_utils.requests, "get", fake_get)


# ── fetch_forecast ─────────────────────────────────────────────────────────────

def test_fetch_parses_daily_series(monkeypatch):
    _stub_get(monkeypatch, _payload([0.0, 5.0, 12.5]))
    forecast = fetch_forecast(19.07, 72.87)
    assert forecast["rain_mm"] == [0.0, 5.0, 12.5]
    assert len(forecast["dates"]) == 3


def test_fetch_returns_none_on_network_error(monkeypatch):
    def boom(*args, **kwargs):
        raise ConnectionError("no network")

    monkeypatch.setattr(weather_utils.requests, "get", boom)
    assert fetch_forecast(19.07, 72.87) is None


def test_fetch_returns_none_on_http_error(monkeypatch):
    _stub_get(monkeypatch, _payload([1.0]), status_ok=False)
    assert fetch_forecast(19.07, 72.87) is None


def test_fetch_returns_none_on_empty_payload(monkeypatch):
    _stub_get(monkeypatch, {"daily": {}})
    assert fetch_forecast(19.07, 72.87) is None


def test_nulls_in_series_become_none_not_crash(monkeypatch):
    _stub_get(monkeypatch, _payload([1.0, None, "bad", 3.0]))
    forecast = fetch_forecast(19.07, 72.87)
    assert forecast["rain_mm"] == [1.0, None, None, 3.0]
    # Gaps are skipped, not treated as zero.
    assert total_rainfall(forecast) == 4.0


def test_nearby_points_reuse_one_cached_call(monkeypatch):
    calls = []
    _stub_get(monkeypatch, _payload([2.0]), calls=calls)
    fetch_forecast(19.071, 72.871)
    fetch_forecast(19.072, 72.872)   # same ~1 km cell
    assert len(calls) == 1


def test_distant_points_are_fetched_separately(monkeypatch):
    calls = []
    _stub_get(monkeypatch, _payload([2.0]), calls=calls)
    fetch_forecast(19.07, 72.87)
    fetch_forecast(26.85, 80.95)
    assert len(calls) == 2


# ── derived values ─────────────────────────────────────────────────────────────

def test_total_and_heavy_days():
    forecast = {
        "dates": ["2026-08-01", "2026-08-02", "2026-08-03"],
        "rain_mm": [5.0, 40.0, 1.0],
    }
    assert total_rainfall(forecast) == 46.0
    assert heavy_rain_dates(forecast) == ["2026-08-02"]


def test_derived_values_tolerate_missing_forecast():
    assert total_rainfall(None) is None
    assert heavy_rain_dates(None) == []
    assert weather_tips(None) == []


# ── tips ───────────────────────────────────────────────────────────────────────

def test_dry_spell_advises_irrigation():
    tips = weather_tips({"dates": ["d1"] * 3, "rain_mm": [1.0, 0.0, 2.0]})
    assert any("irrigation" in t.lower() for t in tips)


def test_wet_window_advises_delaying_irrigation():
    tips = weather_tips({"dates": ["d"] * 3, "rain_mm": [30.0, 25.0, 5.0]})
    assert any("wait" in t.lower() for t in tips)


def test_extreme_rain_advises_drainage():
    tips = weather_tips({"dates": ["d"] * 3, "rain_mm": [80.0, 60.0, 40.0]})
    assert any("drainage" in t.lower() or "waterlog" in t.lower() for t in tips)


def test_tips_available_in_hindi():
    forecast = {"dates": ["d"] * 3, "rain_mm": [1.0, 0.0, 0.0]}
    hindi = weather_tips(forecast, lang="hi")
    assert hindi
    # Devanagari present, and it is not just the English string echoed back.
    assert any(any("ऀ" <= ch <= "ॿ" for ch in t) for t in hindi)
    assert hindi != weather_tips(forecast, lang="en")
