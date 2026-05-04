"""Age at a given fight date (training) vs age for predictions (upcoming fights)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def _to_date(d: Any) -> date | None:
    if d is None:
        return None
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    if hasattr(d, "date") and callable(getattr(d, "date")):
        try:
            return d.date()  # type: ignore[no-any-return]
        except (AttributeError, ValueError):
            pass
    if isinstance(d, str):
        try:
            return date.fromisoformat(d[:10])
        except ValueError:
            return None
    return None


def age_years_on_date(dob: date | None, as_of: date | None) -> float | None:
    """Years old on `as_of` (fight night for historical rows; reference date for predictions)."""
    if dob is None or as_of is None:
        return None
    return (as_of - dob).days / 365.25


def reference_date_for_prediction(event_date: Any) -> date:
    """For upcoming fights with no card date yet, use today so age is current."""
    d = _to_date(event_date)
    if d is not None:
        return d
    return date.today()
