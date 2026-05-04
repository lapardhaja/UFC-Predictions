"""Time-based split resolution."""

from datetime import date

import numpy as np
import pandas as pd

from ml.split_config import masks_from_cutoffs, resolve_time_masks


def test_cutoff_masks_ordering():
    dates = pd.to_datetime(["2020-01-01", "2021-06-01", "2023-01-01", "2024-06-01"])
    m_tr, m_val, m_te = masks_from_cutoffs(dates, date(2022, 1, 1), date(2024, 1, 1))
    assert m_tr.sum() == 2
    assert m_val.sum() == 1
    assert m_te.sum() == 1
    assert m_te[-1]


def test_auto_split_fractions():
    n = 100
    dates = pd.date_range("2015-01-01", periods=n, freq="30D")
    m_tr, m_val, m_te, summary = resolve_time_masks(
        dates, train_cutoff=None, val_cutoff=None, auto_split=True, train_frac=0.7, val_frac=0.15
    )
    assert summary.n_train + summary.n_val + summary.n_test == n
    assert summary.n_train >= 40
    assert summary.mode == "auto"
