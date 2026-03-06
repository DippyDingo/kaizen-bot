from aiogram.fsm.context import FSMContext

from ..common import VIEW_HEALTH
from .builders import HEALTH_MODE_SUMMARY_DAY, HEALTH_MODE_SUMMARY_WEEK


async def _reset_health_mode(state: FSMContext) -> None:
    data = await state.get_data()
    summary_mode = data.get("health_summary_mode", HEALTH_MODE_SUMMARY_DAY)
    if summary_mode not in {HEALTH_MODE_SUMMARY_DAY, HEALTH_MODE_SUMMARY_WEEK}:
        summary_mode = HEALTH_MODE_SUMMARY_DAY

    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=summary_mode,
        health_summary_mode=summary_mode,
        pending_sleep_minutes=None,
        pending_sleep_exact_fell=None,
        pending_sleep_exact_wake=None,
        pending_medication_title=None,
        pending_medication_dose=None,
        pending_medication_time=None,
        pending_workout_type=None,
    )
