from __future__ import annotations

import html
from datetime import date, datetime, timedelta

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BotCommandScopeChat,
    BotCommandScopeChatAdministrators,
    BotCommandScopeChatMember,
    BotCommandScopeDefault,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllChatAdministrators,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)

from backend.database import async_session
from backend.services.diary_service import get_day_diary_entries_count, list_day_diary_entries
from backend.services.health_service import get_day_sleep_total_minutes, get_today_water_total
from backend.services.task_service import list_tasks_for_date
from backend.services.user_service import get_or_create_user
from bot.config import settings
from bot.states import DashboardStates

router = Router()
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")

DashboardKey = tuple[int, int]
DashboardMessageRef = tuple[int, int]

DASHBOARD_MESSAGES: dict[DashboardKey, DashboardMessageRef] = {}
CONFIGURED_WEBAPP_CHATS: set[int] = set()
CLEARED_COMMAND_CHATS: set[int] = set()
MAX_TRACKED_OUTPUT_MESSAGES = 80

VIEW_HOME = "home"
VIEW_TASKS = "tasks"
VIEW_CALENDAR = "calendar"
VIEW_STATS = "stats"
VIEW_HEALTH = "health"
VIEW_DIARY = "diary"

PRIORITY_TEXT: dict[str, str] = {
    "high": "🔴 Важно",
    "medium": "🟡 Обычно",
    "low": "🟢 Когда-нибудь",
}

MONTH_NAMES = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}

WEEKDAY_LABELS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

MONTH_NAMES_GENITIVE = {
    1: "Января",
    2: "Февраля",
    3: "Марта",
    4: "Апреля",
    5: "Мая",
    6: "Июня",
    7: "Июля",
    8: "Августа",
    9: "Сентября",
    10: "Октября",
    11: "Ноября",
    12: "Декабря",
}

WEEKDAY_NAMES_LONG = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье",
}

HOME_LOCATION_NAME = "Стартовый лес"
HOME_DUEL_OPPONENT = "Олег"
HOME_DUEL_OPPONENT_WATER_ML = 800
HOME_TRACK_TITLE = "Naruto OST - Sadness and Sorrow"
HOME_COMPANION_ROLE = "Мудрый наставник"

WEBAPP_BUTTON_TEXT = "🌐 App"


def _short(text: str, limit: int = 22) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _parse_iso_date(value: str | None, default: date) -> date:
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default


def _month_start(day: date) -> date:
    return day.replace(day=1)


def _next_month(day: date) -> date:
    return (day.replace(day=28) + timedelta(days=4)).replace(day=1)


def _prev_month(day: date) -> date:
    return (day.replace(day=1) - timedelta(days=1)).replace(day=1)


def _format_long_date(day: date) -> str:
    return f"{day.day} {MONTH_NAMES_GENITIVE[day.month]}, {WEEKDAY_NAMES_LONG[day.weekday()]}"


def _clamp_percent(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _build_meter(percent: int, total: int, filled: str, empty: str) -> str:
    filled_count = max(0, min(total, int(round(percent / 100 * total))))
    return (filled * filled_count) + (empty * (total - filled_count))


def _build_mana_bar(water_ml: int) -> tuple[str, int]:
    max_steps = 5
    step_ml = 500
    mana_steps = max(0, min(max_steps, int(round(water_ml / step_ml))))
    bar = ("🟦" * mana_steps) + ("⬜️" * (max_steps - mana_steps))
    return bar, mana_steps


def _build_companion_hint(stamina_percent: int, water_ml: int, done_count: int, total_tasks: int) -> str:
    if stamina_percent < 60:
        return (
            "Твоя стамина проседает. По истории, если ты ложишься после 2:00, "
            "завтра завалишь дейлики. Пора отдыхать."
        )
    if water_ml < 1200:
        return "По воде ты отстаёшь от темпа дня. Добавь 250-500 мл сейчас."
    if total_tasks > 0 and done_count < total_tasks:
        return "Добей оставшиеся дейлики сегодня, чтобы не ронять streak."
    return "Темп хороший. Закрепи результат и не теряй ритм."


def _back_row() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text="⬅️ Меню", callback_data="view:home")]


