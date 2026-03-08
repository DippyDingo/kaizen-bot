from aiogram import F
from aiogram.types import CallbackQuery

from ..common import VIEW_HEALTH, VIEW_WATER, _render, router
from .builders import (
    HEALTH_MODE_MEDICATIONS,
    HEALTH_MODE_SLEEP_PANEL,
    HEALTH_MODE_SUMMARY_DAY,
    HEALTH_MODE_SUMMARY_WEEK,
    HEALTH_MODE_WORKOUT_PANEL,
)
from .state import _resolve_health_summary_mode


@router.callback_query(F.data.startswith("health:mode:"))
async def cb_health_mode(callback: CallbackQuery, state) -> None:
    try:
        mode_raw = callback.data.split(":", 2)[2]
    except IndexError:
        await callback.answer("Ошибка")
        return

    data = await state.get_data()
    summary_mode = _resolve_health_summary_mode(data)

    if mode_raw == "day":
        mode = HEALTH_MODE_SUMMARY_DAY
        summary_mode = HEALTH_MODE_SUMMARY_DAY
    elif mode_raw == "week":
        mode = HEALTH_MODE_SUMMARY_WEEK
        summary_mode = HEALTH_MODE_SUMMARY_WEEK
    elif mode_raw == "sleep_panel":
        mode = HEALTH_MODE_SLEEP_PANEL
    elif mode_raw == "workout_panel":
        mode = HEALTH_MODE_WORKOUT_PANEL
    elif mode_raw == "meds":
        mode = HEALTH_MODE_MEDICATIONS
    else:
        await callback.answer("Ошибка")
        return

    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=mode,
        health_summary_mode=summary_mode,
        health_return_mode=None,
        pending_sleep_minutes=None,
        pending_sleep_exact_fell=None,
        pending_sleep_exact_wake=None,
        pending_workout_type=None,
        pending_energy_level=None,
    )
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer("Экран обновлен")


@router.callback_query(F.data == "health:water")
async def cb_health_water(callback: CallbackQuery, state) -> None:
    data = await state.get_data()
    summary_mode = _resolve_health_summary_mode(data)

    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_WATER,
        water_origin_view=VIEW_HEALTH,
        health_summary_mode=summary_mode,
    )
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "health:back")
async def cb_health_back(callback: CallbackQuery, state) -> None:
    data = await state.get_data()
    summary_mode = _resolve_health_summary_mode(data)

    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=summary_mode,
        health_summary_mode=summary_mode,
        health_return_mode=None,
        pending_sleep_minutes=None,
        pending_sleep_exact_fell=None,
        pending_sleep_exact_wake=None,
        pending_workout_type=None,
        pending_energy_level=None,
    )
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()
