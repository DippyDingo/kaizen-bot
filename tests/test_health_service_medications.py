from datetime import date, datetime, time
import unittest

from backend.models import MedicationCourse, MedicationLog
from backend.services.health_service import (
    _build_medication_calendar_marks,
    _build_medication_details,
    _build_medication_schedule_items,
)


class MedicationServiceAggregateTests(unittest.TestCase):
    def test_build_medication_schedule_items_defaults_unchecked_items_to_skipped_for_past_day(self) -> None:
        course_a = MedicationCourse(
            id=1,
            user_id=1,
            title="Magnesium",
            dose="1 tab",
            intake_time=time(8, 0),
            start_date=date(2026, 3, 6),
            end_date=date(2026, 3, 10),
            is_active=True,
            created_at=datetime(2026, 3, 6, 7, 0),
        )
        course_b = MedicationCourse(
            id=2,
            user_id=1,
            title="Vitamin D",
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
            title="Magnesium",
            dose="1 tab",
            scheduled_date=date(2026, 3, 6),
            status="taken",
            logged_at=datetime(2026, 3, 6, 8, 5),
            created_at=datetime(2026, 3, 6, 8, 5),
        )

        items = _build_medication_schedule_items([course_b, course_a], [log], date(2026, 3, 6), today=date(2026, 3, 8))

        self.assertEqual(2, len(items))
        self.assertEqual("08:00", items[0]["intake_time"])
        self.assertEqual("taken", items[0]["status"])
        self.assertEqual(5, items[0]["days_left"])
        self.assertEqual("skipped", items[1]["status"])

    def test_build_medication_schedule_items_uses_pending_for_today_without_log(self) -> None:
        course = MedicationCourse(
            id=1,
            user_id=1,
            title="Magnesium",
            dose="1 tab",
            intake_time=time(8, 0),
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 10),
            is_active=True,
            created_at=datetime(2026, 3, 8, 7, 0),
        )

        items = _build_medication_schedule_items([course], [], date(2026, 3, 8), today=date(2026, 3, 8))

        self.assertEqual(1, len(items))
        self.assertEqual("pending", items[0]["status"])

    def test_build_medication_calendar_marks_uses_planned_for_partial_or_future_days(self) -> None:
        course = MedicationCourse(
            id=1,
            user_id=1,
            title="Magnesium",
            dose="1 tab",
            intake_time=time(8, 0),
            start_date=date(2026, 3, 6),
            end_date=date(2026, 3, 9),
            is_active=True,
            created_at=datetime(2026, 3, 6, 7, 0),
        )
        second_course = MedicationCourse(
            id=2,
            user_id=1,
            title="Vitamin D",
            dose="2000 IU",
            intake_time=time(13, 0),
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 8),
            is_active=True,
            created_at=datetime(2026, 3, 8, 7, 0),
        )
        logs = [
            MedicationLog(
                id=1,
                user_id=1,
                course_id=1,
                title="Magnesium",
                dose="1 tab",
                scheduled_date=date(2026, 3, 6),
                status="taken",
                logged_at=datetime(2026, 3, 6, 8, 5),
                created_at=datetime(2026, 3, 6, 8, 5),
            ),
            MedicationLog(
                id=2,
                user_id=1,
                course_id=1,
                title="Magnesium",
                dose="1 tab",
                scheduled_date=date(2026, 3, 8),
                status="taken",
                logged_at=datetime(2026, 3, 8, 8, 5),
                created_at=datetime(2026, 3, 8, 8, 5),
            ),
        ]

        marks = _build_medication_calendar_marks(
            [course, second_course],
            logs,
            date(2026, 3, 6),
            date(2026, 3, 9),
            today=date(2026, 3, 8),
        )

        self.assertEqual("done", marks[date(2026, 3, 6)])
        self.assertEqual("skipped", marks[date(2026, 3, 7)])
        self.assertEqual("planned", marks[date(2026, 3, 8)])
        self.assertEqual("planned", marks[date(2026, 3, 9)])

    def test_build_medication_calendar_marks_uses_skipped_for_partial_past_day(self) -> None:
        first_course = MedicationCourse(
            id=1,
            user_id=1,
            title="Magnesium",
            dose="1 tab",
            intake_time=time(8, 0),
            start_date=date(2026, 3, 6),
            end_date=date(2026, 3, 6),
            is_active=True,
            created_at=datetime(2026, 3, 6, 7, 0),
        )
        second_course = MedicationCourse(
            id=2,
            user_id=1,
            title="Vitamin D",
            dose="2000 IU",
            intake_time=time(13, 0),
            start_date=date(2026, 3, 6),
            end_date=date(2026, 3, 6),
            is_active=True,
            created_at=datetime(2026, 3, 6, 7, 0),
        )
        logs = [
            MedicationLog(
                id=1,
                user_id=1,
                course_id=1,
                title="Magnesium",
                dose="1 tab",
                scheduled_date=date(2026, 3, 6),
                status="taken",
                logged_at=datetime(2026, 3, 6, 8, 5),
                created_at=datetime(2026, 3, 6, 8, 5),
            ),
        ]

        marks = _build_medication_calendar_marks(
            [first_course, second_course],
            logs,
            date(2026, 3, 6),
            date(2026, 3, 6),
            today=date(2026, 3, 8),
        )

        self.assertEqual("skipped", marks[date(2026, 3, 6)])

    def test_build_medication_calendar_marks_uses_latest_log_per_course_day(self) -> None:
        course = MedicationCourse(
            id=1,
            user_id=1,
            title="Magnesium",
            dose="1 tab",
            intake_time=time(8, 0),
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 8),
            is_active=True,
            created_at=datetime(2026, 3, 8, 7, 0),
        )
        logs = [
            MedicationLog(
                id=1,
                user_id=1,
                course_id=1,
                title="Magnesium",
                dose="1 tab",
                scheduled_date=date(2026, 3, 8),
                status="taken",
                logged_at=datetime(2026, 3, 8, 8, 5),
                created_at=datetime(2026, 3, 8, 8, 5),
            ),
            MedicationLog(
                id=2,
                user_id=1,
                course_id=1,
                title="Magnesium",
                dose="1 tab",
                scheduled_date=date(2026, 3, 8),
                status="skipped",
                logged_at=datetime(2026, 3, 8, 9, 0),
                created_at=datetime(2026, 3, 8, 9, 0),
            ),
        ]

        marks = _build_medication_calendar_marks([course], logs, date(2026, 3, 8), date(2026, 3, 8), today=date(2026, 3, 8))

        self.assertEqual("skipped", marks[date(2026, 3, 8)])

    def test_build_medication_calendar_marks_ignores_inactive_courses(self) -> None:
        archived_course = MedicationCourse(
            id=2,
            user_id=1,
            title="Vitamin D",
            dose="2000 IU",
            intake_time=time(13, 0),
            start_date=date(2026, 3, 6),
            end_date=date(2026, 3, 6),
            is_active=False,
            created_at=datetime(2026, 3, 6, 7, 0),
        )

        marks = _build_medication_calendar_marks([archived_course], [], date(2026, 3, 6), date(2026, 3, 6), today=date(2026, 3, 8))

        self.assertEqual({}, marks)

    def test_build_medication_details_counts_taken_and_default_skips(self) -> None:
        courses = [
            MedicationCourse(
                id=1,
                user_id=1,
                title="Magnesium",
                dose="1 tab",
                intake_time=time(8, 0),
                start_date=date(2026, 3, 6),
                end_date=date(2026, 3, 7),
                is_active=True,
                created_at=datetime(2026, 3, 6, 7, 0),
            ),
            MedicationCourse(
                id=2,
                user_id=1,
                title="Vitamin D",
                dose="2000 IU",
                intake_time=time(13, 0),
                start_date=date(2026, 3, 7),
                end_date=date(2026, 3, 7),
                is_active=True,
                created_at=datetime(2026, 3, 7, 7, 0),
            ),
        ]
        logs = [
            MedicationLog(
                id=1,
                user_id=1,
                course_id=1,
                title="Magnesium",
                dose="1 tab",
                scheduled_date=date(2026, 3, 6),
                status="taken",
                logged_at=datetime(2026, 3, 6, 8, 5),
                created_at=datetime(2026, 3, 6, 8, 5),
            ),
            MedicationLog(
                id=2,
                user_id=1,
                course_id=2,
                title="Vitamin D",
                dose="2000 IU",
                scheduled_date=date(2026, 3, 7),
                status="taken",
                logged_at=datetime(2026, 3, 7, 13, 5),
                created_at=datetime(2026, 3, 7, 13, 5),
            ),
        ]

        details = _build_medication_details(courses, logs, date(2026, 3, 6), date(2026, 3, 7), today=date(2026, 3, 8))

        self.assertEqual(3, details["total_logs"])
        self.assertEqual(2, details["active_days"])
        self.assertEqual(2, details["unique_titles"])
        self.assertEqual(2, details["best_day_logs"])
        self.assertEqual(2, details["taken_count"])
        self.assertEqual(0, details["pending_count"])
        self.assertEqual(1, details["skipped_count"])
        self.assertEqual("Magnesium", details["top_title"])
