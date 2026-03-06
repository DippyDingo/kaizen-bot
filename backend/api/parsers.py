from __future__ import annotations

from datetime import date, datetime

VALID_STATS_PERIODS = {"day", "7d", "30d", "all"}


def parse_request_date(value: str | None, *, today: date | None = None) -> date:
    if not value:
        return today or date.today()

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("date must use YYYY-MM-DD format") from exc


def parse_stats_period(value: str | None) -> str:
    period = (value or "day").strip().lower()
    if period not in VALID_STATS_PERIODS:
        raise ValueError("period must be one of: day, 7d, 30d, all")
    return period
