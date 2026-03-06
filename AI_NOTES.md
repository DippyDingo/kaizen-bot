# AI Notes

Дата фиксации: 2026-03-06

## Правила работы

- Не оставлять заглушки без явного `TODO` с причиной.
- Не дублировать код, выносить общее поведение в переиспользуемые функции и модули.
- Не делать скрытых допущений. При существенной неопределенности сначала уточнять у пользователя.
- После значимых изменений обновлять этот файл.

## Что реализовано

### Архитектура бота

- Бот переведен на single-message интерфейс с обновлением одного сообщения.
- Хендлеры разнесены по модулям:
  - `bot/handlers/single_message_parts/common.py`
  - `bot/handlers/single_message_parts/core.py`
  - `bot/handlers/single_message_parts/tasks.py`
  - `bot/handlers/single_message_parts/calendar.py`
  - `bot/handlers/single_message_parts/diary.py`
  - `bot/handlers/single_message_parts/health.py`
- `bot/handlers/single_message.py` используется как совместимый входной модуль.

### UI и сценарии

- Главное меню, задачи, календарь, статистика, здоровье и дневник работают как отдельные экраны.
- Внутри разделов показываются только релевантные кнопки и кнопка возврата в главное меню.
- Подписи кнопок упрощены: вместо длинных фраз используются короткие русские слова и устойчивые эмодзи.
- Повторяющаяся навигация по датам вынесена в общий хелпер, чтобы не дублировать UI-код.
- Часть глобальной навигации перенесена в меню команд Telegram:
  - `/home`
  - `/tasks`
  - `/calendar`
  - `/diary`
  - `/stats`
  - `/health`
  - `/today`
  - `/cancel`
  - `/help`
- Выявлен UX-конфликт Telegram: `chat menu button` не может одновременно быть меню команд и кнопкой Web App.
- Текущая схема:
  - нижняя системная кнопка чата открывает `🌐 App`,
  - все быстрые действия и переходы по разделам привязаны к главному сообщению через inline-кнопки,
  - `ReplyKeyboard` убрана как нестабильная для этого сценария.
- Команды Telegram через `/` отключены принципиально: бот очищает ранее зарегистрированные команды через Bot API и больше не публикует список команд в чате.
- Для задач реализованы:
  - добавление задачи,
  - выбор приоритета,
  - выбор даты через календарь,
  - переключение выполнения по кнопке `✅`,
  - снятие выполнения повторным нажатием `✅`,
  - удаление по кнопке `❌`.
- Для здоровья реализован учет воды кнопками `+150`, `+250`, `+500 мл`.
- Для воды реализован безопасный откат `↩️ Вода`, который удаляет последнюю запись воды за выбранный день.
- Для календаря реализован выбор дня и переход в задачи/дневник выбранной даты.
- Для дневника реализованы:
  - добавление текстовых записей,
  - добавление голосовых,
  - добавление кружков,
  - добавление фото,
  - добавление видео,
  - просмотр одной записи,
  - выгрузка всех записей дня в чат,
  - очистка выгруженных ботом сообщений.

### Backend и данные

- Настроены модели:
  - `User`
  - `Task`
  - `Habit`
  - `WaterLog`
  - `SleepLog`
  - `DiaryEntry`
- Настроены сервисы:
  - `backend/services/user_service.py`
  - `backend/services/task_service.py`
  - `backend/services/health_service.py`
  - `backend/services/diary_service.py`
  - `backend/services/rpg_service.py`
- Реализовано начисление EXP за задачи, воду, сон и дневник.

### Миграции

- Добавлены миграции:
  - `alembic/versions/20260306_000001_init_mvp.py`
  - `alembic/versions/20260306_000002_add_diary_entries.py`
  - `alembic/versions/20260306_000003_expand_diary_media.py`

### Документация

- Обновлен `README.md` с описанием текущего состояния, планов и команд запуска.

## Текущие ограничения

- Полноценный Web App пока не реализован.
- Большая часть модулей из `PLAN.md` пока не начата.
- Django/DRF слой и отдельная админка пока не подключены к текущему MVP.

## Что обновлять дальше

- При каждом новом изменении фиксировать:
  - что добавлено,
  - какие файлы изменены концептуально,
  - какие ограничения или TODO появились,
  - что осталось следующим шагом.

## 2026-03-06 Review Fixes

