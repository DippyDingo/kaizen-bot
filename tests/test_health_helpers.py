from datetime import date
import unittest

from bot.handlers.single_message_parts.health import (
    _medication_status_icon,
    _parse_exact_sleep_input,
    _parse_medication_days_input,
    _parse_medication_time_input,
    _parse_workout_duration_input,
)


class HealthHelpersTests(unittest.TestCase):
    def test_parse_workout_duration_minutes(self) -> None:
        self.assertEqual(25, _parse_workout_duration_input("25"))

    def test_parse_workout_duration_hh_mm(self) -> None:
        self.assertEqual(75, _parse_workout_duration_input("1:15"))

    def test_parse_workout_duration_rejects_zero(self) -> None:
        self.assertIsNone(_parse_workout_duration_input("0"))

    def test_parse_exact_sleep_input_crosses_midnight(self) -> None:
        parsed = _parse_exact_sleep_input("23:40 07:15", date(2026, 3, 6))
        self.assertIsNotNone(parsed)
        fell_asleep_at, woke_up_at = parsed
        self.assertEqual(date(2026, 3, 5), fell_asleep_at.date())
        self.assertEqual(date(2026, 3, 6), woke_up_at.date())
        self.assertEqual(455, int((woke_up_at - fell_asleep_at).total_seconds() // 60))

    def test_parse_medication_time_input(self) -> None:
        parsed = _parse_medication_time_input("08:30")
        self.assertIsNotNone(parsed)
        self.assertEqual("08:30", parsed.strftime("%H:%M"))

    def test_parse_medication_days_input(self) -> None:
        self.assertEqual(14, _parse_medication_days_input("14"))
        self.assertIsNone(_parse_medication_days_input("0"))

    def test_medication_status_icon(self) -> None:
        self.assertEqual("\U0001f7e2", _medication_status_icon("taken"))
        self.assertEqual("\U0001f534", _medication_status_icon("skipped"))
        self.assertEqual("\U0001f534", _medication_status_icon("pending"))
