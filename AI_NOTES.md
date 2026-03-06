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

## 2026-03-06 Stats Progress Bars

- Added compact visual progress bars to the `Статистика` screen.
- Bars were added only for metrics with a clear scale:
  - tasks completion,
  - average water,
  - average sleep,
  - average sleep quality,
  - diary activity by active days.
- The current implementation uses these scales:
  - tasks: completion percent for the selected period,
  - water: average per day vs `2500 ml/day`,
  - sleep: average per day vs `8 h/day`,
  - sleep quality: current average vs `5/5`,
  - diary: active days vs total days in the selected stats period.
- Updated file:
  - `bot/handlers/single_message_parts/core.py`
## 2026-03-06 Unified Progress Bars

- Unified the visual style of progress bars across `�������`, `��������` and `����������`.
- Moved bar rendering to shared helpers in `bot/handlers/single_message_parts/common.py`.
- Standardized the system to one scale:
  - `5` segments per bar,
  - `??` as the empty segment,
  - fixed colors by metric: tasks `??`, water `??`, sleep `??`, diary `??`, sleep quality `??`.
- Home screen no longer uses a separate red-empty HP bar; it now follows the same scale as the other screens.
- Updated files:
  - `bot/handlers/single_message_parts/common.py`
  - `bot/handlers/single_message_parts/core.py`
  - `bot/handlers/single_message_parts/health.py`
## 2026-03-06 Unified Bar Captions

- Standardized bar captions across `�������`, `��������` and `����������`.
- Added a shared helper for the caption format `label: bar value`.
- Removed mixed variants like `[60%]`, `�������� ����`, `�������� ���` and generic `��������` where a direct metric label is clearer.
- Updated files:
  - `bot/handlers/single_message_parts/common.py`
  - `bot/handlers/single_message_parts/core.py`
  - `bot/handlers/single_message_parts/health.py`
## 2026-03-06 Home Bar Alignment

- Aligned the three main dashboard bars on the home screen into a single monospace block.
- Implemented this through a shared helper in `bot/handlers/single_message_parts/common.py` instead of manual spacing in the screen builder.
- The change is limited to the home status block so the rest of the UI keeps its regular text flow.
- Updated files:
  - `bot/handlers/single_message_parts/common.py`
  - `bot/handlers/single_message_parts/core.py`
## 2026-03-06 Reverted Home Bar Alignment

- Reverted the monospace alignment block for the home status bars.
- Restored the regular inline caption format for `��������`, `����` and `�������` on the main screen.
- Updated files:
  - `bot/handlers/single_message_parts/common.py`
  - `bot/handlers/single_message_parts/core.py`
## 2026-03-06 Shorter Home Bar Labels

- Shortened the three home dashboard bar captions to make them visually more even without using monospace alignment.
- Updated labels:
  - `��������` -> `����`
  - `�������` -> `���`
- Kept the existing inline text flow and the shared bar caption helper.
- Updated file:
  - `bot/handlers/single_message_parts/core.py`
## 2026-03-06 Workout Logs And Health UI

- Added a new `WorkoutLog` model and migration `20260306_000005_add_workout_logs`.
- Added health-service operations for workouts:
  - create workout log,
  - undo last workout log for a selected day,
  - day total minutes,
  - period details for summaries.
- Expanded the `��������` UI with a workout flow:
  - choose workout type,
  - choose duration,
  - save workout,
  - undo last workout.
- Added workout summaries to both health screens:
  - day summary,
  - week summary.
- Current MVP assumptions for workouts:
  - supported types: strength, cardio, mobility,
  - supported durations: 15 / 30 / 45 / 60 minutes,
  - workout log grants `+30 EXP` to match the current project plan.
- Synced `README.md` with the actual state of the repository, including health, statistics and the new workout block.
- Updated files:
  - `backend/models/workout_log.py`
  - `backend/models/__init__.py`
  - `backend/services/health_service.py`
  - `backend/services/__init__.py`
  - `backend/services/rpg_service.py`
  - `bot/handlers/single_message_parts/common.py`
  - `bot/handlers/single_message_parts/health.py`
  - `alembic/versions/20260306_000005_add_workout_logs.py`
  - `README.md`
