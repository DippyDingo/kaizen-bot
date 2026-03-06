import unittest

from backend.services.user_service import set_user_daily_water_target, set_user_daily_workout_target


class _FakeUser:
    daily_water_target_ml = 2500
    daily_workout_target_min = 30


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
