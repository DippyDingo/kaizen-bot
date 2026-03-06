from datetime import date, datetime
from types import SimpleNamespace
import unittest

from backend.api.parsers import parse_request_date, parse_stats_period
from backend.api.serializers import (
    serialize_dashboard_payload,
    serialize_health_payload,
    serialize_stats_payload,
)


class ApiParserTests(unittest.TestCase):
    def test_parse_request_date_uses_default_today(self) -> None:
        default_day = date(2026, 3, 7)

        parsed = parse_request_date(None, today=default_day)

        self.assertEqual(default_day, parsed)

    def test_parse_request_date_accepts_iso_value(self) -> None:
        parsed = parse_request_date("2026-03-05")

        self.assertEqual(date(2026, 3, 5), parsed)

    def test_parse_stats_period_accepts_known_values(self) -> None:
        self.assertEqual("30d", parse_stats_period("30d"))

    def test_parse_stats_period_rejects_unknown_values(self) -> None:
        with self.assertRaises(ValueError):
            parse_stats_period("week")


class ApiSerializerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user = SimpleNamespace(
            preferred_name="Alex",
            first_name="Alexander",
            username="alex",
            level=12,
            exp=450,
            exp_to_next_level=1000,
            current_streak=14,
            longest_streak=20,
            daily_water_target_ml=2500,
            daily_workout_target_min=30,
            created_at=datetime(2026, 1, 1, 10, 0, 0),
        )

    def test_serialize_dashboard_payload_returns_numeric_progress(self) -> None:
        tasks = [
            SimpleNamespace(id=1, title="High pending", priority="high", is_done=False, task_date=date(2026, 3, 7)),
            SimpleNamespace(id=2, title="Done task", priority="medium", is_done=True, task_date=date(2026, 3, 7)),
            SimpleNamespace(id=3, title="Low pending", priority="low", is_done=False, task_date=date(2026, 3, 7)),
        ]

        payload = serialize_dashboard_payload(
            self.user,
            selected_date=date(2026, 3, 7),
            tasks=tasks,
            water_ml=1500,
            sleep_minutes=360,
            diary_count=2,
        )

        self.assertEqual("2026-03-07", payload["date"])
        self.assertEqual("Alex", payload["user"]["display_name"])
        self.assertEqual(33, payload["progress"]["tasks_percent"])
        self.assertEqual(60, payload["progress"]["water_percent"])
        self.assertEqual(75, payload["progress"]["sleep_percent"])
        self.assertEqual(2, len(payload["focus_tasks"]))
        self.assertEqual("High pending", payload["focus_tasks"][0]["title"])

    def test_serialize_health_payload_returns_day_and_week_sections(self) -> None:
        payload = serialize_health_payload(
            self.user,
            selected_date=date(2026, 3, 7),
            week_from=date(2026, 3, 1),
            day_water_total=2000,
            day_sleep_total=420,
            day_workout_total=30,
            day_wellbeing={"has_entry": True, "energy_level": 4, "stress_level": 2},
            day_medication_schedule=[{"course_id": 1, "title": "Magnesium", "dose": "200mg", "intake_time": "09:00", "days_left": 3, "status": "taken"}],
            day_sleep_details={"avg_quality": 4.0},
            week_water_details={"total_ml": 12000, "active_days": 6, "best_day_ml": 2500},
            week_sleep_details={"total_minutes": 2800, "active_days": 7, "best_day_minutes": 480, "avg_quality": 4.3},
            week_workout_details={
                "total_minutes": 150,
                "sessions_count": 4,
                "active_days": 4,
                "best_day_minutes": 60,
                "strength_count": 2,
                "cardio_count": 1,
                "mobility_count": 1,
                "strength_minutes": 90,
                "cardio_minutes": 30,
                "mobility_minutes": 30,
            },
            week_wellbeing_details={"entries_count": 5, "active_days": 5, "avg_energy": 3.8, "avg_stress": 2.4, "best_energy_day": date(2026, 3, 4), "highest_stress_day": date(2026, 3, 2)},
            week_medication_details={"total_logs": 7, "active_days": 7, "unique_titles": 2, "best_day_logs": 2, "top_title": "Magnesium", "taken_count": 6, "skipped_count": 1},
        )

        self.assertEqual(80, payload["day"]["water"]["percent"])
        self.assertEqual(88, payload["day"]["sleep"]["percent"])
        self.assertEqual(1, payload["day"]["medications"]["taken"])
        self.assertEqual("2026-03-04", payload["week"]["wellbeing"]["best_energy_day"])
        self.assertEqual(2, payload["week"]["workout"]["by_type"]["strength"]["sessions"])

    def test_serialize_stats_payload_returns_structured_blocks(self) -> None:
        payload = serialize_stats_payload(
            self.user,
            selected_date=date(2026, 3, 7),
            period="7d",
            stats={
                "period_days": 7,
                "tasks_total": 10,
                "tasks_done": 7,
                "water_total_ml": 14000,
                "sleep_total_minutes": 2800,
                "avg_sleep_quality": 4.1,
                "diary_total": 5,
                "task_details": {"high_count": 3, "medium_count": 4, "low_count": 3, "active_days": 5},
                "water_details": {"active_days": 6, "best_day_ml": 2600},
                "sleep_details": {"active_days": 7, "best_day_minutes": 480, "longest_log_minutes": 510},
                "workout_details": {
                    "total_minutes": 180,
                    "sessions_count": 5,
                    "active_days": 4,
                    "best_day_minutes": 60,
                    "strength_count": 2,
                    "cardio_count": 2,
                    "mobility_count": 1,
                    "strength_minutes": 80,
                    "cardio_minutes": 70,
                    "mobility_minutes": 30,
                },
                "wellbeing_details": {
                    "entries_count": 4,
                    "active_days": 4,
                    "avg_energy": 3.5,
                    "avg_stress": 2.0,
                    "best_energy_day": date(2026, 3, 6),
                    "highest_stress_day": date(2026, 3, 3),
                },
                "medication_details": {
                    "total_logs": 6,
                    "taken_count": 5,
                    "skipped_count": 1,
                    "unique_titles": 2,
                    "active_days": 6,
                    "best_day_logs": 2,
                    "top_title": "Magnesium",
                },
                "diary_details": {"active_days": 3, "best_day_entries": 2},
            },
        )

        self.assertEqual("7d", payload["period"])
        self.assertEqual(70, payload["tasks"]["percent"])
        self.assertEqual(80, payload["water"]["percent_of_target"])
        self.assertEqual(83, payload["sleep"]["percent_of_target"])
        self.assertEqual("2026-03-06", payload["wellbeing"]["best_energy_day"])
