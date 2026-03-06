from datetime import date

from aiogram import F
from aiogram.types import CallbackQuery

from backend.database import async_session
from backend.services.health_service import upsert_wellbeing_log
from backend.services.user_service import get_or_create_user

from ..common import VIEW_HEALTH, _parse_iso_date, _render, router
from .builders import HEALTH_MODE_WELLBEING_ENERGY, HEALTH_MODE_WELLBEING_STRESS
from .state import _reset_health_mode


@router.callback_query(F.data == "wellbeing:start")
async def cb_wellbeing_start(callback: CallbackQuery, state) -> None:
    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=HEALTH_MODE_WELLBEING_ENERGY,
        pending_energy_level=None,
    )
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer("Оцени энергию")


@router.callback_query(F.data == "wellbeing:cancel")
async def cb_wellbeing_cancel(callback: CallbackQuery, state) -> None:
    await _reset_health_mode(state)
    await _render(from_user=callback.from_user, state=state, callback=callback, notice="Запись состояния отменена")
    await callback.answer()


@router.callback_query(F.data.startswith("wellbeing:energy:"))
async def cb_wellbeing_energy(callback: CallbackQuery, state) -> None:
    try:
        energy_level = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка")
        return

    if energy_level not in {1, 2, 3, 4, 5}:
        await callback.answer("Ошибка")
        return

    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=HEALTH_MODE_WELLBEING_STRESS,
        pending_energy_level=energy_level,
    )
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer("Оцени стресс")


@router.callback_query(F.data == "wellbeing:stress:back")
async def cb_wellbeing_stress_back(callback: CallbackQuery, state) -> None:
    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=HEALTH_MODE_WELLBEING_ENERGY,
    )
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data.startswith("wellbeing:stress:"))
async def cb_wellbeing_stress(callback: CallbackQuery, state) -> None:
    try:
        stress_level = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка")
        return

    if stress_level not in {1, 2, 3, 4, 5}:
        await callback.answer("Ошибка")
        return

    data = await state.get_data()
    energy_level = int(data.get("pending_energy_level") or 0)
    if energy_level not in {1, 2, 3, 4, 5}:
        await state.set_state(None)
        await state.update_data(
            view_mode=VIEW_HEALTH,
            health_mode=HEALTH_MODE_WELLBEING_ENERGY,
            pending_energy_level=None,
        )
        await _render(from_user=callback.from_user, state=state, callback=callback, notice="Сначала оцени энергию.")
        await callback.answer("Нет энергии")
        return

    selected_date = _parse_iso_date(data.get("selected_date"), date.today())

    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            last_name=callback.from_user.last_name,
        )
        await upsert_wellbeing_log(
            session=session,
            user_id=user.id,
            logged_date=selected_date,
            energy_level=energy_level,
            stress_level=stress_level,
        )

    await _reset_health_mode(state)
    await _render(
        from_user=callback.from_user,
        state=state,
        callback=callback,
        notice="\n".join(
            [
                "━━━━━━━━━━━━",
                "<b>✅ СОСТОЯНИЕ СОХРАНЕНО</b>",
                f"⚡ Энергия: <b>{energy_level}/5</b>",
                f"😵 Стресс: <b>{stress_level}/5</b>",
                "━━━━━━━━━━━━",
            ]
        ),
    )
    await callback.answer("Сохранено")