## 2026-03-06 Workout Limits And Custom Duration

- Added per-user daily targets:
  - `daily_water_target_ml`
  - `daily_workout_target_min`
- Added migration `20260306_000006_add_user_daily_targets`.
- Settings now allow changing:
  - daily water limit,
  - daily workout limit.
- Main dashboard, health summaries and statistics now use the user's own water target instead of a hardcoded default.
- Workout logging was extended with free duration input:
  - plain minutes, example `25`
  - hours and minutes, example `1:15`
- Workout statistics were expanded with per-type aggregates:
  - strength / cardio / mobility counts,
  - strength / cardio / mobility minutes.
- Weekly health summary now shows workout distribution by type.
- Updated files:
  - `backend/models/user.py`
  - `backend/services/user_service.py`
  - `backend/services/health_service.py`
  - `backend/services/__init__.py`
  - `bot/states/states.py`
  - `bot/handlers/single_message_parts/common.py`
  - `bot/handlers/single_message_parts/core.py`
  - `bot/handlers/single_message_parts/health.py`
  - `alembic/versions/20260306_000006_add_user_daily_targets.py`
  - `README.md`## 2026-03-06 Medication Logs And Minimal Tests

- Added a new `MedicationLog` model and migration `20260306_000007_add_medication_logs`.
- Added medication operations to the health service:
  - create medication log,
  - undo last medication log for a selected day,
  - list latest day medications,
  - period aggregates for statistics and weekly summaries.
- Expanded the `��������` UI with a medication flow:
  - enter medication title,
  - enter dose,
  - save intake,
  - undo last intake.
- Added medication summaries to health screens:
  - day summary with latest intakes,
  - week summary with active days and most frequent medication.
- Expanded the statistics screen with a dedicated medications block.
- Added a minimal `unittest` suite for:
  - stats period helpers,
  - home water target bar helper,
  - health parsing helpers,
  - cancel-view routing,
  - daily target clamping in user service.
- This is not full bot coverage yet; it is the first minimal safety net around the current MVP logic.
- Updated files:
  - `backend/models/medication_log.py`
  - `backend/models/__init__.py`
  - `backend/services/health_service.py`
  - `backend/services/__init__.py`
  - `backend/services/rpg_service.py`
  - `bot/states/states.py`
  - `bot/handlers/single_message_parts/common.py`
  - `bot/handlers/single_message_parts/core.py`
  - `bot/handlers/single_message_parts/health.py`
  - `alembic/versions/20260306_000007_add_medication_logs.py`
  - `tests/test_common_helpers.py`
  - `tests/test_core_logic.py`
  - `tests/test_health_helpers.py`
  - `tests/test_user_service.py`
  - `README.md`## 2026-03-06 Medication Courses And Calendar UI

- Reworked medications from one-off logs into a proper scheduled flow.
- Added a new `MedicationCourse` model and migration `20260306_000008_add_medication_courses_and_schedule_status`.
- Extended `MedicationLog` to store:
  - `course_id`,
  - `scheduled_date`,
  - `status` (`taken` / `skipped`).
- Added medication service operations for:
  - creating a course,
  - archiving a course,
  - toggling day status (`taken` / `skipped` / reset to pending),
  - building medication day schedule,
  - building medication calendar marks.
- The `��������` section now has a dedicated medication window:
  - course creation flow `title -> dose -> time -> days`,
  - medication calendar,
  - per-day scheduled list,
  - `����� / �������` actions,
  - course deletion.
- The medication calendar uses visual day marks:
  - `??` scheduled,
  - `?` fully taken,
  - `??` skipped.
