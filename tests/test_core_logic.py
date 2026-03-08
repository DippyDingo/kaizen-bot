import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.filters.state import StateFilter

from bot.handlers.single_message_parts.common import CHAT_BUTTON_HEALTH, CHAT_BUTTON_SETTINGS, CHAT_NAVIGATION, VIEW_HEALTH, VIEW_SETTINGS
from bot.handlers.single_message_parts.common import router as single_message_router
from bot.handlers.single_message_parts.common_parts.chat_ui import msg_chat_navigation
from bot.handlers.single_message_parts.core_parts.handlers import cmd_start
from bot.handlers.single_message_parts.core import _resolve_cancel_view
from bot.handlers.single_message_parts.tasks_parts.handlers import cb_task_add
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

    def test_fallback_is_limited_to_no_fsm_state(self) -> None:
        fallback_handler = next(
            handler
            for handler in single_message_router.message.handlers
            if getattr(handler.callback, "__name__", "") == "fallback"
        )
        state_filters = [
            filter_object.callback
            for filter_object in fallback_handler.filters
            if isinstance(getattr(filter_object, "callback", None), StateFilter)
        ]

        self.assertEqual(1, len(state_filters))
        self.assertEqual((None,), state_filters[0].states)


class _FakeState:
    def __init__(self) -> None:
        self.data = {}
        self.current_state = None

    async def get_data(self):
        return dict(self.data)

    async def clear(self):
        self.data = {}

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def set_state(self, state):
        self.current_state = state


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
            relocate_dashboard=False,
            entrypoint="chat_menu",
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


class TaskFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_home_task_add_keeps_home_as_origin_view(self) -> None:
        callback = SimpleNamespace(
            data="task:add",
            from_user=SimpleNamespace(id=1, first_name="Test", username=None, last_name=None),
            answer=AsyncMock(),
        )
        state = _FakeState()
        state.data = {"view_mode": "home"}

        with (
            patch("bot.handlers.single_message_parts.tasks_parts.handlers._reset_context", new=AsyncMock(return_value=(SimpleNamespace(isoformat=lambda: "2026-03-08"), SimpleNamespace(isoformat=lambda: "2026-03-01"), "home"))) as reset_context,
            patch("bot.handlers.single_message_parts.tasks_parts.handlers._render", new=AsyncMock()) as render,
        ):
            await cb_task_add(callback, state)

        reset_context.assert_awaited_once_with(state, view_mode="home")
        self.assertEqual("home", state.data["view_mode"])
        self.assertEqual("home", state.data["task_origin_view"])
        self.assertEqual(DashboardStates.waiting_task_title, state.current_state)
        render.assert_awaited_once()
