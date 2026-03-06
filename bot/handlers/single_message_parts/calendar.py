from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from bot.states import DashboardStates

from .common import (
    MONTH_NAMES,
    VIEW_CALENDAR,
    VIEW_DIARY,
    VIEW_TASKS,
    WEEKDAY_LABELS,
    _back_row,
    _month_start,
    _next_month,
    _parse_iso_date,
    _prev_month,
    _render,
    router,
)


def _build_calendar_keyboard(month_date: date, selected_date: date, context: str) -> InlineKeyboardMarkup:
    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdayscalendar(month_date.year, month_date.month)

    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=f"{MONTH_NAMES[month_date.month]} {month_date.year}",
                callback_data="cal:noop",
            )
        ],
        [InlineKeyboardButton(text=w, callback_data="cal:noop") for w in WEEKDAY_LABELS],
    ]

    today = date.today()
    for week in weeks:
        row: list[InlineKeyboardButton] = []
        for day_num in week:
            if day_num == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="cal:noop"))
                continue

            day_date = date(month_date.year, month_date.month, day_num)
            text = str(day_num)
            if day_date == selected_date:
                text = f"🔘{day_num}"
            elif day_date == today:
                text = f"◦{day_num}"

            row.append(
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"cal:pick:{context}:{day_date.isoformat()}",
                )
            )
        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton(
                text="◀️ Месяц",
                callback_data=f"cal:nav:{context}:{_prev_month(month_date).isoformat()}",
            ),
            InlineKeyboardButton(
                text="Месяц ▶️",
                callback_data=f"cal:nav:{context}:{_next_month(month_date).isoformat()}",
            ),
        ]
    )

    if context == "create":
        rows.append(
            [
                InlineKeyboardButton(text="Сегодня", callback_data="cal:today:create"),
                InlineKeyboardButton(text="↩️ Отмена", callback_data="task:cancel"),
            ]
        )
    elif context == "browse":
        rows.append([InlineKeyboardButton(text="Сегодня", callback_data="cal:today:browse")])
        rows.append([InlineKeyboardButton(text="📋 Открыть задачи даты", callback_data="cal:to_tasks")])
        rows.append(_back_row())
    elif context == "diary":
        rows.append([InlineKeyboardButton(text="Сегодня", callback_data="cal:today:diary")])
        rows.append([InlineKeyboardButton(text="📝 Открыть записи даты", callback_data="cal:to_diary")])
        rows.append([InlineKeyboardButton(text="↩️ Назад в дневник", callback_data="diary:close_calendar")])
    else:
        rows.append(_back_row())

    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_calendar_text(selected_date: date, notice: str | None) -> str:
    lines = [
        "<b>📅 КАЛЕНДАРЬ</b>",
        f"Выбранная дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>",
        "Выбери дату и нажми «Открыть задачи даты».",
    ]
    if notice:
        lines.extend(["", f"ℹ️ {notice}"])
    return "\n".join(lines)


def _build_diary_calendar_text(selected_date: date, notice: str | None) -> str:
    lines = [
        "<b>📅 КАЛЕНДАРЬ ДНЕВНИКА</b>",
        f"Выбранная дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>",
        "Выбери день и нажми «Открыть записи даты».",
    ]
    if notice:
        lines.extend(["", f"ℹ️ {notice}"])
    return "\n".join(lines)


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

    if context == "create":
        from .tasks import _finalize_task

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

    if context == "diary":
        await state.update_data(selected_date=picked_date.isoformat(), view_mode=VIEW_DIARY, diary_calendar_mode=True)
        await _render(from_user=callback.from_user, state=state, callback=callback, notice=f"Выбрана дата {picked_date.strftime('%d.%m.%Y')}")
        await callback.answer()
        return

    if context == "create":
        from .tasks import _finalize_task

        await _finalize_task(callback, state, task_date=picked_date)
        return

    await callback.answer("Ошибка")


@router.callback_query(F.data == "cal:to_tasks")
async def cb_cal_to_tasks(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(view_mode=VIEW_TASKS, diary_calendar_mode=False)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "cal:to_diary")
async def cb_cal_to_diary(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(view_mode=VIEW_DIARY, diary_calendar_mode=False)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()