- Statistics were updated to show medication taken vs skipped counts.
- Expanded minimal tests with medication helper coverage.
- Updated files:
  - `backend/models/medication_course.py`
  - `backend/models/medication_log.py`
  - `backend/models/__init__.py`
  - `backend/services/health_service.py`
  - `backend/services/__init__.py`
  - `bot/handlers/single_message_parts/health.py`
  - `bot/handlers/single_message_parts/common.py`
  - `bot/handlers/single_message_parts/calendar.py`
  - `bot/handlers/single_message_parts/core.py`
  - `bot/states/states.py`
  - `alembic/versions/20260306_000008_add_medication_courses_and_schedule_status.py`
  - `tests/test_core_logic.py`
  - `tests/test_health_helpers.py`
  - `README.md`## 2026-03-06 Health Module Refactor

- Split the oversized Telegram health handler into logical modules under `bot/handlers/single_message_parts/health_parts/`:
  - `builders.py`
  - `state.py`
  - `water.py`
  - `sleep.py`
  - `medications.py`
  - `workouts.py`
  - `modes.py`
- `bot/handlers/single_message_parts/health.py` is now a thin compatibility wrapper that re-exports the public helpers and constants used elsewhere in the bot.
- Split the oversized backend health service into domain modules under `backend/services/health_parts/`:
  - `hydration.py`
  - `sleep.py`
  - `workout.py`
  - `medication.py`
- `backend/services/health_service.py` is now a thin compatibility wrapper that re-exports the existing public API, so external imports did not need to change.
- The goal of this refactor was structural only:
  - reduce file size,
  - make each health subdomain easier to navigate,
  - keep runtime behavior and import paths compatible.
- Validation after refactor:
  - `python -m compileall bot backend alembic tests` passed,
  - `\.venv\Scripts\python.exe -m unittest discover -s tests -v` passed.
## 2026-03-06 Common And Core Refactor

- Split the oversized `bot/handlers/single_message_parts/common.py` into logical modules under `bot/handlers/single_message_parts/common_parts/`:
  - `constants.py`
  - `helpers.py`
  - `data.py`
  - `chat_ui.py`
  - `dashboard.py`
- `bot/handlers/single_message_parts/common.py` is now a thin compatibility wrapper that re-exports the existing constants, helpers, chat UI functions, and dashboard functions used by other handlers and tests.
- Split the oversized `bot/handlers/single_message_parts/core.py` into logical modules under `bot/handlers/single_message_parts/core_parts/`:
  - `builders.py`
  - `handlers.py`
- `bot/handlers/single_message_parts/core.py` is now a thin compatibility wrapper that re-exports screen builders and flow helpers while loading handler registrations for router side effects.
- The refactor goal was structural only:
  - reduce navigation cost inside the bot UI layer,
  - isolate pure text/keyboard builders from Telegram handler wiring,
  - preserve external import paths so the rest of the bot did not need bulk edits.
- Validation after refactor:
  - `python -m compileall bot backend alembic tests` passed,
  - `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` passed.

## 2026-03-06 Calendar And Diary Refactor

- Split `bot/handlers/single_message_parts/calendar.py` into `bot/handlers/single_message_parts/calendar_parts/`:
  - `builders.py`
  - `handlers.py`
- Split `bot/handlers/single_message_parts/diary.py` into `bot/handlers/single_message_parts/diary_parts/`:
  - `builders.py`
  - `handlers.py`
- `calendar.py` and `diary.py` are now thin compatibility wrappers that preserve the existing builder imports used by the shared dashboard renderer while loading Telegram handler registrations for router side effects.
- The goal of this refactor was structural only:
  - make the UI layer consistent with `health_parts`, `common_parts`, and `core_parts`,
  - separate text/keyboard builders from callback and message handlers,
  - keep public imports stable.
- Validation after refactor:
  - `python -m compileall bot backend alembic tests` passed,
  - `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` passed.

## 2026-03-06 Tasks Refactor

- Split `bot/handlers/single_message_parts/tasks.py` into `bot/handlers/single_message_parts/tasks_parts/`:
  - `builders.py`
  - `handlers.py`
