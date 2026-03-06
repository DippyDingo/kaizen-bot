from aiogram.fsm.context import FSMContext

from ..common import VIEW_HEALTH
from .builders import HEALTH_MODE_SUMMARY_DAY


async def _reset_health_mode(state: FSMContext) -> None:
    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=HEALTH_MODE_SUMMARY_DAY,
        pending_sleep_minutes=None,
        pending_sleep_exact_fell=None,
        pending_sleep_exact_wake=None,
        pending_medication_title=None,
        pending_medication_dose=None,
        pending_medication_time=None,
        pending_workout_type=None,
    )
