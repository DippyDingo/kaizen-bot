from datetime import date
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bot.handlers.single_message_parts.calendar import _build_calendar_keyboard, _build_task_calendar_text
from bot.handlers.single_message_parts.calendar_parts.handlers import cb_cal_pick
from bot.handlers.single_message_parts.tasks_parts.handlers import cb_task_calendar
from bot.handlers.single_message_parts.tasks import _build_tasks_keyboard
from backend.services.task_service import get_task_calendar_marks


class _FakeState:
    def __init__(self) -> None:
        self.data = {}

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **kwargs):
        self.data.update(kwargs)


class _FakeResult:
    def __init__(self, rows) -> None:
        self._rows = rows

    def all(self):
        return list(self._rows)


class _FakeSession:
    def __init__(self, rows) -> None:
        self.rows = rows

    async def execute(self, _query):
        return _FakeResult(self.rows)


class TaskCalendarServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_task_calendar_marks_maps_day_statuses(self) -> None:
        session = _FakeSession(
            [
                (date(2026, 3, 6), 2, 2),
                (date(2026, 3, 7), 3, 1),
                (date(2026, 3, 8), 4, 0),
            ]
        )

        marks = await get_task_calendar_marks(session, user_id=1, date_from=date(2026, 3, 6), date_to=date(2026, 3, 8))

        self.assertEqual("done", marks[date(2026, 3, 6)]["status"])
        self.assertEqual("mixed", marks[date(2026, 3, 7)]["status"])
        self.assertEqual("open", marks[date(2026, 3, 8)]["status"])

    async def test_get_task_calendar_marks_skips_empty_days(self) -> None:
        session = _FakeSession([])

        marks = await get_task_calendar_marks(session, user_id=1, date_from=date(2026, 3, 6), date_to=date(2026, 3, 8))

        self.assertEqual({}, marks)


class TaskCalendarBuilderTests(unittest.TestCase):
    def test_tasks_keyboard_center_button_opens_task_calendar(self) -> None:
        keyboard = _build_tasks_keyboard([], date(2026, 3, 8))

        self.assertEqual("task:calendar", keyboard.inline_keyboard[0][1].callback_data)

    def test_task_calendar_text_is_compact_for_day_with_tasks(self) -> None:
        text = _build_task_calendar_text(
            date(2026, 3, 8),
            {"total": 3, "done": 0},
            notice=None,
        )

        self.assertIn("<b>📅 Календарь задач</b>", text)
        self.assertIn("✅ всё • 🟡 часть • 🔴 открыто", text)
        self.assertIn("3 задач • 0 выполнено • 3 осталось", text)
        self.assertNotIn("Метки:", text)
        self.assertNotIn("На выбранный день", text)

    def test_task_calendar_text_shows_empty_day_message(self) -> None:
        text = _build_task_calendar_text(
            date(2026, 3, 8),
            {"total": 0, "done": 0},
            notice=None,
        )

        self.assertIn("На этот день задач нет", text)

    def test_task_calendar_builder_renders_status_prefixes(self) -> None:
        keyboard = _build_calendar_keyboard(
            date(2026, 3, 1),
            date(2026, 3, 8),
            context="tasks",
            marks={
                date(2026, 3, 6): "done",
                date(2026, 3, 7): "mixed",
                date(2026, 3, 9): "open",
            },
        )
        all_texts = [button.text for row in keyboard.inline_keyboard for button in row]

        self.assertIn("✅6", all_texts)
        self.assertIn("🟡7", all_texts)
        self.assertIn("🔴9", all_texts)
        self.assertIn("📍 Сегодня", all_texts)
        self.assertIn("↩️ Назад", all_texts)


class TaskCalendarHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_task_calendar_callback_opens_tasks_calendar_mode(self) -> None:
        callback = SimpleNamespace(
            from_user=SimpleNamespace(id=1),
            answer=AsyncMock(),
        )
        state = _FakeState()
        state.data = {"selected_date": "2026-03-08", "view_mode": "tasks"}

        with patch("bot.handlers.single_message_parts.tasks_parts.handlers._render", new=AsyncMock()) as render:
            await cb_task_calendar(callback, state)

        self.assertTrue(state.data["task_calendar_mode"])
        self.assertEqual("tasks", state.data["view_mode"])
        self.assertEqual("2026-03-01", state.data["calendar_month"])
        render.assert_awaited_once()

    async def test_calendar_pick_tasks_returns_to_task_list(self) -> None:
        callback = SimpleNamespace(
            data="cal:pick:tasks:2026-03-10",
            from_user=SimpleNamespace(id=1),
            answer=AsyncMock(),
        )
        state = _FakeState()
        state.data = {"view_mode": "tasks", "task_calendar_mode": True}

        with patch("bot.handlers.single_message_parts.calendar_parts.handlers._render", new=AsyncMock()) as render:
            await cb_cal_pick(callback, state)

        self.assertFalse(state.data["task_calendar_mode"])
        self.assertEqual("tasks", state.data["view_mode"])
        self.assertEqual("2026-03-10", state.data["selected_date"])
        self.assertEqual("2026-03-01", state.data["calendar_month"])
        render.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
