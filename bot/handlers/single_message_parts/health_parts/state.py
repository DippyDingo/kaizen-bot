from aiogram.fsm.context import FSMContext

from ..common import VIEW_HEALTH
from .builders import (
    HEALTH_MODE_MEDICATIONS,
    HEALTH_MODE_SLEEP_PANEL,
    HEALTH_MODE_SUMMARY_DAY,
    HEALTH_MODE_SUMMARY_WEEK,
    HEALTH_MODE_WORKOUT_PANEL,
)


def _resolve_health_summary_mode(data: dict) -> str:
    summary_mode = data.get("health_summary_mode", HEALTH_MODE_SUMMARY_DAY)
    if summary_mode not in {HEALTH_MODE_SUMMARY_DAY, HEALTH_MODE_SUMMARY_WEEK}:
        return HEALTH_MODE_SUMMARY_DAY
    return str(summary_mode)


def _resolve_health_return_mode(data: dict) -> str:
    return_mode = data.get("health_return_mode")
    if return_mode in {HEALTH_MODE_SLEEP_PANEL, HEALTH_MODE_WORKOUT_PANEL, HEALTH_MODE_MEDICATIONS}:
        return str(return_mode)
    return _resolve_health_summary_mode(data)


async def _reset_health_mode(state: FSMContext) -> None:
    data = await state.get_data()
    summary_mode = _resolve_health_summary_mode(data)
    return_mode = _resolve_health_return_mode(data)

    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=return_mode,
        health_summary_mode=summary_mode,
        health_return_mode=None,
        pending_sleep_minutes=None,
        pending_sleep_exact_fell=None,
        pending_sleep_exact_wake=None,
        pending_medication_title=None,
        pending_medication_dose=None,
        pending_medication_time=None,
        pending_workout_type=None,
        pending_energy_level=None,
    )