- `tasks.py` is now a thin compatibility wrapper that preserves the existing task builder imports used by the shared dashboard renderer and re-exports `_finalize_task` for calendar-driven task creation.
- The goal of this refactor was structural only:
  - align tasks with the same handler/module layout already used for `health`, `calendar`, and `diary`,
  - separate task keyboard/text builders from Telegram callback/message handlers,
  - preserve public imports and existing cross-module usage.
- Validation after refactor:
  - `python -m compileall bot backend alembic tests` passed,
  - `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` passed.

## 2026-03-06 Single Message Package Export Cleanup

- Tightened `bot/handlers/single_message_parts/__init__.py` so the package still exposes only `router`, while submodules are imported under private aliases only for handler-registration side effects.
- Added explicit `__all__` declarations to wrapper modules:
  - `calendar.py`
  - `diary.py`
  - `tasks.py`
  - `core.py`
- This removed implicit wrapper re-exports and made the public surface of the single-message package more explicit after the refactor wave.
- Validation after cleanup:
  - `python -m compileall bot backend alembic tests` passed,
  - `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v` passed.

## 2026-03-06 Health UI Cleanup

- Removed the `Лекарства` button from the top `День / Неделя` mode switch in the health screen.
- Kept medications as a separate action entry in the health action area instead of mixing it into summary-mode tabs.
- Made action rows more explicit in the daily summary:
  - `Добавить сон` + `↩️ Сон`
  - `Добавить тренировку` + `↩️ Тренировка`
- Unified cancel/back labels inside health flows:
  - `↩️ Отмена` for flow entry cancellation,
  - `↩️ Назад` for step-back navigation.
- Added a dedicated `↩️ Назад` button inside the medications window.
- Added summary-mode memory for health navigation:
  - when leaving summary to medications and then returning, the bot now goes back to the previously selected `День` or `Неделя` tab.
- Preserved separate medication calendar behavior:
  - back from medication calendar returns to the medications window,
  - back from the medications window returns to the previous summary tab.
- Validation after cleanup:
  - `python -m compileall bot backend alembic tests` passed,
  - `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v` passed.

## 2026-03-06 Tasks Button Order Cleanup

- Moved the `➕ Задача` button to the bottom of the tasks inline keyboard.
- The tasks screen now shows existing tasks first and keeps creation as the last action in the list.
- Validation after cleanup:
  - `python -m compileall bot backend alembic tests` passed.

## 2026-03-06 Home Screen Refresh

- Reworked the main dashboard text into clearer vertical blocks:
  - header,
  - today summary,
  - progress bars,
  - focus of the day,
  - world/context block,
  - companion hint,
  - quick actions marker.
- Added a compact focus list for up to 3 open tasks with priority markers.
- Moved water progress on the home screen from `steps/5` to a percent label based on the user's configured daily target.
- Kept the existing main actions unchanged, but made the home text easier to scan top-to-bottom.
- Validation after refresh:
  - `python -m compileall bot/handlers/single_message_parts/core_parts bot/handlers/single_message_parts/core.py` passed.

## 2026-03-06 Health Undo Button Simplification

- Simplified health-tab cancel/back/undo buttons to icon-only `↩️` labels.
- Applied only inside the `Здоровье` inline keyboards, without changing the underlying actions.
- Validation after cleanup:
  - `python -m compileall bot/handlers/single_message_parts/health_parts bot/handlers/single_message_parts/health.py` passed.

## 2026-03-06 Home Quick Actions Label Removal

- Removed the `Быстрые действия` text label from the main screen.
- The main dashboard now goes directly from the companion block to the inline action buttons.
- Validation after cleanup:
  - `python -m compileall bot/handlers/single_message_parts/core_parts bot/handlers/single_message_parts/core.py` passed.

## 2026-03-06 Separate Water Tab

- Added a dedicated `Вода` dashboard view and chat navigation button `💧 Вода`.
- Moved focused hydration actions into the separate water screen:
  - quick add buttons `150 / 250 / 500 мл`,
  - undo last entry,
  - exact amount entry in ml.
