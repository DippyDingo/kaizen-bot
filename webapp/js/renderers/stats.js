import { setText, minutesToLabel, formatMaybeDate, formatPeriodLabel } from "../formatters.js";

export function renderStatsScreen(payload) {
    setText("stats-heading", formatPeriodLabel(payload.period));
    setText("stats-user-value", payload.user.display_name);
    setText("stats-level-value", `${payload.user.level} · ${payload.user.exp}/${payload.user.exp_to_next_level}`);
    setText("stats-streak-value", `${payload.user.current_streak} · рекорд ${payload.user.longest_streak}`);
    setText("stats-period-days-value", String(payload.period_days));

    setText("stats-tasks-completion", `${payload.tasks.done}/${payload.tasks.total} · ${payload.tasks.percent}%`);
    setText("stats-tasks-priority", `🔴 ${payload.tasks.high_count} · 🟡 ${payload.tasks.medium_count} · 🟢 ${payload.tasks.low_count}`);
    setText("stats-tasks-active-days", String(payload.tasks.active_days));

    setText("stats-water-total", `${payload.water.total_ml} мл`);
    setText("stats-water-average", `${payload.water.average_daily_ml} мл/д`);
    setText("stats-water-best", `${payload.water.best_day_ml} мл`);

    setText("stats-sleep-total", minutesToLabel(payload.sleep.total_minutes));
    setText("stats-sleep-average", `${minutesToLabel(payload.sleep.average_daily_minutes)}/д`);
    setText("stats-sleep-quality", payload.sleep.avg_quality ? `${payload.sleep.avg_quality}/5` : "нет данных");

    setText("stats-workout-total", `${payload.workout.total_minutes} мин`);
    setText("stats-workout-sessions", String(payload.workout.sessions_count));
    setText(
        "stats-workout-types",
        `💪 ${payload.workout.by_type.strength.sessions} · 🏃 ${payload.workout.by_type.cardio.sessions} · 🧘 ${payload.workout.by_type.mobility.sessions}`,
    );

    setText("stats-medications-total", String(payload.medications.total_logs));
    setText("stats-medications-taken", `${payload.medications.taken_count} выпито · ${payload.medications.skipped_count} пропусков`);
    setText("stats-medications-top", payload.medications.top_title || "нет данных");

    setText("stats-wellbeing-energy", payload.wellbeing.avg_energy ? `${payload.wellbeing.avg_energy}/5` : "нет данных");
    setText("stats-wellbeing-stress", payload.wellbeing.avg_stress ? `${payload.wellbeing.avg_stress}/5` : "нет данных");
    setText("stats-wellbeing-active-days", String(payload.wellbeing.active_days));

    setText("stats-diary-total", String(payload.diary.total_entries));
    setText("stats-diary-active-days", String(payload.diary.active_days));
    setText("stats-diary-best-day", String(payload.diary.best_day_entries));
    setText("stats-created-at", formatMaybeDate(payload.user.created_at));
}
