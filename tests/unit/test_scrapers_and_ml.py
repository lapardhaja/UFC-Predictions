from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from scrapers.ufcstats_events import UFCStatsEventsScraper


def test_parse_event_rows():
    html = """
    <table>
    <tr>
      <td>Jan 01, 2024</td>
      <td>Las Vegas, NV</td>
      <td><a class="b-link b-link_style_black" href="/event-details/abc123">UFC 300</a></td>
    </tr>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = UFCStatsEventsScraper.parse_event_rows(soup, upcoming=False)
    assert len(rows) == 1
    assert rows[0]["event_id"] == "abc123"
    assert rows[0]["event_name"] == "UFC 300"


def test_feature_no_leakage():
    from ml.feature_builder import assert_no_leakage_columns

    assert_no_leakage_columns(["win_rate_diff", "sig_acc_diff"])


def test_prediction_sum(sample_card):
    from backend.services.prediction_service import get_prediction_for_fight

    out = get_prediction_for_fight(sample_card, "fight-1")
    pa = out["fighter_a"]["win_probability"]
    pb = out["fighter_b"]["win_probability"]
    assert abs(pa + pb - 1.0) < 1e-6
