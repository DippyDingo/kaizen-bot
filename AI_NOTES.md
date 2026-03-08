# AI_NOTES.md

Дата обновления: 2026-03-08
Статус: актуализировано по текущему состоянию репозитория

## Правила ведения

- Не оставлять заглушки без явного `TODO` с обоснованием.
- Не дублировать код: предпочитать переиспользование и четкие абстракции.
- Не делать скрытых допущений: при реальной неопределенности сначала уточнять.
- После каждого значимого изменения обновлять этот файл по шаблону ниже.
- Все записи в этом файле вести на русском языке.

## Текущее состояние проекта

### Telegram-бот

- Основной интерфейс работает как `single-message dashboard`.
- Основные разделы:
  - `Главная`
  - `Задачи`
  - `Календарь`
  - `Дневник`
  - `Здоровье`
  - `Статистика`
  - `Настройки / Профиль`
- Глобальная навигация идет через быстрые кнопки у поля ввода.
- Нижняя системная кнопка Telegram используется под `Web App` с текстом `Open`.
- Ссылка на активный dashboard хранится и в FSM state, и в БД.

### Backend

- Используется async `SQLAlchemy` + `Alembic`.
- Есть read-only `aiohttp` API foundation в `backend/api/`.
- Реализованы read-only endpoint'ы:
  - `GET /api/v1/dashboard`
  - `GET /api/v1/health`
  - `GET /api/v1/stats`

### Web App

- Есть multi-screen read-only Web App shell.
- Экранов сейчас три:
  - `dashboard`
  - `health`
  - `stats`
- Web App использует `X-Telegram-Init-Data` и не имеет dev-обхода по `telegram_id`.

### Здоровье

- Реализованы блоки:
  - вода
  - сон
  - тренировки
  - лекарства
  - состояние (`энергия / стресс`)
- Есть дневные и недельные summary-экраны.
- Есть периодическая статистика по здоровью.

## Последние значимые изменения

### 2026-03-08 — Исправление FSM-регрессии в Telegram UI

Что добавлено / изменено:
- Исправлен дефект, при котором общий `fallback` перехватывал текст раньше FSM-хендлеров.
- Теперь `fallback` работает только при отсутствии активного состояния через `StateFilter(None)`.
- Это возвращает корректную работу ввода для:
  - задач,
  - дневника,
  - лекарств,
  - других текстовых FSM-flow.

Измененные файлы концептуально:
- `bot/handlers/single_message_parts/core_parts/handlers.py`
- `tests/test_core_logic.py`

Ограничения / TODO:
- Нужны дополнительные интеграционные Telegram-flow тесты на ввод в FSM, а не только regression на роутер.

Следующий шаг:
- Расширить покрытие на реальные message-flow сценарии `задача / дневник / лекарства`.

### 2026-03-08 — Возврат к реальному single-message поведению

Что добавлено / изменено:
- Убрано принудительное `relocate_dashboard` при каждом нажатии быстрых кнопок чата.
- Быстрые кнопки теперь должны обновлять текущее dashboard-сообщение, а не плодить новые.
- Исправлен shortcut `➕ Задача` с главной:
  - создание задачи стартует из `Главной`,
  - не происходит лишнего перехода в экран задач,
  - отмена и сохранение возвращают в исходный экран.
- Для task-flow добавлен `task_origin_view`.

Измененные файлы концептуально:
- `bot/handlers/single_message_parts/common_parts/chat_ui.py`
- `bot/handlers/single_message_parts/common_parts/dashboard.py`
- `bot/handlers/single_message_parts/tasks_parts/handlers.py`
- `bot/handlers/single_message_parts/tasks_parts/builders.py`
- `bot/handlers/single_message_parts/tasks.py`
- `tests/test_core_logic.py`

Ограничения / TODO:
- Реальный live-run бота зависит от сетевого доступа к `api.telegram.org`.
- Нужно отдельно вручную проверить, что новые сообщения больше не копятся именно в Telegram-клиенте.

