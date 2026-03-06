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
  - `💧 Вода`
- Home inline keyboard now keeps only local quick actions:
  - add water,
  - undo water,
  - add task,
  - add diary entry.
- The bot sends one short keyboard-carrier message (`🧭 Меню`) per chat to keep the `ReplyKeyboard` visible.
- Presses on quick chat buttons are handled before FSM text input and the pressed text message is deleted, so navigation does not pollute the chat history.
- Files updated:
  - `bot/handlers/single_message_parts/common.py`
  - `bot/handlers/single_message_parts/core.py`
