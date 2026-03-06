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

## 2026-03-06 Health Sleep Flow

- The `Здоровье` section was expanded from water-only UI to a minimal health dashboard with both water and sleep.
- Health screen now shows:
  - daily water total,
  - daily sleep total,
  - stamina percent based on sleep.
- Added a button-driven sleep logging flow without free text:
  - `😴 Добавить сон` -> choose duration -> choose quality 1-5.
- Sleep logs are saved for the selected date as the wake-up date.
- Added `↩️ Сон` to remove the last sleep log for the selected day.
- Water actions now also reset the temporary health subflow state so the section returns to the main health screen cleanly after actions.
- Added backend support for undoing the last sleep log:
  - `remove_last_sleep_log(...)` in `backend/services/health_service.py`
- Updated files:
  - `backend/services/health_service.py`
  - `backend/services/__init__.py`
  - `bot/handlers/single_message_parts/health.py`
  - `bot/handlers/single_message_parts/common.py`

## 2026-03-06 Exact Sleep Time Input

- Added a separate `🕒 Точное время` entry point inside the sleep flow in `Здоровье`.
- This button starts a dedicated exact-time mode instead of forcing users to use predefined duration buttons only.
- In exact-time mode, the user sends sleep time in one message, for example:
  - `23:40 07:15`
  - `23:40-07:15`
- The first time is interpreted as falling asleep, the second as wake-up time.
- The selected dashboard date is treated as the wake-up date.
- If the fall-asleep time is later than the wake-up time, the bot interprets falling asleep as the previous day.
- After exact times are parsed, the bot does not assume sleep quality automatically; it sends the user to the same 1-5 quality selection step as the duration-based flow.
- Added new FSM state:
  - `DashboardStates.waiting_sleep_exact_time`
- Updated files:
  - `bot/states/states.py`
  - `bot/handlers/single_message_parts/core.py`
  - `bot/handlers/single_message_parts/health.py`

## 2026-03-06 Stats Periods

- The `Статистика` screen was expanded from all-time-only output to period-based analytics.
- Added period switches in the stats UI:
  - `День`
  - `7 дней`
  - `30 дней`
  - `Всё время`
- Stats periods are anchored to the currently selected dashboard date.
- Added backend aggregation helpers for period ranges:
  - tasks totals for a date range,
  - water totals for a date range,
  - sleep totals and average quality for a date range,
  - diary entries count for a date range.
- The stats screen now shows:
  - task completion for the selected period,
  - total and average water,
  - total and average sleep,
  - average sleep quality,
  - diary entries count,
  - level, EXP, streak and account start date.
- Updated files:
  - `backend/services/task_service.py`
  - `backend/services/diary_service.py`
  - `backend/services/health_service.py`
  - `backend/services/__init__.py`
  - `bot/handlers/single_message_parts/common.py`
  - `bot/handlers/single_message_parts/core.py`

## 2026-03-06 Detailed Stats

- The stats screen was further expanded with more detailed breakdowns for tasks, health and diary activity.
- Added detailed task analytics for the selected stats period:
  - total tasks,
  - completed tasks,
  - priority split (`high/medium/low`),
  - number of active task days.
- Added detailed water analytics for the selected stats period:
  - total water,
  - active water days,
  - best water day by ml.
- Added detailed sleep analytics for the selected stats period:
  - total sleep,
  - average sleep,
  - average sleep quality,
  - active sleep days,
  - best sleep day by total duration,
  - longest single sleep log.
- Added detailed diary analytics for the selected stats period:
  - total entries,
  - active diary days,
  - best day by number of entries.
- Updated files:
  - `backend/services/task_service.py`
  - `backend/services/diary_service.py`
  - `backend/services/health_service.py`
  - `backend/services/__init__.py`
  - `bot/handlers/single_message_parts/common.py`
  - `bot/handlers/single_message_parts/core.py`

## 2026-03-06 Visual Stats And Health Summaries

- The stats screen layout was rewritten into visual blocks instead of dense one-line metrics.
- Stats are now grouped into separate readable sections:
  - overall,
  - tasks,
  - water,
  - sleep,
  - diary.
- The `Здоровье` section now has two separate summary screens:
  - day summary,
  - week summary.
- Added health summary switches in the health UI:
  - `День`
  - `Неделя`
- Day health summary focuses on the selected day:
  - water,
  - sleep,
  - stamina,
  - sleep quality.
- Week health summary focuses on the 7-day window ending on the selected date:
  - water total and average,
  - active water days,
  - best water day,
  - sleep total and average,
  - average sleep quality,
  - active sleep days,
  - best sleep day.
- Updated files:
  - `bot/handlers/single_message_parts/health.py`
  - `bot/handlers/single_message_parts/common.py`
  - `bot/handlers/single_message_parts/core.py`

## 2026-03-06 Health Progress Bars

- Added mini progress bars to the `Здоровье` summaries for both day and week views.
- Progress bars now show:
  - water progress,
  - sleep progress.
- The current implementation uses the same implicit targets that already existed in the bot UI:
  - water: `2500 ml / day`
  - sleep: `8 h / day`
- Weekly bars are calculated against the corresponding 7-day targets.
- Updated file:
  - `bot/handlers/single_message_parts/health.py`
