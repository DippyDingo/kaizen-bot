import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bot.handlers.single_message_parts.common_parts.chat_ui import _chat_keyboard, _ensure_chat_keyboard, _reset_chat_ui_state
from bot.handlers.single_message_parts.common_parts.constants import (
    CHAT_KEYBOARD_MESSAGES,
    CLEARED_COMMAND_CHATS,
    CONFIGURED_REPLY_KEYBOARD_CHATS,
    CONFIGURED_WEBAPP_CHATS,
)


class _FakeMessage:
    def __init__(self, chat_id: int = 100) -> None:
        self.chat = SimpleNamespace(id=chat_id)
        self.bot = SimpleNamespace(delete_message=AsyncMock())
        self.from_user = SimpleNamespace(id=chat_id, first_name="Test", username=None, last_name=None)
        self.answer_calls = 0

    async def answer(self, *_args, **_kwargs):
        self.answer_calls += 1
        return SimpleNamespace(chat=SimpleNamespace(id=self.chat.id), message_id=900 + self.answer_calls)


class ChatUiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.old_keyboard_messages = dict(CHAT_KEYBOARD_MESSAGES)
        self.old_reply_chats = set(CONFIGURED_REPLY_KEYBOARD_CHATS)
        self.old_webapp_chats = set(CONFIGURED_WEBAPP_CHATS)
        self.old_cleared_chats = set(CLEARED_COMMAND_CHATS)
        CHAT_KEYBOARD_MESSAGES.clear()
        CONFIGURED_REPLY_KEYBOARD_CHATS.clear()
        CONFIGURED_WEBAPP_CHATS.clear()
        CLEARED_COMMAND_CHATS.clear()

    def tearDown(self) -> None:
        CHAT_KEYBOARD_MESSAGES.clear()
        CHAT_KEYBOARD_MESSAGES.update(self.old_keyboard_messages)
        CONFIGURED_REPLY_KEYBOARD_CHATS.clear()
        CONFIGURED_REPLY_KEYBOARD_CHATS.update(self.old_reply_chats)
        CONFIGURED_WEBAPP_CHATS.clear()
        CONFIGURED_WEBAPP_CHATS.update(self.old_webapp_chats)
        CLEARED_COMMAND_CHATS.clear()
        CLEARED_COMMAND_CHATS.update(self.old_cleared_chats)

    def test_reset_chat_ui_state_clears_all_cached_refs(self) -> None:
        chat_id = 321
        CHAT_KEYBOARD_MESSAGES[chat_id] = 11
        CONFIGURED_REPLY_KEYBOARD_CHATS.add(chat_id)
        CONFIGURED_WEBAPP_CHATS.add(chat_id)
        CLEARED_COMMAND_CHATS.add(chat_id)

        _reset_chat_ui_state(chat_id)

        self.assertNotIn(chat_id, CHAT_KEYBOARD_MESSAGES)
        self.assertNotIn(chat_id, CONFIGURED_REPLY_KEYBOARD_CHATS)
        self.assertNotIn(chat_id, CONFIGURED_WEBAPP_CHATS)
        self.assertNotIn(chat_id, CLEARED_COMMAND_CHATS)

    async def test_ensure_chat_keyboard_recovers_without_cached_carrier_id(self) -> None:
        chat_id = 321
        message = _FakeMessage(chat_id=chat_id)

        with patch(
            "bot.handlers.single_message_parts.common_parts.chat_ui._resolve_carrier_target",
            new=AsyncMock(return_value=(chat_id, 777)),
        ):
            await _ensure_chat_keyboard(message)

        self.assertEqual(0, message.answer_calls)
        self.assertEqual(777, CHAT_KEYBOARD_MESSAGES[chat_id])
        self.assertIn(chat_id, CONFIGURED_REPLY_KEYBOARD_CHATS)

    async def test_ensure_chat_keyboard_reuses_cached_carrier_without_sending(self) -> None:
        chat_id = 321
        CHAT_KEYBOARD_MESSAGES[chat_id] = 777
        CONFIGURED_REPLY_KEYBOARD_CHATS.add(chat_id)
        message = _FakeMessage(chat_id=chat_id)

        await _ensure_chat_keyboard(message)

        self.assertEqual(0, message.answer_calls)

    async def test_ensure_chat_keyboard_force_recreates_and_deletes_previous_carrier(self) -> None:
        chat_id = 321
        message = _FakeMessage(chat_id=chat_id)

        with patch(
            "bot.handlers.single_message_parts.common_parts.chat_ui._resolve_carrier_target",
            new=AsyncMock(return_value=(chat_id, 777)),
        ), patch(
            "bot.handlers.single_message_parts.common_parts.chat_ui._persist_carrier_ref",
            new=AsyncMock(),
        ) as persist_ref:
            await _ensure_chat_keyboard(message, force=True)

        message.bot.delete_message.assert_awaited_once_with(chat_id=chat_id, message_id=777)
        self.assertEqual(1, message.answer_calls)
        persist_ref.assert_awaited_once()

    def test_chat_keyboard_has_no_top_level_calendar_button(self) -> None:
        keyboard = _chat_keyboard()
        all_texts = [button.text for row in keyboard.keyboard for button in row]

        self.assertNotIn("📅 Календарь", all_texts)
        self.assertIn("🏠 Главная", all_texts)
        self.assertIn("📋 Задачи", all_texts)
        self.assertIn("📝 Дневник", all_texts)
        self.assertIn("📊 Статистика", all_texts)
        self.assertIn("❤️ Здоровье", all_texts)
        self.assertIn("⚙️ Настройки", all_texts)


if __name__ == "__main__":
    unittest.main()
