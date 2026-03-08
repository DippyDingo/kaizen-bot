from datetime import date

from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message

from backend.database import async_session
from backend.services.health_service import archive_medication_course, create_medication_course, toggle_medication_intake_status
from backend.services.user_service import get_or_create_user
from bot.states import DashboardStates

from ..common import VIEW_HEALTH, _parse_iso_date, _render, router
from .builders import (
    HEALTH_MODE_MEDICATIONS,
    HEALTH_MODE_MEDICATION_CALENDAR,
    HEALTH_MODE_MEDICATION_TITLE,
    HEALTH_MODE_MEDICATION_DOSE,
    HEALTH_MODE_MEDICATION_TIME,
    HEALTH_MODE_MEDICATION_DAYS,
    _parse_medication_days_input,
    _parse_medication_time_input,
    _short_medication,
)


def _summary_mode_from_data(data: dict) -> str:
    raw = data.get("health_summary_mode")
    return str(raw) if raw in {"summary_day", "summary_week"} else "summary_day"


@router.callback_query(F.data == "med:plan:start")
async def cb_med_start(callback: CallbackQuery, state) -> None:
    data = await state.get_data()
    await state.set_state(DashboardStates.waiting_medication_title)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=HEALTH_MODE_MEDICATION_TITLE,
        health_summary_mode=_summary_mode_from_data(data),
        pending_medication_title=None,
        pending_medication_dose=None,
        pending_medication_time=None,
    )
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer("Жду название")


@router.callback_query(F.data == "med:cancel")
async def cb_med_cancel(callback: CallbackQuery, state) -> None:
    data = await state.get_data()
    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=HEALTH_MODE_MEDICATIONS,
        health_summary_mode=_summary_mode_from_data(data),
        pending_medication_title=None,
        pending_medication_dose=None,
        pending_medication_time=None,
    )
    await _render(from_user=callback.from_user, state=state, callback=callback, notice="Создание курса отменено")
    await callback.answer()


@router.callback_query(F.data == "med:back")
async def cb_med_back(callback: CallbackQuery, state) -> None:
    await state.set_state(DashboardStates.waiting_medication_title)
    await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_MEDICATION_TITLE)
    await _render(from_user=callback.from_user, state=state, callback=callback, notice="Измени название лекарства.")
    await callback.answer()


@router.callback_query(F.data == "med:time:back")
async def cb_med_time_back(callback: CallbackQuery, state) -> None:
    await state.set_state(DashboardStates.waiting_medication_dose)
    await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_MEDICATION_DOSE)
    await _render(from_user=callback.from_user, state=state, callback=callback, notice="Измени дозу.")
    await callback.answer()


@router.callback_query(F.data == "med:days:back")
async def cb_med_days_back(callback: CallbackQuery, state) -> None:
    await state.set_state(None)
    await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_MEDICATION_TIME)
    await _render(from_user=callback.from_user, state=state, callback=callback, notice="Измени время приёма.")
    await callback.answer()


@router.message(StateFilter(DashboardStates.waiting_medication_title), F.text)
async def msg_medication_title(message: Message, state) -> None:
    title = (message.text or "").strip()
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    if len(title) < 2:
        await _render(from_user=message.from_user, state=state, message=message, notice="Название слишком короткое. Пример: Магний")
        return

    await state.set_state(DashboardStates.waiting_medication_dose)
    await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_MEDICATION_DOSE, pending_medication_title=title[:120])
    await _render(from_user=message.from_user, state=state, message=message, notice=f"Лекарство: {_short_medication(title)}. Теперь укажи дозу.")


@router.message(StateFilter(DashboardStates.waiting_medication_dose), F.text)
async def msg_medication_dose(message: Message, state) -> None:
    dose = (message.text or "").strip()
    data = await state.get_data()
    title = str(data.get("pending_medication_title") or "").strip()
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    if not title:
        await state.set_state(DashboardStates.waiting_medication_title)
        await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_MEDICATION_TITLE)
        await _render(from_user=message.from_user, state=state, message=message, notice="Сначала укажи название лекарства.")
        return

    if len(dose) < 1:
        await _render(from_user=message.from_user, state=state, message=message, notice="Укажи дозу. Пример: 1 таблетка")
        return

    await state.set_state(None)
    await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_MEDICATION_TIME, pending_medication_title=title, pending_medication_dose=dose[:120])
    await _render(from_user=message.from_user, state=state, message=message, notice=f"Доза сохранена: {dose[:40]}. Теперь выбери время приёма.")


@router.callback_query(F.data.startswith("med:time:"))
async def cb_med_time(callback: CallbackQuery, state) -> None:
    suffix = callback.data.split(":", 2)[2]
    if suffix == "custom":
        await state.set_state(DashboardStates.waiting_medication_time_text)
        await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_MEDICATION_TIME)
        await _render(from_user=callback.from_user, state=state, callback=callback, notice="Отправь время приёма в формате 08:30")
        await callback.answer("Жду время")
        return

    parsed_time = _parse_medication_time_input(suffix)
    if parsed_time is None:
        await callback.answer("Ошибка времени")
        return

    await state.set_state(None)
    await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_MEDICATION_DAYS, pending_medication_time=parsed_time.strftime("%H:%M"))
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer("Выбери дни")


@router.message(StateFilter(DashboardStates.waiting_medication_time_text), F.text)
async def msg_medication_time_text(message: Message, state) -> None:
    parsed_time = _parse_medication_time_input(message.text or "")
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    if parsed_time is None:
        await _render(from_user=message.from_user, state=state, message=message, notice="Формат времени не распознан. Пример: 08:30")
        return

    await state.set_state(None)
    await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_MEDICATION_DAYS, pending_medication_time=parsed_time.strftime("%H:%M"))
    await _render(from_user=message.from_user, state=state, message=message, notice="Теперь выбери длительность курса.")


