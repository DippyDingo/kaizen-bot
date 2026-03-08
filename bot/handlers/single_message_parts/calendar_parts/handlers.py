from __future__ import annotations

from datetime import date, datetime, timedelta

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.states import DashboardStates

from ..common import VIEW_CALENDAR, VIEW_DIARY, VIEW_HEALTH, VIEW_TASKS, _month_start, _parse_iso_date, _render, router


@router.callback_query(F.data.startswith("date:shift:"))
async def cb_shift_date(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        delta = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка даты")
        return

    data = await state.get_data()
    selected_date = _parse_iso_date(data.get("selected_date"), date.today()) + timedelta(days=delta)
    await state.update_data(selected_date=selected_date.isoformat(), calendar_month=_month_start(selected_date).isoformat())
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data.startswith("cal:nav:"))
async def cb_cal_nav(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        _, _, context, month_iso = callback.data.split(":", 3)
        month_date = _month_start(datetime.strptime(month_iso, "%Y-%m-%d").date())
    except ValueError:
        await callback.answer("Ошибка календаря")
        return

    await state.update_data(calendar_month=month_date.isoformat())

    if context == "browse":
        await state.update_data(view_mode=VIEW_CALENDAR, diary_calendar_mode=False)
    elif context == "diary":
        await state.update_data(view_mode=VIEW_DIARY, diary_calendar_mode=True)
    elif context == "tasks":
        await state.update_data(view_mode=VIEW_TASKS, task_calendar_mode=True)
    elif context == "med":
        from ..health import HEALTH_MODE_MEDICATION_CALENDAR

        await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_MEDICATION_CALENDAR)
    else:
        await state.set_state(DashboardStates.waiting_task_date)

    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data.startswith("cal:today:"))
async def cb_cal_today(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        context = callback.data.split(":", 2)[2]
    except IndexError:
        await callback.answer("Ошибка")
        return

    today = date.today()

    if context == "browse":
        await state.update_data(
            selected_date=today.isoformat(),
            calendar_month=_month_start(today).isoformat(),
            view_mode=VIEW_CALENDAR,
            diary_calendar_mode=False,
        )
        await _render(from_user=callback.from_user, state=state, callback=callback, notice=f"Выбрана дата {today.strftime('%d.%m.%Y')}")
        await callback.answer()
        return

    if context == "tasks":
        await state.update_data(
            selected_date=today.isoformat(),
            calendar_month=_month_start(today).isoformat(),
            view_mode=VIEW_TASKS,
            task_calendar_mode=False,
        )
        await _render(from_user=callback.from_user, state=state, callback=callback, notice=f"Выбрана дата {today.strftime('%d.%m.%Y')}")
        await callback.answer()
        return

    if context == "diary":
        await state.update_data(
            selected_date=today.isoformat(),
            calendar_month=_month_start(today).isoformat(),
            view_mode=VIEW_DIARY,
            diary_calendar_mode=True,
        )
        await _render(from_user=callback.from_user, state=state, callback=callback, notice=f"Выбрана дата {today.strftime('%d.%m.%Y')}")
        await callback.answer()
        return

    if context == "med":
        from ..health import HEALTH_MODE_MEDICATIONS

        await state.update_data(
            selected_date=today.isoformat(),
            calendar_month=_month_start(today).isoformat(),
            view_mode=VIEW_HEALTH,
            health_mode=HEALTH_MODE_MEDICATIONS,
        )
        await _render(from_user=callback.from_user, state=state, callback=callback, notice=f"Выбрана дата {today.strftime('%d.%m.%Y')}")
        await callback.answer()
        return

    if context == "create":
        from ..tasks import _finalize_task

        await _finalize_task(callback, state, task_date=today)
        return

    await callback.answer("Ошибка")


@router.callback_query(F.data.startswith("cal:pick:"))
async def cb_cal_pick(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        _, _, context, picked_iso = callback.data.split(":", 3)
        picked_date = datetime.strptime(picked_iso, "%Y-%m-%d").date()
    except ValueError:
        await callback.answer("Ошибка даты")
        return

    if context == "browse":
        await state.update_data(selected_date=picked_date.isoformat(), view_mode=VIEW_CALENDAR, diary_calendar_mode=False)
        await _render(from_user=callback.from_user, state=state, callback=callback, notice=f"Выбрана дата {picked_date.strftime('%d.%m.%Y')}")
        await callback.answer()
        return

    if context == "tasks":
        await state.update_data(
            selected_date=picked_date.isoformat(),
            calendar_month=_month_start(picked_date).isoformat(),
            view_mode=VIEW_TASKS,
            task_calendar_mode=False,
        )
        await _render(from_user=callback.from_user, state=state, callback=callback, notice=f"Выбрана дата {picked_date.strftime('%d.%m.%Y')}")
        await callback.answer()
        return

    if context == "diary":
        await state.update_data(selected_date=picked_date.isoformat(), view_mode=VIEW_DIARY, diary_calendar_mode=True)
        await _render(from_user=callback.from_user, state=state, callback=callback, notice=f"Выбрана дата {picked_date.strftime('%d.%m.%Y')}")
        await callback.answer()
        return

    if context == "med":
        from ..health import HEALTH_MODE_MEDICATIONS

        await state.update_data(
            selected_date=picked_date.isoformat(),
            view_mode=VIEW_HEALTH,
            health_mode=HEALTH_MODE_MEDICATIONS,
        )
        await _render(from_user=callback.from_user, state=state, callback=callback, notice=f"Выбрана дата {picked_date.strftime('%d.%m.%Y')}")
        await callback.answer()
        return

    if context == "create":
        from ..tasks import _finalize_task

        await _finalize_task(callback, state, task_date=picked_date)
        return

    await callback.answer("Ошибка")


@router.callback_query(F.data == "cal:to_diary")
async def cb_cal_to_diary(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(view_mode=VIEW_DIARY, diary_calendar_mode=False)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "cal:to_tasks")
async def cb_cal_to_tasks(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(view_mode=VIEW_TASKS, task_calendar_mode=False)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "cal:to_med")
async def cb_cal_to_med(callback: CallbackQuery, state: FSMContext) -> None:
    from ..health import HEALTH_MODE_MEDICATIONS

    await state.update_data(view_mode=VIEW_HEALTH, health_mode=HEALTH_MODE_MEDICATIONS)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()
