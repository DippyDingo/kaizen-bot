from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from bot.handlers.single_message_parts.health_parts.wellbeing import (
    cb_wellbeing_energy,
    cb_wellbeing_start,
    cb_wellbeing_stress,
    cb_wellbeing_stress_back,
)


class _FakeState:
    def __init__(self) -> None:
        self.data = {}
        self.current_state = None

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def set_state(self, value):
        self.current_state = value


class _AsyncSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class WellbeingHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_wellbeing_start_opens_energy_selection(self) -> None:
        callback = SimpleNamespace(
            from_user=SimpleNamespace(id=1, first_name="Test", username=None, last_name=None),
            data="wellbeing:start",
            answer=AsyncMock(),
        )
        state = _FakeState()

        with patch("bot.handlers.single_message_parts.health_parts.wellbeing._render", new=AsyncMock()) as render:
            await cb_wellbeing_start(callback, state)

        self.assertEqual("health", state.data["view_mode"])
        self.assertEqual("wellbeing_energy", state.data["health_mode"])
        self.assertIsNone(state.data["pending_energy_level"])
        render.assert_awaited_once()

    async def test_wellbeing_energy_moves_to_stress_step(self) -> None:
        callback = SimpleNamespace(
            from_user=SimpleNamespace(id=1),
            data="wellbeing:energy:4",
            answer=AsyncMock(),
        )
        state = _FakeState()

        with patch("bot.handlers.single_message_parts.health_parts.wellbeing._render", new=AsyncMock()) as render:
            await cb_wellbeing_energy(callback, state)

        self.assertEqual(4, state.data["pending_energy_level"])
        self.assertEqual("wellbeing_stress", state.data["health_mode"])
        render.assert_awaited_once()

    async def test_wellbeing_stress_back_returns_to_energy_step(self) -> None:
        callback = SimpleNamespace(
            from_user=SimpleNamespace(id=1),
            data="wellbeing:stress:back",
            answer=AsyncMock(),
        )
        state = _FakeState()
        state.data.update(pending_energy_level=5, health_mode="wellbeing_stress")

        with patch("bot.handlers.single_message_parts.health_parts.wellbeing._render", new=AsyncMock()) as render:
            await cb_wellbeing_stress_back(callback, state)

        self.assertEqual("wellbeing_energy", state.data["health_mode"])
        self.assertEqual(5, state.data["pending_energy_level"])
        render.assert_awaited_once()

    async def test_wellbeing_stress_saves_and_returns_to_summary(self) -> None:
        callback = SimpleNamespace(
            from_user=SimpleNamespace(id=1, first_name="Test", username=None, last_name=None),
            data="wellbeing:stress:2",
            answer=AsyncMock(),
        )
        state = _FakeState()
        state.data.update(selected_date=date(2026, 3, 7).isoformat(), pending_energy_level=4)
        fake_session = object()

        with (
            patch("bot.handlers.single_message_parts.health_parts.wellbeing.async_session", return_value=_AsyncSessionContext(fake_session)),
            patch("bot.handlers.single_message_parts.health_parts.wellbeing.get_or_create_user", new=AsyncMock(return_value=(SimpleNamespace(id=7), False))),
            patch("bot.handlers.single_message_parts.health_parts.wellbeing.upsert_wellbeing_log", new=AsyncMock()) as upsert_log,
            patch("bot.handlers.single_message_parts.health_parts.wellbeing._reset_health_mode", new=AsyncMock()) as reset_health_mode,
            patch("bot.handlers.single_message_parts.health_parts.wellbeing._render", new=AsyncMock()) as render,
        ):
            await cb_wellbeing_stress(callback, state)

        upsert_log.assert_awaited_once_with(
            session=fake_session,
            user_id=7,
            logged_date=date(2026, 3, 7),
            energy_level=4,
            stress_level=2,
        )
        reset_health_mode.assert_awaited_once_with(state)
        render.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
