from datetime import date, datetime

from aiogram import F
from aiogram.types import CallbackQuery

from backend.database import async_session
from backend.services.health_service import add_water_log, remove_last_water_log
from backend.services.user_service import get_or_create_user

from ..common import VIEW_HEALTH, VIEW_HOME, VIEW_WATER, _parse_iso_date, _render, router
from .state import _reset_health_mode


async def _restore_after_water_action(state) -> None:
    data = await state.get_data()
    view_mode = data.get("view_mode", VIEW_HOME)
    if view_mode != VIEW_HEALTH:
        await state.set_state(None)
        await state.update_data(view_mode=view_mode)
        return

    await _reset_health_mode(state)


@router.callback_query(F.data.regexp(r"^water:(undo|\d+)$"))
async def cb_water(callback: CallbackQuery, state) -> None:
    action = callback.data.split(":", 1)[1]
    if action == "undo":
        await _undo_water(callback, state)
        return

    try:
        amount_ml = int(action)
    except (ValueError, IndexError):
        await callback.answer("Ошибка")
        return

    data = await state.get_data()
    selected_date = _parse_iso_date(data.get("selected_date"), date.today())
    logged_at = datetime.combine(selected_date, datetime.now().time())

    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            last_name=callback.from_user.last_name,
        )
        level_ups = await add_water_log(session, user, amount_ml, logged_at=logged_at)

    await _restore_after_water_action(state)
    notice = f"Добавлено {amount_ml} мл воды (+2 EXP)"
    if level_ups > 0:
        notice += f" | Уровень +{level_ups}"

    await _render(from_user=callback.from_user, state=state, callback=callback, notice=notice)
    await callback.answer("Записано")


async def _undo_water(callback: CallbackQuery, state) -> None:
    data = await state.get_data()
    selected_date = _parse_iso_date(data.get("selected_date"), date.today())

    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            last_name=callback.from_user.last_name,
        )
        amount_ml, level_change = await remove_last_water_log(session, user, selected_date)

    await _restore_after_water_action(state)

    if amount_ml is None:
        await _render(
            from_user=callback.from_user,
            state=state,
            callback=callback,
            notice="За выбранный день нечего отменять.",
        )
        await callback.answer("Пусто")
        return

    notice = f"Убрано {amount_ml} мл воды (-2 EXP)"
    if level_change < 0:
        notice += f" | Уровень {level_change}"

    await _render(from_user=callback.from_user, state=state, callback=callback, notice=notice)
    await callback.answer("Отменено")