@router.callback_query(F.data.startswith("med:days:"))
async def cb_med_days(callback: CallbackQuery, state) -> None:
    suffix = callback.data.split(":", 2)[2]
    if suffix == "custom":
        await state.set_state(DashboardStates.waiting_medication_days_text)
        await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_MEDICATION_DAYS)
        await _render(from_user=callback.from_user, state=state, callback=callback, notice="Отправь количество дней. Пример: 10")
        await callback.answer("Жду число")
        return

    days_count = _parse_medication_days_input(suffix)
    if days_count is None:
        await callback.answer("Ошибка")
        return

    await _finalize_medication_course(callback.from_user, state, callback=callback, days_count=days_count)
    await callback.answer("Курс создан")


@router.message(StateFilter(DashboardStates.waiting_medication_days_text), F.text)
async def msg_medication_days_text(message: Message, state) -> None:
    days_count = _parse_medication_days_input(message.text or "")
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    if days_count is None:
        await _render(from_user=message.from_user, state=state, message=message, notice="Нужно число дней. Пример: 10")
        return

    await _finalize_medication_course(message.from_user, state, message=message, days_count=days_count)


async def _finalize_medication_course(from_user, state, *, days_count: int, callback: CallbackQuery | None = None, message: Message | None = None) -> None:
    data = await state.get_data()
    title = str(data.get("pending_medication_title") or "").strip()
    dose = str(data.get("pending_medication_dose") or "").strip()
    intake_time_raw = str(data.get("pending_medication_time") or "").strip()
    selected_date = _parse_iso_date(data.get("selected_date"), date.today())
    intake_time = _parse_medication_time_input(intake_time_raw)

    if not title or not dose or intake_time is None:
        await state.set_state(DashboardStates.waiting_medication_title)
        await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_MEDICATION_TITLE)
        await _render(from_user=from_user, state=state, callback=callback, message=message, notice="Не хватает данных для курса. Начни заново.")
        return

    async with async_session() as session:
        user, _ = await get_or_create_user(session=session, telegram_id=from_user.id, first_name=from_user.first_name, username=from_user.username, last_name=from_user.last_name)
        course = await create_medication_course(
            session=session,
            user=user,
            title=title[:120],
            dose=dose[:120],
            intake_time=intake_time,
            start_date=selected_date,
            days_count=days_count,
        )

    await state.set_state(None)
    await state.update_data(
        view_mode=VIEW_HEALTH,
        health_mode=HEALTH_MODE_MEDICATIONS,
        pending_medication_title=None,
        pending_medication_dose=None,
        pending_medication_time=None,
    )
    await _render(from_user=from_user, state=state, callback=callback, message=message, notice=f"Курс {_short_medication(course.title)} создан: {course.intake_time.strftime('%H:%M')} | {days_count} дн.")


@router.callback_query(F.data == "med:calendar")
async def cb_med_calendar(callback: CallbackQuery, state) -> None:
    await state.set_state(None)
    await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_MEDICATION_CALENDAR)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "med:close")
async def cb_med_close(callback: CallbackQuery, state) -> None:
    data = await state.get_data()
    await state.set_state(None)
    await state.update_data(view_mode=VIEW_HEALTH, health_mode=_summary_mode_from_data(data))
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "med:close_calendar")
async def cb_med_close_calendar(callback: CallbackQuery, state) -> None:
    await state.set_state(None)
    await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_MEDICATIONS)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data.startswith("med:toggle:"))
async def cb_med_toggle(callback: CallbackQuery, state) -> None:
    try:
        _, _, course_id_raw, status = callback.data.split(":", 3)
        course_id = int(course_id_raw)
    except (ValueError, IndexError):
        await callback.answer("Ошибка")
        return

    data = await state.get_data()
    selected_date = _parse_iso_date(data.get("selected_date"), date.today())

    async with async_session() as session:
        user, _ = await get_or_create_user(session=session, telegram_id=callback.from_user.id, first_name=callback.from_user.first_name, username=callback.from_user.username, last_name=callback.from_user.last_name)
        result_status, course, level_change = await toggle_medication_intake_status(session, user, course_id, selected_date, status)

    if course is None or result_status is None:
        await callback.answer("Курс не найден")
        return

    await state.set_state(None)
    await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_MEDICATIONS)
    if result_status == "taken":
        notice = f"{_short_medication(course.title)} отмечено как выпито (+10 EXP)"
        if level_change > 0:
            notice += f" | Уровень +{level_change}"
    else:
        notice = f"Отметка {_short_medication(course.title)} снята. Сейчас это считается пропуском"
        if level_change < 0:
            notice += f" | Уровень {level_change}"

    await _render(from_user=callback.from_user, state=state, callback=callback, notice=notice)
    await callback.answer()


@router.callback_query(F.data.startswith("med:delete:"))
async def cb_med_delete(callback: CallbackQuery, state) -> None:
    try:
        course_id = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка")
        return

    async with async_session() as session:
        user, _ = await get_or_create_user(session=session, telegram_id=callback.from_user.id, first_name=callback.from_user.first_name, username=callback.from_user.username, last_name=callback.from_user.last_name)
        deleted = await archive_medication_course(session, user, course_id)

    if not deleted:
        await callback.answer("Курс не найден")
        return

    await state.set_state(None)
    await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_MEDICATIONS)
    await _render(from_user=callback.from_user, state=state, callback=callback, notice="Курс лекарства отключен")
    await callback.answer("Удалено")


@router.callback_query(F.data.startswith("med:item:"))
async def cb_med_item(callback: CallbackQuery) -> None:
    await callback.answer("Используй кнопки ниже: выпил, пропуск или удалить курс.")