def _date_nav_row(selected_date: date) -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(text="◀️", callback_data="date:shift:-1"),
        InlineKeyboardButton(text=selected_date.strftime("%d.%m"), callback_data="cal:noop"),
        InlineKeyboardButton(text="▶️", callback_data="date:shift:1"),
    ]


def _diary_type_label(entry_type: str) -> str:
    mapping = {
        "text": "📝 Текст",
        "voice": "🎤 Голосовое",
        "video_note": "⭕ Кружок",
        "photo": "🖼 Фото",
        "video": "🎬 Видео",
    }
    return mapping.get(entry_type, "📎 Медиа")


def _build_diary_entry_preview(entry) -> str:
    base = _diary_type_label(getattr(entry, "entry_type", "text"))
    text = (entry.text or "").replace("\n", " ").strip()
    if text:
        return f"{base}: {html.escape(_short(text, limit=56))}"
    return base


def _extract_diary_payload(message: Message) -> dict | None:
    if message.text:
        return {"entry_type": "text", "text": message.text}

    if message.voice:
        return {
            "entry_type": "voice",
            "text": message.caption,
            "file_id": message.voice.file_id,
            "file_unique_id": message.voice.file_unique_id,
            "mime_type": message.voice.mime_type,
            "duration_sec": message.voice.duration,
        }

    if message.video_note:
        return {
            "entry_type": "video_note",
            "text": message.caption,
            "file_id": message.video_note.file_id,
            "file_unique_id": message.video_note.file_unique_id,
            "duration_sec": message.video_note.duration,
            "width": message.video_note.length,
            "height": message.video_note.length,
        }

    if message.photo:
        best = message.photo[-1]
        return {
            "entry_type": "photo",
            "text": message.caption,
            "file_id": best.file_id,
            "file_unique_id": best.file_unique_id,
            "width": best.width,
            "height": best.height,
        }

    if message.video:
        return {
            "entry_type": "video",
            "text": message.caption,
            "file_id": message.video.file_id,
            "file_unique_id": message.video.file_unique_id,
            "mime_type": message.video.mime_type,
            "duration_sec": message.video.duration,
            "width": message.video.width,
            "height": message.video.height,
        }

    return None


def _webapp_row() -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(
            text=WEBAPP_BUTTON_TEXT,
            web_app=WebAppInfo(url=settings.webapp_url),
        )
    ]


async def _set_webapp_menu_button(message: Message) -> None:
    chat_id = message.chat.id
    if chat_id in CONFIGURED_WEBAPP_CHATS:
        return

    try:
        await message.bot.set_chat_menu_button(
            chat_id=chat_id,
            menu_button=MenuButtonWebApp(text=WEBAPP_BUTTON_TEXT, web_app=WebAppInfo(url=settings.webapp_url)),
        )
        CONFIGURED_WEBAPP_CHATS.add(chat_id)
    except TelegramBadRequest:
        pass


async def initialize_bot_ui(bot: Bot) -> None:
    scopes = (
        BotCommandScopeDefault(),
        BotCommandScopeAllPrivateChats(),
        BotCommandScopeAllGroupChats(),
        BotCommandScopeAllChatAdministrators(),
    )
    for scope in scopes:
        try:
            await bot.delete_my_commands(scope=scope)
        except TelegramBadRequest:
            pass


async def _clear_chat_commands(message: Message) -> None:
    chat_id = message.chat.id
    if chat_id in CLEARED_COMMAND_CHATS:
        return

    scopes = (
        BotCommandScopeChat(chat_id=chat_id),
        BotCommandScopeChatAdministrators(chat_id=chat_id),
        BotCommandScopeChatMember(chat_id=chat_id, user_id=message.from_user.id),
    )
    for scope in scopes:
        try:
            await message.bot.delete_my_commands(scope=scope)
        except TelegramBadRequest:
            pass

    CLEARED_COMMAND_CHATS.add(chat_id)


async def _setup_chat_ui(message: Message) -> None:
    await _clear_chat_commands(message)
    await _set_webapp_menu_button(message)


