from __future__ import annotations

from aiogram import Bot, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    BotCommandScopeChatAdministrators,
    BotCommandScopeChatMember,
    BotCommandScopeDefault,
    InlineKeyboardButton,
    KeyboardButton,
    MenuButtonWebApp,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from bot.config import settings

from .constants import (
    CHAT_BUTTON_CALENDAR,
    CHAT_BUTTON_DIARY,
    CHAT_BUTTON_HEALTH,
    CHAT_BUTTON_HOME,
    CHAT_BUTTON_SETTINGS,
    CHAT_BUTTON_STATS,
    CHAT_BUTTON_TASKS,
    CHAT_KEYBOARD_MESSAGES,
    CHAT_NAVIGATION,
    CLEARED_COMMAND_CHATS,
    CONFIGURED_REPLY_KEYBOARD_CHATS,
    CONFIGURED_WEBAPP_CHATS,
    WEBAPP_BUTTON_TEXT,
    router,
)
from .telemetry import log_ui_event


def _webapp_row() -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(
            text=WEBAPP_BUTTON_TEXT,
            web_app=WebAppInfo(url=settings.webapp_url),
        )
    ]


def _chat_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=CHAT_BUTTON_HOME), KeyboardButton(text=CHAT_BUTTON_TASKS)],
            [KeyboardButton(text=CHAT_BUTTON_DIARY), KeyboardButton(text=CHAT_BUTTON_CALENDAR)],
            [KeyboardButton(text=CHAT_BUTTON_STATS), KeyboardButton(text=CHAT_BUTTON_HEALTH)],
            [KeyboardButton(text=CHAT_BUTTON_SETTINGS)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выбери раздел",
    )


def _reset_chat_ui_state(chat_id: int) -> None:
    CHAT_KEYBOARD_MESSAGES.pop(chat_id, None)
    CONFIGURED_REPLY_KEYBOARD_CHATS.discard(chat_id)
    CONFIGURED_WEBAPP_CHATS.discard(chat_id)
    CLEARED_COMMAND_CHATS.discard(chat_id)
    log_ui_event("chat_ui_reset", chat_id=chat_id)


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
        log_ui_event("webapp_button_configured", chat_id=chat_id)
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
    log_ui_event("chat_commands_cleared", chat_id=chat_id)


async def _ensure_chat_keyboard(message: Message, *, force: bool = False, text: str = "🧭 Меню") -> None:
    chat_id = message.chat.id
    existing_carrier_message_id = CHAT_KEYBOARD_MESSAGES.get(chat_id)
    if not force and chat_id in CONFIGURED_REPLY_KEYBOARD_CHATS and existing_carrier_message_id:
        log_ui_event(
            "carrier_reused",
            chat_id=chat_id,
            carrier_message_id=existing_carrier_message_id,
        )
        return

    previous_message_id = existing_carrier_message_id
    sent = await message.answer(
        text,
        reply_markup=_chat_keyboard(),
        disable_notification=True,
    )
    CHAT_KEYBOARD_MESSAGES[chat_id] = sent.message_id
    CONFIGURED_REPLY_KEYBOARD_CHATS.add(chat_id)
    log_ui_event(
        "carrier_created",
        chat_id=chat_id,
        carrier_message_id=sent.message_id,
    )

    if previous_message_id and previous_message_id != sent.message_id:
        try:
            await message.bot.delete_message(chat_id=chat_id, message_id=previous_message_id)
        except TelegramBadRequest:
            pass


async def _setup_chat_ui(message: Message, *, force_keyboard: bool = False, keyboard_text: str = "🧭 Меню") -> None:
    await _clear_chat_commands(message)
    await _set_webapp_menu_button(message)
    await _ensure_chat_keyboard(message, force=force_keyboard, text=keyboard_text)
    log_ui_event(
        "chat_ui_setup",
        chat_id=message.chat.id,
        carrier_message_id=CHAT_KEYBOARD_MESSAGES.get(message.chat.id),
    )


@router.message(F.text.in_(tuple(CHAT_NAVIGATION)))
async def msg_chat_navigation(message: Message, state: FSMContext) -> None:
    target_view = CHAT_NAVIGATION[(message.text or "").strip()]
    from ..core import _render_command_view

    log_ui_event(
        "navigation_request",
        chat_id=message.chat.id,
        carrier_message_id=CHAT_KEYBOARD_MESSAGES.get(message.chat.id),
        view_mode=target_view,
        entrypoint="chat_menu",
    )
    await _render_command_view(
        message,
        state,
        target_view,
        delete_source_message=True,
        force_keyboard=False,
        relocate_dashboard=False,
        entrypoint="chat_menu",
    )
