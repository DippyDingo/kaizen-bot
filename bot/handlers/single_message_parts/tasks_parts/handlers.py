from __future__ import annotations

from datetime import date

from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from backend.database import async_session
from backend.services.task_service import create_task, delete_task, toggle_task_done
from backend.services.user_service import get_or_create_user
from bot.states import DashboardStates

from ..common import PRIORITY_TEXT, VIEW_HOME, VIEW_TASKS, _month_start, _parse_iso_date, _render, _reset_context, router


async def _finalize_task(callback: CallbackQuery, state: FSMContext, task_date: date) -> None:
    data = await state.get_data()
    title = (data.get("pending_task_title") or "").strip()
    priority = data.get("pending_task_priority")
    target_view = data.get("task_origin_view", VIEW_TASKS)

    if not title or priority not in PRIORITY_TEXT:
        await _reset_context(state, view_mode=target_view)
        await _render(from_user=callback.from_user, state=state, callback=callback, notice="Не удалось создать задачу")
        await callback.answer()
        return

    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            last_name=callback.from_user.last_name,
        )
        task = await create_task(session=session, user=user, title=title, task_date=task_date, priority=priority)

    await state.clear()
    await state.update_data(
        selected_date=task_date.isoformat(),
        calendar_month=_month_start(task_date).isoformat(),
        view_mode=target_view,
    )
    await _render(
        from_user=callback.from_user,
        state=state,
        callback=callback,
        notice=f"Задача #{task.id} добавлена на {task_date.strftime('%d.%m.%Y')}",
    )
    await callback.answer("Сохранено")


@router.callback_query(F.data == "task:add")
async def cb_task_add(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    origin_view = data.get("view_mode", VIEW_TASKS)
    if origin_view not in {VIEW_HOME, VIEW_TASKS}:
        origin_view = VIEW_TASKS
    selected_date, calendar_month, _ = await _reset_context(state, view_mode=origin_view)
    await state.set_state(DashboardStates.waiting_task_title)
    await state.update_data(
        selected_date=selected_date.isoformat(),
        calendar_month=calendar_month.isoformat(),
        view_mode=origin_view,
        task_origin_view=origin_view,
    )
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer("Введи название")


@router.callback_query(F.data == "task:cancel")
async def cb_task_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    target_view = data.get("task_origin_view", VIEW_TASKS)
    await _reset_context(state, view_mode=target_view)
    await _render(from_user=callback.from_user, state=state, callback=callback, notice="Добавление отменено")
    await callback.answer()


@router.message(StateFilter(DashboardStates.waiting_task_title), F.text)
async def msg_task_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await _render(from_user=message.from_user, state=state, message=message, notice="Пустое название")
        return

    await state.update_data(pending_task_title=title)
    await state.set_state(DashboardStates.waiting_task_priority)

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await _render(from_user=message.from_user, state=state, message=message)


@router.callback_query(StateFilter(DashboardStates.waiting_task_priority), F.data.startswith("task:prio:"))
async def cb_task_priority(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        priority = callback.data.split(":", 2)[2]
    except IndexError:
        await callback.answer("Ошибка")
        return

    if priority not in PRIORITY_TEXT:
        await callback.answer("Ошибка")
        return

    data = await state.get_data()
    selected_date = _parse_iso_date(data.get("selected_date"), date.today())
    await state.update_data(pending_task_priority=priority, calendar_month=_month_start(selected_date).isoformat())
    await state.set_state(DashboardStates.waiting_task_date)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer("Выбери дату")


@router.callback_query(F.data.startswith("task:toggle:"))
async def cb_task_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        task_id = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка")
        return

    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            last_name=callback.from_user.last_name,
        )
        task, is_done_now, level_change = await toggle_task_done(session, user, task_id)

    if not task:
        await _render(from_user=callback.from_user, state=state, callback=callback, notice="Задача не найдена")
        await callback.answer()
        return

    if is_done_now:
        notice = f"Задача #{task.id} выполнена (+10 EXP)"
    else:
        notice = f"Выполнение задачи #{task.id} снято (-10 EXP)"

    if level_change > 0:
        notice += f" | Уровень +{level_change}"
    elif level_change < 0:
        notice += f" | Уровень {level_change}"

    await _render(from_user=callback.from_user, state=state, callback=callback, notice=notice)
    await callback.answer("Обновлено")


@router.callback_query(F.data.startswith("task:drop:"))
async def cb_task_drop(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        task_id = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка")
        return

    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            last_name=callback.from_user.last_name,
        )
        deleted = await delete_task(session, user, task_id)

    await _render(
        from_user=callback.from_user,
        state=state,
        callback=callback,
        notice=f"Задача #{task_id} удалена" if deleted else "Задача не найдена",
    )
    await callback.answer()
