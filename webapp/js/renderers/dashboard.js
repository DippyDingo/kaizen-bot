import { $, setProgress, setText, minutesToLabel } from "../formatters.js";

function renderFocusTasks(tasks) {
    const focusList = $("dashboard-focus-list");
    focusList.innerHTML = "";

    if (!tasks.length) {
        const item = document.createElement("li");
        item.className = "focus-empty";
        item.textContent = "Нет открытых задач на выбранную дату.";
        focusList.appendChild(item);
        return;
    }

    for (const task of tasks) {
        const item = document.createElement("li");
        const copy = document.createElement("div");
        copy.className = "focus-copy";
        const title = document.createElement("strong");
        title.textContent = task.title;
        const meta = document.createElement("span");
        meta.className = "focus-meta";
        meta.textContent = task.task_date;
        copy.append(title, meta);

        const priority = document.createElement("span");
        priority.className = "focus-priority";
        priority.textContent = task.priority;

        item.append(copy, priority);
        focusList.appendChild(item);
    }
}

export function renderDashboardScreen(payload) {
    setText("dashboard-tasks-value", `${payload.summary.tasks.done}/${payload.summary.tasks.total}`);
    setText("dashboard-tasks-subvalue", `${payload.summary.tasks.open} открыто`);
    setText("dashboard-water-value", `${payload.summary.water.total_ml} мл`);
    setText("dashboard-water-subvalue", `цель ${payload.summary.water.target_ml} мл`);
    setText("dashboard-sleep-value", minutesToLabel(payload.summary.sleep.total_minutes));
    setText("dashboard-sleep-subvalue", `цель ${minutesToLabel(payload.summary.sleep.target_minutes)}`);
    setText("dashboard-diary-value", String(payload.summary.diary.entries));
    setText("dashboard-diary-subvalue", "записей сегодня");

    setText("dashboard-progress-tasks-value", `${payload.progress.tasks_percent}%`);
    setText("dashboard-progress-water-value", `${payload.progress.water_percent}%`);
    setText("dashboard-progress-sleep-value", `${payload.progress.sleep_percent}%`);

    setProgress("dashboard-progress-tasks-bar", payload.progress.tasks_percent);
    setProgress("dashboard-progress-water-bar", payload.progress.water_percent);
    setProgress("dashboard-progress-sleep-bar", payload.progress.sleep_percent);

    renderFocusTasks(payload.focus_tasks || []);
}
