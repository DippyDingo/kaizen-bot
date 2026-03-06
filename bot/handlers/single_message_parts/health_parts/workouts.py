from datetime import date, datetime

from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message

from backend.database import async_session
from backend.services.health_service import add_workout_log, remove_last_workout_log
from backend.services.user_service import get_or_create_user
from bot.states import DashboardStates

from ..common import VIEW_HEALTH, _parse_iso_date, _render, router
from .builders import HEALTH_MODE_WORKOUT_DURATION, HEALTH_MODE_WORKOUT_TYPE, WORKOUT_DURATION_OPTIONS, WORKOUT_TYPE_LABELS, WORKOUT_TYPE_SHORT, _format_minutes, _parse_workout_duration_input
from .state import _reset_health_mode


@router.callback_query(F.data == "workout:start")
async def cb_workout_start(callback: CallbackQuery, state) -> None:
    await state.set_state(None)
    await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_WORKOUT_TYPE, pending_workout_type=None)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer("Выбери тип")


@router.callback_query(F.data == "workout:cancel")
async def cb_workout_cancel(callback: CallbackQuery, state) -> None:
    await _reset_health_mode(state)
    await _render(from_user=callback.from_user, state=state, callback=callback, notice="Добавление тренировки отменено")
    await callback.answer()


@router.callback_query(F.data == "workout:back")
async def cb_workout_back(callback: CallbackQuery, state) -> None:
    await state.set_state(None)
    await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_WORKOUT_TYPE)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "workout:custom")
async def cb_workout_custom(callback: CallbackQuery, state) -> None:
    await state.set_state(DashboardStates.waiting_workout_duration_text)
    await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_WORKOUT_DURATION)
    await _render(from_user=callback.from_user, state=state, callback=callback, notice="Отправь длительность тренировки: 25 или 1:15")
    await callback.answer("Жду время")


@router.callback_query(F.data.startswith("workout:type:"))
async def cb_workout_type(callback: CallbackQuery, state) -> None:
    try:
        workout_type = callback.data.split(":", 2)[2]
    except IndexError:
        await callback.answer("Ошибка")
        return

    if workout_type not in WORKOUT_TYPE_LABELS:
        await callback.answer("Ошибка")
        return

    await state.set_state(None)
    await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_WORKOUT_DURATION, pending_workout_type=workout_type)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer("Выбери длительность")


@router.callback_query(F.data.startswith("workout:dur:"))
async def cb_workout_duration(callback: CallbackQuery, state) -> None:
    try:
        duration_min = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка")
        return

    if duration_min not in WORKOUT_DURATION_OPTIONS:
        await callback.answer("Ошибка")
        return

    data = await state.get_data()
    workout_type = str(data.get("pending_workout_type") or "")
    if workout_type not in WORKOUT_TYPE_LABELS:
        await state.update_data(health_mode=HEALTH_MODE_WORKOUT_TYPE, pending_workout_type=None)
        await _render(from_user=callback.from_user, state=state, callback=callback, notice="Сначала выбери тип тренировки.")
        await callback.answer("Нет типа")
        return

    selected_date = _parse_iso_date(data.get("selected_date"), date.today())
    logged_at = datetime.combine(selected_date, datetime.now().time())

    async with async_session() as session:
        user, _ = await get_or_create_user(session=session, telegram_id=callback.from_user.id, first_name=callback.from_user.first_name, username=callback.from_user.username, last_name=callback.from_user.last_name)
        _, level_ups = await add_workout_log(session, user, workout_type, duration_min, logged_at=logged_at)

    await _reset_health_mode(state)
    notice = f"Тренировка {WORKOUT_TYPE_SHORT[workout_type]} {_format_minutes(duration_min)} сохранена (+30 EXP)"
    if level_ups > 0:
        notice += f" | Уровень +{level_ups}"

    await _render(from_user=callback.from_user, state=state, callback=callback, notice=notice)
    await callback.answer("Тренировка записана")


@router.message(StateFilter(DashboardStates.waiting_workout_duration_text), F.text)
async def msg_workout_duration_text(message: Message, state) -> None:
    raw_text = (message.text or "").strip()
    duration_min = _parse_workout_duration_input(raw_text)

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    if duration_min is None:
        await _render(from_user=message.from_user, state=state, message=message, notice="Формат не распознан. Примеры: 25 или 1:15")
        return

    data = await state.get_data()
    workout_type = str(data.get("pending_workout_type") or "")
    if workout_type not in WORKOUT_TYPE_LABELS:
        await state.set_state(None)
        await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_WORKOUT_TYPE, pending_workout_type=None)
        await _render(from_user=message.from_user, state=state, message=message, notice="Сначала выбери тип тренировки.")
        return

    selected_date = _parse_iso_date(data.get("selected_date"), date.today())
    logged_at = datetime.combine(selected_date, datetime.now().time())

    async with async_session() as session:
        user, _ = await get_or_create_user(session=session, telegram_id=message.from_user.id, first_name=message.from_user.first_name, username=message.from_user.username, last_name=message.from_user.last_name)
        _, level_ups = await add_workout_log(session, user, workout_type, duration_min, logged_at=logged_at)

    await _reset_health_mode(state)
    notice = f"Тренировка {WORKOUT_TYPE_SHORT[workout_type]} {_format_minutes(duration_min)} сохранена (+30 EXP)"
    if level_ups > 0:
        notice += f" | Уровень +{level_ups}"

    await _render(from_user=message.from_user, state=state, message=message, notice=notice)


@router.callback_query(F.data == "workout:undo")
async def cb_workout_undo(callback: CallbackQuery, state) -> None:
    data = await state.get_data()
    selected_date = _parse_iso_date(data.get("selected_date"), date.today())

    async with async_session() as session:
        user, _ = await get_or_create_user(session=session, telegram_id=callback.from_user.id, first_name=callback.from_user.first_name, username=callback.from_user.username, last_name=callback.from_user.last_name)
        duration_min, level_change, workout_type = await remove_last_workout_log(session, user, selected_date)

    await _reset_health_mode(state)

    if duration_min is None:
        await _render(from_user=callback.from_user, state=state, callback=callback, notice="За выбранный день нечего откатывать по тренировкам.")
        await callback.answer("Пусто")
        return

    workout_label = WORKOUT_TYPE_SHORT.get(workout_type or "", "тренировка")
    notice = f"Убрана тренировка {workout_label} {_format_minutes(duration_min)} (-30 EXP)"
    if level_change < 0:
        notice += f" | Уровень {level_change}"

    await _render(from_user=callback.from_user, state=state, callback=callback, notice=notice)
    await callback.answer("Тренировка отменена")
