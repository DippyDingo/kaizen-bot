from datetime import date, datetime
import unittest
from unittest.mock import AsyncMock, MagicMock

from backend.models import WellbeingLog
from backend.services.health_service import (
    _build_wellbeing_details,
    get_wellbeing_details_for_period,
    get_wellbeing_for_day,
    upsert_wellbeing_log,
)


class _FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _FakeScalars:
    def __init__(self, values):
        self.values = values

    def __iter__(self):
        return iter(self.values)


class _FakeListResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return _FakeScalars(self.values)


class WellbeingServiceAggregateTests(unittest.TestCase):
    def test_build_wellbeing_details_counts_and_extreme_days(self) -> None:
        logs = [
            WellbeingLog(
                id=1,
                user_id=1,
                logged_date=date(2026, 3, 5),
                energy_level=3,
                stress_level=4,
                created_at=datetime(2026, 3, 5, 10, 0),
                updated_at=datetime(2026, 3, 5, 10, 0),
            ),
            WellbeingLog(
                id=2,
                user_id=1,
                logged_date=date(2026, 3, 6),
                energy_level=5,
                stress_level=2,
                created_at=datetime(2026, 3, 6, 10, 0),
                updated_at=datetime(2026, 3, 6, 10, 0),
            ),
            WellbeingLog(
                id=3,
                user_id=1,
                logged_date=date(2026, 3, 7),
                energy_level=4,
                stress_level=5,
                created_at=datetime(2026, 3, 7, 10, 0),
                updated_at=datetime(2026, 3, 7, 10, 0),
            ),
        ]

        details = _build_wellbeing_details(logs)

        self.assertEqual(3, details["entries_count"])
        self.assertEqual(3, details["active_days"])
        self.assertEqual(4.0, details["avg_energy"])
        self.assertEqual(3.67, details["avg_stress"])
        self.assertEqual(date(2026, 3, 6), details["best_energy_day"])
        self.assertEqual(date(2026, 3, 7), details["highest_stress_day"])


class WellbeingServiceAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_upsert_wellbeing_log_creates_new_row_when_missing(self) -> None:
        session = MagicMock()
        session.execute = AsyncMock(return_value=_FakeScalarResult(None))
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        wellbeing_log = await upsert_wellbeing_log(session, user_id=7, logged_date=date(2026, 3, 7), energy_level=4, stress_level=2)

        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once_with(wellbeing_log)
        self.assertEqual(7, wellbeing_log.user_id)
        self.assertEqual(4, wellbeing_log.energy_level)
        self.assertEqual(2, wellbeing_log.stress_level)

    async def test_upsert_wellbeing_log_updates_existing_row_for_same_day(self) -> None:
        existing = WellbeingLog(
            id=1,
            user_id=7,
            logged_date=date(2026, 3, 7),
            energy_level=2,
            stress_level=4,
            created_at=datetime(2026, 3, 7, 8, 0),
            updated_at=datetime(2026, 3, 7, 8, 0),
        )
        session = MagicMock()
        session.execute = AsyncMock(return_value=_FakeScalarResult(existing))
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        wellbeing_log = await upsert_wellbeing_log(session, user_id=7, logged_date=date(2026, 3, 7), energy_level=5, stress_level=1)

        session.add.assert_not_called()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once_with(existing)
        self.assertIs(existing, wellbeing_log)
        self.assertEqual(5, existing.energy_level)
        self.assertEqual(1, existing.stress_level)

    async def test_get_wellbeing_for_day_returns_empty_payload_when_missing(self) -> None:
        session = MagicMock()
        session.execute = AsyncMock(return_value=_FakeScalarResult(None))

        result = await get_wellbeing_for_day(session, user_id=7, target_day=date(2026, 3, 7))

        self.assertEqual({"energy_level": 0, "stress_level": 0, "has_entry": False}, result)

    async def test_get_wellbeing_details_for_period_uses_logs_from_session(self) -> None:
        logs = [
            WellbeingLog(
                id=1,
                user_id=7,
                logged_date=date(2026, 3, 6),
                energy_level=4,
                stress_level=2,
                created_at=datetime(2026, 3, 6, 9, 0),
                updated_at=datetime(2026, 3, 6, 9, 0),
            ),
            WellbeingLog(
                id=2,
                user_id=7,
                logged_date=date(2026, 3, 7),
                energy_level=3,
                stress_level=5,
                created_at=datetime(2026, 3, 7, 9, 0),
                updated_at=datetime(2026, 3, 7, 9, 0),
            ),
        ]
        session = MagicMock()
        session.execute = AsyncMock(return_value=_FakeListResult(logs))

        result = await get_wellbeing_details_for_period(session, user_id=7, date_from=date(2026, 3, 6), date_to=date(2026, 3, 7))

        self.assertEqual(2, result["entries_count"])
        self.assertEqual(2, result["active_days"])
        self.assertEqual(3.5, result["avg_energy"])
        self.assertEqual(3.5, result["avg_stress"])


if __name__ == "__main__":
    unittest.main()