- Single-message handlers are now limited to private chats only. This prevents dashboard fallback logic from touching unrelated messages in groups.
- Dashboard message cache now uses `(chat_id, user_id)` instead of just `user_id`, so one user can safely interact with the bot in different chats without cross-chat message edits.
- Telegram command cleanup was split into:
  - global scope cleanup once on bot startup,
  - per-chat cleanup once for chat-specific scopes.
- Chat UI setup is now cached per chat. The bot no longer repeats `set_chat_menu_button` and chat command cleanup on every command message.
- Files updated for these fixes:
  - `bot/handlers/single_message_parts/common.py`
  - `bot/main.py`

## 2026-03-06 Chat Quick Buttons

- Global navigation was moved from the home inline keyboard into Telegram quick chat buttons (`ReplyKeyboard`):
  - `🏠 Главная`
  - `📋 Задачи`
  - `📝 Дневник`
  - `📅 Календарь`
  - `📊 Статистика`
  - `❤️ Здоровье`
- Home inline keyboard now keeps only local quick actions:
  - add water,
  - undo water,
  - add task,
  - add diary entry.
- The bot sends one short keyboard-carrier message (`🧭 Меню`) per chat to keep the `ReplyKeyboard` visible.
- Presses on quick chat buttons are handled before FSM text input and the pressed text message is deleted, so navigation does not pollute the chat history.
- Main section screens no longer duplicate global navigation with inline `back to menu` buttons.
- Task list layout was changed to two rows per task:
  - first row: task title,
  - second row: `❌` delete button.
- Task title buttons now use Telegram Bot API button styles:
  - `danger` for incomplete tasks,
  - `success` for completed tasks.
- Tapping the task title button toggles task completion directly.
- Task delete button is placed to the right of the task title in the same row.
- Task title buttons now show the priority badge on the left (`🔴`, `🟡`, `🟢`).
- Full task titles are duplicated in the task screen text block so long tasks remain readable even if the inline button is visually compressed by Telegram.
- Daily task lists are now sorted by:
  - incomplete before complete,
  - then `high -> medium -> low` priority,
  - then creation order.
- Diary list buttons no longer show the eye icon in the label.

## 2026-03-06 Reply Keyboard Recovery

- Quick chat buttons now recover more reliably after bot restarts and explicit command entry points.
- The bot now tracks the current keyboard-carrier message per chat and replaces the old one instead of piling up multiple `🧭 Меню` messages.
- Dashboard callback rendering restores the chat quick buttons if the bot runtime was restarted and in-memory keyboard state was lost.

## 2026-03-06 Profile Name And All-Time Stats

- Added `preferred_name` to `users` and a new migration:
  - `alembic/versions/20260306_000004_add_user_preferred_name.py`
- On first `/start`, if `preferred_name` is missing, the bot now asks how to address the user and stores that name for future screens.
- Added a separate profile screen with name display and manual rename action.
- If the profile is opened from statistics, saving a new name now returns to the all-time statistics screen so the updated name is visible immediately there.
- Added a separate `⚙️ Настройки` section in chat quick buttons and moved profile access there.
- Statistics screen no longer acts as an entry point for profile/settings.
- The keyboard-carrier message can now show a prompt text like `Как тебя называть?` instead of the generic `🧭 Меню`.
- Home and stats screens now use `preferred_name` if it is set.
- Statistics screen was switched from per-day to all-time aggregates:
  - total tasks,
  - completed tasks,
  - total water,
  - total sleep,
  - total diary entries,
  - current and longest streak,
  - account start date.
- Main home mana bar already remains interactive because home rendering always recalculates water total for the selected day after `water:*` actions.
- Files updated:
  - `bot/handlers/single_message_parts/common.py`
  - `bot/handlers/single_message_parts/core.py`
  - `bot/handlers/single_message_parts/tasks.py`
  - `bot/handlers/single_message_parts/diary.py`
  - `bot/handlers/single_message_parts/health.py`
  - `bot/handlers/single_message_parts/calendar.py`

## 2026-03-06 README Sync With Plan

- `README.md` was rewritten against the actual repository state and cross-checked with `PLAN.md`.
- The README now clearly separates:
  - what is already implemented in code,
  - what is only partially implemented,
  - what still remains only in the long-term plan.
- The README now includes the current bot navigation, all-time stats, profile/settings flow, current data model status, and the real project structure.
- The README explicitly does not claim unfinished modules like Django/DRF API, full Web App, AI integrations, social/RPG systems, or advanced health features as completed.
