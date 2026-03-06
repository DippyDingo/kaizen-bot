import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup

from bot.handlers.single_message_parts.common_parts.constants import DASHBOARD_MESSAGES
from bot.handlers.single_message_parts.common_parts.dashboard import _relocate_dashboard_message, _reset_context, _upsert_dashboard_message


class _FakeState:
    def __init__(self) -> None:
        self.data = {"dashboard_chat_id": 100, "dashboard_message_id": 200}

    async def get_data(self):
        return dict(self.data)

    async def clear(self):
        self.data = {}

    async def update_data(self, **kwargs):
        self.data.update(kwargs)


class _FakeBot:
    def __init__(self, error_text: str = "message is not modified") -> None:
        self.edit_calls = 0
        self.answer_calls = 0
        self.error_text = error_text
        self.delete_message = AsyncMock()

    async def edit_message_text(self, **_kwargs):
        self.edit_calls += 1
        raise TelegramBadRequest(MagicMock(), self.error_text)


class _FakeMessage:
    def __init__(self, bot) -> None:
        self.bot = bot
        self.chat = SimpleNamespace(id=100)
        self.from_user = SimpleNamespace(id=42, first_name="Test", username=None, last_name=None)

    async def answer(self, **_kwargs):
        self.bot.answer_calls += 1
        return SimpleNamespace(chat=SimpleNamespace(id=100), message_id=201)


class DashboardRenderingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.old_dashboard_messages = dict(DASHBOARD_MESSAGES)
        DASHBOARD_MESSAGES.clear()

    def tearDown(self) -> None:
        DASHBOARD_MESSAGES.clear()
        DASHBOARD_MESSAGES.update(self.old_dashboard_messages)

    async def test_upsert_does_not_send_new_message_when_not_modified(self) -> None:
        state = _FakeState()
        bot = _FakeBot()
        message = _FakeMessage(bot)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])

        await _upsert_dashboard_message(message, state, "same text", keyboard)

        self.assertEqual(1, bot.edit_calls)
        self.assertEqual(0, bot.answer_calls)
        self.assertEqual(100, state.data["dashboard_chat_id"])
        self.assertEqual(200, state.data["dashboard_message_id"])

    async def test_upsert_recreates_dashboard_when_edit_target_is_missing(self) -> None:
        state = _FakeState()
        bot = _FakeBot(error_text="message to edit not found")
        message = _FakeMessage(bot)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])

        with patch(
            "bot.handlers.single_message_parts.common_parts.dashboard._persist_dashboard_ref",
            new=AsyncMock(),
        ) as persist_dashboard_ref:
            await _upsert_dashboard_message(message, state, "fresh text", keyboard)

        self.assertEqual(1, bot.edit_calls)
        self.assertEqual(1, bot.answer_calls)
        persist_dashboard_ref.assert_awaited_once()

    async def test_reset_context_preserves_dashboard_refs(self) -> None:
        state = _FakeState()
        state.data.update(
            selected_date="2026-03-01",
            calendar_month="2026-03-01",
            view_mode="health",
            output_message_ids=[10, 20],
        )

        selected_date, calendar_month, resolved_view = await _reset_context(state, view_mode="tasks")

        self.assertEqual("2026-03-01", selected_date.isoformat())
        self.assertEqual("2026-03-01", calendar_month.isoformat())
        self.assertEqual("tasks", resolved_view)
        self.assertEqual(100, state.data["dashboard_chat_id"])
        self.assertEqual(200, state.data["dashboard_message_id"])
        self.assertEqual([10, 20], state.data["output_message_ids"])

    async def test_relocate_dashboard_clears_ref_and_local_cache(self) -> None:
        bot = _FakeBot()
        message = _FakeMessage(bot)
        state = _FakeState()
        DASHBOARD_MESSAGES[(message.chat.id, message.from_user.id)] = (100, 200)

        with (
            patch(
                "bot.handlers.single_message_parts.common_parts.dashboard._resolve_dashboard_target",
                new=AsyncMock(return_value=(100, 200)),
            ),
            patch(
                "bot.handlers.single_message_parts.common_parts.dashboard._clear_dashboard_ref",
                new=AsyncMock(),
            ) as clear_dashboard_ref,
        ):
            await _relocate_dashboard_message(message, state)

        bot.delete_message.assert_awaited_once_with(chat_id=100, message_id=200)
        clear_dashboard_ref.assert_awaited_once_with(state, message.from_user)
        self.assertNotIn((message.chat.id, message.from_user.id), DASHBOARD_MESSAGES)


if __name__ == "__main__":
    unittest.main()
