const api = {
    dashboard: "/api/v1/dashboard",
    health: "/api/v1/health",
    stats: "/api/v1/stats?period=7d",
};

function $(id) {
    return document.getElementById(id);
}

function minutesToLabel(minutes) {
    const safe = Math.max(0, Number(minutes || 0));
    const hours = Math.floor(safe / 60);
    const rest = safe % 60;
    if (rest === 0) {
        return `${hours} ч`;
    }
    return `${hours} ч ${rest} м`;
}

function setProgress(id, percent) {
    $(id).style.width = `${Math.max(0, Math.min(100, Number(percent || 0)))}%`;
}

function setStatus(message, { visible = true } = {}) {
    const card = $("status-card");
    const body = $("status-message");
    body.textContent = message;
    card.classList.toggle("status-card-hidden", !visible);
}

async function fetchJson(url, initData) {
    const response = await fetch(url, {
        headers: {
            "X-Telegram-Init-Data": initData,
        },
    });

    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        const detail = payload.detail || `HTTP ${response.status}`;
        throw new Error(detail);
    }

    return response.json();
}

function renderDashboard(dashboard) {
    $("hero-title").textContent = `${dashboard.user.display_name}, день под контролем`;
    $("hero-subtitle").textContent = `Уровень ${dashboard.user.level} · EXP ${dashboard.user.exp}/${dashboard.user.exp_to_next_level} · streak ${dashboard.user.current_streak}`;

    $("tasks-value").textContent = `${dashboard.summary.tasks.done}/${dashboard.summary.tasks.total}`;
    $("tasks-subvalue").textContent = `${dashboard.summary.tasks.open} открыто`;
    $("water-value").textContent = `${dashboard.summary.water.total_ml} мл`;
    $("water-subvalue").textContent = `цель ${dashboard.summary.water.target_ml} мл`;
    $("sleep-value").textContent = minutesToLabel(dashboard.summary.sleep.total_minutes);
    $("sleep-subvalue").textContent = `цель ${minutesToLabel(dashboard.summary.sleep.target_minutes)}`;
    $("diary-value").textContent = String(dashboard.summary.diary.entries);
    $("diary-subvalue").textContent = "записей сегодня";

    $("progress-tasks-value").textContent = `${dashboard.progress.tasks_percent}%`;
    $("progress-water-value").textContent = `${dashboard.progress.water_percent}%`;
    $("progress-sleep-value").textContent = `${dashboard.progress.sleep_percent}%`;
    setProgress("progress-tasks-bar", dashboard.progress.tasks_percent);
    setProgress("progress-water-bar", dashboard.progress.water_percent);
    setProgress("progress-sleep-bar", dashboard.progress.sleep_percent);

    const focusList = $("focus-list");
    focusList.innerHTML = "";
    if (!dashboard.focus_tasks.length) {
        focusList.innerHTML = `<li class="focus-empty">Нет открытых задач на выбранную дату.</li>`;
        return;
    }

    for (const task of dashboard.focus_tasks) {
        const item = document.createElement("li");
        item.innerHTML = `
            <div>
                <strong>${task.title}</strong>
            </div>
            <span class="focus-priority">${task.priority}</span>
        `;
        focusList.appendChild(item);
    }
}

function renderHealth(health) {
    $("health-day-water").textContent = `${health.day.water.total_ml}/${health.day.water.target_ml} мл`;
    $("health-day-sleep").textContent = `${minutesToLabel(health.day.sleep.total_minutes)} · качество ${health.day.sleep.avg_quality || 0}`;
    $("health-day-workout").textContent = `${health.day.workout.total_minutes} мин`;
    $("health-day-wellbeing").textContent = health.day.wellbeing.has_entry
        ? `${health.day.wellbeing.energy_level}/5 · стресс ${health.day.wellbeing.stress_level}/5`
        : "нет записи";
    $("health-day-medications").textContent = `${health.day.medications.taken}/${health.day.medications.total} отмечено`;

    $("health-week-water").textContent = `${health.week.water.total_ml} мл · ${health.week.water.active_days} дней`;
    $("health-week-sleep").textContent = `${minutesToLabel(health.week.sleep.total_minutes)} · ср ${health.week.sleep.avg_quality || 0}`;
    $("health-week-workout").textContent = `${health.week.workout.total_minutes} мин · ${health.week.workout.sessions_count} сессий`;
    $("health-week-wellbeing").textContent = `${health.week.wellbeing.avg_energy || 0}/5 · стресс ${health.week.wellbeing.avg_stress || 0}/5`;
    $("health-week-medications").textContent = `${health.week.medications.taken_count}/${health.week.medications.total_logs} выпито`;
}

function renderStats(stats) {
    $("stats-tasks").textContent = `${stats.tasks.done}/${stats.tasks.total} · ${stats.tasks.percent}%`;
    $("stats-water").textContent = `${stats.water.average_daily_ml} мл/д`;
    $("stats-sleep").textContent = `${minutesToLabel(stats.sleep.average_daily_minutes)}/д`;
    $("stats-wellbeing").textContent = `${stats.wellbeing.avg_energy || 0}/5 · ${stats.wellbeing.avg_stress || 0}/5`;
}

async function loadScreen() {
    const webApp = window.Telegram?.WebApp;
    const initData = webApp?.initData;

    if (!initData) {
        setStatus("Этот экран работает только внутри Telegram Web App. Нужен валидный initData.", { visible: true });
        $("hero-title").textContent = "Нет Telegram auth";
        $("hero-subtitle").textContent = "Открой экран через кнопку Web App из бота.";
        return;
    }

    webApp.ready();
    webApp.expand();
    setStatus("Обновляю данные…", { visible: true });

    try {
        const [dashboard, health, stats] = await Promise.all([
            fetchJson(api.dashboard, initData),
            fetchJson(api.health, initData),
            fetchJson(api.stats, initData),
        ]);
        renderDashboard(dashboard);
        renderHealth(health);
        renderStats(stats);
        setStatus(`Данные обновлены на ${new Date().toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}`);
    } catch (error) {
        setStatus(`Не удалось загрузить данные: ${error.message}`, { visible: true });
    }
}

$("refresh-button").addEventListener("click", () => {
    loadScreen();
});

loadScreen();