Следующий шаг:
- Пройти ручной smoke-test в Telegram: `Главная -> Задачи -> Главная -> Задачи` без создания новых dashboard-сообщений.

### 2026-03-08 — Упрощение UX лекарств

Что добавлено / изменено:
- Убрана отдельная кнопка `Пропуск`.
- Для приема лекарства оставлена одна кнопка `✅ Выпил`.
- Новая логика статуса:
  - если прием отмечен — `taken`;
  - если не отмечен — по умолчанию считается пропуском.
- Кнопка `Выпил` теперь:
  - красная, если прием не подтвержден,
  - зеленая, если прием подтвержден.
- Повторное нажатие снимает отметку `Выпил` и возвращает прием в состояние пропуска по умолчанию.
- Обновлены:
  - дневной список лекарств,
  - календарные отметки,
  - агрегаты статистики по лекарствам,
  - unit-тесты.

Измененные файлы концептуально:
- `backend/services/health_parts/medication.py`
- `bot/handlers/single_message_parts/health_parts/builders.py`
- `bot/handlers/single_message_parts/health_parts/medications.py`
- `tests/test_health_service_medications.py`
- `tests/test_health_helpers.py`

Ограничения / TODO:
- Новая модель статусов стала двухсостоянийной на уровне UI (`выпил` / `считается пропуском`).
- Если в будущем понадобится явное разделение `не отмечено` и `подтвержденный пропуск`, потребуется вернуть третье состояние осознанно, с отдельным продуктовым решением.

Следующий шаг:
- Проверить в Telegram, что:
  - красная кнопка видна по умолчанию,
  - зеленеет после отметки,
  - при повторном нажатии возвращается в красный режим,
  - статистика и календарь отражают это одинаково.

## Концептуально важные модули

### UI / Telegram
- `bot/handlers/single_message_parts/common_parts/chat_ui.py`
- `bot/handlers/single_message_parts/common_parts/dashboard.py`
- `bot/handlers/single_message_parts/core_parts/handlers.py`
- `bot/handlers/single_message_parts/tasks_parts/handlers.py`
- `bot/handlers/single_message_parts/health_parts/builders.py`
- `bot/handlers/single_message_parts/health_parts/medications.py`

### Backend / сервисы
- `backend/services/health_parts/medication.py`
- `backend/services/health_parts/wellbeing.py`
- `backend/services/task_service.py`
- `backend/services/diary_service.py`
- `backend/services/user_service.py`

### API / Web App
- `backend/api/app.py`
- `backend/api/handlers.py`
- `backend/api/auth.py`
- `webapp/index.html`
- `webapp/js/app.js`
- `webapp/js/api.js`
- `webapp/js/renderers/*`

## Текущие ограничения

- Live-проверка Telegram зависит от доступа к `api.telegram.org`.
- Быстрые кнопки чата (`ReplyKeyboard`) по ограничениям Telegram не появляются сами по себе до первого пользовательского update.
- После удаления истории Telegram удаляет carrier-сообщение клавиатуры; корректное восстановление идет через новый `/start`.
- Web App через временный tunnel подходит только для разработки и ручной проверки.
- В репозитории уже есть незакоммиченные локальные изменения вне этого файла, включая `README.md`.

## Что логично делать дальше

1. Ручной smoke-test в Telegram на последние фиксы:
   - single-message навигация,
   - `➕ Задача` с главной,
   - лекарства с одной кнопкой `Выпил`.
2. После ручной проверки — отдельный commit последних исправлений.
3. Затем добивать либо Telegram UX-тесты, либо следующий продуктовый блок.

## Шаблон для следующих обновлений

```md
## YYYY-MM-DD — Короткое название изменения

Что добавлено / изменено:
- ...
- ...

Измененные файлы концептуально:
- `path/to/file.py`
- `path/to/another_file.py`

Ограничения / TODO:
- ...
- TODO: ... потому что ...

Следующий шаг:
- ...
```