- Added a new FSM state `waiting_water_amount_text` for exact water input.
- Wired dashboard rendering so the water screen has its own text/keyboard and exact-input mode.
- Removed water action buttons from the health summary keyboard to keep `Здоровье` focused on sleep, workouts, and medications.
- Fixed water callback routing so the same `water:*` callbacks now preserve the current screen:
  - from `Главная` they return to `Главная`,
  - from `Вода` they stay in `Вода`,
  - from `Здоровье` they still return to the health summary mode.
- Removed duplicate `/water` command registration from the standalone water module and kept command navigation centralized in `core`.
- Validation after adding the separate water tab:
  - `python -m compileall bot backend alembic tests` passed,
  - `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v` passed.

## 2026-03-06 Persistent Single-Message Dashboard

- Fixed the main reason dashboard messages accumulated in chat: the bot previously kept the active dashboard message id only in process memory.
- Added persistent dashboard message references on the `users` table:
  - `dashboard_chat_id`
  - `dashboard_message_id`
- Added migration `20260306_000009_add_dashboard_message_ref.py`.
- Updated dashboard rendering flow so navigation now resolves the target message in this order:
  - FSM state data,
  - in-memory cache,
  - persisted user record in the database.
- When a dashboard message is created or edited successfully, the bot now stores the message reference back into state and the database.
- `_reset_context(...)` now preserves the dashboard message reference across view/state resets.
- This makes the single-message UI stable across normal navigation and bot restarts instead of spawning a new dashboard message each time the in-memory pointer is lost.
- Telegram limitation still remains for the persistent chat keyboard carrier message: the reply keyboard still requires its own service message in chat.
- Validation after persistence fix:
  - `python -m compileall bot backend alembic tests` passed,
  - `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v` passed,
  - `.\\.venv\\Scripts\\python.exe -m alembic upgrade head` applied `20260306_000009`.

## 2026-03-06 Water Navigation Adjustment

- Removed `💧 Вода` from the persistent chat keyboard so hydration is no longer a top-level chat section.
- Added a dedicated `💧 Вода` entry back into the health screen action area next to medications.
- Added explicit `⬅️ Назад` navigation inside the water screen.
- Fixed the ambiguity in the water screen controls:
  - `↩️ Отмена` now clearly stays as water undo,
  - `⬅️ Назад` now returns to the originating screen, which is `Здоровье` for the health entry flow.
- Preserved exact ml entry flow and kept `↩️ Назад` from custom water input returning to the main water screen.
- Validation after the navigation adjustment:
  - `python -m compileall bot backend alembic tests` passed,
  - `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v` passed.

## 2026-03-07 Dashboard Duplicate Message Fix

- Root cause of repeated dashboard messages was narrowed down to `_upsert_dashboard_message(...)`.
- Before the fix, if Telegram returned `message is not modified` on `edit_message_text`, the bot treated it like a generic edit failure and sent a brand-new dashboard message with `answer(...)`.
- Added `_is_message_not_modified(...)` helper and aligned message-path behavior with callback-path behavior.
- `_upsert_dashboard_message(...)` now treats `message is not modified` as a no-op and keeps the existing dashboard reference instead of creating a duplicate dashboard message.
- Added regression test `tests/test_dashboard_rendering.py` to verify that `message is not modified` does not trigger a new dashboard message.
- Validation after the fix:
  - `python -m compileall bot backend alembic tests` passed,
  - `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v` passed with 20 tests.

## 2026-03-07 Chat Menu Navigation Hardening

- Refactored reply-keyboard chat navigation to use the same shared `_render_command_view(...)` path as slash commands.
- Before the change, chat-menu navigation used its own duplicated flow in `msg_chat_navigation(...)`.
- Now chat buttons and slash commands go through one rendering path, which reduces divergence and makes menu behavior deterministic.
- Added support in `_render_command_view(...)` for `delete_source_message=True`, so chat-button messages can still be removed without duplicating navigation logic.
- Added regression test `test_chat_navigation_uses_shared_render_command_view` to verify that pressing a chat-menu button dispatches through the shared command-view renderer.
- Validation after the navigation hardening:
  - `python -m compileall bot backend alembic tests` passed,
  - `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v` passed with 21 tests.

