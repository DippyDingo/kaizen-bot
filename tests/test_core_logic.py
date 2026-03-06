import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bot.handlers.single_message_parts.common import CHAT_BUTTON_HEALTH, CHAT_BUTTON_SETTINGS, CHAT_NAVIGATION, VIEW_HEALTH, VIEW_SETTINGS
from bot.handlers.single_message_parts.common_parts.chat_ui import msg_chat_navigation
from bot.handlers.single_message_parts.core_parts.handlers import cmd_start
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
    def __init__(self) -> None:
        self.data = {}

    async def get_data(self):
        return dict(self.data)

    async def clear(self):
        self.data = {}

    async def update_data(self, **kwargs):
        self.data.update(kwargs)


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


class StartHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_cmd_start_relocates_dashboard_before_render(self) -> None:
        message = SimpleNamespace(
            from_user=SimpleNamespace(id=1, first_name="Test", username=None, last_name=None),
            chat=SimpleNamespace(id=1),
        )
        state = _FakeState()

        with (
            patch("bot.handlers.single_message_parts.core_parts.handlers._maybe_start_name_onboarding", new=AsyncMock(return_value=False)),
            patch("bot.handlers.single_message_parts.core_parts.handlers._reset_chat_ui_state") as reset_chat_ui_state,
            patch("bot.handlers.single_message_parts.core_parts.handlers._setup_chat_ui", new=AsyncMock()) as setup_ui,
            patch("bot.handlers.single_message_parts.core_parts.handlers._relocate_dashboard_message", new=AsyncMock()) as relocate_dashboard,
            patch("bot.handlers.single_message_parts.core_parts.handlers._render", new=AsyncMock()) as render,
        ):
            await cmd_start(message, state)

        reset_chat_ui_state.assert_called_once_with(message.chat.id)
        setup_ui.assert_awaited_once_with(message, force_keyboard=True)
        relocate_dashboard.assert_awaited_once_with(message, state)
        render.assert_awaited_once()
