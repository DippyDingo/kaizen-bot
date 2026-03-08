from __future__ import annotations

from aiogram import F, Router

router = Router()
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")

DashboardKey = tuple[int, int]
DashboardMessageRef = tuple[int, int]

DASHBOARD_MESSAGES: dict[DashboardKey, DashboardMessageRef] = {}
CONFIGURED_WEBAPP_CHATS: set[int] = set()
CLEARED_COMMAND_CHATS: set[int] = set()
CONFIGURED_REPLY_KEYBOARD_CHATS: set[int] = set()
CHAT_KEYBOARD_MESSAGES: dict[int, int] = {}
MAX_TRACKED_OUTPUT_MESSAGES = 80

VIEW_HOME = "home"
VIEW_TASKS = "tasks"
VIEW_CALENDAR = "calendar"
VIEW_STATS = "stats"
VIEW_HEALTH = "health"
VIEW_WATER = "water"
VIEW_DIARY = "diary"
VIEW_PROFILE = "profile"
VIEW_SETTINGS = "settings"

CHAT_BUTTON_HOME = "🏠 Главная"
CHAT_BUTTON_TASKS = "📋 Задачи"
CHAT_BUTTON_DIARY = "📝 Дневник"
CHAT_BUTTON_STATS = "📊 Статистика"
CHAT_BUTTON_HEALTH = "❤️ Здоровье"
CHAT_BUTTON_SETTINGS = "⚙️ Настройки"

CHAT_NAVIGATION: dict[str, str] = {
    CHAT_BUTTON_HOME: VIEW_HOME,
    CHAT_BUTTON_TASKS: VIEW_TASKS,
    CHAT_BUTTON_DIARY: VIEW_DIARY,
    CHAT_BUTTON_STATS: VIEW_STATS,
    CHAT_BUTTON_HEALTH: VIEW_HEALTH,
    CHAT_BUTTON_SETTINGS: VIEW_SETTINGS,
}

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

WEBAPP_BUTTON_TEXT = "Open"
BAR_STEPS = 5
BAR_EMPTY = "⬜️"
BAR_FILLED: dict[str, str] = {
    "tasks": "🟩",
    "water": "🟦",
    "sleep": "🟨",
    "workout": "🟧",
    "diary": "🟪",
    "quality": "🟫",
    "energy": "🟨",
    "stress": "🟥",
}
