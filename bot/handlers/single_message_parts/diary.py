from __future__ import annotations

from datetime import date, datetime

from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from backend.database import async_session
from backend.services.diary_service import add_diary_entry, get_user_diary_entry, list_day_diary_entries
from backend.services.user_service import get_or_create_user
from bot.states import DashboardStates

from .common import (
    VIEW_DIARY,
    _back_row,
    _build_diary_entry_preview,
    _clear_output_messages,
    _date_nav_row,
    _diary_type_label,
    _extract_diary_payload,
    _month_start,
    _parse_iso_date,
    _remember_output_message,
    _render,
    _reset_context,
    _send_diary_entry_to_chat,
    router,
)


def _build_diary_keyboard(selected_date: date, entries: list) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        _date_nav_row(selected_date),
        [
            InlineKeyboardButton(text="➕ Запись", callback_data="diary:add"),
            InlineKeyboardButton(text="📅 Календарь", callback_data="diary:calendar"),
        ],
        [
            InlineKeyboardButton(text="📤 Всё", callback_data="diary:dumpday"),
            InlineKeyboardButton(text="🧹 Чат", callback_data="diary:clearout"),
        ],
    ]

    for entry in entries[:8]:
        label = _diary_type_label(getattr(entry, "entry_type", "text")).replace(" ", "")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"👁 {entry.created_at.strftime('%H:%M')} {label}",
                    callback_data=f"diary:view:{entry.id}",
                )
            ]
        )

    rows.append(_back_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_diary_text(
    entries: list,
    selected_date: date,
    mode: str,
    notice: str | None,
    total_count: int | None = None,
) -> str:
    resolved_count = total_count if total_count is not None else len(entries)
    lines = [
        "<b>📝 ДНЕВНИК</b>",
        f"Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>",
        f"Записей за день: <b>{resolved_count}</b>",
    ]

    if mode == "wait_text":
        lines.extend(["", "Отправь текст, кружок, голосовое, фото или видео."])
    else:
        lines.extend(
            [
                "",
                "➕ добавить, 👁 открыть, 📤 показать день, 🧹 очистить чат.",
            ]
        )

    if entries:
        lines.extend(["", "<b>Последние записи:</b>"])
        for entry in entries[:10]:
            preview = _build_diary_entry_preview(entry)
            lines.append(f"• <b>{entry.created_at.strftime('%H:%M')}</b> — {preview}")
    else:
        lines.extend(["", "Записей за эту дату пока нет."])

    if notice:
        lines.extend(["", f"ℹ️ {notice}"])

    return "\n".join(lines)


@router.callback_query(F.data == "view:diary")
async def cb_view_diary(callback: CallbackQuery, state: FSMContext) -> None:
    await _reset_context(state, view_mode=VIEW_DIARY)
    await state.update_data(diary_calendar_mode=False)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "diary:calendar")
async def cb_diary_calendar(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected_date = _parse_iso_date(data.get("selected_date"), date.today())
    await state.update_data(
        view_mode=VIEW_DIARY,
        diary_calendar_mode=True,
        calendar_month=_month_start(selected_date).isoformat(),
    )
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "diary:close_calendar")
async def cb_diary_close_calendar(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(view_mode=VIEW_DIARY, diary_calendar_mode=False)
    await _render(from_user=callback.from_user, state=state, callback=callback)
    await callback.answer()


@router.callback_query(F.data == "diary:add")
async def cb_diary_add(callback: CallbackQuery, state: FSMContext) -> None:
    selected_date, calendar_month, _ = await _reset_context(state, view_mode=VIEW_DIARY)
    await state.set_state(DashboardStates.waiting_diary_text)
    await state.update_data(
        selected_date=selected_date.isoformat(),
        calendar_month=calendar_month.isoformat(),
        view_mode=VIEW_DIARY,
        diary_calendar_mode=False,
    )
    await _render(
        from_user=callback.from_user,
        state=state,
        callback=callback,
        notice="Отправь запись: текст, кружок, голосовое, фото или видео.",
    )
    await callback.answer("Жду запись")


@router.callback_query(F.data.startswith("diary:view:"))
async def cb_diary_view(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        entry_id = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка записи")
        return

    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            last_name=callback.from_user.last_name,
        )
        entry = await get_user_diary_entry(session, user.id, entry_id)

    if not entry:
        await callback.answer("Запись не найдена")
        return

    sent_ok = await _send_diary_entry_to_chat(callback.message, entry, state=state)
    if not sent_ok:
        await callback.answer("Не удалось отправить запись")
        return

    await callback.answer("Открыто")


@router.callback_query(F.data == "diary:dumpday")
async def cb_diary_dump_day(callback: CallbackQuery, state: FSMContext) -> None:
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
        entries = await list_day_diary_entries(session, user.id, selected_date, limit=None)

    if not entries:
        await _render(
            from_user=callback.from_user,
            state=state,
            callback=callback,
            notice=f"За {selected_date.strftime('%d.%m.%Y')} записей нет.",
        )
        await callback.answer("Пусто")
        return

    day_header = f"📝 <b>Дневник за {selected_date.strftime('%d.%m.%Y')}</b>\nЗаписей: <b>{len(entries)}</b>"
    header_msg = await callback.message.answer(day_header)
    await _remember_output_message(state, header_msg)

    sent_count = 0
    for entry in sorted(entries, key=lambda x: x.created_at):
        if await _send_diary_entry_to_chat(callback.message, entry, state=state):
            sent_count += 1

    await _render(
        from_user=callback.from_user,
        state=state,
        callback=callback,
        notice=f"Отправлено записей: {sent_count}/{len(entries)}",
    )
    await callback.answer("Готово")


@router.callback_query(F.data == "diary:clearout")
async def cb_diary_clear_outputs(callback: CallbackQuery, state: FSMContext) -> None:
    removed, skipped = await _clear_output_messages(callback.message, state)

    if removed == 0 and skipped == 0:
        notice = "Нет сообщений для очистки."
    elif skipped == 0:
        notice = f"Очищено сообщений: {removed}."
    else:
        notice = f"Очищено: {removed}. Не удалось удалить: {skipped}."

    await _render(
        from_user=callback.from_user,
        state=state,
        callback=callback,
        notice=notice,
    )
    await callback.answer("Очищено")


@router.message(StateFilter(DashboardStates.waiting_diary_text))
async def msg_diary_text(message: Message, state: FSMContext) -> None:
    payload = _extract_diary_payload(message)
    if not payload:
        await _render(
            from_user=message.from_user,
            state=state,
            message=message,
            notice="Поддерживаются: текст, кружок, голосовое, фото, видео.",
        )
        return

    data = await state.get_data()
    selected_date = _parse_iso_date(data.get("selected_date"), date.today())
    created_at = datetime.combine(selected_date, datetime.now().time())

    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            last_name=message.from_user.last_name,
        )
        level_ups = await add_diary_entry(session, user, created_at=created_at, **payload)

    await _reset_context(state, view_mode=VIEW_DIARY)

    notice = f"{_diary_type_label(payload['entry_type'])} сохранено (+10 EXP)"
    if level_ups > 0:
        notice += f" | Уровень +{level_ups}"

    await _render(from_user=message.from_user, state=state, message=message, notice=notice)