## 2026-03-07 Chat Menu Dashboard Relocation

- Diagnosed the remaining UX issue with reply-keyboard chat buttons: the handlers were working, but they could edit an old dashboard message far above in chat, while the user only saw the persistent `Меню` carrier message near the bottom.
- Added `_relocate_dashboard_message(...)` and `_clear_dashboard_ref(...)` to explicitly drop the old dashboard pointer and remove the previous dashboard message before rendering a fresh one near the current interaction point.
- Extended `_render_command_view(...)` with:
  - `force_keyboard`
  - `relocate_dashboard`
  - preserved `delete_source_message`
- Reply-keyboard navigation now uses:
  - `force_keyboard=False`
  - `relocate_dashboard=True`
  - `delete_source_message=True`
- This keeps the persistent chat keyboard intact, removes the stale off-screen dashboard, and renders the active dashboard near the latest interaction so the user can actually see the opened section.
- Updated the navigation regression test to cover the new relocation behavior.
- Validation after the relocation fix:
  - `python -m compileall bot backend alembic tests` passed,
  - `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v` passed with 21 tests.

## 2026-03-07 Start Flow Relocation Fix

- Fixed the `/start` and onboarding flows after chat history deletion.
- Root issue: the reply-keyboard carrier message `Меню` was sent near the bottom, but `/start` could still try to reuse or leave the dashboard pointer without relocating the actual dashboard message to the current point in chat.
- Updated `/start` so it now calls `_relocate_dashboard_message(...)` before rendering the main screen.
- Updated the name-onboarding start flow to do the same, so first-run users also get the visible profile/onboarding screen under the current chat position.
- Added regression test `test_cmd_start_relocates_dashboard_before_render`.
- Validation after the start-flow fix:
  - `python -m compileall bot backend alembic tests` passed,
  - `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v` passed with 22 tests.

## 2026-03-07 Reply Keyboard Reset After Chat History Deletion

- Added `_reset_chat_ui_state(chat_id)` to clear cached per-chat UI state:
  - reply-keyboard carrier message id,
  - configured reply-keyboard chats,
  - configured Web App menu chats,
  - cleared-command chats.
- `/start` now resets the cached chat UI state before re-publishing the reply keyboard and rendering the main dashboard.
- The first-run onboarding flow does the same, so a fresh chat with no history also gets a reattached reply keyboard reliably.
- This improves recovery after Telegram chat history deletion, where the client removes the reply keyboard together with the deleted messages.
- Limitation remains on the Telegram side: the bot cannot keep reply-keyboard buttons visible in a completely empty chat without sending a new message first.
- Validation after the reset fix:
  - `python -m compileall bot backend alembic tests` passed,
  - `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v` passed with 22 tests.
## 2026-03-07 Telegram UI Stabilization Sprint

- Removed stale top-level chat navigation for the old water button and kept water as an internal health screen only.
- Added structured Telegram UI lifecycle logging in `bot/handlers/single_message_parts/common_parts/telemetry.py`.
- Logged events now cover chat UI reset/setup, carrier creation/reuse, dashboard ref persist/clear, dashboard relocation, callback edits, message edits, `/start`, onboarding start, and fallback render.
- Hardened reply-keyboard recovery: `_ensure_chat_keyboard(...)` now recreates the carrier message if the chat is marked configured but the in-memory carrier id is missing.
- Expanded regression coverage with `tests/test_chat_ui.py` and additional lifecycle tests in `tests/test_dashboard_rendering.py`.
- README synced with the real codebase state, including migration `20260306_000009_add_dashboard_message_ref`, implemented medications, and reply-keyboard recovery limitations.
- Validation after the stabilization pass:
  - `python -m compileall bot backend alembic tests` passed,
  - `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v` passed with 27 tests.
