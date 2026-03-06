import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup

from bot.handlers.single_message_parts.common_parts.dashboard import _upsert_dashboard_message


class _FakeState:
    def __init__(self) -> None:
        self.data = {"dashboard_chat_id": 100, "dashboard_message_id": 200}

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **kwargs):
        self.data.update(kwargs)


class _FakeBot:
    def __init__(self) -> None:
        self.edit_calls = 0
        self.answer_calls = 0

    async def edit_message_text(self, **_kwargs):
        self.edit_calls += 1
        raise TelegramBadRequest(MagicMock(), "message is not modified")


class _FakeMessage:
    def __init__(self, bot) -> None:
        self.bot = bot
        self.chat = SimpleNamespace(id=100)
        self.from_user = SimpleNamespace(id=42, first_name="Test", username=None, last_name=None)

    async def answer(self, **_kwargs):
        self.bot.answer_calls += 1
        return SimpleNamespace(chat=SimpleNamespace(id=100), message_id=201)


class DashboardRenderingTests(unittest.IsolatedAsyncioTestCase):
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


if __name__ == "__main__":
    unittest.main()
