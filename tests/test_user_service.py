import unittest

from backend.services.user_service import (
    set_user_chat_keyboard_message_ref,
    set_user_dashboard_message_ref,
    set_user_daily_water_target,
    set_user_daily_workout_target,
)


class _FakeUser:
    daily_water_target_ml = 2500
    daily_workout_target_min = 30
    dashboard_chat_id = None
    dashboard_message_id = None
    chat_keyboard_chat_id = None
    chat_keyboard_message_id = None


class _FakeSession:
    async def commit(self) -> None:
        return None

    async def refresh(self, _obj) -> None:
        return None


class UserServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_set_user_daily_water_target_clamps_minimum(self) -> None:
        user = _FakeUser()
        session = _FakeSession()

        await set_user_daily_water_target(session, user, 100)

        self.assertEqual(250, user.daily_water_target_ml)

    async def test_set_user_daily_workout_target_clamps_minimum(self) -> None:
        user = _FakeUser()
        session = _FakeSession()

        await set_user_daily_workout_target(session, user, 1)

        self.assertEqual(5, user.daily_workout_target_min)

    async def test_set_user_dashboard_message_ref_updates_message_pointer(self) -> None:
        user = _FakeUser()
        session = _FakeSession()

        await set_user_dashboard_message_ref(session, user, chat_id=123, message_id=456)

        self.assertEqual(123, user.dashboard_chat_id)
        self.assertEqual(456, user.dashboard_message_id)

    async def test_set_user_chat_keyboard_message_ref_updates_message_pointer(self) -> None:
        user = _FakeUser()
        session = _FakeSession()

        await set_user_chat_keyboard_message_ref(session, user, chat_id=321, message_id=654)

        self.assertEqual(321, user.chat_keyboard_chat_id)
        self.assertEqual(654, user.chat_keyboard_message_id)