async def _load_user_and_metrics(from_user, target_date: date) -> tuple[object, list, int, int, int]:
    async with async_session() as session:
        user, _ = await get_or_create_user(
            session=session,
            telegram_id=from_user.id,
            first_name=from_user.first_name,
            username=from_user.username,
            last_name=from_user.last_name,
        )
        tasks = await list_tasks_for_date(session, user.id, target_date)
        water_ml = await get_today_water_total(session, user.id, target_date)
        sleep_minutes = await get_day_sleep_total_minutes(session, user.id, target_date)
        diary_count = await get_day_diary_entries_count(session, user.id, target_date)
    return user, tasks, water_ml, sleep_minutes, diary_count


async def _edit_dashboard_callback(callback: CallbackQuery, text: str, keyboard: InlineKeyboardMarkup) -> None:
    key = (callback.message.chat.id, callback.from_user.id)
    DASHBOARD_MESSAGES[key] = (callback.message.chat.id, callback.message.message_id)
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise


async def _upsert_dashboard_message(message: Message, text: str, keyboard: InlineKeyboardMarkup) -> None:
    key = (message.chat.id, message.from_user.id)
    target = DASHBOARD_MESSAGES.get(key)

    if target:
        chat_id, message_id = target
        try:
            await message.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=keyboard,
            )
            return
        except TelegramBadRequest:
            pass

    sent = await message.answer(text=text, reply_markup=keyboard)
    DASHBOARD_MESSAGES[key] = (sent.chat.id, sent.message_id)


async def _remember_output_message(state: FSMContext, bot_message: Message) -> None:
    data = await state.get_data()
    tracked: list[int] = list(data.get("output_message_ids", []))
    tracked.append(bot_message.message_id)
    if len(tracked) > MAX_TRACKED_OUTPUT_MESSAGES:
        tracked = tracked[-MAX_TRACKED_OUTPUT_MESSAGES:]
    await state.update_data(output_message_ids=tracked)


async def _clear_output_messages(message: Message, state: FSMContext) -> tuple[int, int]:
    data = await state.get_data()
    tracked: list[int] = list(data.get("output_message_ids", []))
    if not tracked:
        return 0, 0

    removed = 0
    skipped = 0
    for msg_id in tracked:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
            removed += 1
        except TelegramBadRequest:
            skipped += 1

    await state.update_data(output_message_ids=[])
    return removed, skipped


async def _reset_context(state: FSMContext, *, view_mode: str | None = None) -> tuple[date, date, str]:
    data = await state.get_data()
    selected_date = _parse_iso_date(data.get("selected_date"), date.today())
    calendar_month = _parse_iso_date(data.get("calendar_month"), _month_start(selected_date))
    output_message_ids = list(data.get("output_message_ids", []))
    old_view = data.get("view_mode", VIEW_HOME)
    await state.clear()
    resolved_view = view_mode or old_view
    await state.update_data(
        selected_date=selected_date.isoformat(),
        calendar_month=calendar_month.isoformat(),
        view_mode=resolved_view,
        output_message_ids=output_message_ids,
    )
    return selected_date, calendar_month, resolved_view


