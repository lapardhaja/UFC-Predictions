"""Time-based train / validation / test masks for fight prediction (no shuffle across time)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class SplitSummary:
    train_cutoff: date
    val_cutoff: date
    mode: str
    n_train: int
    n_val: int
    n_test: int
    train_date_min: str | None
    train_date_max: str | None
    val_date_min: str | None
    val_date_max: str | None
    test_date_min: str | None
    test_date_max: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "train_cutoff": self.train_cutoff.isoformat(),
            "val_cutoff": self.val_cutoff.isoformat(),
            "split_mode": self.mode,
            "n_train": self.n_train,
            "n_val": self.n_val,
            "n_test": self.n_test,
            "train_date_min": self.train_date_min,
            "train_date_max": self.train_date_max,
            "val_date_min": self.val_date_min,
            "val_date_max": self.val_date_max,
            "test_date_min": self.test_date_min,
            "test_date_max": self.test_date_max,
        }


def _normalize_dates(fight_dates: pd.Series | Any) -> pd.Series:
    s = pd.to_datetime(pd.Series(fight_dates), utc=False)
    return s.dt.normalize()


def masks_from_cutoffs(
    fight_dates: pd.Series | Any, train_end: date, val_end: date
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Rows strictly before train_end -> train; [train_end, val_end) -> val; >= val_end -> test."""
    ts = _normalize_dates(fight_dates)
    m_train = (ts < pd.Timestamp(train_end)).values
    m_val = ((ts >= pd.Timestamp(train_end)) & (ts < pd.Timestamp(val_end))).values
    m_test = (ts >= pd.Timestamp(val_end)).values
    return m_train, m_val, m_test


def masks_chronological_fraction(
    fight_dates: pd.Series | Any,
    *,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
    min_train: int = 40,
    min_val: int = 10,
    min_test: int = 5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, date, date]:
    """
    Sort rows by fight date; assign contiguous fractions (train earliest, test latest).
    Returns masks and pseudo-cutoffs (first val date, first test date) for metadata.
    """
    n = len(fight_dates)
    if n == 0:
        raise ValueError("empty fight_dates")
    ts = _normalize_dates(fight_dates)
    order = np.argsort(ts.values.astype("datetime64[ns]"))
    split1 = max(min_train, int(n * train_frac))
    split2 = max(split1 + min_val, int(n * (train_frac + val_frac)))
    split1 = min(split1, n - min_val - min_test)
    split2 = min(split2, n - min_test)
    if split2 <= split1:
        split1 = max(min_train, n // 2)
        split2 = min(n - min_test, split1 + max(min_val, n // 10))

    train_rows = set(order[:split1].tolist())
    val_rows = set(order[split1:split2].tolist())
    test_rows = set(order[split2:].tolist())

    idx = np.arange(n)
    m_train = np.array([i in train_rows for i in idx], dtype=bool)
    m_val = np.array([i in val_rows for i in idx], dtype=bool)
    m_test = np.array([i in test_rows for i in idx], dtype=bool)

    first_val_date = ts.iloc[order[split1]].date()
    first_test_date = ts.iloc[order[split2]].date() if split2 < n else first_val_date
    return m_train, m_val, m_test, first_val_date, first_test_date


def resolve_time_masks(
    fight_dates: pd.Series,
    *,
    train_cutoff: date | None,
    val_cutoff: date | None,
    auto_split: bool,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, SplitSummary]:
    """
    If auto_split: chronological 70/15/15 (configurable).
    Else: use explicit cutoffs; if val or test too small, fall back to auto.
    """
    ts = _normalize_dates(fight_dates)

    if auto_split or train_cutoff is None or val_cutoff is None:
        m_train, m_val, m_test, first_val, first_test = masks_chronological_fraction(
            fight_dates, train_frac=train_frac, val_frac=val_frac
        )
        summary = _build_summary(ts, m_train, m_val, m_test, first_val, first_test, "auto")
        return m_train, m_val, m_test, summary

    m_train, m_val, m_test = masks_from_cutoffs(fight_dates, train_cutoff, val_cutoff)
    if m_val.sum() < 10 or m_test.sum() < 5:
        m_train, m_val, m_test, first_val, first_test = masks_chronological_fraction(
            fight_dates, train_frac=train_frac, val_frac=val_frac
        )
        summary = _build_summary(ts, m_train, m_val, m_test, first_val, first_test, "auto_fallback")
        return m_train, m_val, m_test, summary

    summary = _build_summary(ts, m_train, m_val, m_test, train_cutoff, val_cutoff, "cutoff")
    return m_train, m_val, m_test, summary


def _build_summary(
    ts: pd.Series,
    m_train: np.ndarray,
    m_val: np.ndarray,
    m_test: np.ndarray,
    train_cutoff: date,
    val_cutoff: date,
    mode: str,
) -> SplitSummary:
    def bounds(mask: np.ndarray) -> tuple[str | None, str | None]:
        if not mask.any():
            return None, None
        sub = ts[mask]
        return sub.min().date().isoformat(), sub.max().date().isoformat()

    tmin, tmax = bounds(m_train)
    vmin, vmax = bounds(m_val)
    smin, smax = bounds(m_test)
    return SplitSummary(
        train_cutoff=train_cutoff,
        val_cutoff=val_cutoff,
        mode=mode,
        n_train=int(m_train.sum()),
        n_val=int(m_val.sum()),
        n_test=int(m_test.sum()),
        train_date_min=tmin,
        train_date_max=tmax,
        val_date_min=vmin,
        val_date_max=vmax,
        test_date_min=smin,
        test_date_max=smax,
    )
