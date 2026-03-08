from datetime import date
import unittest

from bot.handlers.single_message_parts.health import (
    HEALTH_MODE_MEDICATIONS,
    HEALTH_MODE_SLEEP_PANEL,
    HEALTH_MODE_SUMMARY_DAY,
    HEALTH_MODE_SUMMARY_WEEK,
    HEALTH_MODE_WORKOUT_PANEL,
    _build_health_keyboard,
    _build_health_text,
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
        self.assertEqual("🟢", _medication_status_icon("taken"))
        self.assertEqual("🔴", _medication_status_icon("skipped"))
        self.assertEqual("🟡", _medication_status_icon("pending"))

    def test_medication_keyboard_uses_single_status_button_in_one_row(self) -> None:
        keyboard = _build_health_keyboard(
            date(2026, 3, 8),
            mode=HEALTH_MODE_MEDICATIONS,
            summary={
                "medication_schedule": [
                    {
                        "course_id": 1,
                        "title": "Magnesium",
                        "dose": "200 mg",
                        "intake_time": "08:00",
                        "status": "skipped",
                    }
                ]
            },
        )

        medication_row = keyboard.inline_keyboard[2]
        self.assertEqual(["08:00 Magnesium", "❌", "🗑"], [button.text for button in medication_row])

    def test_health_root_keyboard_is_navigation_first(self) -> None:
        keyboard = _build_health_keyboard(date(2026, 3, 8), mode=HEALTH_MODE_SUMMARY_DAY)
        rows = keyboard.inline_keyboard

        self.assertEqual(["💧 Вода", "😴 Сон"], [button.text for button in rows[2]])
        self.assertEqual(["🏃 Тренировки", "💊 Лекарства"], [button.text for button in rows[3]])
        self.assertEqual(["🧠 Состояние"], [button.text for button in rows[4]])

        all_texts = [button.text for row in rows for button in row]
        self.assertNotIn("😴 Добавить сон", all_texts)
        self.assertNotIn("🏃 Добавить тренировку", all_texts)
        self.assertNotIn("↩️ Отменить последний", all_texts)

    def test_sleep_panel_keyboard_has_local_actions_only(self) -> None:
        keyboard = _build_health_keyboard(date(2026, 3, 8), mode=HEALTH_MODE_SLEEP_PANEL)
        self.assertEqual(["➕ Добавить сон"], [button.text for button in keyboard.inline_keyboard[1]])
        self.assertEqual(["↩️ Отменить последний"], [button.text for button in keyboard.inline_keyboard[2]])
        self.assertEqual(["⬅️ Назад"], [button.text for button in keyboard.inline_keyboard[3]])

    def test_workout_panel_keyboard_has_local_actions_only(self) -> None:
        keyboard = _build_health_keyboard(date(2026, 3, 8), mode=HEALTH_MODE_WORKOUT_PANEL)
        self.assertEqual(["➕ Добавить тренировку"], [button.text for button in keyboard.inline_keyboard[1]])
        self.assertEqual(["↩️ Отменить последнюю"], [button.text for button in keyboard.inline_keyboard[2]])
        self.assertEqual(["⬅️ Назад"], [button.text for button in keyboard.inline_keyboard[3]])

    def test_health_day_text_is_short_hub_without_explanatory_block(self) -> None:
        text = _build_health_text(
            1200,
            420,
            date(2026, 3, 8),
            None,
            mode=HEALTH_MODE_SUMMARY_DAY,
            summary={
                "day_workout_total": 45,
                "day_medication_total": 3,
                "day_medication_taken": 1,
                "day_energy_level": 3,
                "day_stress_level": 2,
                "day_has_wellbeing": True,
            },
        )

        self.assertNotIn("Быстрые действия", text)
        self.assertNotIn("Уникальных", text)
        self.assertNotIn("Качество сна", text)
        self.assertIn("💧 Вода", text)
        self.assertIn("😴 Сон", text)
        self.assertIn("🏃 Тренировки", text)
        self.assertIn("💊 Лекарства", text)
        self.assertIn("🧠 Состояние", text)

    def test_health_week_text_is_short_summary(self) -> None:
        text = _build_health_text(
            0,
            0,
            date(2026, 3, 8),
            None,
            mode=HEALTH_MODE_SUMMARY_WEEK,
            summary={
                "week_from": date(2026, 3, 2),
                "week_water_total": 8000,
                "week_water_avg": 1143,
                "week_sleep_total": 2400,
                "week_sleep_avg": 343,
                "week_workout_total": 120,
                "week_workout_sessions": 4,
                "week_medication_total": 6,
                "week_medication_active_days": 3,
                "week_wellbeing_active_days": 4,
                "week_avg_energy": 3.5,
                "week_avg_stress": 2.0,
            },
        )

        self.assertNotIn("По типам", text)
        self.assertNotIn("Минуты по типам", text)
        self.assertNotIn("Уникальных", text)
        self.assertNotIn("Чаще всего", text)
        self.assertIn("💧 Вода", text)
        self.assertIn("😴 Сон", text)
        self.assertIn("🏃 Тренировки", text)
        self.assertIn("💊 Лекарства", text)
        self.assertIn("🧠 Состояние", text)


if __name__ == "__main__":
    unittest.main()
