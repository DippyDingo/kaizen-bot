from datetime import date, datetime, time
import unittest

from backend.models import MedicationCourse, MedicationLog
from backend.services.health_service import (
    _build_medication_calendar_marks,
    _build_medication_details,
    _build_medication_schedule_items,
)


class MedicationServiceAggregateTests(unittest.TestCase):
    def test_build_medication_schedule_items_sets_status_and_days_left(self) -> None:
        course_a = MedicationCourse(
            id=1,
            user_id=1,
            title="Магний",
            dose="1 таб",
            intake_time=time(8, 0),
            start_date=date(2026, 3, 6),
            end_date=date(2026, 3, 10),
            is_active=True,
            created_at=datetime(2026, 3, 6, 7, 0),
        )
        course_b = MedicationCourse(
            id=2,
            user_id=1,
            title="Витамин D",
            dose="2000 IU",
            intake_time=time(13, 0),
            start_date=date(2026, 3, 5),
            end_date=date(2026, 3, 7),
            is_active=True,
            created_at=datetime(2026, 3, 5, 7, 0),
        )
        log = MedicationLog(
            id=1,
            user_id=1,
            course_id=1,
            title="Магний",
            dose="1 таб",
            scheduled_date=date(2026, 3, 6),
            status="taken",
            logged_at=datetime(2026, 3, 6, 8, 5),
            created_at=datetime(2026, 3, 6, 8, 5),
        )

        items = _build_medication_schedule_items([course_b, course_a], [log], date(2026, 3, 6))

        self.assertEqual(2, len(items))
        self.assertEqual("08:00", items[0]["intake_time"])
        self.assertEqual("taken", items[0]["status"])
        self.assertEqual(5, items[0]["days_left"])
        self.assertEqual("pending", items[1]["status"])

    def test_build_medication_calendar_marks_distinguishes_done_skipped_and_planned(self) -> None:
        course = MedicationCourse(
            id=1,
            user_id=1,
            title="Магний",
            dose="1 таб",
            intake_time=time(8, 0),
            start_date=date(2026, 3, 6),
            end_date=date(2026, 3, 8),
            is_active=True,
            created_at=datetime(2026, 3, 6, 7, 0),
        )
        logs = [
            MedicationLog(
                id=1,
                user_id=1,
                course_id=1,
                title="Магний",
                dose="1 таб",
                scheduled_date=date(2026, 3, 6),
                status="taken",
                logged_at=datetime(2026, 3, 6, 8, 5),
                created_at=datetime(2026, 3, 6, 8, 5),
            ),
            MedicationLog(
                id=2,
                user_id=1,
                course_id=1,
                title="Магний",
                dose="1 таб",
                scheduled_date=date(2026, 3, 7),
                status="skipped",
                logged_at=datetime(2026, 3, 7, 8, 5),
                created_at=datetime(2026, 3, 7, 8, 5),
            ),
        ]

        marks = _build_medication_calendar_marks([course], logs, date(2026, 3, 6), date(2026, 3, 8))

        self.assertEqual("done", marks[date(2026, 3, 6)])
        self.assertEqual("skipped", marks[date(2026, 3, 7)])
        self.assertEqual("planned", marks[date(2026, 3, 8)])

    def test_build_medication_details_counts_taken_skipped_unique_and_top_title(self) -> None:
        logs = [
            MedicationLog(
                id=1,
                user_id=1,
                course_id=1,
                title="Магний",
                dose="1 таб",
                scheduled_date=date(2026, 3, 6),
                status="taken",
                logged_at=datetime(2026, 3, 6, 8, 5),
                created_at=datetime(2026, 3, 6, 8, 5),
            ),
            MedicationLog(
                id=2,
                user_id=1,
                course_id=1,
                title="Магний",
                dose="1 таб",
                scheduled_date=date(2026, 3, 7),
                status="skipped",
                logged_at=datetime(2026, 3, 7, 8, 5),
                created_at=datetime(2026, 3, 7, 8, 5),
            ),
            MedicationLog(
                id=3,
                user_id=1,
                course_id=2,
                title="Витамин D",
                dose="2000 IU",
                scheduled_date=date(2026, 3, 7),
                status="taken",
                logged_at=datetime(2026, 3, 7, 13, 5),
                created_at=datetime(2026, 3, 7, 13, 5),
            ),
        ]

        details = _build_medication_details(logs)

        self.assertEqual(3, details["total_logs"])
        self.assertEqual(2, details["active_days"])
        self.assertEqual(2, details["unique_titles"])
        self.assertEqual(2, details["best_day_logs"])
        self.assertEqual(2, details["taken_count"])
        self.assertEqual(1, details["skipped_count"])
        self.assertEqual("Магний", details["top_title"])
