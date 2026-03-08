from datetime import date, datetime

from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message

from backend.database import async_session
from backend.services.health_service import add_sleep_log, remove_last_sleep_log
from backend.services.user_service import get_or_create_user
from bot.states import DashboardStates

from ..common import VIEW_HEALTH, _parse_iso_date, _render, router
from .builders import (
    HEALTH_MODE_SLEEP_DURATION,
    HEALTH_MODE_SLEEP_EXACT,
    HEALTH_MODE_SLEEP_PANEL,
    HEALTH_MODE_SLEEP_QUALITY,
    SLEEP_DURATION_OPTIONS,
    SLEEP_QUALITY_LABELS,
    _build_sleep_datetimes,
    _parse_exact_sleep_input,
    _sleep_duration_label,
)
from .state import _reset_health_mode, _resolve_health_summary_mode


def _sleep_return_mode_from_data(data: dict) -> str:
    if data.get("health_mode") == HEALTH_MODE_SLEEP_PANEL:
        return HEALTH_MODE_SLEEP_PANEL
    if data.get("health_return_mode") == HEALTH_MODE_SLEEP_PANEL:
        return HEALTH_MODE_SLEEP_PANEL
    return _resolve_health_summary_mode(data)


@router.callback_query(F.data == "sleep:start")
async def cb_sleep_start(callback: CallbackQuery, state) -> None:
    data = await state.get_data()
    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=HEALTH_MODE_SLEEP_DURATION,
        health_return_mode=_sleep_return_mode_from_data(data),
        pending_sleep_minutes=None,
        pending_sleep_exact_fell=None,
        pending_sleep_exact_wake=None,
        pending_workout_type=None,
    )
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer("Выбери длительность")


@router.callback_query(F.data == "sleep:cancel")
async def cb_sleep_cancel(callback: CallbackQuery, state) -> None:
    await _reset_health_mode(state)
    await _render(from_user=callback.from_user, state=state, callback=callback, notice="Запись сна отменена")
    await callback.answer()


@router.callback_query(F.data == "sleep:back")
async def cb_sleep_back(callback: CallbackQuery, state) -> None:
    data = await state.get_data()
    if data.get("pending_sleep_exact_fell") and data.get("pending_sleep_exact_wake"):
        await state.set_state(DashboardStates.waiting_sleep_exact_time)
        await state.update_data(
            view_mode=VIEW_HEALTH,
            health_mode=HEALTH_MODE_SLEEP_EXACT,
            pending_sleep_minutes=None,
            pending_sleep_exact_fell=None,
            pending_sleep_exact_wake=None,
        )
    else:
        await state.set_state(None)
        await state.update_data(
            view_mode=VIEW_HEALTH,
            health_mode=HEALTH_MODE_SLEEP_DURATION,
            health_return_mode=_sleep_return_mode_from_data(data),
            pending_sleep_exact_fell=None,
            pending_sleep_exact_wake=None,
        )
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "sleep:exact")
async def cb_sleep_exact(callback: CallbackQuery, state) -> None:
    data = await state.get_data()
    await state.set_state(DashboardStates.waiting_sleep_exact_time)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=HEALTH_MODE_SLEEP_EXACT,
        health_return_mode=_sleep_return_mode_from_data(data),
        pending_sleep_minutes=None,
        pending_sleep_exact_fell=None,
        pending_sleep_exact_wake=None,
    )
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer("Жду время")


@router.callback_query(F.data == "sleep:exact:cancel")
async def cb_sleep_exact_cancel(callback: CallbackQuery, state) -> None:
    data = await state.get_data()
    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=HEALTH_MODE_SLEEP_DURATION,
        health_return_mode=_sleep_return_mode_from_data(data),
        pending_sleep_minutes=None,
        pending_sleep_exact_fell=None,
        pending_sleep_exact_wake=None,
    )
    await _render(from_user=callback.from_user, state=state, callback=callback, notice="Точный ввод сна отменен")
    await callback.answer()


@router.callback_query(F.data.startswith("sleep:dur:"))
async def cb_sleep_duration(callback: CallbackQuery, state) -> None:
    try:
        duration_minutes = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка")
        return

    if duration_minutes not in SLEEP_DURATION_OPTIONS:
        await callback.answer("Ошибка")
        return

    data = await state.get_data()
    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=HEALTH_MODE_SLEEP_QUALITY,
        health_return_mode=_sleep_return_mode_from_data(data),
        pending_sleep_minutes=duration_minutes,
        pending_sleep_exact_fell=None,
        pending_sleep_exact_wake=None,
    )
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer("Оцени качество")


