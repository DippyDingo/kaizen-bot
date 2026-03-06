import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bot.handlers.single_message_parts.common import CHAT_BUTTON_HEALTH, CHAT_BUTTON_SETTINGS, CHAT_NAVIGATION, VIEW_HEALTH, VIEW_SETTINGS
from bot.handlers.single_message_parts.common_parts.chat_ui import msg_chat_navigation
from bot.handlers.single_message_parts.core import _resolve_cancel_view
from bot.states import DashboardStates


class CoreLogicTests(unittest.TestCase):
    def test_cancel_from_medication_states_returns_health(self) -> None:
        self.assertEqual(VIEW_HEALTH, _resolve_cancel_view(DashboardStates.waiting_medication_title.state))
        self.assertEqual(VIEW_HEALTH, _resolve_cancel_view(DashboardStates.waiting_medication_dose.state))
        self.assertEqual(VIEW_HEALTH, _resolve_cancel_view(DashboardStates.waiting_medication_time_text.state))
        self.assertEqual(VIEW_HEALTH, _resolve_cancel_view(DashboardStates.waiting_medication_days_text.state))

    def test_cancel_from_settings_limits_returns_settings(self) -> None:
        self.assertEqual(VIEW_SETTINGS, _resolve_cancel_view(DashboardStates.waiting_daily_water_target.state))
        self.assertEqual(VIEW_SETTINGS, _resolve_cancel_view(DashboardStates.waiting_daily_workout_target.state))

    def test_chat_navigation_keeps_health_and_settings(self) -> None:
        self.assertEqual(VIEW_HEALTH, CHAT_NAVIGATION[CHAT_BUTTON_HEALTH])
        self.assertEqual(VIEW_SETTINGS, CHAT_NAVIGATION[CHAT_BUTTON_SETTINGS])


class _FakeState:
    async def get_data(self):
        return {}


class ChatNavigationHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_navigation_uses_shared_render_command_view(self) -> None:
        message = SimpleNamespace(
            text=CHAT_BUTTON_HEALTH,
            from_user=SimpleNamespace(id=1),
            chat=SimpleNamespace(id=1),
        )
        state = _FakeState()

        with patch("bot.handlers.single_message_parts.core._render_command_view", new=AsyncMock()) as render_view:
            await msg_chat_navigation(message, state)

        render_view.assert_awaited_once_with(
            message,
            state,
            VIEW_HEALTH,
            delete_source_message=True,
            force_keyboard=False,
            relocate_dashboard=True,
        )
