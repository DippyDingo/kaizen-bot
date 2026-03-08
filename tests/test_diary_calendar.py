from datetime import date, datetime
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bot.handlers.single_message_parts.calendar import _build_calendar_keyboard, _build_diary_calendar_text
from bot.handlers.single_message_parts.calendar_parts.handlers import cb_cal_pick, cb_cal_today
from bot.handlers.single_message_parts.diary_parts.builders import _build_diary_keyboard, _build_diary_text
from backend.services.diary_service import get_diary_calendar_marks


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


class DiaryCalendarServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_diary_calendar_marks_returns_only_days_with_entries(self) -> None:
        session = _FakeSession(
            [
                ("2026-03-06",),
                ("2026-03-08",),
            ]
        )

        marks = await get_diary_calendar_marks(session, user_id=1, date_from=date(2026, 3, 1), date_to=date(2026, 3, 31))

        self.assertEqual(
            {
                date(2026, 3, 6): "has_entries",
                date(2026, 3, 8): "has_entries",
            },
            marks,
        )


class DiaryBuilderTests(unittest.TestCase):
    def test_diary_keyboard_moves_calendar_to_date_center(self) -> None:
        keyboard = _build_diary_keyboard(date(2026, 3, 8), entries=[])

        self.assertEqual("diary:calendar", keyboard.inline_keyboard[0][1].callback_data)
        all_texts = [button.text for row in keyboard.inline_keyboard for button in row]
        self.assertNotIn("📅 Календарь", all_texts)

    def test_diary_keyboard_has_no_inline_entry_buttons(self) -> None:
        entry = SimpleNamespace(
            id=11,
            created_at=datetime(2026, 3, 8, 14, 30),
            entry_type="text",
        )

        keyboard = _build_diary_keyboard(date(2026, 3, 8), entries=[entry])
        all_callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]

        self.assertNotIn("diary:view:11", all_callbacks)

    def test_diary_text_renders_textual_overview(self) -> None:
        entry = SimpleNamespace(
            created_at=datetime(2026, 3, 8, 14, 30),
            entry_type="text",
            text="Проверка дневника",
        )

        text = _build_diary_text([entry], date(2026, 3, 8), "main", notice=None, total_count=1)

        self.assertIn("<b>📝 Дневник</b>", text)
        self.assertIn("<b>Обзор дня</b>", text)
        self.assertIn("<b>Последние записи</b>", text)
        self.assertIn("14:30", text)

    def test_diary_calendar_text_is_compact(self) -> None:
        text = _build_diary_calendar_text(date(2026, 3, 8), notice=None, day_count=2)

        self.assertIn("<b>📅 Календарь дневника</b>", text)
        self.assertIn("📝 есть записи", text)
        self.assertIn("2 записи за день", text)

    def test_diary_calendar_builder_marks_days_with_entries(self) -> None:
        keyboard = _build_calendar_keyboard(
            date(2026, 3, 1),
            date(2026, 3, 8),
            context="diary",
            marks={date(2026, 3, 6): "has_entries"},
        )
        all_texts = [button.text for row in keyboard.inline_keyboard for button in row]

        self.assertIn("📝6", all_texts)
        self.assertIn("📍 Сегодня", all_texts)
        self.assertIn("↩️ Дневник", all_texts)


class DiaryCalendarHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_calendar_pick_diary_returns_to_diary_overview(self) -> None:
        callback = SimpleNamespace(
            data="cal:pick:diary:2026-03-10",
            from_user=SimpleNamespace(id=1),
            answer=AsyncMock(),
        )
        state = _FakeState()
        state.data = {"view_mode": "diary", "diary_calendar_mode": True}

        with patch("bot.handlers.single_message_parts.calendar_parts.handlers._render", new=AsyncMock()) as render:
            await cb_cal_pick(callback, state)

        self.assertFalse(state.data["diary_calendar_mode"])
        self.assertEqual("diary", state.data["view_mode"])
        self.assertEqual("2026-03-10", state.data["selected_date"])
        self.assertEqual("2026-03-01", state.data["calendar_month"])
        render.assert_awaited_once()

    async def test_calendar_today_diary_returns_to_diary_overview(self) -> None:
        callback = SimpleNamespace(
            data="cal:today:diary",
            from_user=SimpleNamespace(id=1),
            answer=AsyncMock(),
        )
        state = _FakeState()

        with patch("bot.handlers.single_message_parts.calendar_parts.handlers._render", new=AsyncMock()) as render:
            await cb_cal_today(callback, state)

        self.assertEqual("diary", state.data["view_mode"])
        self.assertFalse(state.data["diary_calendar_mode"])
        render.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