@router.callback_query(F.data.startswith("sleep:quality:"))
async def cb_sleep_quality(callback: CallbackQuery, state) -> None:
    try:
        quality = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка")
        return

    if quality not in SLEEP_QUALITY_LABELS:
        await callback.answer("Ошибка")
        return

    data = await state.get_data()
    exact_fell_raw = data.get("pending_sleep_exact_fell")
    exact_wake_raw = data.get("pending_sleep_exact_wake")
    if exact_fell_raw and exact_wake_raw:
        fell_asleep_at = datetime.fromisoformat(exact_fell_raw)
        woke_up_at = datetime.fromisoformat(exact_wake_raw)
        duration_minutes = int((woke_up_at - fell_asleep_at).total_seconds() // 60)
    else:
        duration_minutes = int(data.get("pending_sleep_minutes") or 0)
        if duration_minutes not in SLEEP_DURATION_OPTIONS:
            await state.update_data(health_mode=HEALTH_MODE_SLEEP_DURATION, pending_sleep_minutes=None)
            await _render(from_user=callback.from_user, state=state, callback=callback, notice="Сначала выбери длительность сна.")
            await callback.answer("Нет длительности")
            return

        selected_date = _parse_iso_date(data.get("selected_date"), date.today())
        fell_asleep_at, woke_up_at = _build_sleep_datetimes(selected_date, duration_minutes)

    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            last_name=callback.from_user.last_name,
        )
        _, level_ups = await add_sleep_log(session, user, fell_asleep_at=fell_asleep_at, woke_up_at=woke_up_at, quality=quality)

    await _reset_health_mode(state)
    notice = f"Сон {_sleep_duration_label(duration_minutes)} сохранен, качество {quality}/5 (+20 EXP)"
    if level_ups > 0:
        notice += f" | Уровень +{level_ups}"

    await _render(from_user=callback.from_user, state=state, callback=callback, notice=notice)
    await callback.answer("Сон записан")


@router.message(StateFilter(DashboardStates.waiting_sleep_exact_time), F.text)
async def msg_sleep_exact_time(message: Message, state) -> None:
    raw_text = (message.text or "").strip()
    data = await state.get_data()
    selected_date = _parse_iso_date(data.get("selected_date"), date.today())
    parsed = _parse_exact_sleep_input(raw_text, selected_date)

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    if parsed is None:
        await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_SLEEP_EXACT, pending_sleep_exact_fell=None, pending_sleep_exact_wake=None)
        await _render(from_user=message.from_user, state=state, message=message, notice="Формат не распознан. Пример: 23:40 07:15")
        return

    fell_asleep_at, woke_up_at = parsed
    duration_minutes = int((woke_up_at - fell_asleep_at).total_seconds() // 60)
    if duration_minutes <= 0:
        await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_SLEEP_EXACT, pending_sleep_exact_fell=None, pending_sleep_exact_wake=None)
        await _render(from_user=message.from_user, state=state, message=message, notice="Подъём должен быть позже засыпания.")
        return

    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=HEALTH_MODE_SLEEP_QUALITY,
        health_return_mode=_sleep_return_mode_from_data(data),
        pending_sleep_minutes=duration_minutes,
        pending_sleep_exact_fell=fell_asleep_at.isoformat(),
        pending_sleep_exact_wake=woke_up_at.isoformat(),
    )
    await _render(from_user=message.from_user, state=state, message=message, notice=f"Время сна: {fell_asleep_at.strftime('%H:%M')} -> {woke_up_at.strftime('%H:%M')}. Теперь оцени качество.")


@router.callback_query(F.data == "sleep:undo")
async def cb_sleep_undo(callback: CallbackQuery, state) -> None:
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
        duration_minutes, level_change, quality = await remove_last_sleep_log(session, user, selected_date)

    await _reset_health_mode(state)

    if duration_minutes is None:
        await _render(from_user=callback.from_user, state=state, callback=callback, notice="За выбранный день нечего откатывать по сну.")
        await callback.answer("Пусто")
        return

    notice = f"Убран сон {_sleep_duration_label(duration_minutes)}"
    if quality is not None:
        notice += f", качество {quality}/5"
    notice += " (-20 EXP)"
    if level_change < 0:
        notice += f" | Уровень {level_change}"

    await _render(from_user=callback.from_user, state=state, callback=callback, notice=notice)
    await callback.answer("Сон отменен")