async def _render(
    *,
    from_user,
    state: FSMContext,
    callback: CallbackQuery | None = None,
    message: Message | None = None,
    notice: str | None = None,
) -> None:
    from .calendar import _build_calendar_keyboard, _build_calendar_text, _build_diary_calendar_text
    from .core import _build_home_text, _build_stats_keyboard, _build_stats_text, _home_keyboard
    from .diary import _build_diary_keyboard, _build_diary_text
    from .health import _build_health_keyboard, _build_health_text
    from .tasks import _build_priority_keyboard, _build_tasks_keyboard, _build_tasks_text

    data = await state.get_data()
    selected_date = _parse_iso_date(data.get("selected_date"), date.today())
    calendar_month = _parse_iso_date(data.get("calendar_month"), _month_start(selected_date))
    view_mode = data.get("view_mode", VIEW_HOME)
    diary_calendar_mode = bool(data.get("diary_calendar_mode", False))
    current_state = await state.get_state()

    user, tasks, water_ml, sleep_minutes, diary_count = await _load_user_and_metrics(from_user, selected_date)
    diary_entries: list = []
    if view_mode == VIEW_DIARY or current_state == DashboardStates.waiting_diary_text.state:
        async with async_session() as session:
            diary_entries = await list_day_diary_entries(session, user.id, selected_date, limit=20)

    if current_state == DashboardStates.waiting_task_title.state:
        text = _build_tasks_text(tasks, selected_date, "wait_title", data.get("pending_task_title"), data.get("pending_task_priority"), notice)
        keyboard = _build_tasks_keyboard(tasks, selected_date)
    elif current_state == DashboardStates.waiting_task_priority.state:
        text = _build_tasks_text(tasks, selected_date, "wait_priority", data.get("pending_task_title"), data.get("pending_task_priority"), notice)
        keyboard = _build_priority_keyboard()
    elif current_state == DashboardStates.waiting_task_date.state:
        text = _build_tasks_text(tasks, selected_date, "wait_task_date", data.get("pending_task_title"), data.get("pending_task_priority"), notice)
        keyboard = _build_calendar_keyboard(calendar_month, selected_date, context="create")
    elif current_state == DashboardStates.waiting_diary_text.state:
        text = _build_diary_text(diary_entries, selected_date, "wait_text", notice, total_count=diary_count)
        keyboard = _build_diary_keyboard(selected_date, diary_entries)
    elif view_mode == VIEW_TASKS:
        text = _build_tasks_text(tasks, selected_date, "main", data.get("pending_task_title"), data.get("pending_task_priority"), notice)
        keyboard = _build_tasks_keyboard(tasks, selected_date)
    elif view_mode == VIEW_CALENDAR:
        text = _build_calendar_text(selected_date, notice)
        keyboard = _build_calendar_keyboard(calendar_month, selected_date, context="browse")
    elif view_mode == VIEW_STATS:
        text = _build_stats_text(user, tasks, water_ml, sleep_minutes, selected_date, notice)
        keyboard = _build_stats_keyboard(selected_date)
    elif view_mode == VIEW_HEALTH:
        text = _build_health_text(water_ml, selected_date, notice)
        keyboard = _build_health_keyboard(selected_date)
    elif view_mode == VIEW_DIARY and diary_calendar_mode:
        text = _build_diary_calendar_text(selected_date, notice)
        keyboard = _build_calendar_keyboard(calendar_month, selected_date, context="diary")
    elif view_mode == VIEW_DIARY:
        text = _build_diary_text(diary_entries, selected_date, "main", notice, total_count=diary_count)
        keyboard = _build_diary_keyboard(selected_date, diary_entries)
    else:
        text = _build_home_text(user, tasks, water_ml, sleep_minutes, diary_count, selected_date, notice)
        keyboard = _home_keyboard()

    if callback:
        await _edit_dashboard_callback(callback, text, keyboard)
    elif message:
        await _upsert_dashboard_message(message, text, keyboard)


async def _send_diary_entry_to_chat(message: Message, entry, state: FSMContext | None = None) -> bool:
    text = (entry.text or "").strip()
    safe_text = html.escape(text)

    try:
        if entry.entry_type == "text":
            sent = await message.answer(f"📝 <b>Запись #{entry.id}</b>\n{safe_text or '(пусто)'}")
            if state:
                await _remember_output_message(state, sent)
            return True

        caption = f"📝 Запись #{entry.id}"
        if safe_text:
            caption = f"{caption}\n{safe_text}"

        if entry.entry_type == "voice" and entry.file_id:
            sent = await message.answer_voice(voice=entry.file_id, caption=caption[:1024])
            if state:
                await _remember_output_message(state, sent)
            return True

        if entry.entry_type == "video_note" and entry.file_id:
            sent_note = await message.answer_video_note(video_note=entry.file_id)
            if state:
                await _remember_output_message(state, sent_note)
            if safe_text:
                sent_caption = await message.answer(f"📝 <b>Запись #{entry.id}</b>\n{safe_text}")
                if state:
                    await _remember_output_message(state, sent_caption)
            return True

        if entry.entry_type == "photo" and entry.file_id:
            sent = await message.answer_photo(photo=entry.file_id, caption=caption[:1024])
            if state:
                await _remember_output_message(state, sent)
            return True

        if entry.entry_type == "video" and entry.file_id:
            sent = await message.answer_video(video=entry.file_id, caption=caption[:1024])
            if state:
                await _remember_output_message(state, sent)
            return True

        sent = await message.answer(f"📝 <b>Запись #{entry.id}</b>\n{safe_text or 'Тип записи не поддерживается.'}")
        if state:
            await _remember_output_message(state, sent)
        return True
    except TelegramBadRequest:
        return False
