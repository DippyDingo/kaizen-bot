export class ApiError extends Error {
    constructor(kind, detail, status = 0) {
        super(detail);
        this.name = "ApiError";
        this.kind = kind;
        this.status = status;
        this.detail = detail;
    }
}

function resolveTelegramContext() {
    const webApp = window.Telegram?.WebApp || null;
    const initData = webApp?.initData || "";
    return { webApp, initData };
}

function buildApiError(response, payload) {
    if (response.status === 401) {
        return new ApiError("unauthorized", payload.detail || "Нужен валидный Telegram initData.", response.status);
    }
    if (response.status === 404) {
        return new ApiError("not_found", payload.detail || "Пользователь не найден.", response.status);
    }
    if (response.status === 400) {
        return new ApiError("invalid_query", payload.detail || "Некорректный параметр запроса.", response.status);
    }
    return new ApiError("server", payload.detail || `HTTP ${response.status}`, response.status);
}

async function requestJson(path, initData) {
    if (!initData) {
        throw new ApiError("auth_missing", "Открой Web App из Telegram, чтобы передать initData.", 401);
    }

    let response;
    try {
        response = await fetch(path, {
            headers: {
                "X-Telegram-Init-Data": initData,
            },
        });
    } catch (error) {
        throw new ApiError("network", "Нет соединения с API.", 0);
    }

    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw buildApiError(response, payload);
    }

    return response.json();
}

export function bootstrapTelegramWebApp() {
    const context = resolveTelegramContext();
    if (context.webApp) {
        context.webApp.ready();
        context.webApp.expand();
    }
    return context;
}

export function createApiClient() {
    const { initData } = resolveTelegramContext();

    return {
        initData,
        loadDashboard(selectedDate) {
            return requestJson(`/api/v1/dashboard?date=${encodeURIComponent(selectedDate)}`, initData);
        },
        loadHealth(selectedDate) {
            return requestJson(`/api/v1/health?date=${encodeURIComponent(selectedDate)}`, initData);
        },
        loadStats(selectedDate, period) {
            return requestJson(
                `/api/v1/stats?date=${encodeURIComponent(selectedDate)}&period=${encodeURIComponent(period)}`,
                initData,
            );
        },
    };
}
