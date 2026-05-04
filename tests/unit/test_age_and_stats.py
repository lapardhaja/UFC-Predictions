"""Tests for age reference dates and control parsing."""

from datetime import date

from ml.age_util import age_years_on_date, reference_date_for_prediction
from scrapers.scraper_runner import _map_totals


def test_age_on_fight_night():
    dob = date(1990, 1, 15)
    fight = date(2020, 1, 15)
    age = age_years_on_date(dob, fight)
    assert age is not None
    assert 29.9 < age < 30.1


def test_prediction_reference_uses_today_when_no_event_date():
    assert reference_date_for_prediction(None) == date.today()


def test_map_totals_control_mm_ss():
    totals = {"ctrl": "4:32"}
    out = _map_totals(totals)
    assert out["control_time_seconds"] == 4 * 60 + 32
