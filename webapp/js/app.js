import { ApiError, bootstrapTelegramWebApp, createApiClient } from "./api.js";
import { $, formatDateLabel, formatPeriodLabel, getTodayIsoDate, setText, shiftIsoDate } from "./formatters.js";
import { renderDashboardScreen } from "./renderers/dashboard.js";
import { renderHealthScreen } from "./renderers/health.js";
import { renderStatsScreen } from "./renderers/stats.js";

const SCREEN_TITLES = {
    dashboard: {
        title: "Дашборд",
        subtitle: "Сводка на выбранную дату: задачи, вода, сон и дневник.",
    },
    health: {
        title: "Здоровье",
        subtitle: "Дневные и недельные агрегаты по воде, сну, тренировкам, лекарствам и состоянию.",
    },
    stats: {
        title: "Статистика",
        subtitle: "Периодический read-only срез по текущему API без write-операций.",
    },
};

const appState = {
    activeScreen: "dashboard",
    selectedDate: getTodayIsoDate(),
    statsPeriod: "7d",
    cache: new Map(),
    api: null,
    initData: "",
};

function cacheKey(screen) {
    return `${screen}:${appState.selectedDate}:${screen === "stats" ? appState.statsPeriod : "-"}`;
}

function shiftSelectedDate(diffDays) {
    appState.selectedDate = shiftIsoDate(appState.selectedDate, diffDays);
}

function setStatus(message, kind = "info", { visible = true } = {}) {
    const card = $("status-card");
    const body = $("status-message");
    body.textContent = message;
    card.className = "card status-card";
    if (!visible) {
        card.classList.add("status-card-hidden");
        return;
    }
    card.classList.add(`status-card-${kind}`);
}

function syncShell() {
    const title = SCREEN_TITLES[appState.activeScreen];
    setText("hero-title", title.title);
    setText("hero-subtitle", title.subtitle);
    setText("selected-date", formatDateLabel(appState.selectedDate));

    for (const button of document.querySelectorAll(".screen-tab")) {
        button.classList.toggle("screen-tab-active", button.dataset.screen === appState.activeScreen);
    }

    for (const panel of document.querySelectorAll(".screen-panel")) {
        panel.classList.toggle("screen-panel-active", panel.dataset.screenPanel === appState.activeScreen);
    }

    const periodControls = $("stats-period-controls");
    periodControls.classList.toggle("period-switcher-hidden", appState.activeScreen !== "stats");

    for (const button of document.querySelectorAll(".period-pill")) {
        button.classList.toggle("period-pill-active", button.dataset.period === appState.statsPeriod);
    }
}

async function loadScreenData(screen, { force = false } = {}) {
    const key = cacheKey(screen);
    if (!force && appState.cache.has(key)) {
        return appState.cache.get(key);
    }

    let payload;
    if (screen === "dashboard") {
        payload = await appState.api.loadDashboard(appState.selectedDate);
    } else if (screen === "health") {
        payload = await appState.api.loadHealth(appState.selectedDate);
    } else {
        payload = await appState.api.loadStats(appState.selectedDate, appState.statsPeriod);
    }

    appState.cache.set(key, payload);
    return payload;
}

function renderLoadedScreen(screen, payload) {
    if (screen === "dashboard") {
        renderDashboardScreen(payload);
        return;
    }
    if (screen === "health") {
        renderHealthScreen(payload);
        return;
    }
    renderStatsScreen(payload);
}

function describeError(error) {
    if (!(error instanceof ApiError)) {
        return {
            kind: "error",
            message: error?.message || "Не удалось загрузить экран.",
        };
    }

    if (error.kind === "auth_missing") {
        return {
            kind: "warning",
            message: "Открой Web App через Telegram, чтобы передать initData.",
        };
    }
    if (error.kind === "unauthorized") {
        return {
            kind: "error",
            message: "Telegram auth не прошел. Открой экран заново из бота.",
        };
    }
    if (error.kind === "not_found") {
        return {
            kind: "warning",
            message: "Пользователь еще не зарегистрирован в боте. Сначала открой /start в Telegram.",
        };
    }
    if (error.kind === "invalid_query") {
        return {
            kind: "error",
            message: `Некорректные параметры запроса: ${error.detail}`,
        };
    }
    if (error.kind === "network") {
        return {
            kind: "error",
            message: "Нет соединения с API. Проверь, что процесс backend.api.main запущен.",
        };
    }
    return {
        kind: "error",
        message: `Ошибка API: ${error.detail}`,
    };
}

async function renderActiveScreen({ force = false } = {}) {
    syncShell();
    setStatus(`Загружаю экран «${SCREEN_TITLES[appState.activeScreen].title}»…`, "info");

    try {
        const payload = await loadScreenData(appState.activeScreen, { force });
        renderLoadedScreen(appState.activeScreen, payload);
        const suffix = appState.activeScreen === "stats" ? ` · период ${formatPeriodLabel(appState.statsPeriod)}` : "";
        setStatus(`Данные обновлены: ${formatDateLabel(appState.selectedDate)}${suffix}`, "success");
    } catch (error) {
        const details = describeError(error);
        setStatus(details.message, details.kind);
    }
}

function bindEvents() {
    $("refresh-button").addEventListener("click", () => {
        appState.cache.delete(cacheKey(appState.activeScreen));
        renderActiveScreen({ force: true });
    });

    $("date-prev").addEventListener("click", () => {
        shiftSelectedDate(-1);
        renderActiveScreen();
    });

    $("date-next").addEventListener("click", () => {
        shiftSelectedDate(1);
        renderActiveScreen();
    });

    for (const button of document.querySelectorAll(".screen-tab")) {
        button.addEventListener("click", () => {
            appState.activeScreen = button.dataset.screen;
            renderActiveScreen();
        });
    }

    for (const button of document.querySelectorAll(".period-pill")) {
        button.addEventListener("click", () => {
            if (appState.statsPeriod === button.dataset.period) {
                return;
            }
            appState.statsPeriod = button.dataset.period;
            if (appState.activeScreen === "stats") {
                renderActiveScreen();
            } else {
                syncShell();
            }
        });
    }
}

function bootstrap() {
    const context = bootstrapTelegramWebApp();
    appState.api = createApiClient();
    appState.initData = context.initData;
    bindEvents();

    if (!appState.initData) {
        syncShell();
        setStatus("Этот экран работает только внутри Telegram Mini App. Открой Web App из бота.", "warning");
        setText("hero-title", "Нет Telegram auth");
        setText("hero-subtitle", "API требует X-Telegram-Init-Data, поэтому в обычном браузере данные не загрузятся.");
        return;
    }

    renderActiveScreen();
}

bootstrap();


